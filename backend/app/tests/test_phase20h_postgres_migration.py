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
from app.db.session import normalize_database_url
from app.models.entitlement import EntitlementAssignmentModel
from app.models.organization import OrganizationMembershipModel, OrganizationModel

BACKEND_DIR = Path(__file__).resolve().parents[2]
PHASE20F_HEAD = "20260821_0026"
PHASE20H_HEAD = "20260824_0028"
PHASE20F_TABLES = {
    "plan_versions",
    "plan_entitlements",
    "entitlement_assignments",
    "non_billable_usage_events",
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
def test_phase20h_postgres_migration_cycle_preserves_phase20f_catalog_and_user_assignments() -> None:
    if os.getenv("RUN_POSTGRES_INTEGRATION") != "true":
        pytest.skip("Phase 20H PostgreSQL migration cycle requires RUN_POSTGRES_INTEGRATION=true")
    source_url = normalize_database_url(os.environ["DATABASE_URL"])
    url = make_url(source_url)
    if url.get_backend_name() != "postgresql":
        pytest.skip("Phase 20H PostgreSQL migration cycle requires PostgreSQL DATABASE_URL")
    database_name = f"phase20h_migration_{uuid4().hex[:16]}"
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    temporary_url = url.set(database=database_name).render_as_string(hide_password=False)
    try:
        _assert_migration_lineage()
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{database_name}"'))
        temp = create_engine(temporary_url, isolation_level="AUTOCOMMIT")
        with temp.connect() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        _alembic(temporary_url, "upgrade", PHASE20F_HEAD)
        _alembic(temporary_url, "upgrade", PHASE20H_HEAD)
        user_id, organization_id = _seed_assignments(temporary_url)
        _assert_first_upgrade(temporary_url, user_id, organization_id)

        _alembic(temporary_url, "downgrade", PHASE20F_HEAD)
        _assert_downgrade(temporary_url, user_id, organization_id)

        _alembic(temporary_url, "upgrade", PHASE20H_HEAD)
        _assert_reupgrade(temporary_url, organization_id)
    finally:
        with admin.connect() as connection:
            connection.execute(
                text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :name AND pid <> pg_backend_pid()"),
                {"name": database_name},
            )
            connection.execute(text(f'DROP DATABASE IF EXISTS "{database_name}"'))
        admin.dispose()


def _seed_assignments(database_url: str) -> tuple[str, str]:
    sessions = sessionmaker(bind=create_engine(database_url))
    suffix = uuid4().hex[:12]
    with sessions() as db:
        user = create_user(db, f"phase20h-migration-{suffix}@example.test")
        organization_id = f"org_migration_{suffix}"
        db.add(
            OrganizationModel(
                id=organization_id,
                name="Phase 20H migration",
                slug=f"phase20h-migration-{suffix}",
                status="active",
                created_by_user_id=user.id,
            )
        )
        db.flush()
        db.add_all([
            OrganizationMembershipModel(
                id=f"mbr_migration_{suffix}",
                organization_id=organization_id,
                user_id=user.id,
                role="owner",
                status="active",
            ),
            EntitlementAssignmentModel(
                id=f"assignment_user_{suffix}",
                subject_type="user",
                subject_id=user.id,
                plan_version_id="plan_free_v1",
                effective_from=datetime(2025, 8, 24, tzinfo=UTC),
                source="test",
            ),
            EntitlementAssignmentModel(
                id=f"assignment_org_{suffix}",
                subject_type="organization",
                subject_id=organization_id,
                plan_version_id="plan_portfolio_org_v1",
                effective_from=datetime(2025, 8, 24, tzinfo=UTC),
                source="test",
            ),
        ])
        db.commit()
        return user.id, organization_id


def _assert_first_upgrade(database_url: str, user_id: str, organization_id: str) -> None:
    with create_engine(database_url).connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PHASE20H_HEAD
        assert "organization_invitations" in _tables(connection)
        assert connection.scalar(
            text("SELECT COUNT(*) FROM entitlement_assignments WHERE subject_type = 'organization' AND subject_id = :id"),
            {"id": organization_id},
        ) == 1
        assert connection.scalar(text("SELECT COUNT(*) FROM plan_versions WHERE id = 'plan_portfolio_org_v1'")) == 1
        assert connection.scalar(
            text("SELECT COUNT(*) FROM plan_entitlements WHERE plan_version_id = 'plan_portfolio_org_v1'")
        ) == 1
        assert connection.scalar(
            text("SELECT hard_limit FROM plan_entitlements WHERE plan_version_id = 'plan_portfolio_org_v1' AND entitlement_key = 'limit.organization.seats.count'")
        ) == 5
        assert connection.scalar(
            text("SELECT COUNT(*) FROM entitlement_assignments WHERE subject_type = 'user' AND subject_id = :id"),
            {"id": user_id},
        ) == 1
        _assert_free_v1(connection)
        assert connection.scalar(text("SELECT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ex_entitlement_assignments_no_overlap')")) is True


def _assert_downgrade(database_url: str, user_id: str, organization_id: str) -> None:
    with create_engine(database_url).connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PHASE20F_HEAD
        tables = _tables(connection)
        assert "organization_invitations" not in tables
        assert PHASE20F_TABLES.issubset(tables)
        assert connection.scalar(
            text("SELECT COUNT(*) FROM entitlement_assignments WHERE subject_type = 'organization' AND subject_id = :id"),
            {"id": organization_id},
        ) == 0
        assert connection.scalar(
            text("SELECT COUNT(*) FROM entitlement_assignments WHERE subject_type = 'user' AND subject_id = :id"),
            {"id": user_id},
        ) == 1
        assert connection.scalar(text("SELECT COUNT(*) FROM plan_versions WHERE id = 'plan_portfolio_org_v1'")) == 0
        constraint_definition = connection.scalar(
            text("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'ck_entitlement_assignments_user_only'")
        )
        assert "subject_type" in constraint_definition and "user" in constraint_definition
        assert connection.scalar(
            text("SELECT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'entitlement_assignments_subject_id_fkey' AND contype = 'f' AND pg_get_constraintdef(oid) LIKE '%REFERENCES users%')")
        ) is True
        _assert_free_v1(connection)
        assert connection.scalar(text("SELECT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ex_entitlement_assignments_no_overlap')")) is True
        assert not list((BACKEND_DIR / "migrations" / "versions").glob("*0027*"))


def _assert_reupgrade(database_url: str, organization_id: str) -> None:
    engine = create_engine(database_url)
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PHASE20H_HEAD
        assert "organization_invitations" in _tables(connection)
        assert connection.scalar(text("SELECT COUNT(*) FROM plan_versions WHERE id = 'plan_portfolio_org_v1'")) == 1
        assert connection.scalar(
            text("SELECT COUNT(*) FROM plan_entitlements WHERE plan_version_id = 'plan_portfolio_org_v1'")
        ) == 1
        assert connection.scalar(
            text("SELECT hard_limit FROM plan_entitlements WHERE plan_version_id = 'plan_portfolio_org_v1' AND entitlement_key = 'limit.organization.seats.count'")
        ) == 5
        _assert_free_v1(connection)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO entitlement_assignments "
                "(id, subject_type, subject_id, plan_version_id, effective_from, source, created_at) "
                "VALUES (:id, 'organization', :subject_id, 'plan_portfolio_org_v1', :effective_from, 'test', :created_at)"
            ),
            {
                "id": f"assignment_org_reupgrade_{uuid4().hex[:12]}",
                "subject_id": organization_id,
                "effective_from": datetime(2025, 8, 24, tzinfo=UTC),
                "created_at": datetime.now(UTC),
            },
        )
    with engine.connect() as connection:
        assert connection.scalar(
            text("SELECT COUNT(*) FROM entitlement_assignments WHERE subject_type = 'organization' AND subject_id = :id"),
            {"id": organization_id},
        ) == 1


def _assert_free_v1(connection) -> None:
    rows = connection.execute(
        text("SELECT entitlement_key, hard_limit FROM plan_entitlements WHERE plan_version_id = 'plan_free_v1'")
    )
    assert {row.entitlement_key: row.hard_limit for row in rows} == EXPECTED_FREE_LIMITS


def _tables(connection) -> set[str]:
    return set(connection.scalars(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")))


def _assert_migration_lineage() -> None:
    versions = BACKEND_DIR / "migrations" / "versions"
    assert not list(versions.glob("*0027*"))
    phase20h_migration = next(versions.glob("*20260824_0028*.py"))
    assert 'revision = "20260824_0028"' in phase20h_migration.read_text()
    assert 'down_revision = "20260821_0026"' in phase20h_migration.read_text()


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
