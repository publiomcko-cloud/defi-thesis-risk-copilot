from app.rag.citations import results_to_sources
from app.rag.retriever import RetrievalResult
from app.risk.checklist import generate_monitoring_checklist
from app.risk.framework import RiskScore
from app.risk.scenarios import generate_stress_scenarios
from app.schemas.market_data import MarketDataResponse
from app.schemas.reports import ReportResponse, ReportSection, SourceReference

DEFAULT_DISCLAIMER = (
    "This report is for research and educational purposes only. "
    "It does not execute trades, connect wallets, custody funds, or provide "
    "personalized financial advice."
)


def write_research_report(
    report_id: str,
    protocols: list[str],
    risk_score: RiskScore,
    retrieved_context: list[RetrievalResult],
    market_data: MarketDataResponse,
    missing_data: list[str],
) -> ReportResponse:
    return ReportResponse(
        report_id=report_id,
        risk_rating=risk_score.rating,
        executive_summary=_build_summary(protocols, risk_score),
        protocols=protocols,
        assumptions=[
            "Controlled workflow uses local curated RAG retrieval without web crawling or live LLM calls.",
            "Manual inputs are treated as user-provided and unverified.",
            "Missing data is explicitly listed instead of being inferred.",
        ],
        missing_data=missing_data,
        sections=[
            ReportSection(
                title="Strategy mechanics",
                content=(
                    "The request is parsed, protocols are detected, local sources are retrieved, "
                    "market data adapters are queried, rule-based risk scoring runs, and this "
                    "structured report is generated."
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
                content=" ".join(generate_stress_scenarios(risk_score)),
            ),
            ReportSection(
                title="Monitoring checklist",
                content=" ".join(generate_monitoring_checklist(risk_score)),
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


def render_markdown_report(report: ReportResponse) -> str:
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


def _summarize_retrieved_context(retrieved_context: list[RetrievalResult]) -> str:
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


def _summarize_market_data(market_data: MarketDataResponse) -> str:
    missing_count = len(market_data.missing_fields)
    adapter_count = len(market_data.data.get("adapters", []))
    if missing_count == 0:
        return f"Market data adapters returned complete normalized output from {adapter_count} sources."
    return (
        f"Market data adapters returned partial normalized output from {adapter_count} sources. "
        f"Missing fields: {', '.join(market_data.missing_fields[:10])}."
    )


def _summarize_risk_score(risk_score: RiskScore) -> str:
    components = "; ".join(
        f"{component.category}: +{component.points} ({component.reason})"
        for component in risk_score.components
    )
    return (
        f"Rule-based score: {risk_score.score}. Rating: {risk_score.rating}. "
        f"Confidence: {risk_score.confidence}. Components: {components}."
    )


def _build_summary(protocols: list[str], risk_score: RiskScore) -> str:
    protocol_text = ", ".join(protocols)
    return (
        f"Controlled analysis completed for {protocol_text}. "
        f"Rule-based MVP risk rating: {risk_score.rating} "
        f"(score {risk_score.score}, confidence {risk_score.confidence}). "
        "The workflow used local RAG retrieval, market data adapters, and deterministic scoring."
    )
