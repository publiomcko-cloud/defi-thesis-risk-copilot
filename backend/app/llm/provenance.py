"""Safe in-memory provenance candidates for report synthesis.

The candidate deliberately contains hashes and bounded identifiers only. It is
created before report persistence and written by the orchestration transaction,
never by a provider adapter.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import TYPE_CHECKING, Any

from app.llm.prompts import report_synthesis_prompt_definition
from app.llm.task_registry import get_model_task_definition

if TYPE_CHECKING:
    from app.llm.synthesis import SynthesisResult
    from app.rag.retriever import RetrievalResult
    from app.schemas.reports import ReportResponse


_IDENTIFIER = re.compile(r"^[A-Za-z0-9._:/-]{1,128}$")
_PROVIDER_KEY = re.compile(r"^[a-z0-9_]{1,64}$")
_OUTCOMES = frozenset(
    {"disabled", "provider_unavailable", "succeeded", "validation_fallback", "provider_failure"}
)
_VALIDATION_RESULTS = frozenset(
    {"not_run", "accepted", "invalid_json", "schema_invalid", "unsafe_output", "provider_error", "policy_denied"}
)
_SCOPE_CLASSES = frozenset({"public", "private", "organization", "anonymous"})


@dataclass(frozen=True)
class ModelIdentity:
    provider_key: str
    model_key: str
    model_version: str
    endpoint_class: str
    privacy_classification: str


@dataclass(frozen=True)
class ModelRunCandidate:
    task_key: str
    task_version: str
    prompt_version: str
    output_schema_version: str
    safety_policy_version: str
    prompt_checksum: str
    provider: ModelIdentity | None
    scope_class: str
    deterministic_input_checksum: str
    retrieval_digest: str | None
    retrieval_source_count: int
    validation_result: str
    outcome: str
    fallback_reason: str | None
    latency_ms: int | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    cost_microusd: int | None

    def to_payload(self) -> dict[str, Any]:
        """Return the safe worker envelope; no prompt, sources, or response text."""

        return {
            "task_key": self.task_key,
            "task_version": self.task_version,
            "prompt_version": self.prompt_version,
            "output_schema_version": self.output_schema_version,
            "safety_policy_version": self.safety_policy_version,
            "prompt_checksum": self.prompt_checksum,
            "provider": (
                {
                    "provider_key": self.provider.provider_key,
                    "model_key": self.provider.model_key,
                    "model_version": self.provider.model_version,
                    "endpoint_class": self.provider.endpoint_class,
                    "privacy_classification": self.provider.privacy_classification,
                }
                if self.provider is not None
                else None
            ),
            "scope_class": self.scope_class,
            "deterministic_input_checksum": self.deterministic_input_checksum,
            "retrieval_digest": self.retrieval_digest,
            "retrieval_source_count": self.retrieval_source_count,
            "validation_result": self.validation_result,
            "outcome": self.outcome,
            "fallback_reason": self.fallback_reason,
            "latency_ms": self.latency_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "cost_microusd": self.cost_microusd,
        }


def provider_identity(provider: object) -> ModelIdentity | None:
    """Extract only bounded identifiers from a server-side provider object."""

    provider_key = getattr(provider, "name", None)
    model_key = getattr(provider, "model", None)
    if not isinstance(provider_key, str) or not _PROVIDER_KEY.fullmatch(provider_key):
        return None
    if not isinstance(model_key, str) or not _IDENTIFIER.fullmatch(model_key):
        return None
    endpoint_class = {
        "ollama": "ollama_generate",
        "openai_compatible": "openai_compatible_chat",
    }.get(provider_key, "custom")
    privacy_classification = getattr(provider, "privacy_classification", "unknown")
    if privacy_classification not in {"unknown", "public_only", "private_approved"}:
        privacy_classification = "unknown"
    return ModelIdentity(
        provider_key=provider_key,
        model_key=model_key,
        model_version=model_key,
        endpoint_class=endpoint_class,
        privacy_classification=privacy_classification,
    )


def provider_is_eligible_for_scope(provider: ModelIdentity | None, scope_class: str) -> bool:
    """Fail closed before private or organization content can leave the boundary."""

    if scope_class not in _SCOPE_CLASSES or provider is None:
        return False
    return scope_class == "public" or provider.privacy_classification == "private_approved"


def build_report_synthesis_candidate(
    result: SynthesisResult,
    base_report: ReportResponse,
    retrieved_context: list[RetrievalResult],
    *,
    scope_class: str,
) -> ModelRunCandidate:
    task = get_model_task_definition("report_synthesis")
    prompt = report_synthesis_prompt_definition()
    if scope_class not in _SCOPE_CLASSES:
        scope_class = "private"
    return ModelRunCandidate(
        task_key=task.key,
        task_version=task.version,
        prompt_version=prompt.prompt_version,
        output_schema_version=prompt.output_schema_version,
        safety_policy_version=prompt.safety_policy_version,
        prompt_checksum=prompt.checksum,
        provider=result.provider,
        scope_class=scope_class,
        deterministic_input_checksum=deterministic_report_input_checksum(base_report),
        retrieval_digest=_retrieval_digest(retrieved_context),
        retrieval_source_count=min(len(retrieved_context), 64),
        validation_result=result.validation_result,
        outcome=result.outcome,
        fallback_reason=result.fallback_reason,
        latency_ms=result.latency_ms,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        total_tokens=result.total_tokens,
        cost_microusd=result.cost_microusd,
    )


def candidate_from_payload(payload: object) -> ModelRunCandidate:
    """Accept only the bounded worker provenance envelope, never arbitrary JSON."""

    if not isinstance(payload, dict):
        raise ValueError("Model provenance payload is invalid")
    definition = get_model_task_definition(_required_text(payload, "task_key", 64))
    task_version = _required_text(payload, "task_version", 32)
    if task_version != definition.version:
        raise ValueError("Model provenance task version is invalid")
    prompt = report_synthesis_prompt_definition()
    for field, expected in {
        "prompt_version": prompt.prompt_version,
        "output_schema_version": prompt.output_schema_version,
        "safety_policy_version": prompt.safety_policy_version,
        "prompt_checksum": prompt.checksum,
    }.items():
        if _required_text(payload, field, 64) != expected:
            raise ValueError("Model provenance version linkage is invalid")
    provider_payload = payload.get("provider")
    provider = _provider_from_payload(provider_payload) if provider_payload is not None else None
    scope_class = _required_text(payload, "scope_class", 16)
    outcome = _required_text(payload, "outcome", 32)
    validation_result = _required_text(payload, "validation_result", 32)
    if scope_class not in _SCOPE_CLASSES or outcome not in _OUTCOMES or validation_result not in _VALIDATION_RESULTS:
        raise ValueError("Model provenance state is invalid")
    fallback_reason = payload.get("fallback_reason")
    if fallback_reason is not None and (not isinstance(fallback_reason, str) or not 1 <= len(fallback_reason) <= 64):
        raise ValueError("Model provenance fallback reason is invalid")
    return ModelRunCandidate(
        task_key=definition.key,
        task_version=task_version,
        prompt_version=prompt.prompt_version,
        output_schema_version=prompt.output_schema_version,
        safety_policy_version=prompt.safety_policy_version,
        prompt_checksum=prompt.checksum,
        provider=provider,
        scope_class=scope_class,
        deterministic_input_checksum=_checksum(payload.get("deterministic_input_checksum")),
        retrieval_digest=_optional_checksum(payload.get("retrieval_digest")),
        retrieval_source_count=_bounded_int(payload.get("retrieval_source_count"), 0, 64),
        validation_result=validation_result,
        outcome=outcome,
        fallback_reason=fallback_reason,
        latency_ms=_optional_int(payload.get("latency_ms"), 0, 3_600_000),
        input_tokens=_optional_int(payload.get("input_tokens"), 0, 10_000_000),
        output_tokens=_optional_int(payload.get("output_tokens"), 0, 10_000_000),
        total_tokens=_optional_int(payload.get("total_tokens"), 0, 10_000_000),
        cost_microusd=_optional_int(payload.get("cost_microusd"), 0, 2_147_483_647),
    )


def scope_class_for_actor(actor: object | None, organization_id: str | None = None) -> str:
    if organization_id:
        return "organization"
    if actor is None or (not getattr(actor, "auth_enabled", True) and not getattr(actor, "anonymous_session_id", None)):
        return "public"
    if getattr(actor, "anonymous_session_id", None):
        return "anonymous"
    return "private"


def deterministic_report_input_checksum(report: ReportResponse) -> str:
    payload = {
        "report_id": report.report_id,
        "risk_rating": report.risk_rating,
        "protocols": report.protocols,
        "missing_data": report.missing_data,
        "source_references": [source.model_dump(mode="json") for source in report.sources],
        "disclaimer": report.disclaimer,
    }
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def fallback_report_synthesis_candidate(
    report: ReportResponse,
    *,
    scope_class: str,
    outcome: str,
    validation_result: str,
    fallback_reason: str,
    provider: ModelIdentity | None = None,
) -> ModelRunCandidate:
    """Create a server-derived fallback when an older worker omits metadata."""

    task = get_model_task_definition("report_synthesis")
    prompt = report_synthesis_prompt_definition()
    return ModelRunCandidate(
        task_key=task.key,
        task_version=task.version,
        prompt_version=prompt.prompt_version,
        output_schema_version=prompt.output_schema_version,
        safety_policy_version=prompt.safety_policy_version,
        prompt_checksum=prompt.checksum,
        provider=provider,
        scope_class=scope_class if scope_class in _SCOPE_CLASSES else "private",
        deterministic_input_checksum=deterministic_report_input_checksum(report),
        retrieval_digest=None,
        retrieval_source_count=0,
        validation_result=validation_result,
        outcome=outcome,
        fallback_reason=fallback_reason,
        latency_ms=None,
        input_tokens=None,
        output_tokens=None,
        total_tokens=None,
        cost_microusd=None,
    )


def _retrieval_digest(results: list[RetrievalResult]) -> str | None:
    if not results:
        return None
    references = []
    for result in results[:64]:
        lineage = result.metadata.get("citation_lineage") if isinstance(result.metadata, dict) else None
        references.append(
            {
                "chunk_id": str(result.chunk_id)[:128],
                "source_id": str(lineage.get("source_id", ""))[:128] if isinstance(lineage, dict) else "",
                "document_version_id": str(lineage.get("document_version_id", ""))[:128] if isinstance(lineage, dict) else "",
            }
        )
    return sha256(json.dumps(references, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _provider_from_payload(value: object) -> ModelIdentity:
    if not isinstance(value, dict):
        raise ValueError("Model provenance provider is invalid")
    provider_key = _required_text(value, "provider_key", 64)
    model_key = _required_text(value, "model_key", 128)
    model_version = _required_text(value, "model_version", 128)
    endpoint_class = _required_text(value, "endpoint_class", 32)
    privacy_classification = _required_text(value, "privacy_classification", 32)
    if (
        not _PROVIDER_KEY.fullmatch(provider_key)
        or not _IDENTIFIER.fullmatch(model_key)
        or not _IDENTIFIER.fullmatch(model_version)
        or endpoint_class not in {"ollama_generate", "openai_compatible_chat", "custom"}
        or privacy_classification not in {"unknown", "public_only", "private_approved"}
    ):
        raise ValueError("Model provenance provider is invalid")
    return ModelIdentity(provider_key, model_key, model_version, endpoint_class, privacy_classification)


def _required_text(payload: dict[str, Any], key: str, maximum: int) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not 1 <= len(value) <= maximum:
        raise ValueError("Model provenance text is invalid")
    return value


def _checksum(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("Model provenance checksum is invalid")
    return value


def _optional_checksum(value: object) -> str | None:
    return None if value is None else _checksum(value)


def _bounded_int(value: object, lower: int, upper: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not lower <= value <= upper:
        raise ValueError("Model provenance integer is invalid")
    return value


def _optional_int(value: object, lower: int, upper: int) -> int | None:
    return None if value is None else _bounded_int(value, lower, upper)
