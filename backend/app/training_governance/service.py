from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.schemas import UserContext
from app.auth.service import record_audit_event
from app.jobs.control_service import submit_job
from app.jobs.schemas import JobSubmissionRequest
from app.models.artifact import ArtifactModel
from app.models.job import JobModel
from app.models.training_governance import TrainingDatasetEntryModel, TrainingDatasetManifestModel, TrainingRunModel
from app.training_governance.catalog import (
    COMPUTE_PROFILE_ID,
    DATASET_KEY,
    compute_profile,
    dataset_manifest_snapshot,
    require_checked_in_dataset,
    training_recipe,
)
from app.training_governance.schemas import (
    TrainingArtifactResponse,
    TrainingGovernanceResponse,
    TrainingManifestResponse,
    TrainingRunResponse,
)


def seal_checked_in_manifest(db: Session, actor: UserContext, *, dataset_key: str | None = None) -> TrainingDatasetManifestModel:
    """Seal one code-owned synthetic manifest; unknown sources never enter the database."""

    if not actor.is_admin:
        raise HTTPException(status_code=403, detail="Platform administrator role required")
    require_checked_in_dataset(dataset_key)
    snapshot = dataset_manifest_snapshot()
    existing = db.execute(
        select(TrainingDatasetManifestModel)
        .where(TrainingDatasetManifestModel.purpose == snapshot["purpose"])
        .where(TrainingDatasetManifestModel.dataset_version == snapshot["dataset_version"])
        .with_for_update()
    ).scalars().one_or_none()
    if existing is not None:
        if existing.manifest_checksum != snapshot["manifest_checksum"]:
            raise HTTPException(status_code=409, detail="The sealed dataset version does not match the server-owned manifest.")
        return existing
    now = datetime.now(UTC)
    manifest = TrainingDatasetManifestModel(
        id=f"trainset_{uuid4().hex[:20]}",
        purpose=str(snapshot["purpose"]),
        source_type=str(snapshot["source_type"]),
        dataset_version=str(snapshot["dataset_version"]),
        schema_version=str(snapshot["schema_version"]),
        content_checksum=str(snapshot["content_checksum"]),
        manifest_checksum=str(snapshot["manifest_checksum"]),
        held_out_evaluation_checksum=str(snapshot["held_out_evaluation_checksum"]),
        split_policy_version=str(snapshot["split_policy_version"]),
        eligibility_policy_version=str(snapshot["eligibility_policy_version"]),
        eligibility_result=str(snapshot["eligibility_result"]),
        lifecycle_state=str(snapshot["lifecycle_state"]),
        entry_count=int(snapshot["entry_count"]),
        train_count=int(snapshot["train_count"]),
        validation_count=int(snapshot["validation_count"]),
        test_count=int(snapshot["test_count"]),
        created_by_user_id=actor.id,
        created_at=now,
    )
    try:
        # First-use races are expected in PostgreSQL. The unique immutable identity
        # resolves the race; the savepoint leaves the surrounding job transaction
        # usable for the loser to read the sealed winner.
        with db.begin_nested():
            db.add(manifest)
            db.flush()
            for entry in snapshot["entries"]:
                if not isinstance(entry, dict):
                    raise RuntimeError("The checked-in synthetic training fixture is invalid.")
                db.add(
                    TrainingDatasetEntryModel(
                        id=f"trainentry_{uuid4().hex[:20]}",
                        manifest_id=manifest.id,
                        entry_key=str(entry["entry_key"]),
                        split=str(entry["split"]),
                        source_class=str(entry["source_class"]),
                        source_reference=str(entry["source_reference"]),
                        input_text=str(entry["input_text"]),
                        target_text=str(entry["target_text"]),
                        content_checksum=str(entry["content_checksum"]),
                        input_checksum=str(entry["input_checksum"]),
                        target_checksum=str(entry["target_checksum"]),
                        normalized_content_checksum=str(entry["normalized_content_checksum"]),
                        created_at=now,
                    )
                )
            db.flush()
        return manifest
    except IntegrityError:
        existing = db.execute(
            select(TrainingDatasetManifestModel)
            .where(TrainingDatasetManifestModel.purpose == snapshot["purpose"])
            .where(TrainingDatasetManifestModel.dataset_version == snapshot["dataset_version"])
            .with_for_update()
        ).scalars().one_or_none()
        if existing is None or existing.manifest_checksum != snapshot["manifest_checksum"]:
            raise HTTPException(status_code=409, detail="The sealed dataset version could not be verified.") from None
        return existing


def submit_training_run(
    db: Session,
    actor: UserContext,
    *,
    dataset_key: str | None,
    execution_mode: str,
    idempotency_key: str,
) -> tuple[TrainingRunModel, bool]:
    if not actor.is_admin:
        raise HTTPException(status_code=403, detail="Platform administrator role required")
    if execution_mode not in {"dry_run", "local_fake"}:
        raise HTTPException(status_code=422, detail="Training execution mode is invalid.")
    manifest = seal_checked_in_manifest(db, actor, dataset_key=dataset_key)
    existing_job = db.execute(
        select(JobModel)
        .where(JobModel.idempotency_subject_type == "user")
        .where(JobModel.idempotency_subject_id == actor.id)
        .where(JobModel.job_type == "model.training.prepare")
        .where(JobModel.idempotency_key == idempotency_key)
    ).scalars().one_or_none()
    if existing_job is not None:
        existing_run = db.execute(
            select(TrainingRunModel).where(TrainingRunModel.job_id == existing_job.id)
        ).scalars().one_or_none()
        if existing_run is None:
            raise HTTPException(status_code=409, detail="The idempotent training run is incomplete.")
        return existing_run, True
    recipe = training_recipe()
    profile = compute_profile()
    if profile["compute_profile_id"] != COMPUTE_PROFILE_ID or profile["execution_mode"] != "local_fake":
        raise RuntimeError("The code-owned local compute profile is invalid.")
    run_id = f"trainrun_{uuid4().hex[:20]}"
    execution_snapshot = {
        "schema_version": "training.execution.v1",
        "dataset": {
            "manifest_id": manifest.id,
            "manifest_checksum": manifest.manifest_checksum,
            "dataset_version": manifest.dataset_version,
            "content_checksum": manifest.content_checksum,
            "split_policy_version": manifest.split_policy_version,
            "train_count": manifest.train_count,
            "validation_count": manifest.validation_count,
            "test_count": manifest.test_count,
            "held_out_evaluation_checksum": manifest.held_out_evaluation_checksum,
        },
        "recipe": recipe,
        "compute_profile": profile,
        "environment": "local_fake_controlled_v1",
        "expected_artifact_types": ["training_model_card", "training_execution_receipt"],
        "execution_mode": execution_mode,
        "candidate_class": "not_registry_eligible",
        "real_training_occurred": False,
        "provider_session": "not_applicable",
        "credential_source": "not_applicable",
    }

    def add_run(job: JobModel) -> None:
        db.add(
            TrainingRunModel(
                id=run_id,
                job_id=job.id,
                manifest_id=manifest.id,
                manifest_checksum=manifest.manifest_checksum,
                recipe_key=str(recipe["recipe_key"]),
                recipe_version=str(recipe["recipe_version"]),
                recipe_checksum=str(recipe["recipe_checksum"]),
                base_model_identity=str(profile["base_model_identity"]),
                compute_profile_id=str(profile["compute_profile_id"]),
                compute_profile_version=str(profile["compute_profile_version"]),
                compute_profile_checksum=str(profile["compute_profile_checksum"]),
                execution_mode=execution_mode,
                execution_snapshot=execution_snapshot,
                status="queued",
                cleanup_state="not_required",
                candidate_class="not_registry_eligible",
                real_training_occurred=False,
                estimated_cost_microusd=0,
                actual_cost_microusd=0,
                created_by_user_id=actor.id,
                created_at=datetime.now(UTC),
            )
        )

    job, idempotent = submit_job(
        db,
        actor,
        JobSubmissionRequest(
            job_type="model.training.prepare",
            input_schema_version="model.training.prepare.v1",
            input_json={"training_run_id": run_id},
        ),
        idempotency_key,
        allow_training_governance=True,
        before_commit=add_run,
        extra_server_context={"training_run_id": run_id, "training_execution_snapshot": execution_snapshot},
    )
    if idempotent:
        run = db.execute(select(TrainingRunModel).where(TrainingRunModel.job_id == job.id)).scalars().one_or_none()
        if run is None:
            raise HTTPException(status_code=409, detail="The idempotent training run is incomplete.")
        return run, True
    run = db.get(TrainingRunModel, run_id)
    if run is None:
        raise HTTPException(status_code=409, detail="The training run was not persisted.")
    record_audit_event(
        db,
        actor.id,
        "training_run.submitted",
        "training_run",
        run.id,
        {"job_id": job.id, "manifest_checksum": run.manifest_checksum, "execution_mode": run.execution_mode},
    )
    return run, False


def mark_training_run_started(db: Session, job: JobModel) -> None:
    run = _run_for_job(db, job, lock=True)
    if run.status == "queued":
        run.status = "running"
        run.started_at = datetime.now(UTC)


def mark_training_run_queued_for_retry(db: Session, job: JobModel) -> None:
    if job.job_type != "model.training.prepare":
        return
    run = _run_for_job(db, job, lock=True, required=False)
    if run is not None and run.status == "running":
        run.status = "queued"


def finalize_training_run(db: Session, job: JobModel, worker_result: dict) -> dict[str, object]:
    run = _run_for_job(db, job, lock=True)
    if run.status == "completed":
        return _job_summary(run, _artifacts_for_run(db, run.id))
    expected = local_fake_result(run)
    if worker_result != expected:
        raise HTTPException(status_code=422, detail="Training worker result does not match the server-owned execution snapshot.")
    for artifact_type, payload in _artifact_payloads(run).items():
        existing = db.execute(
            select(ArtifactModel)
            .where(ArtifactModel.job_id == job.id)
            .where(ArtifactModel.artifact_type == artifact_type)
            .with_for_update()
        ).scalars().one_or_none()
        if existing is None:
            existing = ArtifactModel(
                id=f"artifact_{uuid4().hex[:20]}",
                job_id=job.id,
                artifact_type=artifact_type,
                status="available",
                owner_user_id=job.owner_user_id,
                organization_id=None,
                visibility="private",
                resource_type="training_run",
                resource_id=run.id,
                storage_backend="database",
                storage_key=f"training-governance/{run.id}/{artifact_type}.json",
                content_type="application/json",
                size_bytes=len(payload),
                checksum=_sha256_bytes(payload),
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            db.add(existing)
        elif existing.checksum != _sha256_bytes(payload) or existing.size_bytes != len(payload):
            raise HTTPException(status_code=409, detail="Training artifact integrity conflict.")
    run.status = "completed"
    run.cleanup_state = "completed"
    run.result_code = "local_fake_completed"
    run.actual_cost_microusd = 0
    run.completed_at = datetime.now(UTC)
    run.result_json = _artifact_documents(run)
    db.flush()
    return _job_summary(run, _artifacts_for_run(db, run.id, include_pending=True))


def mark_training_run_terminal(db: Session, job: JobModel, *, status: str, result_code: str) -> None:
    if job.job_type != "model.training.prepare":
        return
    run = _run_for_job(db, job, lock=True, required=False)
    if run is None or run.status == "completed":
        return
    if status not in {"failed", "cancelled"}:
        raise ValueError("Training terminal state is invalid.")
    run.status = status
    run.cleanup_state = "completed"
    run.result_code = result_code[:64]
    run.completed_at = datetime.now(UTC)


def governance_snapshot(db: Session) -> TrainingGovernanceResponse:
    manifests = db.execute(select(TrainingDatasetManifestModel).order_by(TrainingDatasetManifestModel.created_at.desc())).scalars().all()
    runs = db.execute(select(TrainingRunModel).order_by(TrainingRunModel.created_at.desc()).limit(100)).scalars().all()
    return TrainingGovernanceResponse(
        manifests=[manifest_response(manifest) for manifest in manifests],
        runs=[run_response(db, run) for run in runs],
        compute_profile=compute_profile(),
        recipe=training_recipe(),
    )


def dispose_training_governance_for_account(db: Session, user_id: str) -> dict[str, int]:
    """Detach a deleted actor without deleting shared sealed manifests or run evidence."""

    manifests = db.execute(
        select(TrainingDatasetManifestModel)
        .where(TrainingDatasetManifestModel.created_by_user_id == user_id)
        .with_for_update()
    ).scalars().all()
    runs = db.execute(
        select(TrainingRunModel)
        .where(TrainingRunModel.created_by_user_id == user_id)
        .with_for_update()
    ).scalars().all()
    for manifest in manifests:
        manifest.created_by_user_id = None
    for run in runs:
        run.created_by_user_id = None
    return {"detached_manifests": len(manifests), "detached_runs": len(runs)}


def manifest_response(manifest: TrainingDatasetManifestModel) -> TrainingManifestResponse:
    return TrainingManifestResponse(
        id=manifest.id,
        dataset_version=manifest.dataset_version,
        manifest_checksum=manifest.manifest_checksum,
        content_checksum=manifest.content_checksum,
        held_out_evaluation_checksum=manifest.held_out_evaluation_checksum,
        eligibility_result=manifest.eligibility_result,
        entry_count=manifest.entry_count,
        train_count=manifest.train_count,
        validation_count=manifest.validation_count,
        test_count=manifest.test_count,
        created_at=manifest.created_at,
    )


def run_response(db: Session, run: TrainingRunModel) -> TrainingRunResponse:
    return TrainingRunResponse(
        id=run.id,
        job_id=run.job_id,
        manifest_id=run.manifest_id,
        manifest_checksum=run.manifest_checksum,
        recipe_key=run.recipe_key,
        recipe_version=run.recipe_version,
        base_model_identity=run.base_model_identity,
        compute_profile_id=run.compute_profile_id,
        compute_profile_version=run.compute_profile_version,
        execution_mode=run.execution_mode,
        status=run.status,
        candidate_class=run.candidate_class,
        real_training_occurred=run.real_training_occurred,
        result_code=run.result_code,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        artifacts=[artifact_response(item) for item in _artifacts_for_run(db, run.id)],
    )


def artifact_response(artifact: ArtifactModel) -> TrainingArtifactResponse:
    return TrainingArtifactResponse(
        id=artifact.id,
        artifact_type=artifact.artifact_type,
        status=artifact.status,
        checksum=artifact.checksum,
        size_bytes=artifact.size_bytes,
        content_type=artifact.content_type,
        storage_backend=artifact.storage_backend,
    )


def local_fake_result(run: TrainingRunModel) -> dict[str, object]:
    payloads = _artifact_payloads(run)
    return {
        "training_run_id": run.id,
        "result_code": "local_fake_completed",
        "artifact_checksums": {key: _sha256_bytes(value) for key, value in payloads.items()},
        "real_training_occurred": False,
    }


def _artifact_documents(run: TrainingRunModel) -> dict[str, dict[str, object]]:
    snapshot = run.execution_snapshot
    if not isinstance(snapshot, dict):
        raise HTTPException(status_code=409, detail="Training execution snapshot is unavailable.")
    model_card = {
        "schema_version": "training.model-card.v1",
        "training_run_id": run.id,
        "task": "report_synthesis_training_preparation",
        "base_model_identity": run.base_model_identity,
        "dataset_manifest_checksum": run.manifest_checksum,
        "dataset_version": snapshot.get("dataset", {}).get("dataset_version"),
        "recipe_checksum": run.recipe_checksum,
        "compute_profile_checksum": run.compute_profile_checksum,
        "execution_mode": run.execution_mode,
        "real_training_occurred": False,
        "candidate_class": "not_registry_eligible",
        "evaluation_state": "not_evaluated",
        "privacy_data_classes": ["checked_in_synthetic"],
        "intended_use": "offline governance evidence only",
        "non_intended_use": ["model registration", "model promotion", "model routing", "production inference"],
        "limitations": [
            "Local fake execution produced no trainable model weights.",
            "This evidence is not eligible for model registration, evaluation, promotion, or routing.",
            "Held-out evaluation datasets and feedback were not loaded.",
        ],
    }
    receipt = {
        "schema_version": "training.execution-receipt.v1",
        "training_run_id": run.id,
        "execution_snapshot_checksum": _sha256_bytes(_canonical_bytes(snapshot)),
        "result_code": "local_fake_completed",
        "provider_session": "not_applicable",
        "network_used": False,
        "real_training_occurred": False,
    }
    return {"training_model_card": model_card, "training_execution_receipt": receipt}


def _artifact_payloads(run: TrainingRunModel) -> dict[str, bytes]:
    return {artifact_type: _canonical_bytes(document) for artifact_type, document in _artifact_documents(run).items()}


def _run_for_job(db: Session, job: JobModel, *, lock: bool, required: bool = True) -> TrainingRunModel | None:
    context = job.input_json.get("_server_context", {}) if isinstance(job.input_json, dict) else {}
    run_id = context.get("training_run_id") if isinstance(context, dict) else None
    statement = select(TrainingRunModel).where(TrainingRunModel.job_id == job.id)
    if isinstance(run_id, str):
        statement = statement.where(TrainingRunModel.id == run_id)
    else:
        if required:
            raise HTTPException(status_code=409, detail="Training run lineage is unavailable.")
        return None
    if lock:
        statement = statement.with_for_update()
    run = db.execute(statement).scalars().one_or_none()
    if run is None and required:
        raise HTTPException(status_code=409, detail="Training run lineage is unavailable.")
    snapshot = run.execution_snapshot if run is not None else None
    dataset = snapshot.get("dataset") if isinstance(snapshot, dict) else None
    if run is not None and (
        not isinstance(dataset, dict)
        or run.manifest_checksum != dataset.get("manifest_checksum")
    ):
        raise HTTPException(status_code=409, detail="Training run manifest integrity is unavailable.")
    return run


def _artifacts_for_run(db: Session, run_id: str, *, include_pending: bool = False) -> list[ArtifactModel]:
    statement = (
        select(ArtifactModel)
        .where(ArtifactModel.resource_type == "training_run")
        .where(ArtifactModel.resource_id == run_id)
        .order_by(ArtifactModel.artifact_type)
    )
    if not include_pending:
        statement = statement.where(ArtifactModel.deleted_at.is_(None))
    return db.execute(statement).scalars().all()


def _job_summary(run: TrainingRunModel, artifacts: list[ArtifactModel]) -> dict[str, object]:
    return {
        "training_run_id": run.id,
        "result_code": run.result_code or "local_fake_completed",
        "artifact_ids": [artifact.id for artifact in artifacts],
        "real_training_occurred": False,
    }


def _canonical_bytes(value: object) -> bytes:
    from app.training_governance.catalog import canonical_bytes

    return canonical_bytes(value)


def _sha256_bytes(value: bytes) -> str:
    import hashlib

    return hashlib.sha256(value).hexdigest()
