from __future__ import annotations

import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.auth.service import create_user, user_context
from app.core.config import Settings
from app.db.session import normalize_database_url
from app.llm import evaluation, research_gpu_ollama
from app.llm.evaluation_authority import PROMOTION_POLICY_CHECKSUM, PROMOTION_POLICY_VERSION
from app.llm.research_gpu_policy import (
    RESEARCH_GPU_EXPECTED_MANIFEST_DIGEST,
    RESEARCH_GPU_EXPECTED_WEIGHTS_DIGEST,
    RESEARCH_GPU_POLICY_CHECKSUM,
    RESEARCH_GPU_POLICY_VERSION,
    research_gpu_binding_checksum_for_payload,
)
from app.models.model_governance import ModelEvaluationCaseResultModel, ModelEvaluationRunModel
from app.llm.research_gpu_ollama import OllamaNativeObservation, SshForwardingEvidence, VerifiedResearchGpuOllamaProvider


BACKEND_DIR = Path(__file__).resolve().parents[2]
PREVIOUS_REVISION = "20261022_0036"
QUALIFIED_REVISION = "20261025_0037"
LEGACY_RUN_ID = "eval_phase22_pg_legacy"
LEGACY_CASE_ID = "evalcase_phase22_pg_legacy"
PUBLIC_DATASET_ID = "dataset_phase22_pg_public"
ADVERSARIAL_DATASET_ID = "dataset_phase22_pg_adversarial"
MODEL_ID = "model_phase22_pg_qwen"
PROMPT_ID = "prompt_phase22_pg_synthesis"


def test_research_gpu_postgres_migration_cycle_preserves_history_and_constraints(monkeypatch) -> None:
    if os.getenv("RUN_F1A1I1_POSTGRES") != "true":
        pytest.skip("F1-A1I.1 PostgreSQL qualification requires RUN_F1A1I1_POSTGRES=true")
    raw_url = os.getenv("DATABASE_URL")
    if not raw_url:
        pytest.skip("F1-A1I.1 PostgreSQL qualification requires DATABASE_URL")
    admin_url = make_url(normalize_database_url(raw_url))
    if admin_url.get_backend_name() != "postgresql":
        pytest.skip("F1-A1I.1 migration qualification requires PostgreSQL")

    database_name = f"f1a1i1_{uuid4().hex[:20]}"
    admin = create_engine(admin_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    temporary_url = admin_url.set(database=database_name).render_as_string(hide_password=False)
    temp = None
    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{database_name}"'))
        temp = create_engine(temporary_url)
        with temp.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        started = perf_counter()
        _alembic(temporary_url, "upgrade", PREVIOUS_REVISION)
        upgrade_0036_seconds = perf_counter() - started
        version = _postgres_version(temp)
        with temp.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PREVIOUS_REVISION
        _seed_legacy_evidence(temp)
        history_before = _historical_snapshot(temp)

        started = perf_counter()
        _alembic(temporary_url, "upgrade", QUALIFIED_REVISION)
        upgrade_0037_seconds = perf_counter() - started
        with temp.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == QUALIFIED_REVISION
            run_columns = _columns(connection, "model_evaluation_runs")
            case_columns = _columns(connection, "model_evaluation_case_results")
            assert {
                "evaluation_binding_checksum",
                "evaluation_binding_json",
                "cold_latency_count",
                "warm_latency_count",
            } <= run_columns
            assert {
                "latency_phase",
                "ollama_load_duration_ns",
                "ollama_total_duration_ns",
                "ollama_prompt_eval_duration_ns",
                "ollama_eval_duration_ns",
                "provider_observed_at",
            } <= case_columns
            defaults = connection.execute(
                text(
                    "SELECT evaluation_binding_checksum, evaluation_binding_json, "
                    "cold_latency_count, cold_latency_total_ms, warm_latency_count, warm_latency_total_ms "
                    "FROM model_evaluation_runs WHERE id = :id"
                ),
                {"id": LEGACY_RUN_ID},
            ).mappings().one()
            assert defaults["evaluation_binding_checksum"] is None
            assert defaults["evaluation_binding_json"] is None
            assert (defaults["cold_latency_count"], defaults["cold_latency_total_ms"]) == (0, 0)
            assert (defaults["warm_latency_count"], defaults["warm_latency_total_ms"]) == (0, 0)
            old_case = connection.execute(
                text(
                    "SELECT latency_phase, ollama_load_duration_ns, provider_observed_at "
                    "FROM model_evaluation_case_results WHERE id = :id"
                ),
                {"id": LEGACY_CASE_ID},
            ).mappings().one()
            assert old_case["latency_phase"] is None
            assert old_case["ollama_load_duration_ns"] is None
            assert old_case["provider_observed_at"] is None

        v1_run_id, v1_case_ids = _run_v1_evaluation(temp, monkeypatch)
        assert v1_case_ids == {
            "ordinary_valid",
            "risk_mutation",
            "source_mutation",
            "instruction_like_context",
            "direct_injection",
        }
        _assert_invalid_constraints_rejected(temp, v1_run_id)
        assert _historical_snapshot(temp) == history_before

        started = perf_counter()
        _alembic(temporary_url, "downgrade", PREVIOUS_REVISION)
        downgrade_seconds = perf_counter() - started
        with temp.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PREVIOUS_REVISION
            assert "evaluation_binding_checksum" not in _columns(connection, "model_evaluation_runs")
            assert "ollama_load_duration_ns" not in _columns(connection, "model_evaluation_case_results")
            assert connection.scalar(
                text("SELECT COUNT(*) FROM model_evaluation_runs WHERE id = :id"), {"id": v1_run_id}
            ) == 1
        assert _historical_snapshot(temp) == history_before

        started = perf_counter()
        _alembic(temporary_url, "upgrade", QUALIFIED_REVISION)
        reupgrade_seconds = perf_counter() - started
        with temp.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == QUALIFIED_REVISION
            assert _columns(connection, "model_evaluation_runs").issuperset(
                {"evaluation_binding_checksum", "cold_latency_count"}
            )
            downgraded_v1 = connection.execute(
                text("SELECT evaluation_binding_checksum, evaluation_binding_json, promotion_eligible "
                     "FROM model_evaluation_runs WHERE id = :id"),
                {"id": v1_run_id},
            ).mappings().one()
            assert downgraded_v1["evaluation_binding_checksum"] is None
            assert downgraded_v1["evaluation_binding_json"] is None
            assert downgraded_v1["promotion_eligible"] is False
        assert _historical_snapshot(temp) == history_before
        print(
            "F1A1I1_PG_QUALIFICATION "
            f"version={version} upgrade_to_0036_s={upgrade_0036_seconds:.3f} "
            f"upgrade_0037_s={upgrade_0037_seconds:.3f} downgrade_s={downgrade_seconds:.3f} "
            f"reupgrade_s={reupgrade_seconds:.3f} expected_constraint_sqlstate=23514"
        )
    finally:
        if temp is not None:
            temp.dispose()
        with admin.connect() as connection:
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :name AND pid <> pg_backend_pid()"
                ),
                {"name": database_name},
            )
            connection.execute(text(f'DROP DATABASE IF EXISTS "{database_name}"'))
        admin.dispose()


def _seed_legacy_evidence(engine) -> None:
    now = datetime.now(UTC)
    with engine.begin() as connection:
        for dataset_id, version, checksum in (
            (PUBLIC_DATASET_ID, "public-v2", "1" * 64),
            (ADVERSARIAL_DATASET_ID, "adversarial-v1", "2" * 64),
        ):
            connection.execute(
                text(
                    "INSERT INTO model_evaluation_datasets "
                    "(id, task_key, task_version, dataset_version, purpose, dataset_checksum, case_count, lifecycle_state, created_at) "
                    "VALUES (:id, 'report_synthesis', 'v1', :version, 'PostgreSQL migration history fixture', :checksum, 1, 'active', :created)"
                ),
                {"id": dataset_id, "version": version, "checksum": checksum, "created": now},
            )
        connection.execute(
            text(
                "INSERT INTO model_registry "
                "(id, provider_key, model_key, model_version, endpoint_class, privacy_classification, lifecycle_state, evaluation_state, promotion_state, created_at) "
                "VALUES (:id, 'ollama', 'legacy-qwen', 'legacy-qwen', 'ollama_generate', 'public_only', 'registered', 'not_evaluated', 'not_promoted', :created)"
            ),
            {"id": MODEL_ID, "created": now},
        )
        connection.execute(
            text(
                "INSERT INTO model_prompt_versions "
                "(id, task_key, task_version, prompt_version, output_schema_version, safety_policy_version, prompt_checksum, created_at) "
                "VALUES (:id, 'report_synthesis', 'v1', 'pg-fixture-v1', 'schema-v1', 'safety-v1', :checksum, :created)"
            ),
            {"id": PROMPT_ID, "checksum": "3" * 64, "created": now},
        )
        connection.execute(
            text(
                "INSERT INTO model_evaluation_runs "
                "(id, task_key, task_version, dataset_id, adversarial_dataset_id, candidate_model_registry_id, "
                "baseline_type, prompt_version_id, environment, policy_version, policy_checksum, code_revision, status, "
                "case_count, passed_case_count, structured_output_valid_count, deterministic_preserved_count, "
                "source_integrity_count, missing_data_honesty_count, unsafe_language_violation_count, "
                "privacy_policy_violation_count, provider_failure_count, latency_known_count, latency_total_ms, "
                "token_observation_count, input_tokens_total, output_tokens_total, total_tokens_total, "
                "cost_observation_count, cost_microusd_total, promotion_eligible, started_at, completed_at) "
                "VALUES (:id, 'report_synthesis', 'v1', :dataset_id, :adversarial_id, :model_id, "
                "'deterministic_fallback', :prompt_id, 'development', :policy_version, :policy_checksum, :revision, 'completed', "
                "1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 900, 1, 31, 12, 43, 0, 0, false, :started, :completed)"
            ),
            {
                "id": LEGACY_RUN_ID,
                "dataset_id": PUBLIC_DATASET_ID,
                "adversarial_id": ADVERSARIAL_DATASET_ID,
                "model_id": MODEL_ID,
                "prompt_id": PROMPT_ID,
                "policy_version": PROMOTION_POLICY_VERSION,
                "policy_checksum": PROMOTION_POLICY_CHECKSUM,
                "revision": "d" * 40,
                "started": now,
                "completed": now,
            },
        )
        connection.execute(
            text(
                "INSERT INTO model_evaluation_case_results "
                "(id, evaluation_run_id, case_id, case_checksum, passed, structured_output_valid, "
                "deterministic_preserved, source_integrity, missing_data_honesty, unsafe_language_violation, "
                "privacy_policy_violation, provider_failure, latency_ms, input_tokens, output_tokens, total_tokens, "
                "reason_code, created_at) VALUES "
                "(:id, :run_id, 'ordinary_valid', :checksum, true, true, true, true, true, false, false, false, "
                "900, 31, 12, 43, 'accepted', :created)"
            ),
            {"id": LEGACY_CASE_ID, "run_id": LEGACY_RUN_ID, "checksum": "4" * 64, "created": now},
        )


def _run_v1_evaluation(engine, monkeypatch) -> tuple[str, set[str]]:
    settings = Settings(
        app_env="development",
        deployment_commit="f" * 40,
        public_demo_mode=False,
        research_gpu_evaluation_enabled=True,
        research_gpu_evaluation_isolated=True,
    )
    monkeypatch.setattr(evaluation, "get_settings", lambda: settings)
    transport = SshForwardingEvidence(4242, "root@203.0.113.10", 2222, 11435, "b" * 64, "c" * 64)
    monkeypatch.setattr(research_gpu_ollama, "verify_ssh_forwarding_process", lambda *_args, **_kwargs: transport)

    class Response:
        status_code = 200

        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    def get(url, *, timeout):
        assert timeout > 0
        if url.endswith("/api/version"):
            return Response({"version": "0.13.2"})
        if url.endswith("/api/tags"):
            return Response({"models": [{"name": "qwen2.5:7b-instruct-q4_K_M", "digest": RESEARCH_GPU_EXPECTED_MANIFEST_DIGEST.removeprefix("sha256:")}]})
        if url.endswith("/api/ps"):
            return Response({"models": []})
        raise AssertionError(url)

    monkeypatch.setattr(research_gpu_ollama.httpx, "get", get)
    monkeypatch.setattr(
        research_gpu_ollama.httpx,
        "head",
        lambda url, *, timeout: Response({})
        if url.endswith("/api/blobs/" + RESEARCH_GPU_EXPECTED_WEIGHTS_DIGEST)
        else pytest.fail(url),
    )
    monkeypatch.setattr(
        research_gpu_ollama.httpx,
        "post",
        lambda url, *, json, timeout: Response({
            "modelfile": "FROM /root/.ollama/models/blobs/sha256-" + RESEARCH_GPU_EXPECTED_WEIGHTS_DIGEST.removeprefix("sha256:"),
            "details": {"format": "gguf", "family": "qwen2", "quantization_level": "Q4_K_M"},
        }) if url.endswith("/api/show") else Response({"done": True}),
    )
    provider = VerifiedResearchGpuOllamaProvider.verify_runtime(
        base_url="http://127.0.0.1:11435",
        expected_manifest_digest=RESEARCH_GPU_EXPECTED_MANIFEST_DIGEST,
        expected_weights_digest=RESEARCH_GPU_EXPECTED_WEIGHTS_DIGEST,
        ssh_pid=4242,
    )
    with Session(engine) as db:
        operator = create_user(db, "f1a1i1-pg-admin@example.test", role="admin")
        actor = user_context(operator)

        def fake_case(_provider, _case, *, provider_timeout_seconds, latency_phase):
            assert provider_timeout_seconds == 45
            provider.last_observation = OllamaNativeObservation(
                phase=latency_phase,
                observed_at=datetime.now(UTC).isoformat(),
                load_duration_ns=900_000_000 if latency_phase == "cold" else 0,
                total_duration_ns=2_500_000_000,
                prompt_eval_duration_ns=700_000_000,
                eval_duration_ns=900_000_000,
                cold_load_confirmed=True,
                native_metrics_valid=True,
            )
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
                "latency_ms": 900,
                "latency_phase": latency_phase,
                "input_tokens": 31,
                "output_tokens": 12,
                "total_tokens": 43,
                "cost_microusd": None,
                "reason_code": "accepted",
            }

        monkeypatch.setattr(evaluation, "_evaluate_case", fake_case)
        run = evaluation.evaluate_report_synthesis_research_gpu_candidate(
            db,
            provider=provider,
            actor=actor,
            model_manifest_digest=provider.manifest_digest,
            model_weights_digest=provider.weights_digest,
            plan="representative",
        )
        assert run.status == "completed"
        assert run.promotion_eligible is False
        assert run.policy_version == RESEARCH_GPU_POLICY_VERSION
        assert run.policy_checksum == RESEARCH_GPU_POLICY_CHECKSUM
        assert run.evaluation_binding_checksum == research_gpu_binding_checksum_for_payload(run.evaluation_binding_json)
        assert run.cold_latency_count == 1
        assert run.warm_latency_count == 4
        cases = db.scalars(
            select(ModelEvaluationCaseResultModel).where(ModelEvaluationCaseResultModel.evaluation_run_id == run.id)
        ).all()
        assert len(cases) == 5
        assert all(case.provider_observed_at is not None and case.ollama_total_duration_ns is not None for case in cases)
        return run.id, {case.case_id for case in cases}


def _assert_invalid_constraints_rejected(engine, run_id: str) -> None:
    statements = [
        (
            "UPDATE model_evaluation_runs SET evaluation_binding_checksum = 'bad', "
            "evaluation_binding_json = '{}'::json WHERE id = :id",
            {"id": LEGACY_RUN_ID},
        ),
        (
            "UPDATE model_evaluation_runs SET evaluation_binding_checksum = NULL, "
            "evaluation_binding_json = '{}'::json WHERE id = :id",
            {"id": LEGACY_RUN_ID},
        ),
        (
            "UPDATE model_evaluation_runs SET cold_latency_count = 6 WHERE id = :id",
            {"id": run_id},
        ),
        (
            "UPDATE model_evaluation_case_results SET latency_phase = 'lukewarm' "
            "WHERE evaluation_run_id = :run_id AND case_id = 'ordinary_valid'",
            {"run_id": run_id},
        ),
        (
            "UPDATE model_evaluation_case_results SET ollama_load_duration_ns = 45000000001 "
            "WHERE evaluation_run_id = :run_id AND case_id = 'ordinary_valid'",
            {"run_id": run_id},
        ),
    ]
    states = []
    for index, (sql, params) in enumerate(statements, start=1):
        try:
            with engine.begin() as connection:
                connection.execute(text(sql), params)
        except DBAPIError as error:
            states.append(getattr(error.orig, "sqlstate", None))
        else:
            raise AssertionError(f"invalid-evidence constraint case {index} unexpectedly passed")
    assert states == ["23514"] * len(statements)


def _historical_snapshot(engine) -> tuple[dict[str, object], dict[str, object]]:
    with engine.connect() as connection:
        run = dict(
            connection.execute(
                text(
                    "SELECT id, task_key, task_version, dataset_id, adversarial_dataset_id, "
                    "candidate_model_registry_id, prompt_version_id, policy_version, policy_checksum, "
                    "code_revision, status, case_count, passed_case_count, latency_total_ms, "
                    "promotion_eligible, started_at, completed_at FROM model_evaluation_runs WHERE id = :id"
                ),
                {"id": LEGACY_RUN_ID},
            ).mappings().one()
        )
        case = dict(
            connection.execute(
                text(
                    "SELECT id, evaluation_run_id, case_id, case_checksum, passed, structured_output_valid, "
                    "deterministic_preserved, source_integrity, latency_ms, input_tokens, output_tokens, "
                    "total_tokens, reason_code, created_at FROM model_evaluation_case_results WHERE id = :id"
                ),
                {"id": LEGACY_CASE_ID},
            ).mappings().one()
        )
        return run, case


def _postgres_version(engine) -> str:
    with engine.connect() as connection:
        return str(connection.scalar(text("SELECT version()")))


def _columns(connection, table: str) -> set[str]:
    return set(
        connection.scalars(
            text("SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = :table"),
            {"table": table},
        )
    )


def _alembic(database_url: str, command: str, revision: str) -> None:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url
    environment["APP_ENV"] = "test"
    result = subprocess.run(
        [sys.executable, "-m", "alembic", command, revision],
        cwd=BACKEND_DIR,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise AssertionError(
            f"Alembic {command} {revision} failed (exit {result.returncode}).\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
