from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, text


BACKEND_DIR = Path(__file__).resolve().parents[2]
PHASE20J_HEAD = "20260828_0029"
PHASE21A_HEAD = "20260904_0030"
EXPECTED_FREE_LIMITS = {
    "limit.analysis.count": 25,
    "limit.simulation.count": 100,
    "limit.options.count": 100,
    "limit.market_data.count": 100,
    "limit.saved_thesis.count": 50,
    "limit.watchlist.count": 25,
    "limit.schedule.active_count": 5,
}
PHASE21A_TABLES = {"model_registry", "model_task_capabilities", "model_prompt_versions", "model_run_provenance"}


def test_phase21a_sqlite_migration_cycle_is_reversible_and_preserves_phase20(tmp_path: Path) -> None:
    _assert_lineage()
    database_url = f"sqlite:///{tmp_path / 'phase21a.sqlite'}"
    _alembic(database_url, "upgrade", PHASE20J_HEAD)
    engine = create_engine(database_url)
    _assert_phase20(engine)

    _alembic(database_url, "upgrade", PHASE21A_HEAD)
    _assert_phase21a(engine)

    _alembic(database_url, "downgrade", PHASE20J_HEAD)
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PHASE20J_HEAD
        assert not PHASE21A_TABLES & _tables(connection)
        _assert_free_v1(connection)
        assert {"organization_invitations", "customer_requests"}.issubset(_tables(connection))

    _alembic(database_url, "upgrade", PHASE21A_HEAD)
    _assert_phase21a(engine)


def _assert_phase20(engine) -> None:
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PHASE20J_HEAD
        _assert_free_v1(connection)
        assert {"organization_invitations", "customer_requests"}.issubset(_tables(connection))


def _assert_phase21a(engine) -> None:
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PHASE21A_HEAD
        assert PHASE21A_TABLES.issubset(_tables(connection))
        assert connection.scalar(
            text("SELECT prompt_checksum FROM model_prompt_versions WHERE id = 'prompt_report_synthesis_v1'")
        ) == "9ac1e2188d270720550406823cdaed68c929b0cdc4bb248b18b3f95191ab3516"
        assert connection.scalar(text("SELECT COUNT(*) FROM model_prompt_versions")) == 1
        _assert_free_v1(connection)


def _assert_free_v1(connection) -> None:
    rows = connection.execute(
        text("SELECT entitlement_key, hard_limit FROM plan_entitlements WHERE plan_version_id = 'plan_free_v1'")
    )
    assert {row.entitlement_key: row.hard_limit for row in rows} == EXPECTED_FREE_LIMITS


def _tables(connection) -> set[str]:
    return set(connection.scalars(text("SELECT name FROM sqlite_master WHERE type = 'table'")))


def _assert_lineage() -> None:
    versions = BACKEND_DIR / "migrations" / "versions"
    assert not list(versions.glob("*0027*"))
    migration = next(versions.glob("*20260904_0030*.py"))
    contents = migration.read_text()
    assert 'revision = "20260904_0030"' in contents
    assert 'down_revision = "20260828_0029"' in contents


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
