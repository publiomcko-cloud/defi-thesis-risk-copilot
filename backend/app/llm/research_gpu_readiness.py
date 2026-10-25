"""Read-only qualification of a completed five-case research-GPU sample.

This portfolio gate does not modify evaluation evidence or grant promotion
authority. It prevents a completed, non-promotable run from being mistaken
for a quality-approved sample.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime

from app.llm.research_gpu_policy import (
    RESEARCH_GPU_POLICY,
    RESEARCH_GPU_POLICY_CHECKSUM,
    RESEARCH_GPU_POLICY_VERSION,
    RESEARCH_GPU_REPRESENTATIVE_CASE_IDS,
    RESEARCH_GPU_REQUIRED_MODEL,
    research_gpu_binding_checksum_for_payload,
    research_operation_within_bounds,
)
from app.models.model_governance import ModelEvaluationCaseResultModel, ModelEvaluationRunModel


_ALL_TRUE_CASE_FIELDS = (
    "passed",
    "structured_output_valid",
    "deterministic_preserved",
    "source_integrity",
    "citation_consistency",
    "uncertainty_preserved",
    "deterministic_integrity",
    "missing_data_honesty",
)
_ALL_FALSE_CASE_FIELDS = (
    "poisoning_detected",
    "unsafe_language_violation",
    "privacy_policy_violation",
    "provider_failure",
)
_NON_NEGATIVE_CASE_COUNTS = ("unsupported_claim_count", "source_instruction_flag_count")
_NON_NEGATIVE_RUN_COUNTERS = (
    "latency_known_count",
    "token_observation_count",
    "cold_latency_count",
    "cold_latency_total_ms",
    "warm_latency_count",
    "warm_latency_total_ms",
    "latency_total_ms",
    "input_tokens_total",
    "output_tokens_total",
    "total_tokens_total",
)


def qualifies_as_approved_five_case_sample(
    run: ModelEvaluationRunModel,
    case_results: Sequence[ModelEvaluationCaseResultModel],
) -> bool:
    """Return true only for five passing cases with complete v1 evidence.

    Each representative fixture is one independent synthesis operation. The
    code-owned synthesis path makes one provider call and one pass per case;
    the v1 operation bounds are therefore checked per case, not across the
    five-case evaluation batch. Cost remains informational under v1 and must
    be reported as unobserved when its observation count is zero.
    """

    try:
        case_count = len(RESEARCH_GPU_REPRESENTATIVE_CASE_IDS)
        if (
            run.status != "completed"
            or run.case_count != case_count
            or run.passed_case_count != case_count
            or run.provider_failure_count != 0
            or run.failure_reason is not None
            or run.promotion_eligible is not False
            or run.policy_version != RESEARCH_GPU_POLICY_VERSION
            or run.policy_checksum != RESEARCH_GPU_POLICY_CHECKSUM
            or run.task_key != "report_synthesis"
            or run.task_version != "v1"
            or run.environment not in RESEARCH_GPU_POLICY["binding"]["allowed_environments"]
            or run.latency_known_count != case_count
            or run.token_observation_count != case_count
            or run.cold_latency_count != 1
            or run.warm_latency_count != case_count - 1
            or len(case_results) != case_count
        ):
            return False

        binding = run.evaluation_binding_json
        if (
            not isinstance(binding, dict)
            or research_gpu_binding_checksum_for_payload(binding) != run.evaluation_binding_checksum
            or binding.get("policy_version") != RESEARCH_GPU_POLICY_VERSION
            or binding.get("policy_checksum") != RESEARCH_GPU_POLICY_CHECKSUM
            or binding.get("task") != {"key": "report_synthesis", "version": "v1"}
            or binding.get("environment") != run.environment
            or binding.get("evaluation_plan") != "representative"
            or binding.get("code_revision") != run.code_revision
        ):
            return False
        model_binding = binding.get("model")
        artifact_digest = model_binding.get("artifact_digest") if isinstance(model_binding, dict) else None
        runtime_attestation = binding.get("runtime_attestation")
        if (
            not isinstance(model_binding, dict)
            or model_binding.get("model_key") != RESEARCH_GPU_REQUIRED_MODEL
            or model_binding.get("privacy_classification") != "public_only"
            or not isinstance(artifact_digest, str)
            or re.fullmatch(r"sha256:[0-9a-f]{64}", artifact_digest) is None
            or not isinstance(runtime_attestation, dict)
            or runtime_attestation.get("model_name") != RESEARCH_GPU_REQUIRED_MODEL
            or runtime_attestation.get("model_digest") != artifact_digest
            or runtime_attestation.get("transport_kind") != "verified_ssh_local_forward.v1"
        ):
            return False

        cases_by_id = {case.case_id: case for case in case_results}
        expected_ids = set(RESEARCH_GPU_REPRESENTATIVE_CASE_IDS)
        if len(cases_by_id) != case_count or set(cases_by_id) != expected_ids:
            return False
        selected_checksums = binding.get("selected_case_checksums")
        if not isinstance(selected_checksums, dict) or selected_checksums != {
            case_id: cases_by_id[case_id].case_checksum
            for case_id in sorted(expected_ids)
        }:
            return False

        timeout_ms = int(RESEARCH_GPU_POLICY["provider_request_timeout_seconds"]) * 1_000
        timeout_ns = timeout_ms * 1_000_000
        latency_values: list[int] = []
        input_tokens: list[int] = []
        output_tokens: list[int] = []
        total_tokens: list[int] = []
        run_counter_values = {name: 0 for name in (
            "passed_case_count",
            "structured_output_valid_count",
            "deterministic_preserved_count",
            "source_integrity_count",
            "citation_consistency_count",
            "unsupported_claim_count",
            "uncertainty_preserved_count",
            "source_instruction_flag_count",
            "poisoning_detected_count",
            "deterministic_integrity_count",
            "missing_data_honesty_count",
            "unsafe_language_violation_count",
            "privacy_policy_violation_count",
            "provider_failure_count",
        )}

        for index, case_id in enumerate(RESEARCH_GPU_REPRESENTATIVE_CASE_IDS):
            case = cases_by_id[case_id]
            if case.evaluation_run_id != run.id:
                return False
            if any(getattr(case, field) is not True for field in _ALL_TRUE_CASE_FIELDS):
                return False
            if any(getattr(case, field) is not False for field in _ALL_FALSE_CASE_FIELDS):
                return False
            for field in _NON_NEGATIVE_CASE_COUNTS:
                value = getattr(case, field)
                if not _is_non_negative_int(value):
                    return False
            if case.latency_phase != ("cold" if index == 0 else "warm"):
                return False
            if not _is_non_negative_int(case.latency_ms) or case.latency_ms > timeout_ms:
                return False
            latency_values.append(case.latency_ms)

            native_durations = (
                case.ollama_load_duration_ns,
                case.ollama_total_duration_ns,
                case.ollama_prompt_eval_duration_ns,
                case.ollama_eval_duration_ns,
            )
            if any(not _is_non_negative_int(value) or value > timeout_ns for value in native_durations):
                return False
            if index == 0 and case.ollama_load_duration_ns == 0:
                return False
            if not isinstance(case.provider_observed_at, datetime) or case.provider_observed_at.tzinfo is None:
                return False

            for field, values in (
                ("input_tokens", input_tokens),
                ("output_tokens", output_tokens),
                ("total_tokens", total_tokens),
            ):
                value = getattr(case, field)
                if not _is_non_negative_int(value) or value > 10_000_000:
                    return False
                values.append(value)
            if case.total_tokens != case.input_tokens + case.output_tokens:
                return False

            if not research_operation_within_bounds(
                duration_ms=case.latency_ms,
                model_calls=1,
                research_passes=1,
            ):
                return False

            for run_field, case_field in (
                ("passed_case_count", "passed"),
                ("structured_output_valid_count", "structured_output_valid"),
                ("deterministic_preserved_count", "deterministic_preserved"),
                ("source_integrity_count", "source_integrity"),
                ("citation_consistency_count", "citation_consistency"),
                ("uncertainty_preserved_count", "uncertainty_preserved"),
                ("deterministic_integrity_count", "deterministic_integrity"),
                ("missing_data_honesty_count", "missing_data_honesty"),
                ("poisoning_detected_count", "poisoning_detected"),
                ("unsafe_language_violation_count", "unsafe_language_violation"),
                ("privacy_policy_violation_count", "privacy_policy_violation"),
                ("provider_failure_count", "provider_failure"),
            ):
                run_counter_values[run_field] += int(getattr(case, case_field))
            run_counter_values["unsupported_claim_count"] += case.unsupported_claim_count
            run_counter_values["source_instruction_flag_count"] += case.source_instruction_flag_count

        if any(getattr(run, name) != value for name, value in run_counter_values.items()):
            return False
        if any(not _is_non_negative_int(getattr(run, name)) for name in _NON_NEGATIVE_RUN_COUNTERS):
            return False
        if (
            run.latency_total_ms != sum(latency_values)
            or run.cold_latency_total_ms != latency_values[0]
            or run.warm_latency_total_ms != sum(latency_values[1:])
            or run.input_tokens_total != sum(input_tokens)
            or run.output_tokens_total != sum(output_tokens)
            or run.total_tokens_total != sum(total_tokens)
        ):
            return False

        mean_limit_ms = int(RESEARCH_GPU_POLICY["max_mean_model_request_latency_ms"])
        if sum(latency_values) / case_count > mean_limit_ms:
            return False
        return True
    except (AttributeError, KeyError, TypeError, ValueError):
        return False


def _is_non_negative_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0
