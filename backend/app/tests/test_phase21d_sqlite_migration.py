from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, text


BACKEND_DIR = Path(__file__).resolve().parents[2]
PHASE21C_HEAD = "20260907_0032"
PHASE21D_HEAD = "20260910_0033"
RESEARCH_TABLES = {
    "thesis_revisions",
    "thesis_assumptions",
    "thesis_assumption_heads",
    "thesis_catalysts",
    "research_report_comparisons",
}
EXPECTED_FREE_LIMITS = {
    "limit.analysis.count": 25,
    "limit.simulation.count": 100,
    "limit.options.count": 100,
    "limit.market_data.count": 100,
    "limit.saved_thesis.count": 50,
    "limit.watchlist.count": 25,
    "limit.schedule.active_count": 5,
}


def test_phase21d_sqlite_migration_cycle_is_reversible_and_preserves_prior_authority(tmp_path: Path) -> None:
    _assert_lineage()
    database_url = f"sqlite:///{tmp_path / 'phase21d.sqlite'}"
    _alembic(database_url, "upgrade", PHASE21C_HEAD)
    engine = create_engine(database_url)
    _assert_phase21c(engine)

    _alembic(database_url, "upgrade", PHASE21D_HEAD)
    _assert_phase21d(engine)
    _alembic(database_url, "downgrade", PHASE21C_HEAD)
    _assert_phase21c(engine)
    with engine.connect() as connection:
        assert not RESEARCH_TABLES & _tables(connection)

    _alembic(database_url, "upgrade", PHASE21D_HEAD)
    _assert_phase21d(engine)


def _assert_phase21c(engine) -> None:
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PHASE21C_HEAD
        tables = _tables(connection)
        assert {"model_run_provenance", "model_evaluation_runs", "model_run_quality_evidence", "model_feedback", "saved_theses", "reports"}.issubset(tables)
        _assert_free_v1(connection)


def _assert_phase21d(engine) -> None:
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PHASE21D_HEAD
        assert RESEARCH_TABLES.issubset(_tables(connection))
        assert {"revision_number", "assumptions_snapshot", "status", "origin"}.issubset(_columns(connection, "thesis_revisions"))
        assert {"state", "evidence_references", "supersedes_record_id"}.issubset(_columns(connection, "thesis_assumptions"))
        _assert_free_v1(connection)


def _assert_free_v1(connection) -> None:
    rows = connection.execute(
        text("SELECT entitlement_key, hard_limit FROM plan_entitlements WHERE plan_version_id = 'plan_free_v1'")
    )
    assert {row.entitlement_key: row.hard_limit for row in rows} == EXPECTED_FREE_LIMITS


def _tables(connection) -> set[str]:
    return set(connection.scalars(text("SELECT name FROM sqlite_master WHERE type = 'table'")))


def _columns(connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(text(f"PRAGMA table_info({table})"))}


def _assert_lineage() -> None:
    versions = BACKEND_DIR / "migrations" / "versions"
    assert not list(versions.glob("*0027*"))
    assert not list(versions.glob("*0034*"))
    migration = versions / "20260910_0033_add_research_intelligence.py"
    assert migration.is_file()
    contents = migration.read_text()
    assert 'revision = "20260910_0033"' in contents
    assert 'down_revision = "20260907_0032"' in contents
    assert len(list(versions.glob("*0033*"))) == 1


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
