from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
PHASE20D_HEAD = "20260814_0025"


def test_phase20f_migration_is_reversible_and_constrains_usage_units(tmp_path: Path) -> None:
    database_path = tmp_path / "phase20f.sqlite"
    _alembic(database_path, "upgrade", PHASE20D_HEAD)
    _alembic(database_path, "upgrade", "head")
    connection = sqlite3.connect(database_path)
    assert {"plan_versions", "plan_entitlements", "entitlement_assignments", "non_billable_usage_events"}.issubset(_tables(connection))
    assert "ix_non_billable_usage_subject_unit" in _indexes(connection, "non_billable_usage_events")
    assert frozenset({"unit_key", "logical_key"}) in _unique_column_sets(connection, "non_billable_usage_events")
    connection.close()
    _alembic(database_path, "downgrade", PHASE20D_HEAD)
    connection = sqlite3.connect(database_path)
    assert not {"plan_versions", "plan_entitlements", "entitlement_assignments", "non_billable_usage_events"} & _tables(connection)
    connection.close()
    _alembic(database_path, "upgrade", "head")


def _alembic(database_path: Path, command: str, revision: str) -> None:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = f"sqlite:///{database_path}"
    subprocess.run([sys.executable, "-m", "alembic", command, revision], cwd=BACKEND_DIR, env=environment, check=True, capture_output=True, text=True)


def _tables(connection: sqlite3.Connection) -> set[str]:
    return {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


def _indexes(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA index_list({table})")}


def _unique_column_sets(connection: sqlite3.Connection, table: str) -> set[frozenset[str]]:
    return {frozenset(row[2] for row in connection.execute(f"PRAGMA index_info('{index_name}')")) for _, index_name, unique, *_ in connection.execute(f"PRAGMA index_list({table})") if unique}
