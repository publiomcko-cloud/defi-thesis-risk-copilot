from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.agents.orchestrator import run_analysis_workflow
from app.evaluation.review_queue import upsert_review_item
from app.evaluation.schemas import EvaluateDiscoveredItemResponse, EvaluationResult
from app.models.analysis_request import AnalysisRequestModel
from app.models.discovered_item import DiscoveredItemModel
from app.models.evaluation_result import EvaluationResultModel
from app.reports.markdown_export import render_markdown_report
from app.schemas.analysis import AnalysisRequest
from app.services.report_service import save_report


def evaluate_discovered_item(
    discovered_item_id: str,
    db: Session,
) -> EvaluateDiscoveredItemResponse:
    item = db.get(DiscoveredItemModel, discovered_item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Discovered item not found")

    request = _analysis_request_from_discovered_item(item)
    analysis_request_id = f"eval_analysis_{uuid4().hex[:12]}"
    report_id = f"eval_report_{uuid4().hex[:12]}"
    workflow_result = run_analysis_workflow(request, report_id, db)
    risk_summary = _build_risk_summary(item, workflow_result)

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

    record = EvaluationResultModel(
        id=f"eval_{uuid4().hex[:12]}",
        discovered_item_id=item.id,
        report_id=workflow_result.report.report_id,
        risk_rating=workflow_result.risk_score.rating,
        risk_score=workflow_result.risk_score.score,
        confidence=workflow_result.risk_score.confidence,
        risk_summary=risk_summary,
        missing_data_json=workflow_result.missing_data,
        sources_json=[
            source.model_dump(mode="json") for source in workflow_result.report.sources
        ],
        report_json=workflow_result.report.model_dump(mode="json"),
    )
    db.add(record)
    db.flush()

    review_item = upsert_review_item(item, record, db)
    db.commit()
    db.refresh(record)

    return EvaluateDiscoveredItemResponse(
        status="completed",
        evaluation_result=_evaluation_schema(record),
        review_item=review_item,
    )


def _analysis_request_from_discovered_item(item: DiscoveredItemModel) -> AnalysisRequest:
    strategy_description = (
        f"Evaluate discovered {item.source_type} candidate '{item.title}' from "
        f"{item.source}. Protocol: {item.protocol or 'unknown'}. "
        f"Asset: {item.asset or 'unknown'}. URL: {item.url or 'not provided'}. "
        "Assess research usefulness, source uncertainty, market relevance, missing data, "
        "and whether this candidate should require human review before RAG ingestion."
    )
    protocols = [item.protocol] if item.protocol and item.protocol != "unknown" else []
    return AnalysisRequest(
        strategy_description=strategy_description,
        protocols=protocols,
        market_url=item.url,
        manual_inputs={},
        analysis_depth="quick",
    )


def _build_risk_summary(item: DiscoveredItemModel, workflow_result) -> str:
    drivers = ", ".join(workflow_result.risk_score.main_risk_drivers)
    missing = "; ".join(workflow_result.missing_data[:6]) or "No missing data recorded."
    return (
        f"Discovered {item.source_type} candidate from {item.source} was evaluated "
        f"with deterministic score {workflow_result.risk_score.score} "
        f"({workflow_result.risk_score.rating}, confidence {workflow_result.risk_score.confidence}). "
        f"Main drivers: {drivers or 'none recorded'}. Missing data: {missing}. "
        "This is a research triage summary only; human review is required before any RAG ingestion."
    )


def _evaluation_schema(record: EvaluationResultModel) -> EvaluationResult:
    return EvaluationResult(
        id=record.id,
        discovered_item_id=record.discovered_item_id,
        report_id=record.report_id,
        risk_rating=record.risk_rating,
        risk_score=record.risk_score,
        confidence=record.confidence,
        risk_summary=record.risk_summary,
        missing_data=record.missing_data_json,
        sources=record.sources_json,
        created_at=record.created_at,
    )
