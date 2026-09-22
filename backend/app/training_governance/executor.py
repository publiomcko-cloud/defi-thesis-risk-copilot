from __future__ import annotations

from fastapi import HTTPException

from app.jobs.cancellation import CancellationContext
from app.jobs.errors import JobErrorCategory, JobExecutionError
from app.jobs.schemas import JobResultEnvelope, WorkerClaimedJob
from app.models.training_governance import TrainingRunModel
from app.training_governance.catalog import compute_profile


class TrainingPreparationJobExecutor:
    """Deterministic local-fake executor with no network, provider, shell, or credential path."""

    def execute(self, job: WorkerClaimedJob, cancellation: CancellationContext | None = None) -> JobResultEnvelope:
        cancellation = cancellation or CancellationContext()
        snapshot = _execution_snapshot(job)
        profile = compute_profile()
        if snapshot.get("compute_profile") != profile or profile["execution_mode"] != "local_fake":
            raise JobExecutionError(JobErrorCategory.PERMANENT_INPUT, "training_profile_invalid", "Training profile is invalid.")
        cancellation.raise_if_cancelled()
        run = TrainingRunModel(
            id=_training_run_id(job),
            job_id=job.id,
            manifest_id=str(snapshot.get("dataset", {}).get("manifest_id", "")),
            manifest_checksum=str(snapshot.get("dataset", {}).get("manifest_checksum", "")),
            recipe_key=str(snapshot.get("recipe", {}).get("recipe_key", "")),
            recipe_version=str(snapshot.get("recipe", {}).get("recipe_version", "")),
            recipe_checksum=str(snapshot.get("recipe", {}).get("recipe_checksum", "")),
            base_model_identity=str(profile["base_model_identity"]),
            compute_profile_id=str(profile["compute_profile_id"]),
            compute_profile_version=str(profile["compute_profile_version"]),
            compute_profile_checksum=str(profile["compute_profile_checksum"]),
            execution_mode=str(snapshot.get("execution_mode", "")),
            execution_snapshot=snapshot,
            status="running",
            cleanup_state="not_required",
            candidate_class="not_registry_eligible",
            real_training_occurred=False,
            estimated_cost_microusd=0,
            actual_cost_microusd=0,
        )
        from app.training_governance.service import local_fake_result

        cancellation.raise_if_cancelled()
        return JobResultEnvelope(result_schema_version="model.training.prepare.v1", result_json=local_fake_result(run))


def _training_run_id(job: WorkerClaimedJob) -> str:
    request = job.input_json.get("request", {}) if isinstance(job.input_json, dict) else {}
    context = job.input_json.get("_server_context", {}) if isinstance(job.input_json, dict) else {}
    value = request.get("training_run_id") if isinstance(request, dict) else None
    context_value = context.get("training_run_id") if isinstance(context, dict) else None
    if not isinstance(value, str) or not value.startswith("trainrun_") or value != context_value:
        raise JobExecutionError(JobErrorCategory.PERMANENT_INPUT, "training_run_invalid", "Training run lineage is invalid.")
    return value


def _execution_snapshot(job: WorkerClaimedJob) -> dict:
    context = job.input_json.get("_server_context", {}) if isinstance(job.input_json, dict) else {}
    snapshot = context.get("training_execution_snapshot") if isinstance(context, dict) else None
    if not isinstance(snapshot, dict) or snapshot.get("schema_version") != "training.execution.v1":
        raise JobExecutionError(JobErrorCategory.PERMANENT_INPUT, "training_snapshot_invalid", "Training execution snapshot is invalid.")
    if snapshot.get("execution_mode") not in {"dry_run", "local_fake"}:
        raise JobExecutionError(JobErrorCategory.PERMANENT_INPUT, "training_mode_invalid", "Training execution mode is invalid.")
    return snapshot
