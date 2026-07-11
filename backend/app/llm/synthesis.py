import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from app.core.config import get_settings
from app.llm.base import LLMProvider, LLMRequest
from app.llm.prompts import SYNTHESIZABLE_SECTION_TITLES, build_report_synthesis_prompt
from app.llm.providers import get_llm_provider
from app.rag.retriever import RetrievalResult
from app.reports.renderer import validate_report_structure
from app.risk.framework import RiskScore
from app.schemas.market_data import MarketDataResponse
from app.schemas.reports import ReportResponse

LLM_USED_ASSUMPTION = (
    "Optional LLM synthesis was used only to improve explanatory wording; "
    "deterministic risk scoring, missing data, sources, market values, and safety rules remain authoritative."
)
LLM_SKIPPED_ASSUMPTION = (
    "Optional LLM synthesis was skipped or unavailable; deterministic report template wording was used."
)


@dataclass(frozen=True)
class SynthesisResult:
    report: ReportResponse
    used_llm: bool
    reason: str


def synthesize_report(
    base_report: ReportResponse,
    retrieved_context: list[RetrievalResult],
    market_data: MarketDataResponse,
    risk_score: RiskScore,
    provider: LLMProvider | None = None,
) -> SynthesisResult:
    settings = get_settings()
    if not settings.llm_synthesis_enabled:
        return SynthesisResult(
            report=_with_assumption(base_report, LLM_SKIPPED_ASSUMPTION),
            used_llm=False,
            reason="disabled",
        )

    active_provider = provider or get_llm_provider(settings)
    if active_provider is None:
        return SynthesisResult(
            report=_with_assumption(base_report, LLM_SKIPPED_ASSUMPTION),
            used_llm=False,
            reason="provider_unavailable",
        )

    try:
        prompt = build_report_synthesis_prompt(
            base_report=base_report,
            retrieved_context=retrieved_context,
            market_data=market_data,
            risk_score=risk_score,
        )
        response = active_provider.generate(
            LLMRequest(
                prompt=prompt,
                timeout_seconds=settings.llm_timeout_seconds,
            )
        )
        payload = _parse_json_object(response.text)
        synthesized = _apply_allowed_synthesis(base_report, payload, risk_score)
        synthesized = _with_assumption(
            synthesized,
            f"{LLM_USED_ASSUMPTION} Provider: {response.provider}; model: {response.model}.",
        )
        validate_report_structure(synthesized)
        return SynthesisResult(
            report=synthesized,
            used_llm=True,
            reason="synthesized",
        )
    except Exception:
        return SynthesisResult(
            report=_with_assumption(base_report, LLM_SKIPPED_ASSUMPTION),
            used_llm=False,
            reason="fallback",
        )


def _apply_allowed_synthesis(
    base_report: ReportResponse,
    payload: dict[str, Any],
    risk_score: RiskScore,
) -> ReportResponse:
    report = base_report.model_copy(deep=True)
    executive_summary = payload.get("executive_summary")
    if isinstance(executive_summary, str) and _is_safe_text(executive_summary):
        report.executive_summary = executive_summary.strip()

    sections = payload.get("sections")
    if isinstance(sections, dict):
        allowed_titles = set(SYNTHESIZABLE_SECTION_TITLES)
        for section in report.sections:
            candidate = sections.get(section.title)
            if (
                section.title in allowed_titles
                and isinstance(candidate, str)
                and _is_safe_text(candidate)
                and _preserves_required_section_facts(section.title, candidate, risk_score)
            ):
                section.content = candidate.strip()

    _enforce_immutable_fields(report, base_report)
    validate_report_structure(report)
    return report


def _enforce_immutable_fields(report: ReportResponse, base_report: ReportResponse) -> None:
    report.report_id = base_report.report_id
    report.status = base_report.status
    report.risk_rating = base_report.risk_rating
    report.strategy_description = base_report.strategy_description
    report.protocols = deepcopy(base_report.protocols)
    report.missing_data = deepcopy(base_report.missing_data)
    report.sources = deepcopy(base_report.sources)
    report.disclaimer = base_report.disclaimer

    immutable_sections = {
        "Strategy Description",
        "Protocols Involved",
        "Risk Rating",
        "Missing Data and Uncertainty",
        "Sources",
        "Disclaimer",
    }
    base_sections = {section.title: section.content for section in base_report.sections}
    for section in report.sections:
        if section.title in immutable_sections:
            section.content = base_sections[section.title]


def _parse_json_object(text: str) -> dict[str, Any]:
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("LLM response must be a JSON object")
    return parsed


def _with_assumption(report: ReportResponse, assumption: str) -> ReportResponse:
    updated = report.model_copy(deep=True)
    updated.assumptions = [
        item for item in updated.assumptions if not item.startswith("Optional LLM synthesis")
    ]
    updated.assumptions.append(assumption)
    return updated


def _is_safe_text(text: str) -> bool:
    lowered = text.lower()
    blocked_phrases = [
        "you should buy",
        "you should sell",
        "buy this",
        "sell this",
        "enter this trade",
        "execute this trade",
        "connect your wallet",
        "not financial advice, but",
    ]
    return not any(phrase in lowered for phrase in blocked_phrases)


def _preserves_required_section_facts(
    title: str,
    text: str,
    risk_score: RiskScore,
) -> bool:
    if title != "Risk Analysis":
        return True
    return risk_score.rating in text and str(risk_score.score) in text
