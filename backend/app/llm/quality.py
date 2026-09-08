"""Deterministic quality and retrieved-source safety checks for report synthesis.

This module intentionally evaluates bounded structure rather than attempting
open-ended factual verification. Retrieved text remains data under every trust
classification; the classification controls observability and defensive prompt
marking, never instruction authority.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any

from app.rag.retriever import RetrievalResult
from app.schemas.reports import ReportResponse


QUALITY_POLICY_VERSION = "report_synthesis.quality.v1"
QUALITY_POLICY = {
    "citation_consistency": "known_url_or_explicit_known_title_only",
    "missing_source_honesty": "required_when_deterministic_missing_data_exists",
    "uncertainty_preservation": "required_when_deterministic_missing_data_exists",
    "source_instruction_treatment": "retrieved_data_never_instruction_authority",
    "deterministic_integrity": "all_authoritative_report_facts_exact",
    "unsafe_language": "zero_tolerance",
}
QUALITY_POLICY_CHECKSUM = sha256(
    json.dumps(QUALITY_POLICY, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()

SOURCE_TRUST_CLASSES = frozenset(
    {"trusted_code_owned", "curated_public", "tenant_private", "untrusted_external"}
)
_URL_PATTERN = re.compile(r"https?://[^\s<>\]\[\"')]+", re.IGNORECASE)
_EXPLICIT_CITATION_PATTERN = re.compile(r"\[(?:source|citation)\s*:\s*([^\]]{1,120})\]", re.IGNORECASE)
_FALSE_COMPLETENESS_PATTERN = re.compile(
    r"\b(?:no|without)\s+(?:missing|uncertain)\s+(?:data|information|evidence)\b|\ball\s+(?:data|facts|sources)\s+(?:are|is)\s+(?:complete|verified)\b",
    re.IGNORECASE,
)
_CONFIDENT_UNSUPPORTED_PATTERN = re.compile(r"\b(?:guaranteed|certain|proven|risk[- ]free)\b", re.IGNORECASE)
_UNCERTAINTY_PATTERN = re.compile(r"\b(?:uncertain|uncertainty|missing|not established|source not available|cannot verify)\b", re.IGNORECASE)
_UNSAFE_OUTPUT_PATTERN = re.compile(
    r"\b(?:you should (?:buy|sell|hold)|buy this|sell this|enter (?:this|a) trade|"
    r"execute (?:this|a) trade|connect (?:your|a) wallet|position size (?:at|to)|"
    r"recommend (?:buying|selling)|place (?:a )?(?:buy|sell) order)\b",
    re.IGNORECASE,
)
_INSTRUCTION_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("ignore_instructions", re.compile(r"\b(?:ignore|disregard|forget)\b.{0,64}\b(?:previous|system|developer|instructions?)\b", re.IGNORECASE)),
    ("override_authority", re.compile(r"\b(?:override|replace|change)\b.{0,64}\b(?:system|developer|safety|validation)\b", re.IGNORECASE)),
    ("credential_exfiltration", re.compile(r"\b(?:reveal|expose|print|show)\b.{0,64}\b(?:secret|api[_ -]?key|credential|token)\b", re.IGNORECASE)),
    ("provider_switch", re.compile(r"\b(?:change|switch|select)\b.{0,64}\b(?:provider|model)\b", re.IGNORECASE)),
    ("tool_execution", re.compile(r"\b(?:call|invoke|run|execute)\b.{0,48}\b(?:tool|function|command)\b", re.IGNORECASE)),
    ("wallet_or_trade", re.compile(r"\b(?:connect (?:a )?wallet|execute (?:a )?trade|place (?:a )?(?:buy|sell) order)\b", re.IGNORECASE)),
    ("validation_bypass", re.compile(r"\b(?:bypass|disable|skip)\b.{0,48}\b(?:validation|safety|guardrail)\b", re.IGNORECASE)),
    ("fake_system_message", re.compile(r"(?:^|\n)\s*(?:system|developer|tool)\s*:\s*", re.IGNORECASE)),
)


@dataclass(frozen=True)
class ModelQualityEvidence:
    citation_consistency: bool
    unsupported_claim_count: int
    missing_source_honesty: bool
    uncertainty_preserved: bool
    source_instruction_flag_count: int
    poisoning_detected: bool
    unsafe_language_violation: bool
    deterministic_integrity: bool
    overall_quality_pass: bool
    reason_code: str | None

    def to_payload(self) -> dict[str, Any]:
        return {
            "quality_policy_version": QUALITY_POLICY_VERSION,
            "quality_policy_checksum": QUALITY_POLICY_CHECKSUM,
            "citation_consistency": self.citation_consistency,
            "unsupported_claim_count": self.unsupported_claim_count,
            "missing_source_honesty": self.missing_source_honesty,
            "uncertainty_preserved": self.uncertainty_preserved,
            "source_instruction_flag_count": self.source_instruction_flag_count,
            "poisoning_detected": self.poisoning_detected,
            "unsafe_language_violation": self.unsafe_language_violation,
            "deterministic_integrity": self.deterministic_integrity,
            "overall_quality_pass": self.overall_quality_pass,
            "reason_code": self.reason_code,
        }


def source_trust_classification(metadata: object) -> str:
    """Derive trust from server-controlled source metadata, never chunk text."""

    if not isinstance(metadata, dict):
        return "untrusted_external"
    visibility = metadata.get("visibility")
    if visibility in {"private", "organization"} or metadata.get("owner_user_id") or metadata.get("organization_id"):
        return "tenant_private"
    if metadata.get("server_source_origin") == "code_owned":
        return "trusted_code_owned"
    if visibility in {"public", "public_demo"} and metadata.get("trust_state") == "approved_for_rag":
        return "curated_public"
    return "untrusted_external"


def detect_instruction_like_content(text: object) -> tuple[str, ...]:
    """Return bounded markers for clear imperative/authority-claim structures."""

    if not isinstance(text, str) or not text.strip():
        return ()
    normalized = " ".join(text.split())
    if _is_discussion_of_instruction_safety(normalized):
        return ()
    return tuple(code for code, pattern in _INSTRUCTION_RULES if pattern.search(normalized))


def retrieved_evidence_for_prompt(results: list[RetrievalResult]) -> list[dict[str, object]]:
    """Render retrieved chunks as explicitly untrusted structured evidence."""

    return [
        {
            "chunk_id": result.chunk_id,
            "trust_class": source_trust_classification(result.metadata),
            "instruction_flags": list(detect_instruction_like_content(result.text)),
            "text": result.text,
        }
        for result in results
    ]


def evaluate_report_synthesis_quality(
    base_report: ReportResponse,
    synthesized_report: ReportResponse,
    retrieved_context: list[RetrievalResult],
) -> ModelQualityEvidence:
    """Evaluate deterministic report-synthesis invariants without an LLM judge."""

    generated_text = "\n".join(
        [
            synthesized_report.executive_summary,
            *[
                section.content
                for section in synthesized_report.sections
                if section.title in {
                    "Strategy Mechanics",
                    "Yield Source",
                    "Key Assumptions",
                    "Stress Scenarios",
                    "Exit Plan",
                    "Monitoring Checklist",
                }
            ],
        ]
    )
    known_urls = {source.url for source in base_report.sources if source.url}
    known_titles = {source.title.casefold() for source in base_report.sources}
    url_violation = any(url not in known_urls for url in _URL_PATTERN.findall(generated_text))
    cited_titles = [value.strip().casefold() for value in _EXPLICIT_CITATION_PATTERN.findall(generated_text)]
    title_violation = any(title not in known_titles for title in cited_titles)
    citation_consistency = not url_violation and not title_violation

    has_missing_data = bool(base_report.missing_data)
    immutable_missing_section = _section_content(synthesized_report, "Missing Data and Uncertainty") == _section_content(base_report, "Missing Data and Uncertainty")
    uncertainty_preserved = not has_missing_data or bool(_UNCERTAINTY_PATTERN.search(generated_text)) or immutable_missing_section
    missing_source_honesty = not has_missing_data or (
        immutable_missing_section and not bool(_FALSE_COMPLETENESS_PATTERN.search(generated_text))
    )
    unsupported_claim_count = min(
        64,
        int(url_violation) + int(title_violation) + int(bool(_CONFIDENT_UNSUPPORTED_PATTERN.search(generated_text))),
    )
    source_flags = tuple(
        flag
        for result in retrieved_context
        for flag in detect_instruction_like_content(result.text)
    )
    output_flags = detect_instruction_like_content(generated_text)
    poisoning_detected = bool(source_flags and output_flags)
    unsafe_language_violation = bool(_UNSAFE_OUTPUT_PATTERN.search(generated_text))
    deterministic_integrity = _deterministic_facts_match(base_report, synthesized_report)
    overall_quality_pass = quality_passes(
        citation_consistency=citation_consistency,
        unsupported_claim_count=unsupported_claim_count,
        missing_source_honesty=missing_source_honesty,
        uncertainty_preserved=uncertainty_preserved,
        poisoning_detected=poisoning_detected,
        unsafe_language_violation=unsafe_language_violation,
        deterministic_integrity=deterministic_integrity,
    )
    return ModelQualityEvidence(
        citation_consistency=citation_consistency,
        unsupported_claim_count=unsupported_claim_count,
        missing_source_honesty=missing_source_honesty,
        uncertainty_preserved=uncertainty_preserved,
        source_instruction_flag_count=min(64, len(source_flags)),
        poisoning_detected=poisoning_detected,
        unsafe_language_violation=unsafe_language_violation,
        deterministic_integrity=deterministic_integrity,
        overall_quality_pass=overall_quality_pass,
        reason_code=_quality_reason(
            citation_consistency,
            unsupported_claim_count,
            missing_source_honesty,
            uncertainty_preserved,
            poisoning_detected,
            unsafe_language_violation,
            deterministic_integrity,
        ),
    )


def quality_passes(
    *,
    citation_consistency: bool,
    unsupported_claim_count: int,
    missing_source_honesty: bool,
    uncertainty_preserved: bool,
    poisoning_detected: bool,
    unsafe_language_violation: bool,
    deterministic_integrity: bool,
) -> bool:
    """Derive the v1 pass bit from bounded constituent checks only."""

    return bool(
        citation_consistency
        and unsupported_claim_count == 0
        and missing_source_honesty
        and uncertainty_preserved
        and not poisoning_detected
        and not unsafe_language_violation
        and deterministic_integrity
    )


def report_verifiable_quality_matches(
    worker: ModelQualityEvidence,
    recomputed: ModelQualityEvidence,
) -> bool:
    """Compare fields the completion control plane can prove from two reports.

    Source-instruction flags and poisoning require retrieved chunks, which are
    intentionally not copied into completion payloads. They stay separate
    bounded authenticated-worker evidence after route-snapshot verification.
    """

    return (
        worker.citation_consistency == recomputed.citation_consistency
        and worker.unsupported_claim_count == recomputed.unsupported_claim_count
        and worker.missing_source_honesty == recomputed.missing_source_honesty
        and worker.uncertainty_preserved == recomputed.uncertainty_preserved
        and worker.unsafe_language_violation == recomputed.unsafe_language_violation
        and worker.deterministic_integrity == recomputed.deterministic_integrity
    )


def quality_evidence_from_payload(payload: object) -> ModelQualityEvidence:
    """Accept only a bounded quality envelope from the authenticated worker path."""

    if not isinstance(payload, dict):
        raise ValueError("Model quality evidence is invalid")
    if (
        payload.get("quality_policy_version") != QUALITY_POLICY_VERSION
        or payload.get("quality_policy_checksum") != QUALITY_POLICY_CHECKSUM
    ):
        raise ValueError("Model quality policy evidence is invalid")
    bool_fields = (
        "citation_consistency",
        "missing_source_honesty",
        "uncertainty_preserved",
        "poisoning_detected",
        "unsafe_language_violation",
        "deterministic_integrity",
        "overall_quality_pass",
    )
    if any(not isinstance(payload.get(field), bool) for field in bool_fields):
        raise ValueError("Model quality evidence is invalid")
    unsupported = payload.get("unsupported_claim_count")
    instruction_flags = payload.get("source_instruction_flag_count")
    reason = payload.get("reason_code")
    if (
        not isinstance(unsupported, int)
        or isinstance(unsupported, bool)
        or not 0 <= unsupported <= 64
        or not isinstance(instruction_flags, int)
        or isinstance(instruction_flags, bool)
        or not 0 <= instruction_flags <= 64
        or (reason is not None and (not isinstance(reason, str) or not 1 <= len(reason) <= 64))
    ):
        raise ValueError("Model quality evidence is invalid")
    derived_pass = quality_passes(
        citation_consistency=payload["citation_consistency"],
        unsupported_claim_count=unsupported,
        missing_source_honesty=payload["missing_source_honesty"],
        uncertainty_preserved=payload["uncertainty_preserved"],
        poisoning_detected=payload["poisoning_detected"],
        unsafe_language_violation=payload["unsafe_language_violation"],
        deterministic_integrity=payload["deterministic_integrity"],
    )
    derived_reason = _quality_reason(
        payload["citation_consistency"],
        unsupported,
        payload["missing_source_honesty"],
        payload["uncertainty_preserved"],
        payload["poisoning_detected"],
        payload["unsafe_language_violation"],
        payload["deterministic_integrity"],
    )
    if (
        payload["overall_quality_pass"] != derived_pass
        or reason != derived_reason
        or (payload["poisoning_detected"] and instruction_flags == 0)
    ):
        raise ValueError("Model quality evidence is internally inconsistent")
    return ModelQualityEvidence(
        citation_consistency=payload["citation_consistency"],
        unsupported_claim_count=unsupported,
        missing_source_honesty=payload["missing_source_honesty"],
        uncertainty_preserved=payload["uncertainty_preserved"],
        source_instruction_flag_count=instruction_flags,
        poisoning_detected=payload["poisoning_detected"],
        unsafe_language_violation=payload["unsafe_language_violation"],
        deterministic_integrity=payload["deterministic_integrity"],
        overall_quality_pass=payload["overall_quality_pass"],
        reason_code=reason,
    )


def _deterministic_facts_match(base: ReportResponse, candidate: ReportResponse) -> bool:
    immutable_titles = {
        "Strategy Description",
        "Protocols Involved",
        "Risk Analysis",
        "Risk Rating",
        "Missing Data and Uncertainty",
        "Sources",
        "Disclaimer",
    }
    base_sections = {section.title: section.content for section in base.sections}
    candidate_sections = {section.title: section.content for section in candidate.sections}
    return bool(
        base.report_id == candidate.report_id
        and base.risk_rating == candidate.risk_rating
        and base.strategy_description == candidate.strategy_description
        and base.protocols == candidate.protocols
        and base.missing_data == candidate.missing_data
        and base.sources == candidate.sources
        and base.disclaimer == candidate.disclaimer
        and all(candidate_sections.get(title) == base_sections.get(title) for title in immutable_titles)
    )


def _section_content(report: ReportResponse, title: str) -> str | None:
    return next((section.content for section in report.sections if section.title == title), None)


def _quality_reason(
    citation_consistency: bool,
    unsupported_claim_count: int,
    missing_source_honesty: bool,
    uncertainty_preserved: bool,
    poisoning_detected: bool,
    unsafe_language_violation: bool,
    deterministic_integrity: bool,
) -> str | None:
    if not deterministic_integrity:
        return "deterministic_integrity_failed"
    if unsafe_language_violation:
        return "unsafe_output"
    if poisoning_detected:
        return "source_poisoning_obeyed"
    if not citation_consistency:
        return "citation_integrity_failed"
    if unsupported_claim_count:
        return "unsupported_claim"
    if not missing_source_honesty:
        return "missing_source_honesty_failed"
    if not uncertainty_preserved:
        return "uncertainty_not_preserved"
    return None


def _is_discussion_of_instruction_safety(text: str) -> bool:
    lowered = text.casefold()
    return bool(
        any(marker in lowered for marker in ("prompt injection", "instruction-like", "security example", "quoted example"))
        and any(marker in lowered for marker in ("do not follow", "should not follow", "example", "discussion", "describes"))
    )
