from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[2]
PHASE20C_HEAD = "20260813_0024"


def test_phase20d_notification_migration_is_reversible_and_constrained(tmp_path: Path) -> None:
    database_path = tmp_path / "phase20d.sqlite"
    _alembic(database_path, "upgrade", PHASE20C_HEAD)
    _alembic(database_path, "upgrade", "head")

    connection = sqlite3.connect(database_path)
    assert {"notification_preferences", "notifications"}.issubset(_tables(connection))
    assert "ix_notifications_retention" in _indexes(connection, "notifications")
    assert "ix_notifications_owner_available" in _indexes(connection, "notifications")
    assert frozenset({"owner_user_id", "idempotency_key"}) in _unique_column_sets(connection, "notifications")
    assert frozenset({"user_id"}) in _unique_column_sets(connection, "notification_preferences")
    connection.close()

    _alembic(database_path, "downgrade", PHASE20C_HEAD)
    connection = sqlite3.connect(database_path)
    assert not {"notification_preferences", "notifications"} & _tables(connection)
    connection.close()

    _alembic(database_path, "upgrade", "head")
    connection = sqlite3.connect(database_path)
    assert "notifications" in _tables(connection)
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
