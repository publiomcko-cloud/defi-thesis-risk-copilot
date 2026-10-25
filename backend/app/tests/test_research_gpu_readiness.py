from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from types import SimpleNamespace

import pytest

from app.llm.research_gpu_policy import (
    RESEARCH_GPU_POLICY_CHECKSUM,
    RESEARCH_GPU_POLICY_VERSION,
    RESEARCH_GPU_REPRESENTATIVE_CASE_IDS,
    RESEARCH_GPU_REQUIRED_MODEL,
    research_gpu_binding_checksum_for_payload,
)
from app.llm.research_gpu_readiness import qualifies_as_approved_five_case_sample


def _sample(passed_count: int) -> tuple[SimpleNamespace, list[SimpleNamespace]]:
    run_id = "eval_readiness_fixture"
    cases = []
    for index, case_id in enumerate(RESEARCH_GPU_REPRESENTATIVE_CASE_IDS):
        passed = index < passed_count
        cases.append(
            SimpleNamespace(
                id=f"case_{index}",
                evaluation_run_id=run_id,
                case_id=case_id,
                case_checksum=sha256(case_id.encode()).hexdigest(),
                passed=passed,
                structured_output_valid=passed,
                deterministic_preserved=passed,
                source_integrity=passed,
                citation_consistency=passed,
                unsupported_claim_count=0,
                uncertainty_preserved=passed,
                source_instruction_flag_count=0,
                poisoning_detected=False,
                deterministic_integrity=passed,
                missing_data_honesty=passed,
                unsafe_language_violation=False,
                privacy_policy_violation=False,
                provider_failure=False,
                latency_ms=1_000,
                latency_phase="cold" if index == 0 else "warm",
                ollama_load_duration_ns=1_000_000 if index == 0 else 0,
                ollama_total_duration_ns=2_000_000,
                ollama_prompt_eval_duration_ns=500_000,
                ollama_eval_duration_ns=1_000_000,
                provider_observed_at=datetime.now(UTC),
                input_tokens=31,
                output_tokens=12,
                total_tokens=43,
            )
        )

    selected_checksums = {case.case_id: case.case_checksum for case in cases}
    binding = {
        "policy_version": RESEARCH_GPU_POLICY_VERSION,
        "policy_checksum": RESEARCH_GPU_POLICY_CHECKSUM,
        "environment": "development",
        "task": {"key": "report_synthesis", "version": "v1"},
        "model": {
            "model_key": RESEARCH_GPU_REQUIRED_MODEL,
            "privacy_classification": "public_only",
            "artifact_digest": "sha256:" + "a" * 64,
        },
        "evaluation_plan": "representative",
        "selected_case_checksums": selected_checksums,
        "code_revision": "f" * 40,
        "runtime_attestation": {
            "model_name": RESEARCH_GPU_REQUIRED_MODEL,
            "model_digest": "sha256:" + "a" * 64,
            "transport_kind": "verified_ssh_local_forward.v1",
        },
    }
    run = SimpleNamespace(
        id=run_id,
        status="completed",
        case_count=5,
        passed_case_count=sum(case.passed for case in cases),
        provider_failure_count=0,
        failure_reason=None if passed_count == 5 else "research_gpu_policy_failed",
        promotion_eligible=False,
        policy_version=RESEARCH_GPU_POLICY_VERSION,
        policy_checksum=RESEARCH_GPU_POLICY_CHECKSUM,
        task_key="report_synthesis",
        task_version="v1",
        environment="development",
        code_revision="f" * 40,
        evaluation_binding_json=binding,
        evaluation_binding_checksum=research_gpu_binding_checksum_for_payload(binding),
        latency_known_count=5,
        token_observation_count=5,
        cold_latency_count=1,
        warm_latency_count=4,
        latency_total_ms=5_000,
        cold_latency_total_ms=1_000,
        warm_latency_total_ms=4_000,
        input_tokens_total=155,
        output_tokens_total=60,
        total_tokens_total=215,
        structured_output_valid_count=sum(case.structured_output_valid for case in cases),
        deterministic_preserved_count=sum(case.deterministic_preserved for case in cases),
        source_integrity_count=sum(case.source_integrity for case in cases),
        citation_consistency_count=sum(case.citation_consistency for case in cases),
        unsupported_claim_count=sum(case.unsupported_claim_count for case in cases),
        uncertainty_preserved_count=sum(case.uncertainty_preserved for case in cases),
        source_instruction_flag_count=sum(case.source_instruction_flag_count for case in cases),
        poisoning_detected_count=sum(case.poisoning_detected for case in cases),
        deterministic_integrity_count=sum(case.deterministic_integrity for case in cases),
        missing_data_honesty_count=sum(case.missing_data_honesty for case in cases),
        unsafe_language_violation_count=sum(case.unsafe_language_violation for case in cases),
        privacy_policy_violation_count=sum(case.privacy_policy_violation for case in cases),
    )
    return run, cases


@pytest.mark.parametrize(
    ("passed_count", "expected_approval"),
    [(0, False), (3, False), (5, True)],
)
def test_only_five_of_five_qualifies_as_approved_and_never_becomes_promotable(
    passed_count: int,
    expected_approval: bool,
) -> None:
    run, cases = _sample(passed_count)

    assert run.status == "completed"
    assert run.promotion_eligible is False
    assert qualifies_as_approved_five_case_sample(run, cases) is expected_approval


@pytest.mark.parametrize("evidence_field", ["latency_ms", "ollama_total_duration_ns", "input_tokens"])
def test_five_of_five_still_fails_if_required_measurement_is_missing(evidence_field: str) -> None:
    run, cases = _sample(5)
    setattr(cases[0], evidence_field, None)

    assert qualifies_as_approved_five_case_sample(run, cases) is False


def test_five_of_five_still_fails_if_v1_mean_latency_limit_is_exceeded() -> None:
    run, cases = _sample(5)
    for case in cases:
        case.latency_ms = 30_001
    run.latency_total_ms = sum(case.latency_ms for case in cases)
    run.cold_latency_total_ms = cases[0].latency_ms
    run.warm_latency_total_ms = sum(case.latency_ms for case in cases[1:])

    assert qualifies_as_approved_five_case_sample(run, cases) is False


def test_five_of_five_still_fails_if_any_case_has_a_provider_failure() -> None:
    run, cases = _sample(5)
    cases[-1].provider_failure = True
    run.provider_failure_count = 1

    assert qualifies_as_approved_five_case_sample(run, cases) is False
