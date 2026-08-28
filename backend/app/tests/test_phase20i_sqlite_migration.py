from __future__ import annotations

import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.auth.service import create_user
from app.models.customer_request import CustomerRequestModel
from app.models.organization import OrganizationInvitationModel, OrganizationMembershipModel, OrganizationModel


BACKEND_DIR = Path(__file__).resolve().parents[2]
PHASE20H_HEAD = "20260824_0028"
PHASE20I_HEAD = "20260828_0029"
EXPECTED_FREE_LIMITS = {
    "limit.analysis.count": 25,
    "limit.simulation.count": 100,
    "limit.options.count": 100,
    "limit.market_data.count": 100,
    "limit.saved_thesis.count": 50,
    "limit.watchlist.count": 25,
    "limit.schedule.active_count": 5,
}


def test_phase20i_sqlite_migration_cycle_preserves_phase20h_and_removes_only_requests(tmp_path: Path) -> None:
    _assert_lineage()
    database_url = f"sqlite:///{tmp_path / 'phase20i.sqlite'}"
    _alembic(database_url, "upgrade", PHASE20H_HEAD)
    engine = create_engine(database_url)
    sessions = sessionmaker(bind=engine)
    with sessions() as db:
        owner = create_user(db, "phase20i-sqlite@example.test")
        organization = OrganizationModel(
            id="org_phase20i_sqlite",
            name="Phase 20I SQLite",
            slug="phase20i-sqlite",
            status="active",
            created_by_user_id=owner.id,
        )
        db.add(organization)
        db.flush()
        db.add_all([
            OrganizationMembershipModel(
                id="mbr_phase20i_sqlite",
                organization_id=organization.id,
                user_id=owner.id,
                role="owner",
                status="active",
            ),
            OrganizationInvitationModel(
                id="inv_phase20i_sqlite",
                organization_id=organization.id,
                destination_email="phase20i-invite@example.test",
                role="member",
                invited_by_user_id=owner.id,
                token_hash="a" * 64,
                status="pending",
                expires_at=datetime(2026, 9, 1, tzinfo=UTC),
            ),
        ])
        db.commit()
        owner_id = owner.id

    _alembic(database_url, "upgrade", PHASE20I_HEAD)
    with sessions() as db:
        db.add(
            CustomerRequestModel(
                id="creq_phase20i_sqlite",
                owner_user_id=owner_id,
                organization_id="org_phase20i_sqlite",
                request_type="support",
                subject="SQLite migration request",
                description="This is bounded private request content.",
                workflow_state="open",
                verification_state="not_required",
            )
        )
        db.commit()
    _assert_upgraded(engine)

    _alembic(database_url, "downgrade", PHASE20H_HEAD)
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PHASE20H_HEAD
        assert "customer_requests" not in _tables(connection)
        assert connection.scalar(text("SELECT COUNT(*) FROM organization_invitations")) == 1
        assert connection.scalar(text("SELECT COUNT(*) FROM plan_versions WHERE id = 'plan_portfolio_org_v1'")) == 1
        _assert_free_v1(connection)

    _alembic(database_url, "upgrade", PHASE20I_HEAD)
    _assert_upgraded(engine)
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT COUNT(*) FROM customer_requests")) == 0
        assert connection.scalar(text("SELECT COUNT(*) FROM organization_invitations")) == 1


def _assert_upgraded(engine) -> None:
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PHASE20I_HEAD
        assert "customer_requests" in _tables(connection)
        assert connection.scalar(text("SELECT COUNT(*) FROM organization_invitations")) == 1
        assert connection.scalar(text("SELECT COUNT(*) FROM plan_versions WHERE id = 'plan_portfolio_org_v1'")) == 1
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
    migration = next(versions.glob("*20260828_0029*.py"))
    contents = migration.read_text()
    assert 'revision = "20260828_0029"' in contents
    assert 'down_revision = "20260824_0028"' in contents


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
