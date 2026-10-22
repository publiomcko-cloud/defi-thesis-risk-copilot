import json
import re
from copy import deepcopy
from dataclasses import dataclass
from math import ceil
from time import monotonic, perf_counter
from typing import Any

import httpx

from app.core.config import get_settings
from sqlalchemy.orm import Session

from app.llm.base import LLMProvider, LLMRequest, LLMResponse, SynthesisBudget
from app.llm.prompts import (
    REPORT_SYNTHESIS_SYSTEM_PROMPT,
    SYNTHESIZABLE_SECTION_TITLES,
    build_report_synthesis_prompt,
)
from app.llm.quality import ModelQualityEvidence, evaluate_report_synthesis_quality
from app.llm.provenance import ModelIdentity, provider_identity, provider_is_eligible_for_scope
from app.models.model_governance import ModelRegistryModel
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
_PROVIDER_WRAPPER_TOKEN_RESERVE = 128


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
    reported_total_tokens: int | None = None
    cost_microusd: int | None = None
    route_version_id: str | None = None
    evaluation_run_id: str | None = None
    deterministic_report: ReportResponse | None = None
    quality_evidence: ModelQualityEvidence | None = None
    provider_call_made: bool = False
    provider_call_state: str = "not_attempted"
    usage_status: str = "not_applicable"


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
    budget: SynthesisBudget | None = None,
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
            db=db,
            route_version_id=resolution.route_version_id,
            evaluation_run_id=resolution.evaluation_run_id,
            model_registry_id=resolution.model_registry_id,
            budget=budget,
        )

    if provider is None:
        return _resolution_fallback(base_report, RouteResolution(None, None, "provider_unavailable", "not_run", "no_route_context"))
    return _synthesize_with_provider(
        base_report,
        retrieved_context,
        market_data,
        risk_score,
        provider,
        content_scope,
        budget=budget,
    )


def synthesize_report_for_evaluation(
    base_report: ReportResponse,
    retrieved_context: list[RetrievalResult],
    market_data: MarketDataResponse,
    risk_score: RiskScore,
    provider: LLMProvider,
) -> SynthesisResult:
    """Internal deterministic evaluator helper; it is never a runtime route."""

    return _synthesize_with_provider(
        base_report,
        retrieved_context,
        market_data,
        risk_score,
        provider,
        "public",
        include_instruction_flags=False,
    )


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
    model_registry_id: str | None = None,
    budget: SynthesisBudget | None = None,
    db: Session | None = None,
    include_instruction_flags: bool = True,
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
    response: LLMResponse | None = None
    actual_cost: int | None = None
    actual_total_tokens: int | None = None
    try:
        prompt = build_report_synthesis_prompt(
            base_report=base_report,
            retrieved_context=retrieved_context,
            market_data=market_data,
            risk_score=risk_score,
            include_instruction_flags=include_instruction_flags,
        )
        max_output_tokens = None
        cost_rates: tuple[int, int] | None = None
        if budget is not None:
            max_output_tokens, cost_rates, budget_failure = _preflight_synthesis_budget(
                prompt,
                budget,
                db,
                model_registry_id,
            )
            if budget_failure is not None:
                return _budget_fallback(
                    base_report,
                    identity,
                    budget_failure,
                    route_version_id,
                    evaluation_run_id,
                )
        provider_timeout = settings.llm_timeout_seconds
        if budget is not None and budget.deadline_monotonic is not None:
            remaining_time = budget.deadline_monotonic - monotonic()
            if remaining_time <= 0.01:
                return _budget_fallback(
                    base_report,
                    identity,
                    "run_wall_time_exhausted",
                    route_version_id,
                    evaluation_run_id,
                )
            provider_timeout = min(provider_timeout, remaining_time)
        response = active_provider.generate(
            LLMRequest(
                prompt=prompt,
                timeout_seconds=provider_timeout,
                max_output_tokens=max_output_tokens,
                system_prompt=REPORT_SYNTHESIS_SYSTEM_PROMPT,
            )
        )
        actual_cost = _valid_cost_value(response.cost_microusd)
        actual_total_tokens = _effective_total_tokens(response)
        input_tokens = _valid_token_value(response.input_tokens)
        output_tokens = _valid_token_value(response.output_tokens)
        if response.cost_microusd is None and cost_rates is not None:
            input_rate, output_rate = cost_rates
            if input_tokens is not None and output_tokens is not None:
                actual_cost = ceil(
                    (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000
                )
        if budget is not None:
            usage_status = _usage_status(response, actual_cost, actual_total_tokens)
            if usage_status in {"invalid", "inconsistent"}:
                return _budget_fallback(
                    base_report,
                    identity,
                    "provider_usage_invalid" if usage_status == "invalid" else "provider_usage_inconsistent",
                    route_version_id,
                    evaluation_run_id,
                    response=response,
                    actual_cost=actual_cost,
                    actual_total_tokens=actual_total_tokens,
                )
            if any(value is None for value in (input_tokens, output_tokens, actual_total_tokens, actual_cost)):
                return _budget_fallback(
                    base_report,
                    identity,
                    "provider_usage_unverifiable",
                    route_version_id,
                    evaluation_run_id,
                    response=response,
                    actual_cost=actual_cost,
                    actual_total_tokens=actual_total_tokens,
                )
            if output_tokens > max_output_tokens or actual_total_tokens > budget.total_tokens:
                return _budget_fallback(
                    base_report,
                    identity,
                    "provider_exceeded_token_budget",
                    route_version_id,
                    evaluation_run_id,
                    response=response,
                    actual_cost=actual_cost,
                    actual_total_tokens=actual_total_tokens,
                )
            if actual_cost > budget.cost_ceiling_microusd:
                return _budget_fallback(
                    base_report,
                    identity,
                    "provider_exceeded_cost_ceiling",
                    route_version_id,
                    evaluation_run_id,
                    response=response,
                    actual_cost=actual_cost,
                    actual_total_tokens=actual_total_tokens,
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
                response=response,
                actual_cost=actual_cost,
                actual_total_tokens=actual_total_tokens,
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
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=actual_total_tokens,
            reported_total_tokens=_valid_token_value(response.total_tokens),
            cost_microusd=actual_cost,
            route_version_id=route_version_id,
            evaluation_run_id=evaluation_run_id,
            quality_evidence=quality,
            provider_call_made=True,
            provider_call_state="output_accepted",
            usage_status=_usage_status(response, actual_cost, actual_total_tokens),
        )
    except json.JSONDecodeError:
        return _validation_fallback(base_report, identity, started, "invalid_json", "malformed_json", route_version_id, evaluation_run_id, response, actual_cost, actual_total_tokens)
    except SynthesisValidationError as exc:
        return _validation_fallback(base_report, identity, started, exc.result, exc.reason, route_version_id, evaluation_run_id, response, actual_cost, actual_total_tokens)
    except ValueError:
        return _validation_fallback(base_report, identity, started, "schema_invalid", "schema_validation_failed", route_version_id, evaluation_run_id, response, actual_cost, actual_total_tokens)
    except (httpx.ConnectError, httpx.ConnectTimeout):
        return SynthesisResult(
            report=_with_assumption(base_report, LLM_SKIPPED_ASSUMPTION),
            used_llm=False,
            reason="provider_unavailable",
            outcome="provider_unavailable",
            validation_result="connection_not_established",
            fallback_reason="provider_connection_failed_before_transmission",
            provider=identity,
            latency_ms=_elapsed_ms(started),
            route_version_id=route_version_id,
            evaluation_run_id=evaluation_run_id,
            provider_call_state="rejected_before_transmission",
            usage_status="not_applicable",
        )
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
            provider_call_made=True,
            provider_call_state="uncertain",
            usage_status="unknown",
        )


def _preflight_synthesis_budget(
    prompt: str,
    budget: SynthesisBudget,
    db: Session | None,
    model_registry_id: str | None,
) -> tuple[int | None, tuple[int, int] | None, str | None]:
    # Without a provider-specific tokenizer, a UTF-8 byte count is a
    # conservative token upper bound for text plus a fixed reserve for message
    # framing/system instructions. Never understate the prompt for preflight.
    estimated_input_tokens = len(prompt.encode("utf-8")) + _PROVIDER_WRAPPER_TOKEN_RESERVE
    max_output_tokens = min(
        budget.max_output_tokens,
        budget.total_tokens - estimated_input_tokens,
    )
    if max_output_tokens < 1:
        return None, None, "token_budget_insufficient"
    if db is None or model_registry_id is None:
        return None, None, "cost_ceiling_unpriced_route"
    model = db.get(ModelRegistryModel, model_registry_id)
    if (
        model is None
        or model.input_cost_microusd_per_million is None
        or model.output_cost_microusd_per_million is None
    ):
        return None, None, "cost_ceiling_unpriced_route"
    rates = (
        model.input_cost_microusd_per_million,
        model.output_cost_microusd_per_million,
    )
    maximum_cost = ceil(
        (
            estimated_input_tokens * rates[0]
            + max_output_tokens * rates[1]
        )
        / 1_000_000
    )
    if maximum_cost > budget.cost_ceiling_microusd:
        return None, rates, "cost_ceiling_exceeded"
    return max_output_tokens, rates, None


def _budget_fallback(
    report: ReportResponse,
    provider: ModelIdentity | None,
    reason: str,
    route_version_id: str | None,
    evaluation_run_id: str | None,
    *,
    response: LLMResponse | None = None,
    actual_cost: int | None = None,
    actual_total_tokens: int | None = None,
) -> SynthesisResult:
    return SynthesisResult(
        report=_with_assumption(report, LLM_SKIPPED_ASSUMPTION),
        used_llm=False,
        reason="validation_fallback",
        outcome="validation_fallback",
        validation_result="policy_denied",
        fallback_reason=reason,
        provider=provider,
        route_version_id=route_version_id,
        evaluation_run_id=evaluation_run_id,
        input_tokens=_valid_token_value(response.input_tokens) if response else None,
        output_tokens=_valid_token_value(response.output_tokens) if response else None,
        total_tokens=actual_total_tokens if response else None,
        reported_total_tokens=_valid_token_value(response.total_tokens) if response else None,
        cost_microusd=actual_cost,
        provider_call_made=response is not None,
        provider_call_state="response_received_rejected" if response else "not_attempted",
        usage_status=_usage_status(response, actual_cost, actual_total_tokens),
    )


def _validation_fallback(
    base_report: ReportResponse,
    provider: ModelIdentity | None,
    started: float,
    validation_result: str,
    fallback_reason: str,
    route_version_id: str | None = None,
    evaluation_run_id: str | None = None,
    response: LLMResponse | None = None,
    actual_cost: int | None = None,
    actual_total_tokens: int | None = None,
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
        input_tokens=_valid_token_value(response.input_tokens) if response else None,
        output_tokens=_valid_token_value(response.output_tokens) if response else None,
        total_tokens=actual_total_tokens if response else None,
        reported_total_tokens=_valid_token_value(response.total_tokens) if response else None,
        cost_microusd=actual_cost,
        provider_call_made=response is not None,
        provider_call_state="response_received_rejected" if response else "not_attempted",
        usage_status=_usage_status(response, actual_cost, actual_total_tokens),
    )


def _quality_fallback(
    base_report: ReportResponse,
    provider: ModelIdentity | None,
    started: float,
    quality: ModelQualityEvidence,
    route_version_id: str | None,
    evaluation_run_id: str | None,
    response: LLMResponse | None = None,
    actual_cost: int | None = None,
    actual_total_tokens: int | None = None,
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
        input_tokens=_valid_token_value(response.input_tokens) if response else None,
        output_tokens=_valid_token_value(response.output_tokens) if response else None,
        total_tokens=actual_total_tokens if response else None,
        reported_total_tokens=_valid_token_value(response.total_tokens) if response else None,
        cost_microusd=actual_cost,
        provider_call_made=response is not None,
        provider_call_state="response_received_rejected" if response else "not_attempted",
        usage_status=_usage_status(response, actual_cost, actual_total_tokens),
    )


def _usage_status(
    response: LLMResponse | None,
    actual_cost: int | None,
    actual_total_tokens: int | None = None,
) -> str:
    if response is None:
        return "not_applicable"
    observed = (response.input_tokens, response.output_tokens, response.total_tokens)
    if any(value is not None and _valid_token_value(value) is None for value in observed):
        return "invalid"
    if response.cost_microusd is not None and _valid_cost_value(response.cost_microusd) is None:
        return "invalid"
    if (
        response.input_tokens is not None
        and response.output_tokens is not None
        and response.total_tokens is not None
        and response.total_tokens != response.input_tokens + response.output_tokens
    ):
        return "inconsistent"
    total = actual_total_tokens if actual_total_tokens is not None else _effective_total_tokens(response)
    evidence = (
        _valid_token_value(response.input_tokens),
        _valid_token_value(response.output_tokens),
        total,
        _valid_cost_value(actual_cost),
    )
    if all(value is not None for value in evidence):
        return "known"
    return "partial" if any(value is not None for value in evidence) else "unknown"


def _valid_token_value(value: object) -> int | None:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 10_000_000:
        return None
    return value


def _valid_cost_value(value: object) -> int | None:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 2_147_483_647:
        return None
    return value


def _effective_total_tokens(response: LLMResponse) -> int | None:
    """Use the largest valid observed total; components can never be undercut."""

    reported_total = _valid_token_value(response.total_tokens)
    input_tokens = _valid_token_value(response.input_tokens)
    output_tokens = _valid_token_value(response.output_tokens)
    components_total = (
        input_tokens + output_tokens
        if input_tokens is not None and output_tokens is not None
        else None
    )
    known_totals = [value for value in (reported_total, components_total) if value is not None]
    return max(known_totals) if known_totals else None


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
    report.research_question = base_report.research_question
    report.question_answer = deepcopy(base_report.question_answer)
    report.protocols = deepcopy(base_report.protocols)
    report.missing_data = deepcopy(base_report.missing_data)
    report.sources = deepcopy(base_report.sources)
    report.disclaimer = base_report.disclaimer

    immutable_sections = {
        "Strategy Description",
        "Research Question",
        "Question-Specific Answer",
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
