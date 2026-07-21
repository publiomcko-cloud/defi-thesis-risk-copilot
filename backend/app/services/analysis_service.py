from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from app.auth.schemas import UserContext
from app.agents.orchestrator import run_analysis_workflow
from app.core.config import get_settings
from app.models.analysis_request import AnalysisRequestModel
from app.quotas.service import ACTION_ANALYSIS, consume_quota
from app.reports.markdown_export import render_markdown_report
from app.schemas.analysis import AnalysisRequest, AnalysisResponse
from app.services.report_service import save_report


def analyze_strategy(
    request: AnalysisRequest,
    db: Session,
    actor: UserContext | None = None,
) -> AnalysisResponse:
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
