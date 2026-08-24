from __future__ import annotations

import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.auth.service import create_user
from app.models.entitlement import EntitlementAssignmentModel

BACKEND_DIR = Path(__file__).resolve().parents[2]
PHASE20F_HEAD = "20260821_0026"
PHASE20H_HEAD = "20260824_0028"


def test_phase20h_sqlite_migration_cycle_updates_assignment_subject_semantics(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'phase20h.sqlite'}"
    _alembic(database_url, "upgrade", PHASE20F_HEAD)
    engine = create_engine(database_url)
    sessions = sessionmaker(bind=engine)
    with sessions() as db:
        user = create_user(db, "phase20h-migration@example.test")
        user_assignment_id = "assignment_phase20h_user"
        db.add(
            EntitlementAssignmentModel(
                id=user_assignment_id,
                subject_type="user",
                subject_id=user.id,
                plan_version_id="plan_free_v1",
                effective_from=datetime(2026, 8, 21, tzinfo=UTC),
                source="test",
            )
        )
        db.commit()

    _alembic(database_url, "upgrade", PHASE20H_HEAD)
    with sessions() as db:
        db.add(
            EntitlementAssignmentModel(
                id="assignment_phase20h_org",
                subject_type="organization",
                subject_id="org_without_user_fk",
                plan_version_id="plan_portfolio_org_v1",
                effective_from=datetime(2026, 8, 24, tzinfo=UTC),
                source="test",
            )
        )
        db.commit()
        assert db.get(EntitlementAssignmentModel, user_assignment_id) is not None
        assert db.get(EntitlementAssignmentModel, "assignment_phase20h_org") is not None

    _alembic(database_url, "downgrade", PHASE20F_HEAD)
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PHASE20F_HEAD
        assert connection.scalar(text("SELECT COUNT(*) FROM entitlement_assignments WHERE subject_type = 'organization'")) == 0
        assert connection.scalar(text("SELECT COUNT(*) FROM entitlement_assignments WHERE id = :id"), {"id": user_assignment_id}) == 1
        assignment_sql = connection.scalar(text("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'entitlement_assignments'"))
        assert "subject_type = 'user'" in assignment_sql
        foreign_keys = connection.execute(text("PRAGMA foreign_key_list('entitlement_assignments')")).mappings().all()
        assert any(item["from"] == "subject_id" and item["table"] == "users" for item in foreign_keys)

    _alembic(database_url, "upgrade", PHASE20H_HEAD)
    with sessions() as db:
        db.add(
            EntitlementAssignmentModel(
                id="assignment_phase20h_org_reupgrade",
                subject_type="organization",
                subject_id="org_without_user_fk_reupgrade",
                plan_version_id="plan_portfolio_org_v1",
                effective_from=datetime(2026, 8, 24, tzinfo=UTC),
                source="test",
            )
        )
        db.commit()


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
