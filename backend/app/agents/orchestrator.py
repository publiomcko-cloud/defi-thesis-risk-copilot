from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.agents.market_data_agent import fetch_strategy_market_data
from app.agents.protocol_research_agent import retrieve_protocol_context
from app.agents.report_writer_agent import write_research_report
from app.agents.risk_scoring_agent import score_parsed_strategy
from app.agents.strategy_parser import ParsedStrategy, parse_strategy
from app.rag.retriever import RetrievalResult
from app.rag.scope import derive_retrieval_scope
from app.auth.schemas import UserContext
from app.llm.provenance import ModelRunCandidate, build_report_synthesis_candidate, scope_class_for_actor
from app.jobs.cancellation import CancellationContext
from app.risk.framework import RiskScore
from app.schemas.analysis import AnalysisRequest
from app.schemas.market_data import MarketDataResponse
from app.schemas.reports import ReportResponse


@dataclass(frozen=True)
class AnalysisWorkflowResult:
    parsed_strategy: ParsedStrategy
    retrieved_context: list[RetrievalResult]
    market_data: MarketDataResponse
    missing_data: list[str]
    risk_score: RiskScore
    report: ReportResponse
    model_run: ModelRunCandidate


def run_analysis_workflow(
    request: AnalysisRequest,
    report_id: str,
    db: Session,
    actor: UserContext | None = None,
    organization_id: str | None = None,
    cancellation: CancellationContext | None = None,
) -> AnalysisWorkflowResult:
    _check_cancelled(cancellation)
    parsed_strategy = parse_strategy(request)
    _check_cancelled(cancellation)
    retrieved_context = retrieve_protocol_context(
        parsed_strategy.description,
        parsed_strategy.protocols,
        scope=derive_retrieval_scope(db, actor),
        db=db,
        actor=actor,
    )
    _check_cancelled(cancellation)
    market_data = fetch_strategy_market_data(parsed_strategy, db)
    _check_cancelled(cancellation)
    missing_data = _build_missing_data(retrieved_context, market_data.missing_fields)
    risk_score = score_parsed_strategy(parsed_strategy, missing_data)
    _check_cancelled(cancellation)
    content_scope = scope_class_for_actor(actor, organization_id=organization_id)
    synthesis = write_research_report(
        report_id=report_id,
        strategy_description=parsed_strategy.description,
        protocols=parsed_strategy.protocols,
        risk_score=risk_score,
        retrieved_context=retrieved_context,
        market_data=market_data,
        missing_data=missing_data,
        content_scope=content_scope,
    )
    _check_cancelled(cancellation)

    return AnalysisWorkflowResult(
        parsed_strategy=parsed_strategy,
        retrieved_context=retrieved_context,
        market_data=market_data,
        missing_data=missing_data,
        risk_score=risk_score,
        report=synthesis.report,
        model_run=build_report_synthesis_candidate(
            result=synthesis,
            base_report=synthesis.report,
            retrieved_context=retrieved_context,
            scope_class=content_scope,
        ),
    )


def _check_cancelled(cancellation: CancellationContext | None) -> None:
    if cancellation is not None:
        cancellation.raise_if_cancelled()


def _build_missing_data(
    retrieved_context: list[RetrievalResult],
    market_missing_fields: list[str],
) -> list[str]:
    missing_data = [
        "Liquidation buffer calculation",
    ]
    missing_data.extend(f"Market data: {field}" for field in market_missing_fields)
    if not retrieved_context:
        return ["Retrieved protocol documentation"] + missing_data
    return missing_data
