from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.llm.governance import ensure_report_synthesis_prompt_version


BACKEND_DIR = Path(__file__).resolve().parents[2]
PHASE21A_HEAD = "20260904_0030"
PHASE21B_HEAD = "20260906_0031"
EXPECTED_FREE_LIMITS = {
    "limit.analysis.count": 25,
    "limit.simulation.count": 100,
    "limit.options.count": 100,
    "limit.market_data.count": 100,
    "limit.saved_thesis.count": 50,
    "limit.watchlist.count": 25,
    "limit.schedule.active_count": 5,
}
PHASE21B_TABLES = {
    "model_evaluation_datasets",
    "model_evaluation_runs",
    "model_evaluation_case_results",
    "model_route_versions",
    "model_route_assignments",
    "model_route_transitions",
}


def test_phase21b_sqlite_migration_cycle_is_reversible_and_preserves_phase20_and_21a(tmp_path: Path) -> None:
    _assert_lineage()
    database_url = f"sqlite:///{tmp_path / 'phase21b.sqlite'}"
    _alembic(database_url, "upgrade", PHASE21A_HEAD)
    engine = create_engine(database_url)
    _assert_phase21a(engine)

    _alembic(database_url, "upgrade", PHASE21B_HEAD)
    _assert_phase21b(engine)
    _materialize_runtime_prompt_v2(engine)

    _alembic(database_url, "downgrade", PHASE21A_HEAD)
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PHASE21A_HEAD
        assert not PHASE21B_TABLES & _tables(connection)
        columns = _columns(connection, "model_run_provenance")
        assert {"route_version_id", "evaluation_run_id"}.isdisjoint(columns)
        _assert_phase20(connection)
        assert connection.scalar(text("SELECT COUNT(*) FROM model_registry")) == 0
        assert connection.scalar(text("SELECT prompt_checksum FROM model_prompt_versions WHERE id = 'prompt_report_synthesis_v1'"))

    _alembic(database_url, "upgrade", PHASE21B_HEAD)
    _assert_phase21b(engine)
    _materialize_runtime_prompt_v2(engine)


def _assert_phase21a(engine) -> None:
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PHASE21A_HEAD
        assert {"model_registry", "model_task_capabilities", "model_prompt_versions", "model_run_provenance"}.issubset(_tables(connection))
        assert connection.scalar(text("SELECT prompt_checksum FROM model_prompt_versions WHERE id = 'prompt_report_synthesis_v1'"))
        _assert_phase20(connection)


def _assert_phase21b(engine) -> None:
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PHASE21B_HEAD
        assert PHASE21B_TABLES.issubset(_tables(connection))
        assert {"route_version_id", "evaluation_run_id"}.issubset(_columns(connection, "model_run_provenance"))
        _assert_phase20(connection)


def _materialize_runtime_prompt_v2(engine) -> None:
    Session = sessionmaker(bind=engine)
    with Session() as db:
        prompt = ensure_report_synthesis_prompt_version(db)
        db.commit()
        assert prompt.id == "prompt_report_synthesis_v3"


def _assert_phase20(connection) -> None:
    rows = connection.execute(text("SELECT entitlement_key, hard_limit FROM plan_entitlements WHERE plan_version_id = 'plan_free_v1'"))
    assert {row.entitlement_key: row.hard_limit for row in rows} == EXPECTED_FREE_LIMITS
    assert {"organization_invitations", "customer_requests"}.issubset(_tables(connection))


def _tables(connection) -> set[str]:
    return set(connection.scalars(text("SELECT name FROM sqlite_master WHERE type = 'table'")))


def _columns(connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(text(f"PRAGMA table_info({table})"))}


def _assert_lineage() -> None:
    versions = BACKEND_DIR / "migrations" / "versions"
    assert not list(versions.glob("*0027*"))
    migrations = list(versions.glob("*20260906_0031*.py"))
    assert len(migrations) == 1
    contents = migrations[0].read_text()
    assert 'revision = "20260906_0031"' in contents
    assert 'down_revision = "20260904_0030"' in contents


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
