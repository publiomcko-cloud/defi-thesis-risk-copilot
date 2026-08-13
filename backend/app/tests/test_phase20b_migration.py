from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[2]
PHASE20A_HEAD = "20260728_0022"


def test_phase20b_migration_is_reversible_and_preserves_existing_identity_data(tmp_path: Path) -> None:
    database_path = tmp_path / "phase20b.sqlite"
    _alembic(database_path, "upgrade", PHASE20A_HEAD)
    connection = sqlite3.connect(database_path)
    connection.execute(
        """
        INSERT INTO users (
            id, email, role, platform_role, account_status, plan, auth_provider,
            is_active, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "user_phase20b_preserved",
            "phase20b-preserved@example.test",
            "common",
            "user",
            "active",
            "free",
            "legacy_local",
            1,
            "2026-07-31T00:00:00+00:00",
            "2026-07-31T00:00:00+00:00",
        ),
    )
    connection.commit()
    connection.close()

    _alembic(database_path, "upgrade", "head")
    connection = sqlite3.connect(database_path)
    assert {
        "privacy_preferences",
        "privacy_preference_decisions",
        "product_analytics_events",
    }.issubset(_tables(connection))
    assert {
        "ix_privacy_preferences_user_enabled",
        "ix_privacy_preferences_user_id",
        "ix_privacy_preferences_purpose",
    }.issubset(_indexes(connection, "privacy_preferences"))
    assert "ix_product_analytics_events_expiry" in _indexes(
        connection, "product_analytics_events"
    )
    assert frozenset({"user_id", "purpose", "idempotency_key"}) in _unique_column_sets(
        connection, "privacy_preference_decisions"
    )
    assert frozenset({"event_key"}) in _unique_column_sets(
        connection, "product_analytics_events"
    )
    connection.close()

    _alembic(database_path, "downgrade", PHASE20A_HEAD)
    connection = sqlite3.connect(database_path)
    assert not {
        "privacy_preferences",
        "privacy_preference_decisions",
        "product_analytics_events",
    } & _tables(connection)
    assert connection.execute(
        "SELECT email FROM users WHERE id = ?", ("user_phase20b_preserved",)
    ).fetchone() == ("phase20b-preserved@example.test",)
    connection.close()

    _alembic(database_path, "upgrade", "head")
    connection = sqlite3.connect(database_path)
    assert "product_analytics_events" in _tables(connection)
    assert connection.execute(
        "SELECT COUNT(*) FROM users WHERE id = ?", ("user_phase20b_preserved",)
    ).fetchone() == (1,)
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
    return {
        row[0]
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }


def _indexes(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA index_list({table})")}


def _unique_column_sets(connection: sqlite3.Connection, table: str) -> set[frozenset[str]]:
    return {
        frozenset(
            row[2]
            for row in connection.execute(f"PRAGMA index_info('{index_name}')")
        )
        for _, index_name, unique, *_ in connection.execute(f"PRAGMA index_list({table})")
        if unique
    }
