from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.analysis_request import AnalysisRequestModel
from app.rag.citations import results_to_sources
from app.rag.retriever import Retriever
from app.schemas.analysis import AnalysisRequest, AnalysisResponse, RiskRating
from app.schemas.reports import ReportResponse, ReportSection, SourceReference
from app.services.report_service import save_report

DEFAULT_DISCLAIMER = (
    "This report is for research and educational purposes only. "
    "It does not execute trades, connect wallets, custody funds, or provide "
    "personalized financial advice."
)


def analyze_strategy(request: AnalysisRequest, db: Session) -> AnalysisResponse:
    protocols = _normalize_protocols(request)
    risk_rating = _mock_risk_rating(protocols, request)
    retrieved_context = Retriever().retrieve(
        request.strategy_description,
        top_k=4,
        protocols=[protocol for protocol in protocols if protocol != "unknown"],
    )
    analysis_request_id = f"analysis_{uuid4().hex[:12]}"
    report_id = f"report_{uuid4().hex[:12]}"
    summary = _build_summary(protocols, risk_rating)

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
        missing_data=[
            "Retrieved protocol documentation",
            "Live liquidity depth",
            "Current borrow APY",
            "Oracle configuration",
            "Liquidation buffer calculation",
        ],
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
                title="Risk analysis",
                content=(
                    f"Mock rating: {risk_rating}. This placeholder favors caution "
                    "for multi-protocol or leveraged DeFi strategies until real "
                    "risk scoring is implemented."
                ),
            ),
            ReportSection(
                title="Monitoring checklist",
                content=(
                    "Track borrow APY, liquidity, oracle status, maturity timing, "
                    "collateral movement, protocol changes, and missing assumptions."
                ),
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


def _mock_risk_rating(
    protocols: list[str],
    request: AnalysisRequest,
) -> RiskRating:
    score = 1
    if len([protocol for protocol in protocols if protocol != "unknown"]) > 1:
        score += 2
    if request.manual_inputs.ltv is not None and request.manual_inputs.ltv > 0:
        score += 1
    if request.manual_inputs.borrow_apy is None:
        score += 1
    if request.manual_inputs.liquidity_usd is None:
        score += 1

    if score <= 2:
        return "Conservative"
    if score <= 4:
        return "Moderate"
    if score <= 6:
        return "Aggressive"
    return "Very Risky"


def _build_summary(protocols: list[str], risk_rating: RiskRating) -> str:
    protocol_text = ", ".join(protocols)
    return (
        f"Mock analysis completed for {protocol_text}. "
        f"Initial placeholder risk rating: {risk_rating}. "
        "Future phases will replace this with source-backed retrieval, market data, "
        "and deterministic risk scoring."
    )
