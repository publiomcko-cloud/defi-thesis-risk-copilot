from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from app.agents.orchestrator import AnalysisWorkflowResult, run_analysis_workflow
from app.auth.service import user_context
from app.db.session import SessionLocal
from app.jobs.errors import JobErrorCategory, JobExecutionError
from app.jobs.schemas import JobResultEnvelope, WorkerClaimedJob
from app.models.user import UserModel
from app.schemas.analysis import AnalysisRequest


class AnalysisExecutionError(JobExecutionError):
    """A worker could not produce a valid deterministic analysis result."""


class AnalysisJobExecutor:
    """Runs the deterministic analysis workflow outside the public API process."""

    def __init__(
        self,
        session_factory: Callable[[], Session] = SessionLocal,
        workflow_runner: Callable[..., AnalysisWorkflowResult] = run_analysis_workflow,
    ) -> None:
        self._session_factory = session_factory
        self._workflow_runner = workflow_runner

    def execute(self, job: WorkerClaimedJob) -> JobResultEnvelope:
        request, report_id = _analysis_input(job)
        with self._session_factory() as db:
            owner = db.get(UserModel, _owner_id(job))
            if owner is None:
                raise AnalysisExecutionError(JobErrorCategory.PERMANENT_AUTHORIZATION, "analysis_owner_unavailable", "Analysis owner is unavailable.")
            workflow_result = self._workflow_runner(request, report_id, db, actor=user_context(owner))
            return JobResultEnvelope(
                result_schema_version="analysis.generate.v1",
                result_json={
                    "analysis_request": {
                        "strategy_description": workflow_result.parsed_strategy.description,
                        "protocols": workflow_result.parsed_strategy.protocols,
                        "market_url": workflow_result.parsed_strategy.market_url,
                        "manual_inputs": workflow_result.parsed_strategy.manual_inputs,
                        "analysis_depth": workflow_result.parsed_strategy.analysis_depth,
                    },
                    "report": workflow_result.report.model_dump(mode="json"),
                },
            )


def _analysis_input(job: WorkerClaimedJob) -> tuple[AnalysisRequest, str]:
    try:
        request_payload = job.input_json["request"]["analysis_request"]
        report_id = job.input_json["_server_context"]["report_id"]
        if not isinstance(report_id, str) or not report_id.startswith("report_"):
            raise ValueError("invalid report id")
        return AnalysisRequest.model_validate(request_payload), report_id
    except (KeyError, TypeError, ValueError) as exc:
        raise AnalysisExecutionError(JobErrorCategory.PERMANENT_INPUT, "analysis_input_invalid", "Analysis job input is invalid.") from exc


def _owner_id(job: WorkerClaimedJob) -> str:
    try:
        owner_id = job.input_json["_server_context"]["owner_user_id"]
    except (KeyError, TypeError) as exc:
        raise AnalysisExecutionError(JobErrorCategory.PERMANENT_AUTHORIZATION, "analysis_owner_unavailable", "Analysis job owner is unavailable.") from exc
    if not isinstance(owner_id, str) or not owner_id:
        raise AnalysisExecutionError(JobErrorCategory.PERMANENT_AUTHORIZATION, "analysis_owner_unavailable", "Analysis job owner is unavailable.")
    return owner_id
