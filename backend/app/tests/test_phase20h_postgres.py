from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import delete, event, select
from sqlalchemy.orm import sessionmaker

from app.auth.service import create_user, user_context
from app.db.session import create_database_engine
from app.models.entitlement import EntitlementAssignmentModel, PlanEntitlementModel, PlanVersionModel
from app.models.organization import OrganizationInvitationModel, OrganizationMembershipModel, OrganizationModel
from app.models.user import UserModel
from app.organizations.schemas import InvitationCreateRequest, OrganizationCreateRequest
from app.organizations.service import create_invitation, create_organization, seat_status

EXPECTED_FREE_LIMITS = {
    "limit.analysis.count": 25,
    "limit.simulation.count": 100,
    "limit.options.count": 100,
    "limit.market_data.count": 100,
    "limit.saved_thesis.count": 50,
    "limit.watchlist.count": 25,
    "limit.schedule.active_count": 5,
}

pytestmark = pytest.mark.postgres_integration


@pytest.fixture(scope="module")
def postgres_sessions() -> sessionmaker:
    if os.getenv("RUN_POSTGRES_INTEGRATION") != "true":
        pytest.skip("Phase 20H PostgreSQL tests require RUN_POSTGRES_INTEGRATION=true")
    engine = create_database_engine()
    if engine.dialect.name != "postgresql":
        pytest.skip("Phase 20H PostgreSQL tests require a PostgreSQL DATABASE_URL")
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_postgres_final_seat_race_has_one_winner_under_organization_row_lock(postgres_sessions: sessionmaker) -> None:
    suffix = uuid4().hex[:12]
    owner_id, organization_id = _seed_organization(postgres_sessions, suffix, active_count=4)
    engine = postgres_sessions.kw["bind"]
    lock_barrier = Barrier(2)
    lock_selects = 0

    def synchronize_org_lock(connection, cursor, statement, parameters, context, executemany):
        nonlocal lock_selects
        if 'FROM organizations' in statement and 'FOR UPDATE' in statement:
            lock_selects += 1
            lock_barrier.wait(timeout=10)

    def invite(email: str) -> tuple[str, int | str]:
        with postgres_sessions() as db:
            try:
                owner = db.get(UserModel, owner_id)
                invitation = create_invitation(
                    db,
                    user_context(owner),
                    organization_id,
                    InvitationCreateRequest(email=email),
                )
                return "success", invitation.id
            except HTTPException as error:
                db.rollback()
                return "error", error.status_code

    event.listen(engine, "before_cursor_execute", synchronize_org_lock)
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(invite, [f"race-one-{suffix}@example.test", f"race-two-{suffix}@example.test"]))
        assert sorted(item[0] for item in results) == ["error", "success"]
        assert [item[1] for item in results if item[0] == "error"] == [409]
        assert lock_selects == 2
        with postgres_sessions() as db:
            seats = seat_status(db, organization_id)
            assert seats == {"limit": 5, "active": 4, "reserved": 1, "consumed": 5, "remaining": 0}
            invitations = db.execute(
                select(OrganizationInvitationModel).where(OrganizationInvitationModel.organization_id == organization_id)
            ).scalars().all()
            assert len(invitations) == 1
    finally:
        event.remove(engine, "before_cursor_execute", synchronize_org_lock)
        _cleanup_organization(postgres_sessions, suffix, organization_id)


def test_postgres_organization_creation_flushes_before_owner_membership(postgres_sessions: sessionmaker) -> None:
    suffix = uuid4().hex[:12]
    organization_id = ""
    try:
        with postgres_sessions() as db:
            owner = create_user(db, f"phase20h-create-{suffix}@example.test")
            organization = create_organization(
                db,
                user_context(owner),
                OrganizationCreateRequest(name=f"Phase 20H create {suffix}"),
            )
            organization_id = organization.id
            assert seat_status(db, organization_id) == {
                "limit": 5,
                "active": 1,
                "reserved": 0,
                "consumed": 1,
                "remaining": 4,
            }
    finally:
        if organization_id:
            _cleanup_organization(postgres_sessions, suffix, organization_id)


def test_postgres_organization_assignment_allows_higher_limit_without_changing_free_v1(postgres_sessions: sessionmaker) -> None:
    suffix = uuid4().hex[:12]
    default_owner_id, default_org_id = _seed_organization(postgres_sessions, f"default-{suffix}", active_count=5)
    high_owner_id, high_org_id = _seed_organization(postgres_sessions, f"high-{suffix}", active_count=5)
    plan_id = f"plan_org_high_{suffix}"
    try:
        with postgres_sessions() as db:
            default_owner = db.get(UserModel, default_owner_id)
            with pytest.raises(HTTPException, match="seat limit"):
                create_invitation(
                    db,
                    user_context(default_owner),
                    default_org_id,
                    InvitationCreateRequest(email=f"blocked-{suffix}@example.test"),
                )
            db.rollback()
            db.add(
                PlanVersionModel(
                    id=plan_id,
                    plan_key=f"test-org-high-{suffix}",
                    version=1,
                    status="active",
                    effective_from=datetime(2025, 8, 24, tzinfo=UTC),
                )
            )
            db.flush()
            db.add_all([
                PlanEntitlementModel(
                    id=f"ent_org_high_{suffix}",
                    plan_version_id=plan_id,
                    entitlement_key="limit.organization.seats.count",
                    hard_limit=7,
                ),
                EntitlementAssignmentModel(
                    id=f"assignment_org_high_{suffix}",
                    subject_type="organization",
                    subject_id=high_org_id,
                    plan_version_id=plan_id,
                    effective_from=datetime(2025, 8, 24, tzinfo=UTC),
                    source="test",
                ),
            ])
            db.commit()
            high_owner = db.get(UserModel, high_owner_id)
            invitation = create_invitation(
                db,
                user_context(high_owner),
                high_org_id,
                InvitationCreateRequest(email=f"allowed-{suffix}@example.test"),
            )
            assert invitation.token
            assert seat_status(db, default_org_id)["limit"] == 5
            assert seat_status(db, high_org_id)["limit"] == 7
            free_limits = {
                row.entitlement_key: row.hard_limit
                for row in db.execute(
                    select(PlanEntitlementModel).where(PlanEntitlementModel.plan_version_id == "plan_free_v1")
                ).scalars()
            }
            assert free_limits == EXPECTED_FREE_LIMITS
    finally:
        with postgres_sessions() as db:
            db.execute(delete(EntitlementAssignmentModel).where(EntitlementAssignmentModel.plan_version_id == plan_id))
            db.execute(delete(PlanEntitlementModel).where(PlanEntitlementModel.plan_version_id == plan_id))
            db.execute(delete(PlanVersionModel).where(PlanVersionModel.id == plan_id))
            db.commit()
        _cleanup_organization(postgres_sessions, f"default-{suffix}", default_org_id)
        _cleanup_organization(postgres_sessions, f"high-{suffix}", high_org_id)


def _seed_organization(sessions: sessionmaker, suffix: str, *, active_count: int) -> tuple[str, str]:
    with sessions() as db:
        owner = create_user(db, f"phase20h-owner-{suffix}@example.test")
        members = [owner]
        for index in range(active_count - 1):
            members.append(create_user(db, f"phase20h-member-{suffix}-{index}@example.test"))
        organization_id = f"org_phase20h_{suffix}"
        db.add(
            OrganizationModel(
                id=organization_id,
                name=f"Phase 20H {suffix}",
                slug=f"phase20h-{suffix}",
                status="active",
                created_by_user_id=owner.id,
            )
        )
        db.flush()
        for index, user in enumerate(members):
            db.add(
                OrganizationMembershipModel(
                    id=f"mbr_phase20h_{suffix}_{index}",
                    organization_id=organization_id,
                    user_id=user.id,
                    role="owner" if user.id == owner.id else "member",
                    status="active",
                )
            )
        db.commit()
        return owner.id, organization_id


def _cleanup_organization(sessions: sessionmaker, suffix: str, organization_id: str) -> None:
    with sessions() as db:
        user_ids = list(
            db.scalars(
                select(OrganizationMembershipModel.user_id).where(
                    OrganizationMembershipModel.organization_id == organization_id
                )
            )
        )
        db.execute(delete(OrganizationInvitationModel).where(OrganizationInvitationModel.organization_id == organization_id))
        db.execute(delete(EntitlementAssignmentModel).where(EntitlementAssignmentModel.subject_id == organization_id))
        db.execute(delete(OrganizationMembershipModel).where(OrganizationMembershipModel.organization_id == organization_id))
        db.execute(delete(OrganizationModel).where(OrganizationModel.id == organization_id))
        if user_ids:
            db.execute(delete(UserModel).where(UserModel.id.in_(user_ids)))
        db.commit()
