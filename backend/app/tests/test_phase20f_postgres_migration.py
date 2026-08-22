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
PHASE20D_HEAD = "20260814_0025"
PHASE20F_HEAD = "20260821_0026"
PHASE20F_TABLES = {"plan_versions", "plan_entitlements", "entitlement_assignments", "non_billable_usage_events"}
EXPECTED_LIMITS = {
    "limit.analysis.count": 25, "limit.simulation.count": 100, "limit.options.count": 100,
    "limit.market_data.count": 100, "limit.saved_thesis.count": 50,
    "limit.watchlist.count": 25, "limit.schedule.active_count": 5,
}


@pytest.mark.postgres_integration
def test_phase20f_postgres_migration_cycle_isolated_database() -> None:
    if os.getenv("RUN_POSTGRES_INTEGRATION") != "true":
        pytest.skip("Phase 20F PostgreSQL migration cycle requires RUN_POSTGRES_INTEGRATION=true")
    source_url = normalize_database_url(os.environ["DATABASE_URL"])
    url = make_url(source_url)
    if url.get_backend_name() != "postgresql":
        pytest.skip("Phase 20F PostgreSQL migration cycle requires PostgreSQL DATABASE_URL")
    database_name = f"phase20f_migration_{uuid4().hex[:16]}"
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    temporary_url = url.set(database=database_name).render_as_string(hide_password=False)
    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{database_name}"'))
        # Historical migrations can require pgvector. btree_gist is deliberately
        # created by 0026 and intentionally left installed on downgrade.
        temp = create_engine(temporary_url, isolation_level="AUTOCOMMIT")
        with temp.connect() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        _alembic(temporary_url, "upgrade", PHASE20D_HEAD)
        _alembic(temporary_url, "upgrade", PHASE20F_HEAD)
        _assert_phase20f_upgrade(temporary_url)
        _alembic(temporary_url, "downgrade", PHASE20D_HEAD)
        with create_engine(temporary_url).connect() as connection:
            assert not PHASE20F_TABLES & _tables(connection)
            assert {"monitoring_schedules", "notifications"}.issubset(_tables(connection))
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PHASE20D_HEAD
            # It may pre-exist or be shared, so 0026 never drops btree_gist.
            assert connection.scalar(text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'btree_gist')")) is True
        _alembic(temporary_url, "upgrade", PHASE20F_HEAD)
        _assert_phase20f_upgrade(temporary_url)
    finally:
        with admin.connect() as connection:
            connection.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :name AND pid <> pg_backend_pid()"), {"name": database_name})
            connection.execute(text(f'DROP DATABASE IF EXISTS "{database_name}"'))
        admin.dispose()


def _alembic(database_url: str, command: str, revision: str) -> None:
    environment = os.environ.copy(); environment["DATABASE_URL"] = database_url
    subprocess.run([sys.executable, "-m", "alembic", command, revision], cwd=BACKEND_DIR, env=environment, check=True, capture_output=True, text=True)


def _assert_phase20f_upgrade(database_url: str) -> None:
    with create_engine(database_url).connect() as connection:
        assert PHASE20F_TABLES.issubset(_tables(connection))
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PHASE20F_HEAD
        assert connection.scalar(text("SELECT status FROM plan_versions WHERE id = 'plan_free_v1'")) == "active"
        rows = connection.execute(text("SELECT entitlement_key, hard_limit FROM plan_entitlements WHERE plan_version_id = 'plan_free_v1'"))
        assert dict(rows) == EXPECTED_LIMITS
        assert connection.scalar(text("SELECT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ex_entitlement_assignments_no_overlap')")) is True


def _tables(connection) -> set[str]:
    return set(connection.scalars(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")))
