from __future__ import annotations

import json
from hashlib import sha256

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import create_user, user_context
from app.core.config import Settings
from app.db.base import Base
from app.llm import evaluation
from app.llm.base import LLMRequest, LLMResponse
from app.llm.evaluation import (
    ModelEvaluationError,
    evaluate_report_synthesis_research_gpu_candidate,
    evaluation_run_snapshot,
    promote_evaluation_route,
    route_snapshot,
)
from app.llm.evaluation_authority import PROMOTION_POLICY, PROMOTION_POLICY_CHECKSUM
from app.llm.evaluation_data import report_synthesis_adversarial_dataset, report_synthesis_public_dataset
from app.llm import research_gpu_ollama
from app.llm.research_gpu_policy import (
    RESEARCH_GPU_EXPECTED_MANIFEST_DIGEST,
    RESEARCH_GPU_EXPECTED_WEIGHTS_DIGEST,
    RESEARCH_GPU_POLICY,
    RESEARCH_GPU_POLICY_CHECKSUM,
    RESEARCH_GPU_POLICY_VERSION,
    ResearchGpuPolicyError,
    evaluation_case_plan,
    normalized_policy_payload,
    research_gpu_binding_checksum,
    research_gpu_provider_is_allowed,
    research_operation_within_bounds,
    resolve_research_gpu_policy,
)
from app.models.model_governance import ModelEvaluationCaseResultModel, ModelEvaluationRunModel, ModelRegistryModel
from app.llm.research_gpu_ollama import (
    OllamaNativeObservation,
    ResearchGpuAdapterError,
    SshForwardingEvidence,
    VerifiedResearchGpuOllamaProvider,
)

# Importing the app registers the full ORM metadata used by the in-memory DB.
from app.main import app as _app  # noqa: F401


MANIFEST_DIGEST = RESEARCH_GPU_EXPECTED_MANIFEST_DIGEST
MODEL_DIGEST = RESEARCH_GPU_EXPECTED_WEIGHTS_DIGEST
BASE_URL = "http://127.0.0.1:11435"
TUNNEL_EVIDENCE = SshForwardingEvidence(
    ssh_pid=4242,
    ssh_target="root@203.0.113.10",
    ssh_port=22,
    local_port=11435,
    known_hosts_sha256="b" * 64,
    ssh_command_sha256="c" * 64,
)


class _HttpResponse:
    status_code = 200

    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self.payload


def _verified_provider(monkeypatch, *, loaded_models: tuple[str, ...] = ()) -> VerifiedResearchGpuOllamaProvider:
    monkeypatch.setattr(
        research_gpu_ollama,
        "verify_ssh_forwarding_process",
        lambda _pid, _url: TUNNEL_EVIDENCE,
    )

    def get(url: str, *, timeout: float):
        assert timeout > 0
        if url.endswith("/api/version"):
            return _HttpResponse({"version": "0.13.2"})
        if url.endswith("/api/tags"):
            return _HttpResponse({"models": [{"name": "qwen2.5:7b-instruct-q4_K_M", "digest": MANIFEST_DIGEST.removeprefix("sha256:")}]})
        if url.endswith("/api/ps"):
            return _HttpResponse({"models": [{"name": name} for name in loaded_models]})
        raise AssertionError(f"unexpected URL {url}")

    monkeypatch.setattr(research_gpu_ollama.httpx, "get", get)
    monkeypatch.setattr(
        research_gpu_ollama.httpx,
        "head",
        lambda url, *, timeout: _HttpResponse({})
        if url.endswith("/api/blobs/" + MODEL_DIGEST)
        else pytest.fail(url),
    )
    monkeypatch.setattr(
        research_gpu_ollama.httpx,
        "post",
        lambda url, *, json, timeout: _HttpResponse({
            "modelfile": "FROM /root/.ollama/models/blobs/sha256-" + MODEL_DIGEST.removeprefix("sha256:"),
            "details": {"format": "gguf", "family": "qwen2", "quantization_level": "Q4_K_M"},
        }) if url.endswith("/api/show") else _HttpResponse({"done": True}),
    )
    return VerifiedResearchGpuOllamaProvider.verify_runtime(
        base_url=BASE_URL,
        expected_manifest_digest=MANIFEST_DIGEST,
        expected_weights_digest=MODEL_DIGEST,
        ssh_pid=4242,
    )


def _set_fake_observation(provider: VerifiedResearchGpuOllamaProvider, phase: str) -> None:
    provider.last_observation = OllamaNativeObservation(
        phase=phase,
        observed_at="2026-10-25T12:00:00+00:00",
        load_duration_ns=1_000_000 if phase == "cold" else 0,
        total_duration_ns=2_000_000,
        prompt_eval_duration_ns=500_000,
        eval_duration_ns=1_000_000,
        cold_load_confirmed=True,
        native_metrics_valid=True,
    )


def _dataset_authority(dataset_id: str, checksum: str) -> dict[str, object]:
    return {
        "dataset_id": dataset_id,
        "task_key": "report_synthesis",
        "task_version": "v1",
        "dataset_version": "v1",
        "checksum": checksum,
        "case_count": 2,
    }


def _binding_runtime_attestation() -> dict[str, object]:
    return {
        "server_version": "0.13.2",
        "model_name": "qwen2.5:7b-instruct-q4_K_M",
        "manifest_digest": MANIFEST_DIGEST,
        "weights_digest": MODEL_DIGEST,
        "weights_layer_media_type": "application/vnd.ollama.image.model",
        "quantization": "Q4_K_M",
        "transport_kind": "verified_ssh_local_forward.v1",
        "transport": TUNNEL_EVIDENCE.to_payload(),
        "local_endpoint": BASE_URL,
        "verified_at": "2026-10-25T12:00:00+00:00",
        "cold_model_absent_at": "2026-10-25T12:00:01+00:00",
        "loaded_model_names_before_unload": [],
    }


def _binding(**overrides: object) -> str:
    values: dict[str, object] = {
        "environment": "development",
        "task_key": "report_synthesis",
        "task_version": "v1",
        "model_registry_id": "model_ollama_qwen_v1",
        "provider_key": "ollama",
        "model_key": "qwen2.5:7b-instruct-q4_K_M",
        "model_version": "qwen2.5:7b-instruct-q4_K_M",
        "endpoint_class": "ollama_generate",
        "privacy_classification": "public_only",
        "model_manifest_digest": MANIFEST_DIGEST,
        "model_weights_digest": MODEL_DIGEST,
        "prompt_version_id": "prompt_report_synthesis_v3",
        "prompt_checksum": "b" * 64,
        "ordinary_dataset": _dataset_authority("report_synthesis_public_v2", "c" * 64),
        "adversarial_dataset": _dataset_authority("report_synthesis_adversarial_v1", "d" * 64),
        "evaluation_plan": "representative",
        "selected_case_checksums": {"ordinary_valid": "e" * 64},
        "code_revision": "f" * 40,
        "runtime_attestation": _binding_runtime_attestation(),
    }
    values.update(overrides)
    return research_gpu_binding_checksum(**values)  # type: ignore[arg-type]


def test_policy_versions_are_stable_and_v3_non_latency_requirements_are_unchanged() -> None:
    assert PROMOTION_POLICY_CHECKSUM == "309f35a2842827002dae007a8d3f4e2ac5c082326b9e6697969d858b8c37f25c"
    assert RESEARCH_GPU_POLICY_VERSION == "report_synthesis.research_gpu.v2"
    payload = normalized_policy_payload()
    assert sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == RESEARCH_GPU_POLICY_CHECKSUM
    non_latency = dict(RESEARCH_GPU_POLICY["non_latency_requirements"])
    assert non_latency == {key: value for key, value in PROMOTION_POLICY.items() if key != "max_average_latency_ms"}
    payload["max_mean_model_request_latency_ms"] = 1
    assert RESEARCH_GPU_POLICY["max_mean_model_request_latency_ms"] == 30_000
    with pytest.raises(TypeError):
        RESEARCH_GPU_POLICY["max_mean_model_request_latency_ms"] = 1


@pytest.mark.parametrize("environment", ["development", "dev", "exercise"])
def test_policy_requires_both_server_flags_and_allowed_isolated_environment(environment: str) -> None:
    assert resolve_research_gpu_policy(
        enabled=True,
        isolated=True,
        app_env=environment,
        public_demo_mode=False,
    )["enabled_by_default"] is False


@pytest.mark.parametrize(
    "settings",
    [
        {"enabled": False, "isolated": True, "app_env": "development", "public_demo_mode": False},
        {"enabled": True, "isolated": False, "app_env": "development", "public_demo_mode": False},
        {"enabled": True, "isolated": True, "app_env": "staging", "public_demo_mode": False},
        {"enabled": True, "isolated": True, "app_env": "production", "public_demo_mode": False},
        {"enabled": True, "isolated": True, "app_env": "development", "public_demo_mode": True},
    ],
)
def test_policy_selection_fails_closed(settings: dict[str, object]) -> None:
    with pytest.raises(ResearchGpuPolicyError):
        resolve_research_gpu_policy(**settings)  # type: ignore[arg-type]


def test_policy_and_binding_checksums_bind_every_authority() -> None:
    baseline = _binding()
    assert baseline == _binding()
    changes = [
        {"model_registry_id": "another-model"},
        {"prompt_checksum": "1" * 64},
        {"ordinary_dataset": _dataset_authority("report_synthesis_public_v2", "1" * 64)},
        {"adversarial_dataset": _dataset_authority("report_synthesis_adversarial_v1", "2" * 64)},
        {"environment": "exercise"},
        {"evaluation_plan": "full"},
        {"selected_case_checksums": {"ordinary_valid": "3" * 64}},
        {"code_revision": "e" * 40},
        {"runtime_attestation": {**_binding_runtime_attestation(), "server_version": "0.13.3"}},
    ]
    assert all(_binding(**change) != baseline for change in changes)
    with pytest.raises(ResearchGpuPolicyError, match="weights digest"):
        _binding(model_weights_digest="mutable-model-tag")
    with pytest.raises(ResearchGpuPolicyError, match="manifest digest"):
        _binding(model_manifest_digest="sha256:" + "1" * 64)
    with pytest.raises(ResearchGpuPolicyError, match="environment"):
        _binding(environment="production")


def test_research_gpu_provider_requires_local_public_only_pinned_ollama(monkeypatch) -> None:
    provider = _verified_provider(monkeypatch)
    assert research_gpu_provider_is_allowed(provider, provider.manifest_digest, provider.weights_digest)
    provider.base_url = "https://models.example.net"
    assert not research_gpu_provider_is_allowed(provider, provider.manifest_digest, provider.weights_digest)
    provider.base_url = BASE_URL
    provider.privacy_classification = "unknown"
    assert not research_gpu_provider_is_allowed(provider, provider.manifest_digest, provider.weights_digest)
    provider.privacy_classification = "public_only"
    assert not research_gpu_provider_is_allowed(provider, provider.manifest_digest, "sha256:" + "b" * 64)


def test_research_operation_bounds_are_inclusive_and_reject_missing_or_late_measurements() -> None:
    assert research_operation_within_bounds(duration_ms=120_000, model_calls=2, research_passes=2)
    assert research_operation_within_bounds(duration_ms=0, model_calls=0, research_passes=0)
    assert not research_operation_within_bounds(duration_ms=120_001, model_calls=2, research_passes=2)
    assert not research_operation_within_bounds(duration_ms=120_000, model_calls=3, research_passes=2)
    assert not research_operation_within_bounds(duration_ms=120_000, model_calls=2, research_passes=3)
    assert not research_operation_within_bounds(duration_ms=True, model_calls=2, research_passes=2)
    assert not research_operation_within_bounds(duration_ms=None, model_calls=2, research_passes=2)  # type: ignore[arg-type]


def test_only_the_code_owned_five_case_or_full_corpus_plans_are_available() -> None:
    ordinary = report_synthesis_public_dataset().cases
    adversarial = report_synthesis_adversarial_dataset().cases
    representative, ids = evaluation_case_plan(ordinary, adversarial, plan="representative")
    full, full_ids = evaluation_case_plan(ordinary, adversarial, plan="full")
    assert len(representative) == len(ids) == 5
    assert ids == ("ordinary_valid", "risk_mutation", "source_mutation", "instruction_like_context", "direct_injection")
    assert len(full) == len(full_ids) == 31
    with pytest.raises(ResearchGpuPolicyError):
        evaluation_case_plan(ordinary, adversarial, plan="client-selected")


def test_evaluation_timeout_override_is_bounded_without_sleeping(monkeypatch) -> None:
    provider = _verified_provider(monkeypatch)
    requests = []

    def post(url: str, *, json: dict[str, object], timeout: float):
        if url.endswith("/api/show"):
            return _HttpResponse({
                "modelfile": "FROM /root/.ollama/models/blobs/sha256-" + MODEL_DIGEST.removeprefix("sha256:"),
                "details": {"format": "gguf", "family": "qwen2", "quantization_level": "Q4_K_M"},
            })
        requests.append((url, json, timeout))
        return _HttpResponse({
            "model": provider.model,
            "response": "not json",
            "prompt_eval_count": 7,
            "eval_count": 3,
            "load_duration": 1_000_000,
            "total_duration": 2_000_000,
            "prompt_eval_duration": 500_000,
            "eval_duration": 1_000_000,
        })

    monkeypatch.setattr(research_gpu_ollama.httpx, "post", post)
    provider.prepare_cold_start()
    case = report_synthesis_public_dataset().cases[0]
    result = evaluation._evaluate_case(
        provider,
        case,
        provider_timeout_seconds=45,
        latency_phase="cold",
    )
    assert result["structured_output_valid"] is False
    assert result["provider_failure"] is False
    assert result["latency_phase"] == "cold"
    assert result["input_tokens"] == 7 and result["output_tokens"] == 3
    assert requests[0][0] == f"{BASE_URL}/api/generate"
    assert requests[0][1]["model"] == "qwen2.5:7b-instruct-q4_K_M"
    assert requests[0][1]["stream"] is False and requests[0][1]["format"] == "json"
    assert requests[0][2] == 45
    with pytest.raises(ValueError, match="bounded contract"):
        evaluation._evaluate_case(provider, case, provider_timeout_seconds=45.001)


@pytest.fixture
def evaluation_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with session_factory() as db:
            yield db
    finally:
        Base.metadata.drop_all(engine)


def _passing_metrics(*, latency_phase: str) -> dict[str, object]:
    return {
        "passed": True,
        "structured_output_valid": True,
        "deterministic_preserved": True,
        "source_integrity": True,
        "citation_consistency": True,
        "unsupported_claim_count": 0,
        "uncertainty_preserved": True,
        "source_instruction_flag_count": 0,
        "poisoning_detected": False,
        "deterministic_integrity": True,
        "missing_data_honesty": True,
        "unsafe_language_violation": False,
        "provider_failure": False,
        "latency_ms": 30_000 if latency_phase == "cold" else 1_000,
        "latency_phase": latency_phase,
        "input_tokens": 10,
        "output_tokens": 5,
        "total_tokens": 15,
        "cost_microusd": None,
        "reason_code": "accepted",
    }


def _isolated_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "app_env": "development",
        "deployment_commit": "f" * 40,
        "public_demo_mode": False,
        "research_gpu_evaluation_enabled": True,
        "research_gpu_evaluation_isolated": True,
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def test_internal_gpu_evaluation_binds_and_persists_cold_warm_nonpromotable_evidence(
    evaluation_db,
    monkeypatch,
) -> None:
    settings = _isolated_settings()
    monkeypatch.setattr(evaluation, "get_settings", lambda: settings)
    provider = _verified_provider(monkeypatch)
    actor = user_context(create_user(evaluation_db, "gpu-policy@example.test", role="admin"))
    phases: list[str] = []

    def fake_case(_provider, _case, *, provider_timeout_seconds, latency_phase):
        assert provider_timeout_seconds == 45
        assert not evaluation_db.in_transaction()
        phases.append(latency_phase)
        _set_fake_observation(provider, latency_phase)
        return _passing_metrics(latency_phase=latency_phase)

    monkeypatch.setattr(evaluation, "_evaluate_case", fake_case)
    run = evaluate_report_synthesis_research_gpu_candidate(
        evaluation_db,
        provider=provider,
        actor=actor,
        model_manifest_digest=provider.manifest_digest,
        model_weights_digest=provider.weights_digest,
    )
    results = evaluation_db.execute(
        select(ModelEvaluationCaseResultModel)
        .where(ModelEvaluationCaseResultModel.evaluation_run_id == run.id)
        .order_by(ModelEvaluationCaseResultModel.created_at, ModelEvaluationCaseResultModel.case_id)
    ).scalars().all()
    candidate = evaluation_db.get(ModelRegistryModel, run.candidate_model_registry_id)
    snapshot = evaluation_run_snapshot(run)
    assert run.status == "completed"
    assert run.policy_version == RESEARCH_GPU_POLICY_VERSION
    assert run.policy_checksum == RESEARCH_GPU_POLICY_CHECKSUM
    assert run.evaluation_binding_checksum and len(run.evaluation_binding_checksum) == 64
    assert run.promotion_eligible is False
    assert run.failure_reason is None
    assert run.cold_latency_count == 1 and run.cold_latency_total_ms == 30_000
    assert run.warm_latency_count == 4 and run.warm_latency_total_ms == 4_000
    assert snapshot["latency_mean_ms"] == 6_800
    assert snapshot["cold_latency_mean_ms"] == 30_000
    assert snapshot["warm_latency_mean_ms"] == 1_000
    assert run.latency_known_count == 5 and run.token_observation_count == 5
    assert run.cost_observation_count == 0  # unknown app-level cost is not a zero-cost claim
    assert "runtime_attestation" in run.evaluation_binding_json
    assert all(row.provider_observed_at is not None for row in results)
    assert all(row.ollama_total_duration_ns == 2_000_000 for row in results)
    assert [row.latency_phase for row in results].count("cold") == 1
    assert [row.latency_phase for row in results].count("warm") == 4
    assert phases == ["cold", "warm", "warm", "warm", "warm"]
    assert candidate is not None
    assert candidate.lifecycle_state == "registered"
    assert candidate.evaluation_state == "not_evaluated"
    assert route_snapshot(evaluation_db, environment="development")["policy_version"] is None
    with pytest.raises(ModelEvaluationError, match="Passing completed"):
        promote_evaluation_route(evaluation_db, evaluation_run_id=run.id, actor=actor)

    # Even a corrupted eligibility bit cannot make a research-GPU run pass the
    # exact v3 promotion-version/checksum gate.
    evaluation_db.execute(
        ModelEvaluationRunModel.__table__.update()
        .where(ModelEvaluationRunModel.id == run.id)
        .values(promotion_eligible=True)
    )
    evaluation_db.commit()
    with pytest.raises(ModelEvaluationError, match="current promotion policy"):
        promote_evaluation_route(evaluation_db, evaluation_run_id=run.id, actor=actor)


def test_missing_native_metrics_finalize_as_incomplete_without_mutating_case_reason(
    evaluation_db,
    monkeypatch,
) -> None:
    monkeypatch.setattr(evaluation, "get_settings", lambda: _isolated_settings())
    actor = user_context(create_user(evaluation_db, "gpu-missing-native@example.test", role="admin"))
    provider = _verified_provider(monkeypatch)

    def fake_case(_provider, _case, *, provider_timeout_seconds, latency_phase):
        assert provider_timeout_seconds == 45
        row = _passing_metrics(latency_phase=latency_phase)
        if latency_phase == "cold":
            provider.last_observation = None
            row["passed"] = False
            row["structured_output_valid"] = False
            row["reason_code"] = "unexpected_output_fields"
        else:
            _set_fake_observation(provider, latency_phase)
        return row

    monkeypatch.setattr(evaluation, "_evaluate_case", fake_case)
    run = evaluate_report_synthesis_research_gpu_candidate(
        evaluation_db,
        provider=provider,
        actor=actor,
        model_manifest_digest=provider.manifest_digest,
        model_weights_digest=provider.weights_digest,
    )
    cases = evaluation_db.execute(
        select(ModelEvaluationCaseResultModel).where(
            ModelEvaluationCaseResultModel.evaluation_run_id == run.id
        )
    ).scalars().all()
    cold = next(row for row in cases if row.latency_phase == "cold")

    assert run.status == "completed"
    assert run.case_count == 5
    assert run.failure_reason == "research_gpu_measurements_incomplete"
    assert run.promotion_eligible is False
    assert run.provider_failure_count == 0
    assert len(cases) == 5
    assert cold.reason_code == "unexpected_output_fields"
    assert cold.provider_failure is False
    assert cold.ollama_total_duration_ns is None
    assert cold.provider_observed_at is None


def test_cold_timeout_finalizes_all_cases_without_retry_or_unverified_warm_phase(
    evaluation_db,
    monkeypatch,
) -> None:
    monkeypatch.setattr(evaluation, "get_settings", lambda: _isolated_settings())
    actor = user_context(create_user(evaluation_db, "gpu-cold-timeout@example.test", role="admin"))
    provider = _verified_provider(monkeypatch)
    generate_requests: list[str] = []

    def post(url: str, *, json: dict[str, object], timeout: float):
        if url.endswith("/api/show"):
            return _HttpResponse({
                "modelfile": "FROM /root/.ollama/models/blobs/sha256-" + MODEL_DIGEST.removeprefix("sha256:"),
                "details": {"format": "gguf", "family": "qwen2", "quantization_level": "Q4_K_M"},
            })
        generate_requests.append(url)
        raise research_gpu_ollama.httpx.ReadTimeout("synthetic cold request timeout")

    monkeypatch.setattr(research_gpu_ollama.httpx, "post", post)
    run = evaluate_report_synthesis_research_gpu_candidate(
        evaluation_db,
        provider=provider,
        actor=actor,
        model_manifest_digest=provider.manifest_digest,
        model_weights_digest=provider.weights_digest,
    )
    cases = evaluation_db.execute(
        select(ModelEvaluationCaseResultModel).where(
            ModelEvaluationCaseResultModel.evaluation_run_id == run.id
        )
    ).scalars().all()
    by_case = {row.case_id: row for row in cases}

    assert len(cases) == 5
    assert generate_requests == [f"{BASE_URL}/api/generate"]
    assert run.status == "completed"
    assert run.case_count == 5
    assert run.failure_reason == "research_gpu_measurements_incomplete"
    assert run.promotion_eligible is False
    assert run.provider_failure_count == 1
    assert by_case["ordinary_valid"].provider_failure is True
    assert by_case["ordinary_valid"].reason_code == "provider_error"
    assert by_case["ordinary_valid"].latency_phase == "cold"
    assert by_case["risk_mutation"].provider_failure is False
    assert by_case["risk_mutation"].reason_code == "runtime_evidence_incomplete"
    assert by_case["risk_mutation"].latency_phase is None
    assert by_case["risk_mutation"].latency_ms is None


def test_genuine_immutable_binding_mutation_still_fails_closed(evaluation_db, monkeypatch) -> None:
    monkeypatch.setattr(evaluation, "get_settings", lambda: _isolated_settings())
    actor = user_context(create_user(evaluation_db, "gpu-authority-mutation@example.test", role="admin"))
    provider = _verified_provider(monkeypatch)
    mutated = False

    def fake_case(_provider, _case, *, provider_timeout_seconds, latency_phase):
        nonlocal mutated
        assert provider_timeout_seconds == 45
        _set_fake_observation(provider, latency_phase)
        if not mutated:
            run = evaluation_db.execute(
                select(ModelEvaluationRunModel).where(ModelEvaluationRunModel.status == "running")
            ).scalar_one()
            payload = dict(run.evaluation_binding_json)
            payload["code_revision"] = "0" * 40
            run.evaluation_binding_json = payload
            evaluation_db.commit()
            mutated = True
        return _passing_metrics(latency_phase=latency_phase)

    monkeypatch.setattr(evaluation, "_evaluate_case", fake_case)
    with pytest.raises(ModelEvaluationError, match="immutable authority changed before completion"):
        evaluate_report_synthesis_research_gpu_candidate(
            evaluation_db,
            provider=provider,
            actor=actor,
            model_manifest_digest=provider.manifest_digest,
            model_weights_digest=provider.weights_digest,
        )
    run = evaluation_db.execute(select(ModelEvaluationRunModel)).scalar_one()
    assert mutated is True
    assert run.status == "failed"
    assert run.failure_reason == "research_evaluation_interrupted"
    assert run.promotion_eligible is False
    assert run.case_count == 0


def test_uncertain_adapter_refusal_is_not_counted_as_provider_failure(monkeypatch) -> None:
    provider = _verified_provider(monkeypatch)
    provider._request_phase_uncertain = True
    case = report_synthesis_public_dataset().cases[0]

    result = evaluation._evaluate_case(
        provider,
        case,
        provider_timeout_seconds=45,
        latency_phase="warm",
    )

    assert result["provider_failure"] is False
    assert result["provider_call_made"] is False
    assert result["reason_code"] == "runtime_evidence_incomplete"
    assert result["latency_ms"] is not None


@pytest.mark.parametrize(
    ("cold_ms", "warm_ms", "expected_failure"),
    [(30_000, 30_000, None), (30_001, 30_001, "research_gpu_policy_failed"), (45_000, 1_000, None)],
)
def test_latency_thresholds_include_cold_and_accept_exact_timeout_boundary(
    evaluation_db,
    monkeypatch,
    cold_ms: int,
    warm_ms: int,
    expected_failure: str | None,
) -> None:
    monkeypatch.setattr(evaluation, "get_settings", lambda: _isolated_settings())
    actor = user_context(create_user(evaluation_db, f"gpu-boundary-{cold_ms}-{warm_ms}@example.test", role="admin"))
    provider = _verified_provider(monkeypatch)

    def fake_case(_provider, _case, *, provider_timeout_seconds, latency_phase):
        assert provider_timeout_seconds == 45
        _set_fake_observation(provider, latency_phase)
        row = _passing_metrics(latency_phase=latency_phase)
        row["latency_ms"] = cold_ms if latency_phase == "cold" else warm_ms
        return row

    monkeypatch.setattr(evaluation, "_evaluate_case", fake_case)
    run = evaluate_report_synthesis_research_gpu_candidate(
        evaluation_db,
        provider=provider,
        actor=actor,
        model_manifest_digest=provider.manifest_digest,
        model_weights_digest=provider.weights_digest,
    )
    assert run.failure_reason == expected_failure
    assert run.promotion_eligible is False
    assert run.latency_known_count == 5
    if cold_ms == warm_ms == 30_000:
        assert run.latency_total_ms / run.latency_known_count == 30_000


@pytest.mark.parametrize("missing", ["latency", "tokens", "provider_failure", "late_response"])
def test_incomplete_usage_provider_failure_and_late_response_fail_closed(
    evaluation_db,
    monkeypatch,
    missing: str,
) -> None:
    monkeypatch.setattr(evaluation, "get_settings", lambda: _isolated_settings())
    actor = user_context(create_user(evaluation_db, f"gpu-{missing}@example.test", role="admin"))
    provider = _verified_provider(monkeypatch)

    def fake_case(_provider, _case, *, provider_timeout_seconds, latency_phase):
        assert provider_timeout_seconds == 45
        _set_fake_observation(provider, latency_phase)
        row = _passing_metrics(latency_phase=latency_phase)
        if missing == "latency" and latency_phase == "cold":
            row["latency_ms"] = None
        elif missing == "tokens" and latency_phase == "cold":
            row["input_tokens"] = None
            row["output_tokens"] = None
            row["total_tokens"] = None
        elif missing == "provider_failure" and latency_phase == "cold":
            row["provider_failure"] = True
            row["passed"] = False
        elif missing == "late_response" and latency_phase == "cold":
            row["latency_ms"] = 45_001
        return row

    monkeypatch.setattr(evaluation, "_evaluate_case", fake_case)
    run = evaluate_report_synthesis_research_gpu_candidate(
        evaluation_db,
        provider=provider,
        actor=actor,
        model_manifest_digest=provider.manifest_digest,
        model_weights_digest=provider.weights_digest,
    )
    assert run.promotion_eligible is False
    assert run.failure_reason == "research_gpu_policy_failed"
    if missing == "latency":
        assert run.latency_known_count == 4 and run.latency_total_ms == 4_000
    elif missing == "tokens":
        assert run.token_observation_count == 4 and run.input_tokens_total == 40
    elif missing == "provider_failure":
        assert run.provider_failure_count == 1
    else:
        assert run.latency_known_count == 5 and run.latency_total_ms == 49_001


def test_gpu_evaluation_entrypoint_is_disabled_by_default_and_has_no_http_route(evaluation_db, monkeypatch) -> None:
    default_settings = Settings(app_env="development")
    assert default_settings.research_gpu_evaluation_enabled is False
    assert default_settings.research_gpu_evaluation_isolated is False
    monkeypatch.setattr(evaluation, "get_settings", lambda: default_settings)
    provider = object()
    actor = user_context(create_user(evaluation_db, "gpu-disabled@example.test", role="admin"))
    with pytest.raises(ModelEvaluationError, match="disabled"):
        evaluate_report_synthesis_research_gpu_candidate(
            evaluation_db,
            provider=provider,
            actor=actor,
            model_manifest_digest=MANIFEST_DIGEST,
            model_weights_digest=MODEL_DIGEST,
        )
    assert not any("research-gpu" in getattr(route, "path", "") for route in _app.routes)
