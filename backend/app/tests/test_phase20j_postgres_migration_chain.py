from __future__ import annotations

import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.orm import sessionmaker

from app.auth.service import create_user
from app.db.session import normalize_database_url
from app.models.customer_request import CustomerRequestModel
from app.models.organization import (
    OrganizationInvitationModel,
    OrganizationMembershipModel,
    OrganizationModel,
)


BACKEND_DIR = Path(__file__).resolve().parents[2]
PHASE20A_HEAD = "20260728_0022"
PHASE20J_HEAD = "20260828_0029"
PHASE20_TABLES = {
    "privacy_preference_decisions",
    "privacy_preferences",
    "product_analytics_events",
    "monitoring_schedules",
    "monitoring_schedule_occurrences",
    "notification_preferences",
    "notifications",
    "plan_versions",
    "plan_entitlements",
    "entitlement_assignments",
    "non_billable_usage_events",
    "organization_invitations",
    "customer_requests",
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


@pytest.mark.postgres_integration
def test_phase20j_postgres_migration_chain_preserves_prior_authorities_and_reseeds_catalogs() -> None:
    if os.getenv("RUN_POSTGRES_INTEGRATION") != "true":
        pytest.skip("Phase 20J PostgreSQL migration chain requires RUN_POSTGRES_INTEGRATION=true")
    source_url = normalize_database_url(os.environ["DATABASE_URL"])
    url = make_url(source_url)
    if url.get_backend_name() != "postgresql":
        pytest.skip("Phase 20J PostgreSQL migration chain requires PostgreSQL DATABASE_URL")

    database_name = f"phase20j_migration_{uuid4().hex[:16]}"
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    temporary_url = url.set(database=database_name).render_as_string(hide_password=False)
    try:
        _assert_lineage()
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{database_name}"'))
        temp = create_engine(temporary_url, isolation_level="AUTOCOMMIT")
        with temp.connect() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        temp.dispose()

        _alembic(temporary_url, "upgrade", PHASE20A_HEAD)
        owner_id, organization_id = _seed_phase16_authorities(temporary_url)
        _assert_phase20a_boundary(temporary_url)

        _alembic(temporary_url, "upgrade", PHASE20J_HEAD)
        _seed_final_phase20_records(temporary_url, owner_id, organization_id)
        _assert_final_head(temporary_url, expected_records=True)

        _alembic(temporary_url, "downgrade", PHASE20A_HEAD)
        _assert_downgrade(temporary_url)

        _alembic(temporary_url, "upgrade", PHASE20J_HEAD)
        _assert_final_head(temporary_url, expected_records=False)
    finally:
        with admin.connect() as connection:
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :name AND pid <> pg_backend_pid()"
                ),
                {"name": database_name},
            )
            connection.execute(text(f'DROP DATABASE IF EXISTS "{database_name}"'))
        admin.dispose()


def _seed_phase16_authorities(database_url: str) -> tuple[str, str]:
    sessions = sessionmaker(bind=create_engine(database_url))
    suffix = uuid4().hex[:12]
    with sessions() as db:
        owner = create_user(db, f"phase20j-migration-{suffix}@example.test")
        organization = OrganizationModel(
            id=f"org_phase20j_migration_{suffix}",
            name="Phase 20J migration",
            slug=f"phase20j-migration-{suffix}",
            status="active",
            created_by_user_id=owner.id,
        )
        db.add(organization)
        db.flush()
        db.add(
            OrganizationMembershipModel(
                id=f"mbr_phase20j_migration_{suffix}",
                organization_id=organization.id,
                user_id=owner.id,
                role="owner",
                status="active",
            )
        )
        db.commit()
        return owner.id, organization.id


def _seed_final_phase20_records(database_url: str, owner_id: str, organization_id: str) -> None:
    sessions = sessionmaker(bind=create_engine(database_url))
    suffix = uuid4().hex[:12]
    with sessions() as db:
        db.add_all(
            [
                OrganizationInvitationModel(
                    id=f"inv_phase20j_migration_{suffix}",
                    organization_id=organization_id,
                    destination_email=f"phase20j-invite-{suffix}@example.test",
                    role="member",
                    invited_by_user_id=owner_id,
                    token_hash="c" * 64,
                    status="pending",
                    expires_at=datetime(2026, 9, 30, tzinfo=UTC),
                ),
                CustomerRequestModel(
                    id=f"creq_phase20j_migration_{suffix}",
                    owner_user_id=owner_id,
                    organization_id=organization_id,
                    request_type="support",
                    subject="PostgreSQL migration chain request",
                    description="Bounded private request content.",
                    workflow_state="open",
                    verification_state="not_required",
                ),
            ]
        )
        db.commit()


def _assert_phase20a_boundary(database_url: str) -> None:
    with create_engine(database_url).connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PHASE20A_HEAD
        tables = _tables(connection)
        assert {"users", "organizations", "organization_memberships", "rate_limit_buckets"}.issubset(tables)
        assert not PHASE20_TABLES & tables
        assert connection.scalar(text("SELECT COUNT(*) FROM users")) == 1
        assert connection.scalar(text("SELECT COUNT(*) FROM organizations")) == 1
        assert connection.scalar(text("SELECT COUNT(*) FROM organization_memberships")) == 1


def _assert_final_head(database_url: str, *, expected_records: bool) -> None:
    with create_engine(database_url).connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PHASE20J_HEAD
        tables = _tables(connection)
        assert PHASE20_TABLES.issubset(tables)
        assert {"users", "organizations", "organization_memberships", "rate_limit_buckets"}.issubset(tables)
        assert connection.scalar(text("SELECT COUNT(*) FROM users")) == 1
        assert connection.scalar(text("SELECT COUNT(*) FROM organizations")) == 1
        assert connection.scalar(text("SELECT COUNT(*) FROM organization_memberships")) == 1
        _assert_free_v1(connection)
        assert connection.scalar(
            text("SELECT hard_limit FROM plan_entitlements WHERE plan_version_id = 'plan_portfolio_org_v1' AND entitlement_key = 'limit.organization.seats.count'")
        ) == 5
        for constraint in (
            "uq_product_analytics_events_event_key",
            "uq_monitoring_schedule_occurrence_time",
            "uq_notifications_owner_idempotency",
            "ex_entitlement_assignments_no_overlap",
            "uq_organization_invitations_token_hash",
            "ck_customer_requests_request_type",
        ):
            assert _has_constraint(connection, constraint)

        expected_count = 1 if expected_records else 0
        assert connection.scalar(text("SELECT COUNT(*) FROM organization_invitations")) == expected_count
        assert connection.scalar(text("SELECT COUNT(*) FROM customer_requests")) == expected_count


def _assert_downgrade(database_url: str) -> None:
    with create_engine(database_url).connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PHASE20A_HEAD
        tables = _tables(connection)
        assert not PHASE20_TABLES & tables
        assert {"users", "organizations", "organization_memberships", "rate_limit_buckets"}.issubset(tables)
        assert connection.scalar(text("SELECT COUNT(*) FROM users")) == 1
        assert connection.scalar(text("SELECT COUNT(*) FROM organizations")) == 1
        assert connection.scalar(text("SELECT COUNT(*) FROM organization_memberships")) == 1


def _assert_free_v1(connection: Connection) -> None:
    rows = connection.execute(
        text("SELECT entitlement_key, hard_limit FROM plan_entitlements WHERE plan_version_id = 'plan_free_v1'")
    )
    assert {row.entitlement_key: row.hard_limit for row in rows} == EXPECTED_FREE_LIMITS


def _has_constraint(connection: Connection, name: str) -> bool:
    return connection.scalar(
        text("SELECT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = :name)"), {"name": name}
    ) is True


def _tables(connection: Connection) -> set[str]:
    return set(connection.scalars(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")))


def _assert_lineage() -> None:
    versions = BACKEND_DIR / "migrations" / "versions"
    assert not list(versions.glob("*0027*"))
    expected_edges = {
        "20260731_0023": "20260728_0022",
        "20260813_0024": "20260731_0023",
        "20260814_0025": "20260813_0024",
        "20260821_0026": "20260814_0025",
        "20260824_0028": "20260821_0026",
        "20260828_0029": "20260824_0028",
    }
    for revision, down_revision in expected_edges.items():
        migration = next(versions.glob(f"*{revision}*.py"))
        contents = migration.read_text()
        assert f'revision = "{revision}"' in contents
        assert f'down_revision = "{down_revision}"' in contents


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
