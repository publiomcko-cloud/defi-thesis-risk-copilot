from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, text


BACKEND_DIR = Path(__file__).resolve().parents[2]
PHASE21D_HEAD = "20260910_0033"
PHASE21E_HEAD = "20260911_0034"
TRAINING_TABLES = {"training_dataset_manifests", "training_dataset_entries", "training_runs"}
EXPECTED_FREE_LIMITS = {
    "limit.analysis.count": 25,
    "limit.simulation.count": 100,
    "limit.options.count": 100,
    "limit.market_data.count": 100,
    "limit.saved_thesis.count": 50,
    "limit.watchlist.count": 25,
    "limit.schedule.active_count": 5,
}


def test_phase21e_sqlite_migration_cycle_is_reversible_and_preserves_prior_authorities(tmp_path: Path) -> None:
    _assert_lineage()
    database_url = f"sqlite:///{tmp_path / 'phase21e.sqlite'}"
    _alembic(database_url, "upgrade", PHASE21D_HEAD)
    engine = create_engine(database_url)
    _assert_21d(engine)
    _alembic(database_url, "upgrade", PHASE21E_HEAD)
    _assert_21e(engine)
    _alembic(database_url, "downgrade", PHASE21D_HEAD)
    _assert_21d(engine)
    with engine.connect() as connection:
        assert not TRAINING_TABLES & _tables(connection)
    _alembic(database_url, "upgrade", PHASE21E_HEAD)
    _assert_21e(engine)


def _assert_21d(engine) -> None:
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PHASE21D_HEAD
        assert {"thesis_revisions", "model_registry", "jobs", "artifacts", "vast_sessions"}.issubset(_tables(connection))
        assert not TRAINING_TABLES & _tables(connection)
        assert not {"trg_phase21e_manifest_immutable", "trg_phase21e_entry_immutable", "trg_phase21e_run_snapshot_immutable"} & set(
            connection.scalars(text("SELECT name FROM sqlite_master WHERE type = 'trigger'"))
        )
        _assert_free_v1(connection)


def _assert_21e(engine) -> None:
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PHASE21E_HEAD
        assert TRAINING_TABLES.issubset(_tables(connection))
        assert {"manifest_checksum", "held_out_evaluation_checksum", "split_policy_version", "eligibility_result"}.issubset(_columns(connection, "training_dataset_manifests"))
        assert {"split", "normalized_content_checksum", "source_class"}.issubset(_columns(connection, "training_dataset_entries"))
        assert {"job_id", "execution_snapshot", "candidate_class", "real_training_occurred", "result_json"}.issubset(_columns(connection, "training_runs"))
        _assert_free_v1(connection)
        triggers = set(connection.scalars(text("SELECT name FROM sqlite_master WHERE type = 'trigger'")))
        assert {"trg_phase21e_manifest_immutable", "trg_phase21e_entry_immutable", "trg_phase21e_run_snapshot_immutable"}.issubset(triggers)


def _assert_free_v1(connection) -> None:
    rows = connection.execute(text("SELECT entitlement_key, hard_limit FROM plan_entitlements WHERE plan_version_id = 'plan_free_v1'"))
    assert {row.entitlement_key: row.hard_limit for row in rows} == EXPECTED_FREE_LIMITS


def _tables(connection) -> set[str]:
    return set(connection.scalars(text("SELECT name FROM sqlite_master WHERE type = 'table'")))


def _columns(connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(text(f"PRAGMA table_info({table})"))}


def _assert_lineage() -> None:
    versions = BACKEND_DIR / "migrations" / "versions"
    assert not list(versions.glob("*0027*"))
    migration = versions / "20260911_0034_add_training_compute_governance.py"
    assert migration.is_file()
    contents = migration.read_text()
    assert 'revision = "20260911_0034"' in contents
    assert 'down_revision = "20260910_0033"' in contents
    assert len(list(versions.glob("*0034*"))) == 1


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
