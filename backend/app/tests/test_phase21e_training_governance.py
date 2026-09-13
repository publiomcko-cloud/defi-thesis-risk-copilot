from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import create_user, user_context
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.jobs.schemas import WorkerCredentialCreateRequest, WorkerRegistrationRequest
from app.jobs.worker_service import issue_worker_credential, register_worker
from app.jobs.worker_protocol import recover_expired_jobs
from app.main import app
from app.models.artifact import ArtifactModel
from app.models.job import JobModel
from app.models.model_governance import ModelRegistryModel
from app.models.training_governance import TrainingDatasetEntryModel, TrainingDatasetManifestModel, TrainingRunModel
from app.models.vast_session import VastSessionModel
from app.training_governance import catalog
from app.training_governance.executor import TrainingPreparationJobExecutor


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def training_client(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_PROVIDER", "legacy_local")
    monkeypatch.setenv("AUTH_SECRET_KEY", "phase21e-training-secret")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("JOBS_ENABLED", "true")
    monkeypatch.setenv("WORKER_API_ENABLED", "true")
    monkeypatch.setenv("WORKER_TOKEN_PEPPER", "phase21e-worker-pepper")
    get_settings.cache_clear()
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as db:
        admin = create_user(db, "phase21e-admin@example.test", role="admin", token="phase21e-admin-token")
        user = create_user(db, "phase21e-user@example.test", token="phase21e-user-token")
        worker = register_worker(
            db,
            user_context(admin),
            WorkerRegistrationRequest(
                name="phase21e-local-fake-worker",
                protocol_version="v1",
                allowed_job_types=["model.training.prepare"],
            ),
        )
        issued = issue_worker_credential(db, user_context(admin), worker.id, WorkerCredentialCreateRequest())
        db.commit()

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app), Session, issued.token
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_admin_only_server_owned_manifest_and_training_job_surface(training_client) -> None:
    client, Session, _ = training_client
    admin_headers = _user_auth("phase21e-admin-token")
    assert client.get("/api/admin/training-governance", headers=_user_auth("phase21e-user-token")).status_code == 403
    for prohibited_source in (
        "private-saved-thesis",
        "organization-thesis",
        "private-report",
        "organization-report",
        "private-knowledge-document",
        "feedback-comment",
        "arbitrary-user-upload",
    ):
        assert client.post(
            "/api/admin/training-governance/manifests/seal",
            headers=admin_headers,
            json={"dataset_key": prohibited_source},
        ).status_code == 422
    sealed = client.post("/api/admin/training-governance/manifests/seal", headers=admin_headers, json={})
    assert sealed.status_code == 201
    manifest = sealed.json()
    assert (manifest["entry_count"], manifest["train_count"], manifest["validation_count"], manifest["test_count"]) == (12, 8, 2, 2)

    generic = client.post(
        "/api/jobs",
        headers={**admin_headers, "Idempotency-Key": "phase21e-generic-rejected"},
        json={"job_type": "model.training.prepare", "input_schema_version": "model.training.prepare.v1", "input_json": {"training_run_id": "trainrun_client"}},
    )
    assert generic.status_code == 403
    rejected_body = client.post(
        "/api/admin/training-governance/runs",
        headers={**admin_headers, "Idempotency-Key": "phase21e-extra-rejected"},
        json={"dataset_key": "report_synthesis_training_synthetic_v1", "raw_examples": [{"private": "no"}]},
    )
    assert rejected_body.status_code == 422
    for index, forbidden_compute_input in enumerate(
        (
            {"compute_profile": "unknown-provider"},
            {"vast_offer_id": "offer-anything"},
            {"image": "untrusted/image:latest"},
            {"shell_command": "echo unsafe"},
            {"provider_url": "https://provider.invalid"},
            {"api_key": "not-accepted"},
        )
    ):
        response = client.post(
            "/api/admin/training-governance/runs",
            headers={**admin_headers, "Idempotency-Key": f"phase21e-forbidden-{index}"},
            json=forbidden_compute_input,
        )
        assert response.status_code == 422

    with Session() as db:
        record = db.scalars(select(TrainingDatasetManifestModel)).one()
        rows = db.scalars(select(TrainingDatasetEntryModel).where(TrainingDatasetEntryModel.manifest_id == record.id)).all()
        assert {row.source_class for row in rows} == {"checked_in_synthetic"}
        assert {row.split for row in rows} == {"train", "validation", "test"}
        assert record.eligibility_result == "approved_checked_in_synthetic"
        assert not db.scalars(select(ModelRegistryModel)).all()


def test_real_worker_lifecycle_is_idempotent_and_never_calls_provider_compute(training_client) -> None:
    client, Session, worker_token = training_client
    admin_headers = _user_auth("phase21e-admin-token")
    first = _submit_training(client, admin_headers, "phase21e-worker-run")
    replay = _submit_training(client, admin_headers, "phase21e-worker-run")
    assert replay["id"] == first["id"]
    lease = _claim(client, worker_token)
    assert lease["job_type"] == "model.training.prepare"
    payload = _lease_payload(lease)
    started = client.post(f"/internal/workers/v1/jobs/{lease['id']}/start", headers=_worker_auth(worker_token), json=payload)
    assert started.status_code == 200
    result = TrainingPreparationJobExecutor().execute(_claimed_job(lease))
    tampered_result = result.model_copy(deep=True)
    tampered_result.result_json["artifact_checksums"]["training_model_card"] = "0" * 64
    assert client.post(
        f"/internal/workers/v1/jobs/{lease['id']}/complete",
        headers=_worker_auth(worker_token),
        json={**payload, "result": tampered_result.model_dump(mode="json")},
    ).status_code == 422
    complete = client.post(
        f"/internal/workers/v1/jobs/{lease['id']}/complete",
        headers=_worker_auth(worker_token),
        json={**payload, "result": result.model_dump(mode="json")},
    )
    assert complete.status_code == 200
    assert complete.json()["status"] == "completed"
    assert client.post(
        f"/internal/workers/v1/jobs/{lease['id']}/complete",
        headers=_worker_auth(worker_token),
        json={**payload, "result": result.model_dump(mode="json")},
    ).status_code == 409

    with Session() as db:
        run = db.get(TrainingRunModel, first["id"])
        assert run is not None
        assert run.status == "completed"
        assert run.real_training_occurred is False
        assert run.candidate_class == "not_registry_eligible"
        assert run.actual_cost_microusd == 0
        assert run.result_json and run.result_json["training_model_card"]["real_training_occurred"] is False
        assert run.result_json["training_model_card"]["evaluation_state"] == "not_evaluated"
        assert run.result_json["training_model_card"]["non_intended_use"] == ["model registration", "model promotion", "model routing", "production inference"]
        assert run.result_json["training_execution_receipt"]["network_used"] is False
        snapshot = run.execution_snapshot
        assert snapshot["environment"] == "local_fake_controlled_v1"
        assert snapshot["expected_artifact_types"] == ["training_model_card", "training_execution_receipt"]
        assert "expected_result" not in str(snapshot)
        assert "expected_failure_class" not in str(snapshot)
        artifacts = db.scalars(select(ArtifactModel).where(ArtifactModel.resource_id == run.id)).all()
        assert {(artifact.artifact_type, artifact.status) for artifact in artifacts} == {
            ("training_execution_receipt", "available"),
            ("training_model_card", "available"),
        }
        assert all(artifact.checksum and len(artifact.checksum) == 64 for artifact in artifacts)
        assert not db.scalars(select(VastSessionModel)).all()
        assert not db.scalars(select(ModelRegistryModel)).all()
        manifest_id = run.manifest_id
    deleted = client.request("DELETE", "/api/account", headers=admin_headers, json={"confirmation": "DELETE"})
    assert deleted.status_code == 200
    with Session() as db:
        run = db.get(TrainingRunModel, first["id"])
        manifest = db.get(TrainingDatasetManifestModel, manifest_id)
        assert run is not None and run.created_by_user_id is None
        assert manifest is not None and manifest.created_by_user_id is None
        assert db.scalars(select(TrainingDatasetEntryModel).where(TrainingDatasetEntryModel.manifest_id == manifest_id)).all()


def test_training_cancellation_and_terminal_failure_preserve_manifest_evidence(training_client) -> None:
    client, Session, worker_token = training_client
    admin_headers = _user_auth("phase21e-admin-token")
    cancelled = _submit_training(client, admin_headers, "phase21e-cancel-run")
    job_id = _job_id_for_run(Session, cancelled["id"])
    assert client.post(f"/api/jobs/{job_id}/cancel", headers=admin_headers).json()["status"] == "cancelled"
    with Session() as db:
        run = db.get(TrainingRunModel, cancelled["id"])
        assert run is not None and run.status == "cancelled"
        manifest_id = run.manifest_id

    failed = _submit_training(client, admin_headers, "phase21e-failed-run")
    failed_job_id = _job_id_for_run(Session, failed["id"])
    with Session() as db:
        job = db.get(JobModel, failed_job_id)
        assert job is not None
        job.max_attempts = 1
        db.commit()
    lease = _claim(client, worker_token)
    assert lease["id"] == failed_job_id
    payload = _lease_payload(lease)
    assert client.post(f"/internal/workers/v1/jobs/{lease['id']}/start", headers=_worker_auth(worker_token), json=payload).status_code == 200
    failed_response = client.post(
        f"/internal/workers/v1/jobs/{lease['id']}/fail",
        headers=_worker_auth(worker_token),
        json={**payload, "error_code": "training_input_invalid", "error_summary": "The controlled local input is invalid.", "error_category": "permanent_input"},
    )
    assert failed_response.json()["status"] == "dead_letter"
    with Session() as db:
        run = db.get(TrainingRunModel, failed["id"])
        assert run is not None and run.status == "failed"
        assert db.get(TrainingDatasetManifestModel, manifest_id) is not None
        assert db.scalars(select(TrainingDatasetEntryModel).where(TrainingDatasetEntryModel.manifest_id == manifest_id)).all()


def test_lease_loss_retry_and_stale_completion_produce_one_local_fake_artifact_set(training_client) -> None:
    client, Session, worker_token = training_client
    admin_headers = _user_auth("phase21e-admin-token")
    submitted = _submit_training(client, admin_headers, "phase21e-lease-recovery")
    first_lease = _claim(client, worker_token)
    first_payload = _lease_payload(first_lease)
    assert client.post(f"/internal/workers/v1/jobs/{first_lease['id']}/start", headers=_worker_auth(worker_token), json=first_payload).status_code == 200
    stale_result = TrainingPreparationJobExecutor().execute(_claimed_job(first_lease))
    with Session() as db:
        job = db.get(JobModel, first_lease["id"])
        assert job is not None
        job.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    with Session() as db:
        assert recover_expired_jobs(db, now=datetime.now(UTC)) == 1
        db.commit()
        run = db.get(TrainingRunModel, submitted["id"])
        job = db.get(JobModel, first_lease["id"])
        assert run is not None and run.status == "queued"
        assert job is not None and job.status == "retry_wait"
        job.available_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    assert client.post(
        f"/internal/workers/v1/jobs/{first_lease['id']}/complete",
        headers=_worker_auth(worker_token),
        json={**first_payload, "result": stale_result.model_dump(mode="json")},
    ).status_code == 409
    second_lease = _claim(client, worker_token)
    assert second_lease["lease_generation"] == first_lease["lease_generation"] + 1
    second_payload = _lease_payload(second_lease)
    assert client.post(f"/internal/workers/v1/jobs/{second_lease['id']}/start", headers=_worker_auth(worker_token), json=second_payload).status_code == 200
    result = TrainingPreparationJobExecutor().execute(_claimed_job(second_lease))
    assert client.post(
        f"/internal/workers/v1/jobs/{second_lease['id']}/complete",
        headers=_worker_auth(worker_token),
        json={**second_payload, "result": result.model_dump(mode="json")},
    ).json()["status"] == "completed"
    with Session() as db:
        artifacts = db.scalars(select(ArtifactModel).where(ArtifactModel.resource_id == submitted["id"])).all()
        assert len(artifacts) == 2
        assert db.get(TrainingRunModel, submitted["id"]).status == "completed"


def test_catalog_rejects_cross_split_duplicates_and_keeps_evaluation_cases_held_out(monkeypatch) -> None:
    original = catalog.checked_in_entries()
    duplicate = [*original, {"id": "synthetic-duplicate", "input": original[0]["input"], "target": original[0]["target"]}]
    monkeypatch.setattr(catalog, "checked_in_entries", lambda: duplicate)
    with pytest.raises(RuntimeError, match="duplicate normalized content"):
        catalog.dataset_manifest_snapshot()
    evaluation = catalog._current_evaluation_fingerprints()
    assert evaluation["policy"] == "excluded_not_loaded"
    assert evaluation["cases"]
    assert all("expected_result" not in entry for entry in original)


def _submit_training(client: TestClient, headers: dict[str, str], key: str) -> dict:
    response = client.post(
        "/api/admin/training-governance/runs",
        headers={**headers, "Idempotency-Key": key},
        json={"execution_mode": "dry_run"},
    )
    assert response.status_code == 202, response.text
    return response.json()


def _job_id_for_run(Session, run_id: str) -> str:
    with Session() as db:
        run = db.get(TrainingRunModel, run_id)
        assert run is not None
        return run.job_id


def _claim(client: TestClient, worker_token: str) -> dict:
    response = client.post("/internal/workers/v1/claim", headers=_worker_auth(worker_token), json={"protocol_version": "v1"})
    assert response.status_code == 200, response.text
    assert response.json()["job"] is not None
    return response.json()["job"]


def _claimed_job(lease: dict):
    from app.jobs.schemas import WorkerClaimedJob

    return WorkerClaimedJob.model_validate(lease)


def _lease_payload(lease: dict) -> dict:
    return {"lease_generation": lease["lease_generation"], "lease_token": lease["lease_token"]}


def _user_auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _worker_auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
