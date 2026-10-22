from dataclasses import dataclass
from time import monotonic

from sqlalchemy.orm import Session

from app.agents.market_data_agent import fetch_strategy_market_data
from app.agents.protocol_research_agent import retrieve_protocol_context
from app.agents.report_writer_agent import write_research_report
from app.agents.research_tools import (
    DeterministicRiskOutput,
    MarketObservationOutput,
    ProtocolRetrievalOutput,
    ReportSynthesisOutput,
    ResearchToolLedger,
    ResearchToolName,
)
from app.agents.risk_scoring_agent import score_parsed_strategy
from app.agents.strategy_parser import ParsedStrategy, parse_strategy
from app.auth.schemas import UserContext
from app.jobs.cancellation import CancellationContext
from app.llm.base import SynthesisBudget
from app.llm.provenance import ModelRunCandidate, build_report_synthesis_candidate, scope_class_for_actor
from app.llm.quality import ModelQualityEvidence
from app.llm.synthesis import SynthesisResult
from app.rag.citations import validate_retrieval_citations
from app.research_copilot.evidence import build_question_answer, question_evidence_needs_followup
from app.rag.retriever import RetrievalResult
from app.rag.scope import derive_retrieval_scope
from app.risk.framework import RiskScore
from app.schemas.analysis import AnalysisRequest
from app.schemas.market_data import MarketDataResponse
from app.schemas.reports import ReportResponse
from app.schemas.research import ResearchToolTrace


class ResearchWorkflowTimeout(TimeoutError):
    """The bounded synchronous research request exceeded its server deadline."""


@dataclass(frozen=True)
class AnalysisWorkflowResult:
    parsed_strategy: ParsedStrategy
    retrieved_context: list[RetrievalResult]
    market_data: MarketDataResponse
    missing_data: list[str]
    risk_score: RiskScore
    report: ReportResponse
    deterministic_report: ReportResponse
    model_run: ModelRunCandidate
    model_quality: ModelQualityEvidence | None
    pass_count: int = 1
    tool_invocation_count: int = 0
    tool_trace: list[ResearchToolTrace] | None = None
    model_call_count: int = 0
    provider_call_state: str = "not_attempted"
    usage_status: str = "not_applicable"


def run_analysis_workflow(
    request: AnalysisRequest,
    report_id: str,
    db: Session,
    actor: UserContext | None = None,
    organization_id: str | None = None,
    cancellation: CancellationContext | None = None,
    execution_route_snapshot: object | None = None,
    require_execution_route_snapshot: bool = False,
    research_question: str | None = None,
    research_max_passes: int = 1,
    source_document_budget: int = 4,
    max_tool_invocations: int = 8,
    max_model_calls: int = 2,
    deadline_monotonic: float | None = None,
    synthesis_budget: SynthesisBudget | None = None,
    thesis_assumptions: list[str] | None = None,
) -> AnalysisWorkflowResult:
    is_research_run = research_question is not None
    if is_research_run and not 1 <= research_max_passes <= 2:
        raise ValueError("research pass limit must be between one and two")
    if is_research_run and not 1 <= source_document_budget <= 8:
        raise ValueError("research document budget must be between one and eight")
    if is_research_run:
        ledger = ResearchToolLedger(
            max_invocations=max_tool_invocations,
            max_model_calls=max_model_calls,
        )
    else:
        ledger = None

    _check_limits(cancellation, deadline_monotonic)
    parsed_strategy = parse_strategy(request)
    _check_limits(cancellation, deadline_monotonic)
    retrieval_scope = derive_retrieval_scope(db, actor)
    first_query = parsed_strategy.description
    if research_question:
        first_query = f"{parsed_strategy.description}\nResearch question: {research_question}"[:5_000]

    if ledger is None:
        retrieved_context = retrieve_protocol_context(
            first_query,
            parsed_strategy.protocols,
            scope=retrieval_scope,
            db=db,
            actor=actor,
        )
    else:
        first_top_k = min(source_document_budget, max(1, (source_document_budget + 1) // 2))
        retrieved_context = []

        def retrieve_first(_tool_input):
            result = retrieve_protocol_context(
                first_query,
                parsed_strategy.protocols,
                top_k=first_top_k,
                scope=retrieval_scope,
                db=db,
                actor=actor,
            )
            retrieved_context.extend(_limit_unique_documents(result, first_top_k))
            return ProtocolRetrievalOutput(
                chunk_ids=[item.chunk_id for item in retrieved_context],
                protocols=sorted({str(item.metadata.get("protocol", "unknown")) for item in retrieved_context})[:3],
                count=len(retrieved_context),
            )

        ledger.invoke(
            ResearchToolName.PROTOCOL_RETRIEVAL,
            {
                "query": first_query,
                "protocols": _bounded_protocols(parsed_strategy.protocols),
                "top_k": first_top_k,
            },
            retrieve_first,
            pass_number=1,
        )
    _check_limits(cancellation, deadline_monotonic)
    retrieved_context, initial_citation_issues = _validated_context(retrieved_context)

    if ledger is None:
        market_data = fetch_strategy_market_data(parsed_strategy, db)
    else:
        market_holder: dict[str, MarketDataResponse] = {}

        def observe_market(_tool_input):
            result = fetch_strategy_market_data(parsed_strategy, db)
            market_holder["value"] = result
            adapters = result.data.get("adapters", [])
            return MarketObservationOutput(
                status=result.status,
                sources=[str(item.get("source", "unknown"))[:32] for item in adapters[:8]],
                missing_fields=result.missing_fields[:64],
            )

        ledger.invoke(
            ResearchToolName.MARKET_OBSERVATION,
            {
                "protocols": _bounded_protocols(parsed_strategy.protocols),
                "manual_inputs": parsed_strategy.manual_inputs,
            },
            observe_market,
            pass_number=1,
        )
        market_data = market_holder["value"]
    _check_limits(cancellation, deadline_monotonic)

    pass_count = 1
    followup_gap = False
    question_answer = (
        build_question_answer(research_question, retrieved_context)
        if ledger is not None and research_question is not None
        else None
    )
    if ledger is not None and research_max_passes > 1:
        known_protocols = set(_bounded_protocols(parsed_strategy.protocols))
        covered_protocols = {
            str(item.metadata.get("protocol", "")).lower()
            for item in retrieved_context
        }
        missing_protocols = sorted(known_protocols - covered_protocols)
        followup_gap = bool(
            missing_protocols
            or question_evidence_needs_followup(question_answer)
        )
        remaining_documents = source_document_budget - len(retrieved_context)
        if followup_gap and remaining_documents > 0 and ledger.remaining_invocations >= 3:
            pass_count = 2
            focus = ", ".join(missing_protocols) if missing_protocols else "question-relevant evidence"
            followup_query = (
                f"Research question: {research_question}. Follow-up evidence gap: {focus}. "
                "Find separate curated protocol documentation relevant to this question."
            )[:5_000]
            query_protocols = missing_protocols or sorted(known_protocols)

            def retrieve_followup(_tool_input):
                result = retrieve_protocol_context(
                    followup_query,
                    query_protocols,
                    top_k=min(8, remaining_documents),
                    scope=retrieval_scope,
                    db=db,
                    actor=actor,
                )
                retrieved_context.extend(
                    _limit_unique_documents(
                        result,
                        remaining_documents,
                        already_seen=retrieved_context,
                    )
                )
                return ProtocolRetrievalOutput(
                    chunk_ids=[item.chunk_id for item in retrieved_context[:8]],
                    protocols=sorted({str(item.metadata.get("protocol", "unknown")) for item in retrieved_context})[:3],
                    count=len(retrieved_context),
                )

            ledger.invoke(
                ResearchToolName.PROTOCOL_RETRIEVAL,
                {
                    "query": followup_query,
                    "protocols": _bounded_protocols(query_protocols),
                    "top_k": min(8, remaining_documents),
                },
                retrieve_followup,
                pass_number=2,
            )
    _check_limits(cancellation, deadline_monotonic)

    retrieved_context, followup_citation_issues = _validated_context(retrieved_context)
    citation_issues = initial_citation_issues + followup_citation_issues
    if ledger is not None and research_question is not None:
        question_answer = build_question_answer(research_question, retrieved_context)
    missing_data = _build_missing_data(retrieved_context, market_data.missing_fields)
    if ledger is not None:
        final_covered_protocols = {
            str(item.metadata.get("protocol", "")).lower()
            for item in retrieved_context
        }
        still_missing_protocols = sorted(
            set(_bounded_protocols(parsed_strategy.protocols)) - final_covered_protocols
        )
        missing_data.extend(
            f"Research evidence gap: no curated source was retrieved for {protocol}"
            for protocol in still_missing_protocols
        )
    if citation_issues:
        missing_data.append("Research evidence gap: retrieved material with incomplete citation metadata was omitted")
    if question_answer is not None and question_evidence_needs_followup(question_answer):
        missing_data.append(
            "Research evidence gap: question-specific evidence is "
            + ("weak" if question_answer.status == "weak" else "insufficient")
        )
    if question_answer is not None and question_answer.potential_contradictions:
        missing_data.append("Research evidence gap: potentially conflicting source statements require review")
    risk_score: RiskScore
    if ledger is None:
        risk_score = score_parsed_strategy(parsed_strategy, missing_data)
    else:
        risk_holder: dict[str, RiskScore] = {}

        def calculate_risk(_tool_input):
            result = score_parsed_strategy(parsed_strategy, missing_data)
            risk_holder["value"] = result
            return DeterministicRiskOutput(
                score=result.score,
                rating=result.rating,
                confidence=result.confidence,
            )

        ledger.invoke(
            ResearchToolName.DETERMINISTIC_RISK,
            {
                "strategy_description": parsed_strategy.description,
                "protocols": _bounded_protocols(parsed_strategy.protocols),
                "missing_data": missing_data,
            },
            calculate_risk,
            pass_number=pass_count,
        )
        risk_score = risk_holder["value"]
    _check_limits(cancellation, deadline_monotonic)

    content_scope = scope_class_for_actor(actor, organization_id=organization_id)
    if ledger is None:
        synthesis = write_research_report(
            report_id=report_id,
            strategy_description=parsed_strategy.description,
            protocols=parsed_strategy.protocols,
            risk_score=risk_score,
            retrieved_context=retrieved_context,
            market_data=market_data,
            missing_data=missing_data,
            content_scope=content_scope,
            db=db,
            execution_route_snapshot=execution_route_snapshot,
            require_execution_route_snapshot=require_execution_route_snapshot,
        )
    else:
        synthesis_holder: dict[str, SynthesisResult] = {}

        def synthesize(_tool_input):
            result = write_research_report(
                report_id=report_id,
                strategy_description=parsed_strategy.description,
                protocols=parsed_strategy.protocols,
                risk_score=risk_score,
                retrieved_context=retrieved_context,
                market_data=market_data,
                missing_data=missing_data,
                content_scope=content_scope,
                db=db,
                research_question=research_question,
                synthesis_budget=synthesis_budget,
                thesis_assumptions=thesis_assumptions,
                question_answer=question_answer,
            )
            synthesis_holder["value"] = result
            return ReportSynthesisOutput(
                used_llm=result.used_llm,
                outcome=result.outcome,
                provider=result.provider.provider_key if result.provider else None,
                model_key=result.provider.model_key if result.provider else None,
                total_tokens=result.total_tokens,
                cost_microusd=result.cost_microusd,
            )

        ledger.invoke(
            ResearchToolName.REPORT_SYNTHESIS,
            {
                "report_id": report_id,
                "research_question": research_question,
                "source_document_count": len(retrieved_context),
                "token_budget": synthesis_budget.total_tokens if synthesis_budget else 6_000,
                "cost_ceiling_microusd": synthesis_budget.cost_ceiling_microusd if synthesis_budget else 0,
            },
            synthesize,
            pass_number=pass_count,
        )
        synthesis = synthesis_holder["value"]
        if not synthesis.used_llm:
            ledger.trace[-1]["status"] = "fallback"
    _check_limits(cancellation, deadline_monotonic)

    deterministic_report = synthesis.deterministic_report or synthesis.report
    return AnalysisWorkflowResult(
        parsed_strategy=parsed_strategy,
        retrieved_context=retrieved_context,
        market_data=market_data,
        missing_data=missing_data,
        risk_score=risk_score,
        report=synthesis.report,
        deterministic_report=deterministic_report,
        model_run=build_report_synthesis_candidate(
            result=synthesis,
            base_report=deterministic_report,
            retrieved_context=retrieved_context,
            scope_class=content_scope,
        ),
        model_quality=synthesis.quality_evidence,
        pass_count=pass_count,
        tool_invocation_count=len(ledger.trace) if ledger else 0,
        tool_trace=[ResearchToolTrace.model_validate(item) for item in ledger.trace] if ledger else None,
        model_call_count=int(synthesis.provider_call_made),
        provider_call_state=synthesis.provider_call_state,
        usage_status=synthesis.usage_status,
    )


def _check_limits(
    cancellation: CancellationContext | None,
    deadline_monotonic: float | None,
) -> None:
    if cancellation is not None:
        cancellation.raise_if_cancelled()
    if deadline_monotonic is not None and monotonic() >= deadline_monotonic:
        raise ResearchWorkflowTimeout("bounded synchronous research request timed out")


def _bounded_protocols(protocols: list[str]) -> list[str]:
    allowed = {"aave", "morpho", "pendle"}
    return sorted({protocol.lower() for protocol in protocols if protocol.lower() in allowed})[:3]


def _limit_unique_documents(
    results: list[RetrievalResult],
    limit: int,
    *,
    already_seen: list[RetrievalResult] | None = None,
) -> list[RetrievalResult]:
    seen = {
        _document_key(item)
        for item in already_seen or []
    }
    selected: list[RetrievalResult] = []
    for result in results:
        key = _document_key(result)
        if key in seen:
            continue
        selected.append(result)
        seen.add(key)
        if len(selected) >= limit:
            break
    return selected


def _document_key(result: RetrievalResult) -> str:
    metadata = result.metadata
    return str(
        metadata.get("document_version_id")
        or metadata.get("document_title")
        or metadata.get("source_url")
        or result.chunk_id
    )


def _validated_context(results: list[RetrievalResult]) -> tuple[list[RetrievalResult], list[str]]:
    valid: list[RetrievalResult] = []
    issues: list[str] = []
    for result in results:
        result_issues = validate_retrieval_citations([result])
        if result_issues:
            issues.extend(result_issues)
        else:
            valid.append(result)
    return valid, issues


def _build_missing_data(
    retrieved_context: list[RetrievalResult],
    market_missing_fields: list[str],
) -> list[str]:
    missing_data = ["Liquidation buffer calculation"]
    missing_data.extend(f"Market data: {field}" for field in market_missing_fields)
    if not retrieved_context:
        return ["Retrieved protocol documentation"] + missing_data
    return missing_data
