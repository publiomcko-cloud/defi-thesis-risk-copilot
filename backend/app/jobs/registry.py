from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import HTTPException

from app.jobs.schemas import JobResultEnvelope
from app.core.config import Settings
from app.jobs.errors import JobErrorCategory
from app.schemas.analysis import AnalysisRequest


InputValidator = Callable[[dict], None]
ResultValidator = Callable[[dict], None]


@dataclass(frozen=True)
class JobTypeSpec:
    job_type: str
    input_schema_versions: frozenset[str]
    result_schema_versions: frozenset[str]
    input_validator: InputValidator
    result_validator: ResultValidator
    executor_name: str
    cost_estimator_name: str
    retryable_categories: frozenset[JobErrorCategory]
    accepted_failure_categories: frozenset[JobErrorCategory]
    requires_provider: bool
    maximum_attempt_runtime_seconds: int | None = None

    def execution_horizon_seconds(self, settings: Settings) -> int:
        if self.job_type == "vast.session.start":
            return settings.vast_startup_timeout_seconds + settings.vast_reconciliation_grace_seconds + settings.job_cleanup_grace_seconds
        return self.maximum_attempt_runtime_seconds or settings.analysis_job_max_attempt_runtime_seconds


def _analysis_input(value: dict) -> None:
    try:
        AnalysisRequest.model_validate(value["analysis_request"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="analysis.generate input must contain a valid analysis_request.") from exc


def _analysis_result(value: dict) -> None:
    if not isinstance(value.get("analysis_request"), dict) or not isinstance(value.get("report"), dict):
        raise HTTPException(status_code=422, detail="analysis.generate result must contain deterministic analysis_request and report data.")


def _vast_input(value: dict) -> None:
    if set(value) != {"allow_remote_gpu", "warm_instance"} or not all(isinstance(value[key], bool) for key in value):
        raise HTTPException(status_code=422, detail="vast.session.start input must use the server-approved boolean request shape.")


def _vast_result(value: dict) -> None:
    if not isinstance(value.get("vast_session_id"), str) or not isinstance(value.get("provider_status"), str):
        raise HTTPException(status_code=422, detail="vast.session.start result is invalid.")


JOB_TYPE_REGISTRY: dict[str, JobTypeSpec] = {
    "analysis.generate": JobTypeSpec(
        job_type="analysis.generate",
        input_schema_versions=frozenset({"analysis.generate.v1"}),
        result_schema_versions=frozenset({"analysis.generate.v1"}),
        input_validator=_analysis_input,
        result_validator=_analysis_result,
        executor_name="analysis",
        cost_estimator_name="deterministic_zero_cost",
        retryable_categories=frozenset({JobErrorCategory.RETRYABLE_INFRASTRUCTURE}),
        accepted_failure_categories=frozenset({JobErrorCategory.PERMANENT_INPUT, JobErrorCategory.PERMANENT_AUTHORIZATION, JobErrorCategory.RETRYABLE_INFRASTRUCTURE}),
        requires_provider=False,
        # The analysis horizon is entirely environment-configured so an operator can
        # lower or raise it without changing the registry source.
        maximum_attempt_runtime_seconds=None,
    ),
    "vast.session.start": JobTypeSpec(
        job_type="vast.session.start",
        input_schema_versions=frozenset({"vast.session.start.v1"}),
        result_schema_versions=frozenset({"vast.session.start.v1"}),
        input_validator=_vast_input,
        result_validator=_vast_result,
        executor_name="vast",
        cost_estimator_name="server_profiled_vast",
        retryable_categories=frozenset({JobErrorCategory.RETRYABLE_INFRASTRUCTURE, JobErrorCategory.RETRYABLE_PROVIDER}),
        accepted_failure_categories=frozenset({JobErrorCategory.PERMANENT_INPUT, JobErrorCategory.PERMANENT_AUTHORIZATION, JobErrorCategory.RETRYABLE_INFRASTRUCTURE, JobErrorCategory.RETRYABLE_PROVIDER, JobErrorCategory.UNCERTAIN_EXTERNAL_SIDE_EFFECT}),
        requires_provider=True,
    ),
}


def get_job_spec(job_type: str) -> JobTypeSpec:
    spec = JOB_TYPE_REGISTRY.get(job_type)
    if spec is None:
        raise HTTPException(status_code=422, detail="Unsupported durable job type.")
    return spec


def validate_submission_schema(job_type: str, schema_version: str, payload: dict) -> JobTypeSpec:
    spec = get_job_spec(job_type)
    if schema_version not in spec.input_schema_versions:
        raise HTTPException(status_code=422, detail="Unsupported durable job input schema version.")
    spec.input_validator(payload)
    return spec


def validate_result_schema(job_type: str, schema_version: str, result: JobResultEnvelope) -> JobTypeSpec:
    spec = get_job_spec(job_type)
    if schema_version not in spec.result_schema_versions or result.result_schema_version != schema_version:
        raise HTTPException(status_code=422, detail="Unsupported durable job result schema version.")
    spec.result_validator(result.result_json)
    return spec


def executor_for_job_type(job_type: str):
    """Resolve only a registry-declared executor; imports remain lazy for workers."""

    spec = get_job_spec(job_type)
    if spec.executor_name == "analysis":
        from app.jobs.analysis_executor import AnalysisJobExecutor

        return AnalysisJobExecutor()
    if spec.executor_name == "vast":
        from app.jobs.vast_executor import VastJobExecutor

        return VastJobExecutor()
    raise HTTPException(status_code=422, detail="No durable executor is registered for this job type.")
