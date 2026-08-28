from __future__ import annotations

import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.auth.service import create_user
from app.models.customer_request import CustomerRequestModel
from app.models.organization import OrganizationInvitationModel, OrganizationMembershipModel, OrganizationModel
from app.db.session import normalize_database_url


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


@pytest.mark.postgres_integration
def test_phase20i_postgres_migration_cycle_preserves_phase20h_schema_and_catalog() -> None:
    if os.getenv("RUN_POSTGRES_INTEGRATION") != "true":
        pytest.skip("Phase 20I PostgreSQL migration cycle requires RUN_POSTGRES_INTEGRATION=true")
    source_url = normalize_database_url(os.environ["DATABASE_URL"])
    url = make_url(source_url)
    if url.get_backend_name() != "postgresql":
        pytest.skip("Phase 20I PostgreSQL migration cycle requires PostgreSQL DATABASE_URL")
    database_name = f"phase20i_migration_{uuid4().hex[:16]}"
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    temporary_url = url.set(database=database_name).render_as_string(hide_password=False)
    try:
        _assert_lineage()
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{database_name}"'))
        temp = create_engine(temporary_url, isolation_level="AUTOCOMMIT")
        with temp.connect() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        _alembic(temporary_url, "upgrade", PHASE20H_HEAD)
        owner_id, organization_id = _seed_phase20h_records(temporary_url)
        _alembic(temporary_url, "upgrade", PHASE20I_HEAD)
        with sessionmaker(bind=create_engine(temporary_url))() as db:
            db.add(
                CustomerRequestModel(
                    id="creq_phase20i_migration",
                    owner_user_id=owner_id,
                    organization_id=organization_id,
                    request_type="support",
                    subject="PostgreSQL migration request",
                    description="Bounded private request content.",
                    workflow_state="open",
                    verification_state="not_required",
                )
            )
            db.commit()
        _assert_upgraded(temporary_url)

        _alembic(temporary_url, "downgrade", PHASE20H_HEAD)
        with create_engine(temporary_url).connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PHASE20H_HEAD
            assert "customer_requests" not in _tables(connection)
            assert connection.scalar(text("SELECT COUNT(*) FROM organization_invitations")) == 1
            assert connection.scalar(text("SELECT COUNT(*) FROM plan_versions WHERE id = 'plan_portfolio_org_v1'")) == 1
            _assert_free_v1(connection)

        _alembic(temporary_url, "upgrade", PHASE20I_HEAD)
        _assert_upgraded(temporary_url)
        with create_engine(temporary_url).connect() as connection:
            assert connection.scalar(text("SELECT COUNT(*) FROM customer_requests")) == 0
            assert connection.scalar(text("SELECT COUNT(*) FROM organization_invitations")) == 1
    finally:
        with admin.connect() as connection:
            connection.execute(
                text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :name AND pid <> pg_backend_pid()"),
                {"name": database_name},
            )
            connection.execute(text(f'DROP DATABASE IF EXISTS "{database_name}"'))
        admin.dispose()


def _seed_phase20h_records(database_url: str) -> tuple[str, str]:
    sessions = sessionmaker(bind=create_engine(database_url))
    with sessions() as db:
        owner = create_user(db, f"phase20i-migration-{uuid4().hex[:12]}@example.test")
        organization = OrganizationModel(
            id=f"org_phase20i_migration_{uuid4().hex[:12]}",
            name="Phase 20I migration",
            slug=f"phase20i-migration-{uuid4().hex[:12]}",
            status="active",
            created_by_user_id=owner.id,
        )
        db.add(organization)
        db.flush()
        db.add_all([
            OrganizationMembershipModel(
                id=f"mbr_phase20i_migration_{uuid4().hex[:12]}",
                organization_id=organization.id,
                user_id=owner.id,
                role="owner",
                status="active",
            ),
            OrganizationInvitationModel(
                id=f"inv_phase20i_migration_{uuid4().hex[:12]}",
                organization_id=organization.id,
                destination_email="phase20i-invite@example.test",
                role="member",
                invited_by_user_id=owner.id,
                token_hash="b" * 64,
                status="pending",
                expires_at=datetime(2026, 9, 1, tzinfo=UTC),
            ),
        ])
        db.commit()
        return owner.id, organization.id


def _assert_upgraded(database_url: str) -> None:
    with create_engine(database_url).connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PHASE20I_HEAD
        assert "customer_requests" in _tables(connection)
        assert connection.scalar(text("SELECT COUNT(*) FROM organization_invitations")) == 1
        assert connection.scalar(text("SELECT COUNT(*) FROM plan_versions WHERE id = 'plan_portfolio_org_v1'")) == 1
        _assert_free_v1(connection)
        assert connection.scalar(
            text("SELECT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_customer_requests_request_type')")
        ) is True


def _assert_free_v1(connection) -> None:
    rows = connection.execute(
        text("SELECT entitlement_key, hard_limit FROM plan_entitlements WHERE plan_version_id = 'plan_free_v1'")
    )
    assert {row.entitlement_key: row.hard_limit for row in rows} == EXPECTED_FREE_LIMITS


def _tables(connection) -> set[str]:
    return set(connection.scalars(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")))


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
