from __future__ import annotations

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.auth.service import create_user, user_context
from app.db.session import create_database_engine, normalize_database_url
from app.core.config import get_settings
from app.llm.base import LLMRequest, LLMResponse
from app.llm.evaluation import evaluate_report_synthesis_candidate, promote_evaluation_route, rollback_route
from app.llm.governance import ensure_report_synthesis_prompt_version
from app.llm.routing import capture_report_synthesis_execution_route, resolve_report_synthesis_execution_route
from app.models.model_governance import (
    ModelEvaluationCaseResultModel,
    ModelEvaluationRunModel,
    ModelRegistryModel,
    ModelRouteAssignmentModel,
    ModelRouteTransitionModel,
    ModelRouteVersionModel,
    ModelTaskCapabilityModel,
)


BACKEND_DIR = Path(__file__).resolve().parents[2]
PHASE21A_HEAD = "20260904_0030"
PHASE21B_HEAD = "20260906_0031"
EXPECTED_FREE_LIMITS = {
    "limit.analysis.count": 25,
    "limit.simulation.count": 100,
    "limit.options.count": 100,
    "limit.market_data.count": 100,
    "limit.saved_thesis.count": 50,
    "limit.watchlist.count": 25,
    "limit.schedule.active_count": 5,
}
PHASE21B_TABLES = {
    "model_evaluation_datasets",
    "model_evaluation_runs",
    "model_evaluation_case_results",
    "model_route_versions",
    "model_route_assignments",
    "model_route_transitions",
}


pytestmark = pytest.mark.postgres_integration


class PostgresSyntheticProvider:
    name = "phase21b_provider"
    privacy_classification = "private_approved"

    def __init__(self, model: str) -> None:
        self.model = model

    def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            text=(
                '{"executive_summary":"Synthetic educational summary preserves uncertainty.",'
                '"sections":{"Strategy Mechanics":"Synthetic mechanics remain bounded."}}'
            ),
            provider=self.name,
            model=self.model,
            input_tokens=9,
            output_tokens=5,
            total_tokens=14,
        )


@pytest.fixture(scope="module")
def postgres_sessions() -> sessionmaker:
    if os.getenv("RUN_POSTGRES_INTEGRATION") != "true":
        pytest.skip("Phase 21B PostgreSQL tests require RUN_POSTGRES_INTEGRATION=true")
    engine = create_database_engine()
    if engine.dialect.name != "postgresql":
        pytest.skip("Phase 21B PostgreSQL tests require a PostgreSQL DATABASE_URL")
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_postgres_simultaneous_promotions_leave_one_authoritative_assignment(postgres_sessions: sessionmaker) -> None:
    suffix = uuid4().hex[:12]
    operator_id, run_a, run_b = _seed_passing_runs(postgres_sessions, suffix)
    barrier = Barrier(2)
    route_ids: list[str] = []
    try:
        def promote_with_actor(run_id: str) -> str:
            from app.models.user import UserModel

            with postgres_sessions() as db:
                operator = user_context(db.get(UserModel, operator_id))
                barrier.wait(timeout=10)
                return promote_evaluation_route(db, evaluation_run_id=run_id, actor=operator).id

        with ThreadPoolExecutor(max_workers=2) as executor:
            route_ids = list(executor.map(promote_with_actor, [run_a, run_b]))
        assert len(set(route_ids)) == 2
        with postgres_sessions() as db:
            assignments = db.scalars(
                select(ModelRouteAssignmentModel).where(ModelRouteAssignmentModel.task_key == "report_synthesis")
            ).all()
            assert len(assignments) == 1
            assert assignments[0].active_route_version_id in route_ids
            routes = db.scalars(select(ModelRouteVersionModel).where(ModelRouteVersionModel.id.in_(route_ids))).all()
            assert len(routes) == 2
            assert len([route for route in routes if route.id == assignments[0].active_route_version_id]) == 1
            assert len(db.scalars(select(ModelRouteTransitionModel).where(ModelRouteTransitionModel.assignment_id == assignments[0].id)).all()) == 2
    finally:
        _cleanup_routes(postgres_sessions, suffix)


def test_postgres_promotion_and_rollback_race_keeps_consistent_assignment_history(postgres_sessions: sessionmaker) -> None:
    suffix = uuid4().hex[:12]
    operator_id, run_a, run_b = _seed_passing_runs(postgres_sessions, suffix)
    try:
        from app.models.user import UserModel

        with postgres_sessions() as db:
            operator = user_context(db.get(UserModel, operator_id))
            route_a = promote_evaluation_route(db, evaluation_run_id=run_a, actor=operator)
        barrier = Barrier(2)

        def promote_b() -> str:
            with postgres_sessions() as db:
                operator = user_context(db.get(UserModel, operator_id))
                barrier.wait(timeout=10)
                return promote_evaluation_route(db, evaluation_run_id=run_b, actor=operator).id

        def rollback_a() -> str | None:
            with postgres_sessions() as db:
                operator = user_context(db.get(UserModel, operator_id))
                barrier.wait(timeout=10)
                return rollback_route(db, route_version_id=route_a.id, actor=operator).active_route_version_id

        with ThreadPoolExecutor(max_workers=2) as executor:
            promoted_b, rollback_result = list(executor.map(lambda operation: operation(), [promote_b, rollback_a]))
        with postgres_sessions() as db:
            assignment = db.scalars(select(ModelRouteAssignmentModel).where(ModelRouteAssignmentModel.task_key == "report_synthesis")).one()
            assert assignment.active_route_version_id in {None, promoted_b}
            assert db.get(ModelRouteVersionModel, assignment.active_route_version_id) is not None if assignment.active_route_version_id else True
            transitions = db.scalars(select(ModelRouteTransitionModel).where(ModelRouteTransitionModel.assignment_id == assignment.id)).all()
            assert len(transitions) in {2, 3}
            assert rollback_result in {None, route_a.id, promoted_b}
    finally:
        _cleanup_routes(postgres_sessions, suffix)


def test_postgres_execution_snapshot_remains_historical_across_route_changes(postgres_sessions: sessionmaker, monkeypatch) -> None:
    monkeypatch.setenv("LLM_SYNTHESIS_ENABLED", "true")
    get_settings.cache_clear()
    suffix = uuid4().hex[:12]
    operator_id, run_a, run_b = _seed_passing_runs(postgres_sessions, suffix)
    try:
        from app.models.user import UserModel

        provider_a = PostgresSyntheticProvider(f"model-a-{suffix}")
        with postgres_sessions() as db:
            operator = user_context(db.get(UserModel, operator_id))
            route_a = promote_evaluation_route(db, evaluation_run_id=run_a, actor=operator)
            snapshot = capture_report_synthesis_execution_route(
                db,
                content_scope="private",
                configured_provider=provider_a,
            )
            route_b = promote_evaluation_route(db, evaluation_run_id=run_b, actor=operator)
            after_promotion = resolve_report_synthesis_execution_route(
                db,
                content_scope="private",
                snapshot_payload=snapshot,
                configured_provider=provider_a,
            )
            assert (after_promotion.route_version_id, after_promotion.evaluation_run_id) == (route_a.id, run_a)
            assignment = db.scalars(
                select(ModelRouteAssignmentModel).where(
                    ModelRouteAssignmentModel.task_key == route_a.task_key,
                    ModelRouteAssignmentModel.task_version == route_a.task_version,
                    ModelRouteAssignmentModel.environment == route_a.environment,
                )
            ).one()
            assert assignment.active_route_version_id == route_b.id

            rollback_route(db, route_version_id=route_b.id, actor=operator)
            rollback_route(db, route_version_id=route_a.id, actor=operator)
            after_rollback = resolve_report_synthesis_execution_route(
                db,
                content_scope="private",
                snapshot_payload=snapshot,
                configured_provider=provider_a,
            )
            assert (after_rollback.route_version_id, after_rollback.evaluation_run_id) == (route_a.id, run_a)
            assert assignment.active_route_version_id is None
    finally:
        get_settings.cache_clear()
        _cleanup_routes(postgres_sessions, suffix)


def test_phase21b_postgres_migration_cycle_preserves_phase20_and_21a() -> None:
    if os.getenv("RUN_POSTGRES_INTEGRATION") != "true":
        pytest.skip("Phase 21B PostgreSQL migration requires RUN_POSTGRES_INTEGRATION=true")
    source_url = normalize_database_url(os.environ["DATABASE_URL"])
    url = make_url(source_url)
    if url.get_backend_name() != "postgresql":
        pytest.skip("Phase 21B PostgreSQL migration requires a PostgreSQL DATABASE_URL")
    database_name = f"phase21b_migration_{uuid4().hex[:16]}"
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    temporary_url = url.set(database=database_name).render_as_string(hide_password=False)
    try:
        _assert_lineage()
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{database_name}"'))
        temp = create_engine(temporary_url, isolation_level="AUTOCOMMIT")
        with temp.connect() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        temp.dispose()

        _alembic(temporary_url, "upgrade", PHASE21A_HEAD)
        _assert_phase21a(temporary_url)
        _alembic(temporary_url, "upgrade", PHASE21B_HEAD)
        _assert_phase21b(temporary_url)
        _materialize_runtime_prompt_v2(temporary_url)
        _alembic(temporary_url, "downgrade", PHASE21A_HEAD)
        _assert_phase21a(temporary_url)
        _alembic(temporary_url, "upgrade", PHASE21B_HEAD)
        _assert_phase21b(temporary_url)
        _materialize_runtime_prompt_v2(temporary_url)
    finally:
        with admin.connect() as connection:
            connection.execute(
                text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :name AND pid <> pg_backend_pid()"),
                {"name": database_name},
            )
            connection.execute(text(f'DROP DATABASE IF EXISTS "{database_name}"'))
        admin.dispose()


def _seed_passing_runs(postgres_sessions: sessionmaker, suffix: str) -> tuple[str, str, str]:
    with postgres_sessions() as db:
        operator = create_user(db, f"phase21b-postgres-{suffix}@example.test", role="admin")
        actor = user_context(operator)
        run_a = evaluate_report_synthesis_candidate(db, provider=PostgresSyntheticProvider(f"model-a-{suffix}"), actor=actor)
        run_b = evaluate_report_synthesis_candidate(db, provider=PostgresSyntheticProvider(f"model-b-{suffix}"), actor=actor)
        return operator.id, run_a.id, run_b.id


def _cleanup_routes(postgres_sessions: sessionmaker, suffix: str) -> None:
    with postgres_sessions() as db:
        model_ids = db.scalars(select(ModelRegistryModel.id).where(ModelRegistryModel.provider_key == "phase21b_provider").where(ModelRegistryModel.model_key.like(f"%-{suffix}"))).all()
        if model_ids:
            run_ids = db.scalars(select(ModelEvaluationRunModel.id).where(ModelEvaluationRunModel.candidate_model_registry_id.in_(model_ids))).all()
            route_ids = db.scalars(select(ModelRouteVersionModel.id).where(ModelRouteVersionModel.model_registry_id.in_(model_ids))).all()
            assignment_ids = db.scalars(
                select(ModelRouteTransitionModel.assignment_id).where(
                    ModelRouteTransitionModel.from_route_version_id.in_(route_ids)
                    | ModelRouteTransitionModel.to_route_version_id.in_(route_ids)
                )
            ).all()
            if assignment_ids:
                db.execute(delete(ModelRouteTransitionModel).where(ModelRouteTransitionModel.assignment_id.in_(assignment_ids)))
                db.execute(delete(ModelRouteAssignmentModel).where(ModelRouteAssignmentModel.id.in_(assignment_ids)))
            if route_ids:
                db.execute(delete(ModelRouteVersionModel).where(ModelRouteVersionModel.id.in_(route_ids)))
            if run_ids:
                db.execute(delete(ModelEvaluationCaseResultModel).where(ModelEvaluationCaseResultModel.evaluation_run_id.in_(run_ids)))
                db.execute(delete(ModelEvaluationRunModel).where(ModelEvaluationRunModel.id.in_(run_ids)))
            db.execute(delete(ModelTaskCapabilityModel).where(ModelTaskCapabilityModel.model_registry_id.in_(model_ids)))
            db.execute(delete(ModelRegistryModel).where(ModelRegistryModel.id.in_(model_ids)))
        from app.models.user import UserModel

        users = db.scalars(select(UserModel.id).where(UserModel.email.like(f"phase21b-postgres-{suffix}%"))).all()
        if users:
            db.execute(delete(UserModel).where(UserModel.id.in_(users)))
        db.commit()


def _assert_phase21a(database_url: str) -> None:
    with create_engine(database_url).connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PHASE21A_HEAD
        tables = _tables(connection)
        assert {"model_registry", "model_task_capabilities", "model_prompt_versions", "model_run_provenance"}.issubset(tables)
        assert not PHASE21B_TABLES & tables
        assert {"route_version_id", "evaluation_run_id"}.isdisjoint(_columns(connection, "model_run_provenance"))
        assert connection.scalar(text("SELECT COUNT(*) FROM model_prompt_versions WHERE id = 'prompt_report_synthesis_v1'")) == 1
        _assert_free_v1(connection)


def _assert_phase21b(database_url: str) -> None:
    with create_engine(database_url).connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PHASE21B_HEAD
        assert PHASE21B_TABLES.issubset(_tables(connection))
        assert {"route_version_id", "evaluation_run_id"}.issubset(_columns(connection, "model_run_provenance"))
        assert connection.scalar(text("SELECT COUNT(*) FROM model_prompt_versions WHERE id = 'prompt_report_synthesis_v1'")) == 1
        _assert_free_v1(connection)


def _materialize_runtime_prompt_v2(database_url: str) -> None:
    with sessionmaker(bind=create_engine(database_url))() as db:
        assert ensure_report_synthesis_prompt_version(db).id == "prompt_report_synthesis_v2"
        db.commit()


def _assert_free_v1(connection) -> None:
    rows = connection.execute(text("SELECT entitlement_key, hard_limit FROM plan_entitlements WHERE plan_version_id = 'plan_free_v1'"))
    assert {row.entitlement_key: row.hard_limit for row in rows} == EXPECTED_FREE_LIMITS


def _tables(connection) -> set[str]:
    return set(connection.scalars(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")))


def _columns(connection, table: str) -> set[str]:
    return set(connection.scalars(text("SELECT column_name FROM information_schema.columns WHERE table_name = :table"), {"table": table}))


def _assert_lineage() -> None:
    versions = BACKEND_DIR / "migrations" / "versions"
    assert not list(versions.glob("*0027*"))
    migration = next(versions.glob("*20260906_0031*.py"))
    contents = migration.read_text()
    assert 'revision = "20260906_0031"' in contents
    assert 'down_revision = "20260904_0030"' in contents


def _alembic(database_url: str, command: str, revision: str) -> None:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url
    subprocess.run([sys.executable, "-m", "alembic", command, revision], cwd=BACKEND_DIR, env=environment, check=True, capture_output=True, text=True)
