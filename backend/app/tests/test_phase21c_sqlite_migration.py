from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.llm.governance import ensure_report_synthesis_prompt_version


BACKEND_DIR = Path(__file__).resolve().parents[2]
PHASE21B_HEAD = "20260906_0031"
PHASE21C_HEAD = "20260907_0032"
EXPECTED_FREE_LIMITS = {
    "limit.analysis.count": 25,
    "limit.simulation.count": 100,
    "limit.options.count": 100,
    "limit.market_data.count": 100,
    "limit.saved_thesis.count": 50,
    "limit.watchlist.count": 25,
    "limit.schedule.active_count": 5,
}
PHASE21C_TABLES = {"model_run_quality_evidence", "model_feedback"}


def test_phase21c_sqlite_migration_cycle_is_reversible_and_preserves_prior_authority(tmp_path: Path) -> None:
    _assert_lineage()
    database_url = f"sqlite:///{tmp_path / 'phase21c.sqlite'}"
    _alembic(database_url, "upgrade", PHASE21B_HEAD)
    engine = create_engine(database_url)
    _assert_phase21b(engine)

    _alembic(database_url, "upgrade", PHASE21C_HEAD)
    _assert_phase21c(engine)
    _materialize_current_prompt(engine)

    _alembic(database_url, "downgrade", PHASE21B_HEAD)
    _assert_phase21b(engine)
    with engine.connect() as connection:
        assert not PHASE21C_TABLES & _tables(connection)
        assert {"adversarial_dataset_id", "citation_consistency_count"}.isdisjoint(
            _columns(connection, "model_evaluation_runs")
        )
        assert {"citation_consistency", "poisoning_detected"}.isdisjoint(
            _columns(connection, "model_evaluation_case_results")
        )

    _alembic(database_url, "upgrade", PHASE21C_HEAD)
    _assert_phase21c(engine)
    _materialize_current_prompt(engine)


def _assert_phase21b(engine) -> None:
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PHASE21B_HEAD
        tables = _tables(connection)
        assert {"model_registry", "model_evaluation_runs", "model_route_versions", "model_run_provenance"}.issubset(tables)
        assert not PHASE21C_TABLES & tables
        _assert_phase20(connection)


def _assert_phase21c(engine) -> None:
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PHASE21C_HEAD
        assert PHASE21C_TABLES.issubset(_tables(connection))
        assert {
            "adversarial_dataset_id",
            "citation_consistency_count",
            "unsupported_claim_count",
            "uncertainty_preserved_count",
            "source_instruction_flag_count",
            "poisoning_detected_count",
            "deterministic_integrity_count",
        }.issubset(_columns(connection, "model_evaluation_runs"))
        assert {
            "citation_consistency",
            "unsupported_claim_count",
            "uncertainty_preserved",
            "source_instruction_flag_count",
            "poisoning_detected",
            "deterministic_integrity",
        }.issubset(_columns(connection, "model_evaluation_case_results"))
        _assert_phase20(connection)


def _materialize_current_prompt(engine) -> None:
    with sessionmaker(bind=engine)() as db:
        assert ensure_report_synthesis_prompt_version(db).id == "prompt_report_synthesis_v3"
        db.commit()


def _assert_phase20(connection) -> None:
    rows = connection.execute(
        text("SELECT entitlement_key, hard_limit FROM plan_entitlements WHERE plan_version_id = 'plan_free_v1'")
    )
    assert {row.entitlement_key: row.hard_limit for row in rows} == EXPECTED_FREE_LIMITS
    assert {"organization_invitations", "customer_requests"}.issubset(_tables(connection))


def _tables(connection) -> set[str]:
    return set(connection.scalars(text("SELECT name FROM sqlite_master WHERE type = 'table'")))


def _columns(connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(text(f"PRAGMA table_info({table})"))}


def _assert_lineage() -> None:
    versions = BACKEND_DIR / "migrations" / "versions"
    assert not list(versions.glob("*0027*"))
    migration = versions / "20260907_0032_add_model_quality_feedback.py"
    assert migration.is_file()
    contents = migration.read_text()
    assert 'revision = "20260907_0032"' in contents
    assert 'down_revision = "20260906_0031"' in contents
    assert len(list(versions.glob("*0032*"))) == 1


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
