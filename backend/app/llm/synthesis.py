import json
import re
from copy import deepcopy
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from app.core.config import get_settings
from sqlalchemy.orm import Session

from app.llm.base import LLMProvider, LLMRequest
from app.llm.prompts import SYNTHESIZABLE_SECTION_TITLES, build_report_synthesis_prompt
from app.llm.quality import ModelQualityEvidence, evaluate_report_synthesis_quality
from app.llm.provenance import ModelIdentity, provider_identity, provider_is_eligible_for_scope
from app.llm.routing import (
    RouteResolution,
    resolve_report_synthesis_execution_route,
    resolve_report_synthesis_route,
)
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
    outcome: str
    validation_result: str
    fallback_reason: str | None = None
    provider: ModelIdentity | None = None
    latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    cost_microusd: int | None = None
    route_version_id: str | None = None
    evaluation_run_id: str | None = None
    deterministic_report: ReportResponse | None = None
    quality_evidence: ModelQualityEvidence | None = None


class SynthesisValidationError(ValueError):
    def __init__(self, result: str, reason: str) -> None:
        super().__init__(reason)
        self.result = result
        self.reason = reason


def synthesize_report(
    base_report: ReportResponse,
    retrieved_context: list[RetrievalResult],
    market_data: MarketDataResponse,
    risk_score: RiskScore,
    provider: LLMProvider | None = None,
    content_scope: str = "public",
    db: Session | None = None,
    execution_route_snapshot: object | None = None,
    require_execution_route_snapshot: bool = False,
) -> SynthesisResult:
    """Synthesize only through the durable route in production workflows.

    A direct provider is retained only for legacy unit tests and the internal
    evaluation executor, both of which have no application database context.
    Runtime callers always pass ``db`` and cannot turn adapter configuration
    into authority.
    """

    settings = get_settings()
    if not settings.llm_synthesis_enabled:
        return _resolution_fallback(base_report, RouteResolution(None, None, "disabled", "not_run", "synthesis_disabled"))

    if db is not None:
        if require_execution_route_snapshot:
            resolution = resolve_report_synthesis_execution_route(
                db,
                content_scope=content_scope,
                snapshot_payload=execution_route_snapshot,
                configured_provider=provider,
                settings=settings,
            )
        else:
            resolution = resolve_report_synthesis_route(
                db,
                content_scope=content_scope,
                configured_provider=provider,
                settings=settings,
            )
        if resolution.provider is None:
            return _resolution_fallback(base_report, resolution)
        return _synthesize_with_provider(
            base_report,
            retrieved_context,
            market_data,
            risk_score,
            resolution.provider,
            content_scope,
            route_version_id=resolution.route_version_id,
            evaluation_run_id=resolution.evaluation_run_id,
        )

    if provider is None:
        return _resolution_fallback(base_report, RouteResolution(None, None, "provider_unavailable", "not_run", "no_route_context"))
    return _synthesize_with_provider(base_report, retrieved_context, market_data, risk_score, provider, content_scope)


def synthesize_report_for_evaluation(
    base_report: ReportResponse,
    retrieved_context: list[RetrievalResult],
    market_data: MarketDataResponse,
    risk_score: RiskScore,
    provider: LLMProvider,
) -> SynthesisResult:
    """Internal deterministic evaluator helper; it is never a runtime route."""

    return _synthesize_with_provider(base_report, retrieved_context, market_data, risk_score, provider, "public")


def _synthesize_with_provider(
    base_report: ReportResponse,
    retrieved_context: list[RetrievalResult],
    market_data: MarketDataResponse,
    risk_score: RiskScore,
    active_provider: LLMProvider,
    content_scope: str,
    *,
    route_version_id: str | None = None,
    evaluation_run_id: str | None = None,
) -> SynthesisResult:
    settings = get_settings()
    identity = provider_identity(active_provider)
    if not provider_is_eligible_for_scope(identity, content_scope):
        return SynthesisResult(
            report=_with_assumption(base_report, LLM_SKIPPED_ASSUMPTION),
            used_llm=False,
            reason="provider_unavailable",
            outcome="provider_unavailable",
            validation_result="policy_denied",
            fallback_reason="private_provider_not_approved",
            provider=identity,
            route_version_id=route_version_id,
            evaluation_run_id=evaluation_run_id,
        )

    started = perf_counter()
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
        _validate_synthesis_payload(payload)
        synthesized = _apply_allowed_synthesis(base_report, payload)
        quality = evaluate_report_synthesis_quality(base_report, synthesized, retrieved_context)
        if not quality.overall_quality_pass:
            return _quality_fallback(
                base_report,
                identity,
                started,
                quality,
                route_version_id,
                evaluation_run_id,
            )
        synthesized = _with_assumption(
            synthesized,
            f"{LLM_USED_ASSUMPTION} Provider: {response.provider}; model: {response.model}.",
        )
        validate_report_structure(synthesized)
        return SynthesisResult(
            report=synthesized,
            used_llm=True,
            reason="succeeded",
            outcome="succeeded",
            validation_result="accepted",
            provider=identity,
            latency_ms=_elapsed_ms(started),
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            total_tokens=response.total_tokens,
            cost_microusd=response.cost_microusd,
            route_version_id=route_version_id,
            evaluation_run_id=evaluation_run_id,
            quality_evidence=quality,
        )
    except json.JSONDecodeError:
        return _validation_fallback(base_report, identity, started, "invalid_json", "malformed_json", route_version_id, evaluation_run_id)
    except SynthesisValidationError as exc:
        return _validation_fallback(base_report, identity, started, exc.result, exc.reason, route_version_id, evaluation_run_id)
    except ValueError:
        return _validation_fallback(base_report, identity, started, "schema_invalid", "schema_validation_failed", route_version_id, evaluation_run_id)
    except Exception:
        return SynthesisResult(
            report=_with_assumption(base_report, LLM_SKIPPED_ASSUMPTION),
            used_llm=False,
            reason="provider_failure",
            outcome="provider_failure",
            validation_result="provider_error",
            fallback_reason="provider_error",
            provider=identity,
            latency_ms=_elapsed_ms(started),
            route_version_id=route_version_id,
            evaluation_run_id=evaluation_run_id,
        )


def _validation_fallback(
    base_report: ReportResponse,
    provider: ModelIdentity | None,
    started: float,
    validation_result: str,
    fallback_reason: str,
    route_version_id: str | None = None,
    evaluation_run_id: str | None = None,
) -> SynthesisResult:
    return SynthesisResult(
        report=_with_assumption(base_report, LLM_SKIPPED_ASSUMPTION),
        used_llm=False,
        reason="validation_fallback",
        outcome="validation_fallback",
        validation_result=validation_result,
        fallback_reason=fallback_reason,
        provider=provider,
        latency_ms=_elapsed_ms(started),
        route_version_id=route_version_id,
        evaluation_run_id=evaluation_run_id,
    )


def _quality_fallback(
    base_report: ReportResponse,
    provider: ModelIdentity | None,
    started: float,
    quality: ModelQualityEvidence,
    route_version_id: str | None,
    evaluation_run_id: str | None,
) -> SynthesisResult:
    return SynthesisResult(
        report=_with_assumption(base_report, LLM_SKIPPED_ASSUMPTION),
        used_llm=False,
        reason="validation_fallback",
        outcome="validation_fallback",
        validation_result="unsafe_output" if quality.unsafe_language_violation else "schema_invalid",
        fallback_reason=quality.reason_code or "quality_policy_failed",
        provider=provider,
        latency_ms=_elapsed_ms(started),
        route_version_id=route_version_id,
        evaluation_run_id=evaluation_run_id,
        quality_evidence=quality,
    )


def _resolution_fallback(base_report: ReportResponse, resolution: RouteResolution) -> SynthesisResult:
    return SynthesisResult(
        report=_with_assumption(base_report, LLM_SKIPPED_ASSUMPTION),
        used_llm=False,
        reason=resolution.outcome,
        outcome=resolution.outcome,
        validation_result=resolution.validation_result,
        fallback_reason=resolution.fallback_reason,
        provider=resolution.identity,
        route_version_id=resolution.route_version_id,
        evaluation_run_id=resolution.evaluation_run_id,
    )


def _apply_allowed_synthesis(
    base_report: ReportResponse,
    payload: dict[str, Any],
) -> ReportResponse:
    report = base_report.model_copy(deep=True)
    executive_summary = payload["executive_summary"]
    report.executive_summary = executive_summary.strip()

    sections = payload["sections"]
    for section in report.sections:
        candidate = sections.get(section.title)
        if candidate is not None:
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
        "Risk Analysis",
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


def _validate_synthesis_payload(payload: dict[str, Any]) -> None:
    if set(payload) != {"executive_summary", "sections"}:
        raise SynthesisValidationError("schema_invalid", "unexpected_output_fields")
    summary = payload.get("executive_summary")
    sections = payload.get("sections")
    if not isinstance(summary, str) or not 1 <= len(summary.strip()) <= 4000:
        raise SynthesisValidationError("schema_invalid", "invalid_executive_summary")
    if not isinstance(sections, dict):
        raise SynthesisValidationError("schema_invalid", "invalid_sections")
    allowed_titles = set(SYNTHESIZABLE_SECTION_TITLES)
    if not set(sections).issubset(allowed_titles):
        raise SynthesisValidationError("schema_invalid", "unexpected_section")
    for title, content in sections.items():
        if not isinstance(title, str) or not isinstance(content, str) or not 1 <= len(content.strip()) <= 4000:
            raise SynthesisValidationError("schema_invalid", "invalid_section_content")


def _with_assumption(report: ReportResponse, assumption: str) -> ReportResponse:
    updated = report.model_copy(deep=True)
    updated.assumptions = [
        item for item in updated.assumptions if not item.startswith("Optional LLM synthesis")
    ]
    updated.assumptions.append(assumption)
    return updated


def _elapsed_ms(started: float) -> int:
    return min(max(int(round((perf_counter() - started) * 1000)), 0), 3_600_000)
