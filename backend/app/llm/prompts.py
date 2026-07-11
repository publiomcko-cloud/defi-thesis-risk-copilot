import json

from app.rag.retriever import RetrievalResult
from app.risk.framework import RiskScore
from app.schemas.market_data import MarketDataResponse
from app.schemas.reports import ReportResponse

SAFETY_RULES = [
    "Do not connect wallets.",
    "Do not execute trades.",
    "Do not provide buy, sell, hold, entry, exit, or position-sizing instructions.",
    "Do not provide personalized financial, investment, legal, or tax advice.",
    "Do not invent market values, missing fields, or sources.",
    "Do not change the deterministic risk rating, risk score, missing data, sources, or disclaimer.",
    "Use educational, non-advisory language.",
]

SYNTHESIZABLE_SECTION_TITLES = [
    "Strategy Mechanics",
    "Yield Source",
    "Key Assumptions",
    "Risk Analysis",
    "Stress Scenarios",
    "Exit Plan",
    "Monitoring Checklist",
]


def build_report_synthesis_prompt(
    base_report: ReportResponse,
    retrieved_context: list[RetrievalResult],
    market_data: MarketDataResponse,
    risk_score: RiskScore,
) -> str:
    payload = {
        "task": (
            "Rewrite or enrich only the allowed explanatory report sections. "
            "Return strict JSON with keys: executive_summary and sections. "
            "sections must be an object keyed by section title."
        ),
        "allowed_section_titles": SYNTHESIZABLE_SECTION_TITLES,
        "immutable_fields": {
            "report_id": base_report.report_id,
            "risk_rating": base_report.risk_rating,
            "protocols": base_report.protocols,
            "missing_data": base_report.missing_data,
            "sources": [source.model_dump(mode="json") for source in base_report.sources],
            "disclaimer": base_report.disclaimer,
        },
        "strategy_description": base_report.strategy_description,
        "deterministic_executive_summary": base_report.executive_summary,
        "deterministic_sections": {
            section.title: section.content for section in base_report.sections
        },
        "retrieved_rag_context": [
            {
                "text": result.text,
                "metadata": result.metadata,
                "similarity_score": result.similarity_score,
            }
            for result in retrieved_context
        ],
        "market_data_summary": {
            "status": market_data.status,
            "source": market_data.source,
            "missing_fields": market_data.missing_fields,
            "assumptions": market_data.assumptions,
            "data": market_data.data,
        },
        "risk_score": {
            "score": risk_score.score,
            "rating": risk_score.rating,
            "confidence": risk_score.confidence,
            "main_risk_drivers": risk_score.main_risk_drivers,
            "components": [
                component.__dict__ for component in risk_score.components
            ],
        },
        "safety_rules": SAFETY_RULES,
    }
    return (
        "You are a controlled report synthesis layer for a DeFi research app.\n"
        "Use the JSON context below. Return only valid JSON. Do not use markdown fences.\n"
        "The JSON output shape must be:\n"
        "{\"executive_summary\":\"...\", \"sections\": {\"Section Title\":\"content\"}}\n\n"
        f"{json.dumps(payload, indent=2)}"
    )
