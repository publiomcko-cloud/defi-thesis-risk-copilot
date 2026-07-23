from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[2]
PHASE16_HEAD = "20260721_0010"


def _alembic(database_path: Path, command: str, revision: str) -> None:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = f"sqlite:///{database_path}"
    subprocess.run(
        [sys.executable, "-m", "alembic", command, revision],
        cwd=BACKEND_DIR,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )


def test_phase17a_upgrade_downgrade_upgrade_has_durable_job_contract(tmp_path: Path) -> None:
    database_path = tmp_path / "phase17a.sqlite"
    _alembic(database_path, "upgrade", PHASE16_HEAD)
    _alembic(database_path, "upgrade", "head")

    connection = sqlite3.connect(database_path)
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {
        "jobs",
        "job_attempts",
        "job_events",
        "job_capacity_reservations",
        "workers",
        "worker_credentials",
        "artifacts",
    }.issubset(
        tables
    )
    assert _indexes(connection, "jobs") >= {
        "ix_jobs_claim",
        "ix_jobs_owner_status",
        "ix_jobs_org_status",
        "ix_jobs_retention",
    }
    assert "ix_worker_credentials_worker_status" in _indexes(connection, "worker_credentials")
    assert {frozenset({"token_prefix"}), frozenset({"token_hash"})}.issubset(
        _unique_column_sets(connection, "worker_credentials")
    )
    assert "ix_job_events_job_created" in _indexes(connection, "job_events")
    assert _indexes(connection, "job_capacity_reservations") >= {
        "ix_job_capacity_reservations_scope_type",
        "ix_job_capacity_reservations_scope_id",
    }
    assert frozenset({"scope_type", "scope_id"}) in _unique_column_sets(connection, "job_capacity_reservations")
    assert frozenset({"job_id", "sequence_number"}) in _unique_column_sets(connection, "job_events")
    assert _indexes(connection, "artifacts") >= {
        "ix_artifacts_owner_deleted",
        "ix_artifacts_org_visibility_deleted",
        "ix_artifacts_retention",
    }
    connection.close()

    _alembic(database_path, "downgrade", PHASE16_HEAD)
    _alembic(database_path, "upgrade", "head")
    connection = sqlite3.connect(database_path)
    assert connection.execute("SELECT COUNT(*) FROM jobs").fetchone() == (0,)
    connection.close()


def _indexes(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA index_list({table})")}


def _unique_column_sets(connection: sqlite3.Connection, table: str) -> set[frozenset[str]]:
    return {
        frozenset(row[2] for row in connection.execute(f"PRAGMA index_info('{index_name}')"))
        for _, index_name, unique, *_ in connection.execute(f"PRAGMA index_list({table})")
        if unique
    }
