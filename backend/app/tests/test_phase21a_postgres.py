from __future__ import annotations

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.db.session import create_database_engine, normalize_database_url
from app.llm.governance import ensure_configured_model_registration
from app.llm.provenance import ModelIdentity
from app.models.model_governance import ModelRegistryModel, ModelTaskCapabilityModel


BACKEND_DIR = Path(__file__).resolve().parents[2]
PHASE20J_HEAD = "20260828_0029"
PHASE21A_HEAD = "20260904_0030"
EXPECTED_FREE_LIMITS = {
    "limit.analysis.count": 25,
    "limit.simulation.count": 100,
    "limit.options.count": 100,
    "limit.market_data.count": 100,
    "limit.saved_thesis.count": 50,
    "limit.watchlist.count": 25,
    "limit.schedule.active_count": 5,
}


pytestmark = pytest.mark.postgres_integration


@pytest.fixture(scope="module")
def postgres_sessions() -> sessionmaker:
    if os.getenv("RUN_POSTGRES_INTEGRATION") != "true":
        pytest.skip("Phase 21A PostgreSQL tests require RUN_POSTGRES_INTEGRATION=true")
    engine = create_database_engine()
    if engine.dialect.name != "postgresql":
        pytest.skip("Phase 21A PostgreSQL tests require a PostgreSQL DATABASE_URL")
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_postgres_concurrent_configured_model_registration_is_one_winner(postgres_sessions: sessionmaker) -> None:
    identity = ModelIdentity("ollama", f"phase21a-{uuid4().hex[:12]}", "v1", "ollama_generate", "unknown")
    barrier = Barrier(2)

    def register() -> str:
        with postgres_sessions() as db:
            barrier.wait(timeout=10)
            record = ensure_configured_model_registration(db, identity)
            db.commit()
            return record.id

    model_id = ""
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            result_ids = list(executor.map(lambda _: register(), range(2)))
        assert result_ids[0] == result_ids[1]
        model_id = result_ids[0]
        with postgres_sessions() as db:
            assert db.scalar(select(func.count()).select_from(ModelRegistryModel).where(ModelRegistryModel.id == model_id)) == 1
            assert db.scalar(
                select(func.count()).select_from(ModelTaskCapabilityModel).where(ModelTaskCapabilityModel.model_registry_id == model_id)
            ) == 1
    finally:
        if model_id:
            with postgres_sessions() as db:
                db.execute(delete(ModelTaskCapabilityModel).where(ModelTaskCapabilityModel.model_registry_id == model_id))
                db.execute(delete(ModelRegistryModel).where(ModelRegistryModel.id == model_id))
                db.commit()


def test_phase21a_postgres_migration_cycle_preserves_phase20_and_reseeds_prompt() -> None:
    if os.getenv("RUN_POSTGRES_INTEGRATION") != "true":
        pytest.skip("Phase 21A PostgreSQL migration requires RUN_POSTGRES_INTEGRATION=true")
    source_url = normalize_database_url(os.environ["DATABASE_URL"])
    url = make_url(source_url)
    if url.get_backend_name() != "postgresql":
        pytest.skip("Phase 21A PostgreSQL migration requires PostgreSQL DATABASE_URL")

    database_name = f"phase21a_migration_{uuid4().hex[:16]}"
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

        _alembic(temporary_url, "upgrade", PHASE20J_HEAD)
        _assert_phase20(temporary_url)
        _alembic(temporary_url, "upgrade", PHASE21A_HEAD)
        _assert_phase21a(temporary_url)
        _alembic(temporary_url, "downgrade", PHASE20J_HEAD)
        _assert_phase20(temporary_url)
        _alembic(temporary_url, "upgrade", PHASE21A_HEAD)
        _assert_phase21a(temporary_url)
    finally:
        with admin.connect() as connection:
            connection.execute(
                text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :name AND pid <> pg_backend_pid()"),
                {"name": database_name},
            )
            connection.execute(text(f'DROP DATABASE IF EXISTS "{database_name}"'))
        admin.dispose()


def _assert_phase20(database_url: str) -> None:
    with create_engine(database_url).connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PHASE20J_HEAD
        tables = _tables(connection)
        assert {"organization_invitations", "customer_requests", "plan_versions", "plan_entitlements"}.issubset(tables)
        assert not {"model_registry", "model_task_capabilities", "model_prompt_versions", "model_run_provenance"} & tables
        _assert_free_v1(connection)


def _assert_phase21a(database_url: str) -> None:
    with create_engine(database_url).connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PHASE21A_HEAD
        tables = _tables(connection)
        assert {"model_registry", "model_task_capabilities", "model_prompt_versions", "model_run_provenance"}.issubset(tables)
        assert connection.scalar(text("SELECT COUNT(*) FROM model_prompt_versions WHERE id = 'prompt_report_synthesis_v1'")) == 1
        assert connection.scalar(
            text("SELECT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_model_run_report_task')")
        ) is True
        _assert_free_v1(connection)


def _assert_free_v1(connection) -> None:
    rows = connection.execute(
        text("SELECT entitlement_key, hard_limit FROM plan_entitlements WHERE plan_version_id = 'plan_free_v1'")
    )
    assert {row.entitlement_key: row.hard_limit for row in rows} == EXPECTED_FREE_LIMITS


def _tables(connection) -> set[str]:
    return set(connection.scalars(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")))


def _assert_lineage() -> None:
    versions = BACKEND_DIR / "migrations" / "versions"
    assert not list(versions.glob("*0027*"))
    migration = next(versions.glob("*20260904_0030*.py"))
    contents = migration.read_text()
    assert 'revision = "20260904_0030"' in contents
    assert 'down_revision = "20260828_0029"' in contents


def _alembic(database_url: str, command: str, revision: str) -> None:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url
    subprocess.run(
        [sys.executable, "-m", "alembic", command, revision],
        cwd=BACKEND_DIR,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
