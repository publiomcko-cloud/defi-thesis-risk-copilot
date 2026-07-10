from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.analysis_request import AnalysisRequestModel
from app.rag.citations import results_to_sources
from app.rag.retriever import Retriever
from app.risk.checklist import generate_monitoring_checklist
from app.risk.scenarios import generate_stress_scenarios
from app.risk.scoring import score_strategy_risk
from app.schemas.analysis import AnalysisRequest, AnalysisResponse
from app.schemas.market_data import MarketDataRequest
from app.schemas.reports import ReportResponse, ReportSection, SourceReference
from app.services.market_data_service import fetch_market_data_summary
from app.services.report_service import save_report

DEFAULT_DISCLAIMER = (
    "This report is for research and educational purposes only. "
    "It does not execute trades, connect wallets, custody funds, or provide "
    "personalized financial advice."
)


def analyze_strategy(request: AnalysisRequest, db: Session) -> AnalysisResponse:
    protocols = _normalize_protocols(request)
    retrieved_context = Retriever().retrieve(
        request.strategy_description,
        top_k=4,
        protocols=[protocol for protocol in protocols if protocol != "unknown"],
    )
    market_data = fetch_market_data_summary(
        MarketDataRequest(
            protocols=protocols,
            market_url=request.market_url,
            manual_inputs=request.manual_inputs.model_dump(exclude_none=True),
        ),
        db,
    )
    analysis_request_id = f"analysis_{uuid4().hex[:12]}"
    report_id = f"report_{uuid4().hex[:12]}"
    missing_data = _build_missing_data(retrieved_context, market_data.missing_fields)
    risk_score = score_strategy_risk(
        strategy_description=request.strategy_description,
        protocols=protocols,
        manual_inputs=request.manual_inputs.model_dump(exclude_none=True),
        missing_data=missing_data,
    )
    risk_rating = risk_score.rating
    stress_scenarios = generate_stress_scenarios(risk_score)
    monitoring_checklist = generate_monitoring_checklist(risk_score)
    summary = _build_summary(protocols, risk_score)

    db.add(
        AnalysisRequestModel(
            id=analysis_request_id,
            strategy_description=request.strategy_description,
            protocols=protocols,
            market_url=request.market_url,
            manual_inputs_json=request.manual_inputs.model_dump(exclude_none=True),
            analysis_depth=request.analysis_depth,
        )
    )

    report = ReportResponse(
        report_id=report_id,
        risk_rating=risk_rating,
        executive_summary=summary,
        protocols=protocols,
        assumptions=[
            "Phase 5 uses local curated RAG retrieval without web crawling or live LLM calls.",
            "Manual inputs are treated as user-provided and unverified.",
            "Missing data is explicitly listed instead of being inferred.",
        ],
        missing_data=missing_data,
        sections=[
            ReportSection(
                title="Strategy mechanics",
                content=(
                    "The request is captured and normalized for a future controlled "
                    "analysis workflow covering retrieval, data lookup, risk scoring, "
                    "and report generation."
                ),
            ),
            ReportSection(
                title="Retrieved context",
                content=_summarize_retrieved_context(retrieved_context),
            ),
            ReportSection(
                title="Market data summary",
                content=_summarize_market_data(market_data),
            ),
            ReportSection(
                title="Risk analysis",
                content=_summarize_risk_score(risk_score),
            ),
            ReportSection(
                title="Stress scenarios",
                content=" ".join(stress_scenarios),
            ),
            ReportSection(
                title="Monitoring checklist",
                content=" ".join(monitoring_checklist),
            ),
        ],
        sources=[
            SourceReference(
                title="MVP scope",
                source_type="internal_doc",
                url="docs/mvp_scope.md",
            ),
            SourceReference(
                title="Risk framework",
                source_type="internal_doc",
                url="docs/risk_framework.md",
            ),
        ]
        + results_to_sources(retrieved_context),
        disclaimer=DEFAULT_DISCLAIMER,
    )
    save_report(
        report=report,
        analysis_request_id=analysis_request_id,
        report_markdown=_render_markdown_report(report),
        db=db,
    )
    db.commit()

    return AnalysisResponse(
        report_id=report_id,
        status="completed",
        risk_rating=risk_rating,
        summary=summary,
    )


def _summarize_retrieved_context(retrieved_context: list) -> str:
    if not retrieved_context:
        return (
            "No local RAG chunks were retrieved. Run "
            "`python scripts/ingest_demo_docs.py` to build the local knowledge index."
        )

    summaries = []
    for result in retrieved_context[:3]:
        metadata = result.metadata
        summaries.append(
            f"{metadata['protocol']} / {metadata['section_title']}: "
            f"{result.text.replace(chr(10), ' ')[:220]}"
        )
    return " ".join(summaries)


def _build_missing_data(
    retrieved_context: list,
    market_missing_fields: list[str],
) -> list[str]:
    missing_data = [
        "Liquidation buffer calculation",
    ]
    missing_data.extend(f"Market data: {field}" for field in market_missing_fields)
    if not retrieved_context:
        return ["Retrieved protocol documentation"] + missing_data
    return missing_data


def _summarize_market_data(market_data: object) -> str:
    missing_count = len(market_data.missing_fields)
    adapter_count = len(market_data.data.get("adapters", []))
    if missing_count == 0:
        return f"Market data adapters returned complete normalized output from {adapter_count} sources."
    return (
        f"Market data adapters returned partial normalized output from {adapter_count} sources. "
        f"Missing fields: {', '.join(market_data.missing_fields[:10])}."
    )


def _render_markdown_report(report: ReportResponse) -> str:
    sections = "\n\n".join(
        f"## {section.title}\n\n{section.content}" for section in report.sections
    )
    assumptions = "\n".join(f"- {item}" for item in report.assumptions)
    missing_data = "\n".join(f"- {item}" for item in report.missing_data)
    sources = "\n".join(
        f"- {source.title} ({source.url or source.source_type})"
        for source in report.sources
    )
    return (
        f"# Strategy Risk Report\n\n"
        f"Risk rating: **{report.risk_rating}**\n\n"
        f"{report.executive_summary}\n\n"
        f"{sections}\n\n"
        f"## Assumptions\n\n{assumptions}\n\n"
        f"## Missing Data\n\n{missing_data}\n\n"
        f"## Sources\n\n{sources}\n\n"
        f"## Disclaimer\n\n{report.disclaimer}\n"
    )


def _normalize_protocols(request: AnalysisRequest) -> list[str]:
    if request.protocols:
        return sorted({protocol.lower() for protocol in request.protocols})

    description = request.strategy_description.lower()
    detected = [
        protocol
        for protocol in ("pendle", "morpho", "aave")
        if protocol in description
    ]
    return detected or ["unknown"]


def _summarize_risk_score(risk_score: object) -> str:
    components = "; ".join(
        f"{component.category}: +{component.points} ({component.reason})"
        for component in risk_score.components
    )
    return (
        f"Rule-based score: {risk_score.score}. Rating: {risk_score.rating}. "
        f"Confidence: {risk_score.confidence}. Components: {components}."
    )


def _build_summary(protocols: list[str], risk_score: object) -> str:
    protocol_text = ", ".join(protocols)
    return (
        f"Mock analysis completed for {protocol_text}. "
        f"Rule-based MVP risk rating: {risk_score.rating} "
        f"(score {risk_score.score}, confidence {risk_score.confidence}). "
        "Phase 5 already uses local curated RAG retrieval when the index is present. "
        "Phase 6 adds market data adapters, and Phase 7 adds deterministic risk scoring."
    )
