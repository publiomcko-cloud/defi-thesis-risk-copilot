from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth.schemas import UserContext
from app.agents.orchestrator import run_analysis_workflow
from app.core.config import get_settings
from app.jobs.control_service import submit_job
from app.jobs.schemas import JobSubmissionRequest
from app.models.analysis_request import AnalysisRequestModel
from app.models.artifact import ArtifactModel
from app.models.job import JobModel
from app.models.report import ReportModel
from app.quotas.service import ACTION_ANALYSIS, consume_quota
from app.reports.markdown_export import render_markdown_report
from app.schemas.analysis import AnalysisRequest, AnalysisResponse
from app.schemas.reports import ReportResponse
from app.services.report_service import save_report


def analyze_strategy(
    request: AnalysisRequest,
    db: Session,
    actor: UserContext | None = None,
    idempotency_key: str | None = None,
) -> AnalysisResponse:
    if _uses_async_analysis(actor):
        return submit_async_analysis(request, db, actor, idempotency_key)

    if actor is not None:
        consume_quota(db, actor, ACTION_ANALYSIS)
    analysis_request_id = f"analysis_{uuid4().hex[:12]}"
    report_id = f"report_{uuid4().hex[:12]}"
    workflow_result = run_analysis_workflow(request, report_id, db, actor=actor)
    visibility = "public_demo" if actor is None else "private"
    expires_at = (
        datetime.now(UTC) + timedelta(hours=get_settings().anonymous_retention_hours)
        if actor and actor.anonymous_session_id
        else None
    )

    db.add(
        AnalysisRequestModel(
            id=analysis_request_id,
            strategy_description=workflow_result.parsed_strategy.description,
            protocols=workflow_result.parsed_strategy.protocols,
            market_url=workflow_result.parsed_strategy.market_url,
            manual_inputs_json=workflow_result.parsed_strategy.manual_inputs,
            analysis_depth=workflow_result.parsed_strategy.analysis_depth,
            owner_user_id=None if actor is None or actor.anonymous_session_id else actor.id,
            visibility=visibility,
            anonymous_session_id=actor.anonymous_session_id if actor else None,
            expires_at=expires_at,
        )
    )
    save_report(
        report=workflow_result.report,
        analysis_request_id=analysis_request_id,
        report_markdown=render_markdown_report(workflow_result.report),
        db=db,
        owner_user_id=None if actor is None or actor.anonymous_session_id else actor.id,
        visibility=visibility,
        anonymous_session_id=actor.anonymous_session_id if actor else None,
        expires_at=expires_at,
    )
    db.commit()

    return AnalysisResponse(
        report_id=workflow_result.report.report_id,
        status="completed",
        risk_rating=workflow_result.report.risk_rating,
        summary=workflow_result.report.executive_summary,
    )


def submit_async_analysis(
    request: AnalysisRequest,
    db: Session,
    actor: UserContext,
    idempotency_key: str | None,
) -> AnalysisResponse:
    """Queue a private authenticated analysis with an immutable server-owned snapshot."""

    if not idempotency_key:
        raise HTTPException(status_code=422, detail="Idempotency-Key is required for asynchronous analysis.")
    job, _ = submit_job(
        db,
        actor,
        JobSubmissionRequest(
            job_type="analysis.generate",
            input_schema_version="analysis.generate.v1",
            input_json={"analysis_request": request.model_dump(mode="json")},
        ),
        idempotency_key,
    )
    report = db.get(ReportModel, job.result_resource_id) if job.status == "completed" else None
    return AnalysisResponse(
        report_id=job.result_resource_id or "",
        job_id=job.id,
        status=job.status,
        risk_rating=report.risk_rating if report else None,
        summary=report.summary if report else None,
    )


def _uses_async_analysis(actor: UserContext | None) -> bool:
    return bool(
        get_settings().async_analysis_enabled
        and actor is not None
        and actor.auth_enabled
        and actor.anonymous_session_id is None
    )


def persist_async_analysis_completion(db: Session, job: JobModel, result_json: dict) -> None:
    """Persist one deterministic report while the control plane still owns completion.

    The worker sends a schema-checked, secret-free result envelope. This function is
    called inside the worker completion transaction, so a cancelled job cannot leave
    a completed report behind and a retry cannot create a second report.
    """

    context = _async_job_context(job)
    try:
        normalized = result_json["analysis_request"]
        report = ReportResponse.model_validate(result_json["report"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Worker analysis result is invalid.") from exc
    if report.report_id != context["report_id"]:
        raise HTTPException(status_code=422, detail="Worker analysis result used an unexpected report identifier.")

    existing_request = db.get(AnalysisRequestModel, context["analysis_request_id"])
    existing_report = db.get(ReportModel, context["report_id"])
    if existing_request is not None or existing_report is not None:
        if (
            existing_request is not None
            and existing_report is not None
            and existing_request.source_job_id == job.id
            and existing_report.source_job_id == job.id
        ):
            return
        raise HTTPException(status_code=409, detail="Analysis result resource is already linked to another job.")

    try:
        parsed = AnalysisRequest.model_validate(
            {
                "strategy_description": normalized["strategy_description"],
                "protocols": normalized["protocols"],
                "market_url": normalized.get("market_url"),
                "manual_inputs": normalized["manual_inputs"],
                "analysis_depth": normalized["analysis_depth"],
            }
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Worker analysis normalization is invalid.") from exc

    try:
        report_markdown = render_markdown_report(report)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Worker analysis report is structurally invalid.") from exc

    db.add(
        AnalysisRequestModel(
            id=context["analysis_request_id"],
            strategy_description=parsed.strategy_description,
            protocols=parsed.protocols,
            market_url=parsed.market_url,
            manual_inputs_json=parsed.manual_inputs.model_dump(mode="json"),
            analysis_depth=parsed.analysis_depth,
            owner_user_id=job.owner_user_id,
            organization_id=job.organization_id,
            visibility=job.visibility,
            source_job_id=job.id,
        )
    )
    save_report(
        report=report,
        analysis_request_id=context["analysis_request_id"],
        report_markdown=report_markdown,
        db=db,
        owner_user_id=job.owner_user_id,
        organization_id=job.organization_id,
        visibility=job.visibility,
        source_job_id=job.id,
    )
    artifact = db.get(ArtifactModel, f"artifact_{job.id}")
    if artifact is None:
        db.add(
            ArtifactModel(
                id=f"artifact_{job.id}",
                job_id=job.id,
                artifact_type="report_reference",
                status="available",
                owner_user_id=job.owner_user_id,
                organization_id=job.organization_id,
                visibility=job.visibility,
                resource_type="report",
                resource_id=context["report_id"],
                storage_backend="database",
                content_type="application/json",
                retention_until=datetime.now(UTC) + timedelta(days=get_settings().job_terminal_retention_days),
            )
        )
    db.flush()


def _async_job_context(job: JobModel) -> dict[str, str]:
    try:
        context = job.input_json["_server_context"]
        analysis_request_id = context["analysis_request_id"]
        report_id = context["report_id"]
    except (KeyError, TypeError) as exc:
        raise HTTPException(status_code=422, detail="Analysis job context is invalid.") from exc
    if not (
        isinstance(analysis_request_id, str)
        and analysis_request_id.startswith("analysis_")
        and isinstance(report_id, str)
        and report_id.startswith("report_")
    ):
        raise HTTPException(status_code=422, detail="Analysis job context is invalid.")
    return {"analysis_request_id": analysis_request_id, "report_id": report_id}
