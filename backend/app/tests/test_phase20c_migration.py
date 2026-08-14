from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[2]
PHASE20B_HEAD = "20260731_0023"


def test_phase20c_migration_is_reversible_and_preserves_existing_identity_data(tmp_path: Path) -> None:
    database_path = tmp_path / "phase20c.sqlite"
    _alembic(database_path, "upgrade", PHASE20B_HEAD)
    connection = sqlite3.connect(database_path)
    connection.execute(
        """
        INSERT INTO users (
            id, email, role, platform_role, account_status, plan, auth_provider,
            is_active, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "user_phase20c_preserved",
            "phase20c-preserved@example.test",
            "common",
            "user",
            "active",
            "free",
            "legacy_local",
            1,
            "2026-08-13T00:00:00+00:00",
            "2026-08-13T00:00:00+00:00",
        ),
    )
    connection.commit()
    connection.close()

    _alembic(database_path, "upgrade", "head")
    connection = sqlite3.connect(database_path)
    assert {"monitoring_schedules", "monitoring_schedule_occurrences"}.issubset(_tables(connection))
    assert {"ix_monitoring_schedules_due", "ix_monitoring_schedules_owner_status"}.issubset(
        _indexes(connection, "monitoring_schedules")
    )
    assert {
        "ix_monitoring_schedule_occurrences_schedule_time",
        "ix_monitoring_schedule_occurrences_expiry",
        "ix_monitoring_schedule_occurrences_job",
    }.issubset(_indexes(connection, "monitoring_schedule_occurrences"))
    assert frozenset({"schedule_id", "scheduled_for"}) in _unique_column_sets(
        connection, "monitoring_schedule_occurrences"
    )
    connection.close()

    _alembic(database_path, "downgrade", PHASE20B_HEAD)
    connection = sqlite3.connect(database_path)
    assert not {"monitoring_schedules", "monitoring_schedule_occurrences"} & _tables(connection)
    assert connection.execute(
        "SELECT email FROM users WHERE id = ?", ("user_phase20c_preserved",)
    ).fetchone() == ("phase20c-preserved@example.test",)
    connection.close()

    _alembic(database_path, "upgrade", "head")
    connection = sqlite3.connect(database_path)
    assert "monitoring_schedules" in _tables(connection)
    assert connection.execute("SELECT COUNT(*) FROM users").fetchone() == (1,)
    connection.close()


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


def _tables(connection: sqlite3.Connection) -> set[str]:
    return {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


def _indexes(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA index_list({table})")}


def _unique_column_sets(connection: sqlite3.Connection, table: str) -> set[frozenset[str]]:
    return {
        frozenset(row[2] for row in connection.execute(f"PRAGMA index_info('{index_name}')"))
        for _, index_name, unique, *_ in connection.execute(f"PRAGMA index_list({table})")
        if unique
    }
