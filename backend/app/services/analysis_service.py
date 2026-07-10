from uuid import uuid4

from app.schemas.analysis import AnalysisRequest, AnalysisResponse, RiskRating
from app.schemas.reports import ReportResponse, ReportSection, SourceReference
from app.services.report_service import save_report

DEFAULT_DISCLAIMER = (
    "This report is for research and educational purposes only. "
    "It does not execute trades, connect wallets, custody funds, or provide "
    "personalized financial advice."
)


def analyze_strategy(request: AnalysisRequest) -> AnalysisResponse:
    protocols = _normalize_protocols(request)
    risk_rating = _mock_risk_rating(protocols, request)
    report_id = f"report_{uuid4().hex[:12]}"
    summary = _build_summary(protocols, risk_rating)

    report = ReportResponse(
        report_id=report_id,
        risk_rating=risk_rating,
        executive_summary=summary,
        protocols=protocols,
        assumptions=[
            "Phase 2 uses mocked analysis without live RAG, market data, or LLM calls.",
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
        ],
        disclaimer=DEFAULT_DISCLAIMER,
    )
    save_report(report)

    return AnalysisResponse(
        report_id=report_id,
        status="completed",
        risk_rating=risk_rating,
        summary=summary,
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
