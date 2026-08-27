from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import delete, event, func, select
from sqlalchemy.orm import sessionmaker

from app.auth.service import create_user, user_context
from app.db.session import create_database_engine
from app.models.entitlement import EntitlementAssignmentModel, PlanEntitlementModel, PlanVersionModel
from app.models.organization import OrganizationInvitationModel, OrganizationMembershipModel, OrganizationModel
from app.models.user import UserModel
from app.organizations.schemas import (
    InvitationAcceptRequest,
    InvitationCreateRequest,
    MembershipUpdateRequest,
    OrganizationCreateRequest,
)
from app.organizations.service import (
    accept_invitation,
    create_invitation,
    create_organization,
    resend_invitation,
    revoke_invitation,
    seat_status,
    update_member,
)

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


def test_postgres_active_member_duplicate_invites_cannot_reserve_another_seat(postgres_sessions: sessionmaker) -> None:
    suffix = uuid4().hex[:12]
    owner_id, organization_id = _seed_organization(postgres_sessions, suffix, active_count=1)
    engine = postgres_sessions.kw["bind"]
    lock_barrier = Barrier(2)
    lock_selects = 0

    def synchronize_org_lock(connection, cursor, statement, parameters, context, executemany):
        nonlocal lock_selects
        if "FROM organizations" in statement and "FOR UPDATE" in statement:
            lock_selects += 1
            lock_barrier.wait(timeout=10)

    def invite_active_owner() -> tuple[str, int | str]:
        with postgres_sessions() as db:
            try:
                owner = db.get(UserModel, owner_id)
                create_invitation(
                    db,
                    user_context(owner),
                    organization_id,
                    InvitationCreateRequest(email=owner.email),
                )
                return "success", "unexpected"
            except HTTPException as error:
                db.rollback()
                return "error", error.status_code

    event.listen(engine, "before_cursor_execute", synchronize_org_lock)
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: invite_active_owner(), range(2)))
        assert results == [("error", 409), ("error", 409)]
        assert lock_selects == 2
        with postgres_sessions() as db:
            owner_membership = db.execute(
                select(OrganizationMembershipModel)
                .where(OrganizationMembershipModel.organization_id == organization_id)
                .where(OrganizationMembershipModel.user_id == owner_id)
            ).scalars().one()
            assert (owner_membership.role, owner_membership.status) == ("owner", "active")
            assert _pending_invitations(db, organization_id) == []
            assert seat_status(db, organization_id) == {
                "limit": 5,
                "active": 1,
                "reserved": 0,
                "consumed": 1,
                "remaining": 4,
            }
    finally:
        event.remove(engine, "before_cursor_execute", synchronize_org_lock)
        _cleanup_organization(postgres_sessions, suffix, organization_id)


def test_postgres_generic_patch_cannot_bypass_invitation_reactivation(postgres_sessions: sessionmaker) -> None:
    suffix = uuid4().hex[:12]
    owner_id, organization_id = _seed_organization(postgres_sessions, suffix, active_count=4)
    removed_id = pending_id = ""
    try:
        with postgres_sessions() as db:
            owner = db.get(UserModel, owner_id)
            removed = create_user(db, f"phase20h-removed-{suffix}@example.test")
            pending = create_user(db, f"phase20h-pending-{suffix}@example.test")
            removed_id, pending_id = removed.id, pending.id
            db.add_all([
                OrganizationMembershipModel(id=f"mbr_removed_{suffix}", organization_id=organization_id, user_id=removed.id, role="viewer", status="removed"),
                OrganizationMembershipModel(id=f"mbr_pending_{suffix}", organization_id=organization_id, user_id=pending.id, role="member", status="pending"),
            ])
            db.commit()
            before = seat_status(db, organization_id)
            assert before == {"limit": 5, "active": 4, "reserved": 1, "consumed": 5, "remaining": 0}
            for membership_id in (f"mbr_removed_{suffix}", f"mbr_pending_{suffix}"):
                with pytest.raises(HTTPException, match="invitation") as error:
                    update_member(
                        db,
                        user_context(owner),
                        organization_id,
                        membership_id,
                        MembershipUpdateRequest(status="active"),
                    )
                assert error.value.status_code == 409
                db.rollback()
            assert seat_status(db, organization_id) == before
            assert db.get(OrganizationMembershipModel, f"mbr_removed_{suffix}").status == "removed"
            assert db.get(OrganizationMembershipModel, f"mbr_pending_{suffix}").status == "pending"

            assert update_member(
                db,
                user_context(owner),
                organization_id,
                f"mbr_pending_{suffix}",
                MembershipUpdateRequest(status="removed"),
            ).status == "removed"
            invitation = create_invitation(
                db,
                user_context(owner),
                organization_id,
                InvitationCreateRequest(email=removed.email, role="admin"),
            )
            reactivated = accept_invitation(
                db,
                user_context(removed),
                InvitationAcceptRequest(token=invitation.token),
            )
            assert (reactivated.id, reactivated.role, reactivated.status) == (f"mbr_removed_{suffix}", "admin", "active")
            assert db.execute(
                select(func.count())
                .select_from(OrganizationMembershipModel)
                .where(OrganizationMembershipModel.organization_id == organization_id)
                .where(OrganizationMembershipModel.user_id == removed.id)
            ).scalar_one() == 1
            assert seat_status(db, organization_id) == {
                "limit": 5,
                "active": 5,
                "reserved": 0,
                "consumed": 5,
                "remaining": 0,
            }
    finally:
        _cleanup_organization(
            postgres_sessions,
            suffix,
            organization_id,
            extra_user_ids=[item for item in (removed_id, pending_id) if item],
        )


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


def test_postgres_resend_vs_revoke_serializes_one_invitation_lifecycle(postgres_sessions: sessionmaker) -> None:
    suffix = uuid4().hex[:12]
    owner_id, organization_id, recipient_id, invitation = _seed_pending_invitation(postgres_sessions, suffix)
    engine = postgres_sessions.kw["bind"]

    def resend() -> tuple[str, int | str]:
        with postgres_sessions() as db:
            try:
                owner = db.get(UserModel, owner_id)
                response = resend_invitation(db, user_context(owner), organization_id, invitation.id)
                return "resend", response.id
            except HTTPException as error:
                db.rollback()
                return "resend_error", error.status_code

    def revoke() -> tuple[str, int | str]:
        with postgres_sessions() as db:
            try:
                owner = db.get(UserModel, owner_id)
                response = revoke_invitation(db, user_context(owner), organization_id, invitation.id)
                return "revoke", response.status
            except HTTPException as error:
                db.rollback()
                return "revoke_error", error.status_code

    try:
        results, lock_selects = _run_invitation_lock_race(engine, [resend, revoke])
        assert lock_selects == 2
        assert {item[0] for item in results}.issubset({"resend", "resend_error", "revoke", "revoke_error"})
        with postgres_sessions() as db:
            original = db.get(OrganizationInvitationModel, invitation.id)
            pending = _pending_invitations(db, organization_id)
            assert original.status in {"revoked", "superseded"}
            assert len(pending) <= 1
            assert all(item.id != original.id for item in pending)
            assert seat_status(db, organization_id)["reserved"] == len(pending)
            assert seat_status(db, organization_id)["consumed"] == 1 + len(pending)
            _assert_token_is_invalid(db, recipient_id, invitation.token)
    finally:
        _cleanup_organization(postgres_sessions, suffix, organization_id, extra_user_ids=[recipient_id])


def test_postgres_resend_vs_accept_has_one_authoritative_outcome(postgres_sessions: sessionmaker) -> None:
    suffix = uuid4().hex[:12]
    owner_id, organization_id, recipient_id, invitation = _seed_pending_invitation(postgres_sessions, suffix)
    engine = postgres_sessions.kw["bind"]

    def resend() -> tuple[str, int | str]:
        with postgres_sessions() as db:
            try:
                owner = db.get(UserModel, owner_id)
                response = resend_invitation(db, user_context(owner), organization_id, invitation.id)
                return "resend", response.id
            except HTTPException as error:
                db.rollback()
                return "resend_error", error.status_code

    def accept() -> tuple[str, int | str]:
        with postgres_sessions() as db:
            try:
                recipient = db.get(UserModel, recipient_id)
                response = accept_invitation(db, user_context(recipient), InvitationAcceptRequest(token=invitation.token))
                return "accept", response.id
            except HTTPException as error:
                db.rollback()
                return "accept_error", error.status_code

    try:
        results, lock_selects = _run_invitation_lock_race(engine, [resend, accept])
        assert lock_selects == 2
        assert len([item for item in results if item[0] in {"resend", "accept"}]) == 1
        with postgres_sessions() as db:
            original = db.get(OrganizationInvitationModel, invitation.id)
            memberships = _recipient_memberships(db, organization_id, recipient_id)
            pending = _pending_invitations(db, organization_id)
            assert original.status in {"accepted", "superseded"}
            assert len(memberships) <= 1
            assert len(pending) <= 1
            assert not (memberships and pending and original.status == "accepted")
            assert seat_status(db, organization_id) == {
                "limit": 5,
                "active": 1 + len(memberships),
                "reserved": len(pending),
                "consumed": 2,
                "remaining": 3,
            }
            _assert_token_is_invalid(db, recipient_id, invitation.token)
    finally:
        _cleanup_organization(postgres_sessions, suffix, organization_id, extra_user_ids=[recipient_id])


def test_postgres_revoke_vs_accept_has_one_terminal_invitation_state(postgres_sessions: sessionmaker) -> None:
    suffix = uuid4().hex[:12]
    owner_id, organization_id, recipient_id, invitation = _seed_pending_invitation(postgres_sessions, suffix)
    engine = postgres_sessions.kw["bind"]

    def revoke() -> tuple[str, int | str]:
        with postgres_sessions() as db:
            try:
                owner = db.get(UserModel, owner_id)
                response = revoke_invitation(db, user_context(owner), organization_id, invitation.id)
                return "revoke", response.status
            except HTTPException as error:
                db.rollback()
                return "revoke_error", error.status_code

    def accept() -> tuple[str, int | str]:
        with postgres_sessions() as db:
            try:
                recipient = db.get(UserModel, recipient_id)
                response = accept_invitation(db, user_context(recipient), InvitationAcceptRequest(token=invitation.token))
                return "accept", response.id
            except HTTPException as error:
                db.rollback()
                return "accept_error", error.status_code

    try:
        results, lock_selects = _run_invitation_lock_race(engine, [revoke, accept])
        assert lock_selects == 2
        assert any(item[0] in {"revoke", "accept"} for item in results)
        with postgres_sessions() as db:
            original = db.get(OrganizationInvitationModel, invitation.id)
            memberships = _recipient_memberships(db, organization_id, recipient_id)
            assert original.status in {"revoked", "accepted"}
            assert len(memberships) == (1 if original.status == "accepted" else 0)
            assert _pending_invitations(db, organization_id) == []
            assert seat_status(db, organization_id)["consumed"] == 1 + len(memberships)
            _assert_token_is_invalid(db, recipient_id, invitation.token)
    finally:
        _cleanup_organization(postgres_sessions, suffix, organization_id, extra_user_ids=[recipient_id])


def test_postgres_duplicate_acceptance_creates_one_membership_without_double_counting(postgres_sessions: sessionmaker) -> None:
    suffix = uuid4().hex[:12]
    _, organization_id, recipient_id, invitation = _seed_pending_invitation(postgres_sessions, suffix)
    engine = postgres_sessions.kw["bind"]

    def accept() -> tuple[str, int | str]:
        with postgres_sessions() as db:
            try:
                recipient = db.get(UserModel, recipient_id)
                response = accept_invitation(db, user_context(recipient), InvitationAcceptRequest(token=invitation.token))
                return "accept", response.id
            except HTTPException as error:
                db.rollback()
                return "accept_error", error.status_code

    try:
        results, lock_selects = _run_invitation_lock_race(engine, [accept, accept])
        assert lock_selects == 2
        assert [item[0] for item in results].count("accept") == 1
        assert [item[1] for item in results if item[0] == "accept_error"] == [409]
        with postgres_sessions() as db:
            original = db.get(OrganizationInvitationModel, invitation.id)
            assert original.status == "accepted"
            assert len(_recipient_memberships(db, organization_id, recipient_id)) == 1
            assert _pending_invitations(db, organization_id) == []
            assert seat_status(db, organization_id) == {
                "limit": 5,
                "active": 2,
                "reserved": 0,
                "consumed": 2,
                "remaining": 3,
            }
    finally:
        _cleanup_organization(postgres_sessions, suffix, organization_id, extra_user_ids=[recipient_id])


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


def _seed_pending_invitation(
    sessions: sessionmaker,
    suffix: str,
) -> tuple[str, str, str, object]:
    owner_id, organization_id = _seed_organization(sessions, suffix, active_count=1)
    with sessions() as db:
        owner = db.get(UserModel, owner_id)
        recipient = create_user(db, f"phase20h-invitation-recipient-{suffix}@example.test")
        invitation = create_invitation(
            db,
            user_context(owner),
            organization_id,
            InvitationCreateRequest(email=recipient.email),
        )
        return owner_id, organization_id, recipient.id, invitation


def _run_invitation_lock_race(engine, operations) -> tuple[list[tuple[str, int | str]], int]:
    barrier = Barrier(len(operations))
    lock_selects = 0

    def synchronize_invitation_lock(connection, cursor, statement, parameters, context, executemany):
        nonlocal lock_selects
        if "FROM organization_invitations" in statement and "FOR UPDATE" in statement:
            lock_selects += 1
            barrier.wait(timeout=10)

    event.listen(engine, "before_cursor_execute", synchronize_invitation_lock)
    try:
        with ThreadPoolExecutor(max_workers=len(operations)) as executor:
            results = list(executor.map(lambda operation: operation(), operations))
        return results, lock_selects
    finally:
        event.remove(engine, "before_cursor_execute", synchronize_invitation_lock)


def _pending_invitations(db, organization_id: str) -> list[OrganizationInvitationModel]:
    return list(
        db.scalars(
            select(OrganizationInvitationModel)
            .where(OrganizationInvitationModel.organization_id == organization_id)
            .where(OrganizationInvitationModel.status == "pending")
        )
    )


def _recipient_memberships(db, organization_id: str, recipient_id: str) -> list[OrganizationMembershipModel]:
    return list(
        db.scalars(
            select(OrganizationMembershipModel)
            .where(OrganizationMembershipModel.organization_id == organization_id)
            .where(OrganizationMembershipModel.user_id == recipient_id)
            .where(OrganizationMembershipModel.status == "active")
        )
    )


def _assert_token_is_invalid(db, recipient_id: str, token: str) -> None:
    recipient = db.get(UserModel, recipient_id)
    with pytest.raises(HTTPException, match="invalid"):
        accept_invitation(db, user_context(recipient), InvitationAcceptRequest(token=token))
    db.rollback()


def _cleanup_organization(
    sessions: sessionmaker,
    suffix: str,
    organization_id: str,
    *,
    extra_user_ids: list[str] | None = None,
) -> None:
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
        user_ids.extend(extra_user_ids or [])
        if user_ids:
            db.execute(delete(UserModel).where(UserModel.id.in_(user_ids)))
        db.commit()
