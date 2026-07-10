from uuid import uuid4

from sqlalchemy.orm import Session

from app.agents.orchestrator import run_analysis_workflow
from app.models.analysis_request import AnalysisRequestModel
from app.reports.markdown_export import render_markdown_report
from app.schemas.analysis import AnalysisRequest, AnalysisResponse
from app.services.report_service import save_report


def analyze_strategy(request: AnalysisRequest, db: Session) -> AnalysisResponse:
    analysis_request_id = f"analysis_{uuid4().hex[:12]}"
    report_id = f"report_{uuid4().hex[:12]}"
    workflow_result = run_analysis_workflow(request, report_id, db)

    db.add(
        AnalysisRequestModel(
            id=analysis_request_id,
            strategy_description=workflow_result.parsed_strategy.description,
            protocols=workflow_result.parsed_strategy.protocols,
            market_url=workflow_result.parsed_strategy.market_url,
            manual_inputs_json=workflow_result.parsed_strategy.manual_inputs,
            analysis_depth=workflow_result.parsed_strategy.analysis_depth,
        )
    )
    save_report(
        report=workflow_result.report,
        analysis_request_id=analysis_request_id,
        report_markdown=render_markdown_report(workflow_result.report),
        db=db,
    )
    db.commit()

    return AnalysisResponse(
        report_id=workflow_result.report.report_id,
        status="completed",
        risk_rating=workflow_result.report.risk_rating,
        summary=workflow_result.report.executive_summary,
    )
