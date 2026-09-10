from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.db.session import normalize_database_url


BACKEND_DIR = Path(__file__).resolve().parents[2]
PHASE21C_HEAD = "20260907_0032"
PHASE21D_HEAD = "20260910_0033"
RESEARCH_TABLES = {"thesis_revisions", "thesis_assumptions", "thesis_assumption_heads", "thesis_catalysts", "research_report_comparisons"}
EXPECTED_FREE_LIMITS = {
    "limit.analysis.count": 25, "limit.simulation.count": 100, "limit.options.count": 100,
    "limit.market_data.count": 100, "limit.saved_thesis.count": 50, "limit.watchlist.count": 25,
    "limit.schedule.active_count": 5,
}


@pytest.mark.postgres_integration
def test_phase21d_postgres_migration_cycle_is_reversible_and_preserves_21a_to_21c() -> None:
    if os.getenv("RUN_POSTGRES_INTEGRATION") != "true":
        pytest.skip("Phase 21D PostgreSQL migration requires RUN_POSTGRES_INTEGRATION=true")
    source_url = normalize_database_url(os.environ["DATABASE_URL"])
    url = make_url(source_url)
    if url.get_backend_name() != "postgresql":
        pytest.skip("Phase 21D PostgreSQL migration requires a PostgreSQL DATABASE_URL")
    name = f"phase21d_migration_{uuid4().hex[:16]}"
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    temporary_url = url.set(database=name).render_as_string(hide_password=False)
    try:
        _assert_lineage()
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}"'))
        temporary = create_engine(temporary_url, isolation_level="AUTOCOMMIT")
        with temporary.connect() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        temporary.dispose()
        _alembic(temporary_url, "upgrade", PHASE21C_HEAD)
        _assert_21c(temporary_url)
        _alembic(temporary_url, "upgrade", PHASE21D_HEAD)
        _assert_21d(temporary_url)
        _alembic(temporary_url, "downgrade", PHASE21C_HEAD)
        _assert_21c(temporary_url)
        _alembic(temporary_url, "upgrade", PHASE21D_HEAD)
        _assert_21d(temporary_url)
    finally:
        with admin.connect() as connection:
            connection.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :name AND pid <> pg_backend_pid()"), {"name": name})
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
        admin.dispose()


def _assert_21c(database_url: str) -> None:
    with create_engine(database_url).connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PHASE21C_HEAD
        assert {"model_registry", "model_evaluation_runs", "model_run_provenance", "model_run_quality_evidence", "model_feedback"}.issubset(_tables(connection))
        assert not RESEARCH_TABLES & _tables(connection)
        _assert_free_v1(connection)


def _assert_21d(database_url: str) -> None:
    with create_engine(database_url).connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PHASE21D_HEAD
        assert RESEARCH_TABLES.issubset(_tables(connection))
        assert connection.scalar(text("SELECT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_thesis_revisions_number')")) is True
        assert connection.scalar(text("SELECT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_research_report_comparisons_inputs')")) is True
        _assert_free_v1(connection)


def _assert_free_v1(connection) -> None:
    rows = connection.execute(text("SELECT entitlement_key, hard_limit FROM plan_entitlements WHERE plan_version_id = 'plan_free_v1'"))
    assert {row.entitlement_key: row.hard_limit for row in rows} == EXPECTED_FREE_LIMITS


def _tables(connection) -> set[str]:
    return set(connection.scalars(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")))


def _assert_lineage() -> None:
    versions = BACKEND_DIR / "migrations" / "versions"
    assert not list(versions.glob("*0027*"))
    assert not list(versions.glob("*0034*"))
    migration = versions / "20260910_0033_add_research_intelligence.py"
    assert migration.is_file()
    assert 'down_revision = "20260907_0032"' in migration.read_text()


def _alembic(database_url: str, command: str, revision: str) -> None:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url
    subprocess.run([sys.executable, "-m", "alembic", command, revision], cwd=BACKEND_DIR, env=environment, check=True, capture_output=True, text=True)
