import hashlib
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import create_user, user_context
from app.db.base import Base
from app.models.entitlement import EntitlementAssignmentModel, PlanEntitlementModel, PlanVersionModel
from app.models.organization import OrganizationInvitationModel, OrganizationMembershipModel, OrganizationModel
from app.organizations.schemas import InvitationAcceptRequest, InvitationCreateRequest, MembershipUpdateRequest
from app.organizations.service import (
    accept_invitation,
    create_invitation,
    resend_invitation,
    revoke_invitation,
    seat_status,
    update_member,
)
from fastapi import HTTPException


@pytest.fixture
def seats():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine); Session = sessionmaker(bind=engine)
    with Session() as db:
        owner = create_user(db, "seat-owner@example.test")
        owner_id = owner.id
        org_id = "org_seats"; org = OrganizationModel(id=org_id, name="Seats", slug="seats", status="active", created_by_user_id=owner.id)
        db.add_all([org, OrganizationMembershipModel(id="mbr_owner", organization_id=org.id, user_id=owner.id, role="owner", status="active")])
        _plans(db); db.commit()
    return Session, owner_id, org_id


def test_seat_projection_counts_active_pending_and_invitation_lifecycle(seats):
    Session, owner_id, org_id = seats
    with Session() as db:
        owner = user_context(db.get(__import__('app.models.user', fromlist=['UserModel']).UserModel, owner_id))
        assert seat_status(db, org_id) == {"limit": 5, "active": 1, "reserved": 0, "consumed": 1, "remaining": 4}
        pending_user = create_user(db, "legacy-pending@example.test")
        db.add(OrganizationMembershipModel(id="mbr_pending", organization_id=org_id, user_id=pending_user.id, role="member", status="pending"))
        db.add(OrganizationInvitationModel(id="inv_live", organization_id=org_id, destination_email="new@example.test", role="member", invited_by_user_id=owner_id, token_hash="a" * 64, status="pending", expires_at=datetime.now(UTC)+timedelta(days=1)))
        db.add(OrganizationInvitationModel(id="inv_expired", organization_id=org_id, destination_email="old@example.test", role="member", invited_by_user_id=owner_id, token_hash="b" * 64, status="pending", expires_at=datetime.now(UTC)-timedelta(days=1)))
        db.add(OrganizationInvitationModel(id="inv_revoked", organization_id=org_id, destination_email="revoked@example.test", role="member", invited_by_user_id=owner_id, token_hash="c" * 64, status="revoked", expires_at=datetime.now(UTC)+timedelta(days=1)))
        db.commit()
        assert seat_status(db, org_id) == {"limit": 5, "active": 1, "reserved": 2, "consumed": 3, "remaining": 2}
        first = create_invitation(db, owner, org_id, InvitationCreateRequest(email="fourth@example.test"))
        assert first.token and seat_status(db, org_id)["consumed"] == 4
        assert seat_status(db, org_id)["consumed"] == 4


def test_limit_higher_assignment_and_missing_catalog_fail_closed(seats):
    Session, owner_id, org_id = seats
    with Session() as db:
        owner = user_context(db.get(__import__('app.models.user', fromlist=['UserModel']).UserModel, owner_id))
        for index in range(4):
            user = create_user(db, f"active-{index}@example.test")
            db.add(OrganizationMembershipModel(id=f"mbr_{index}", organization_id=org_id, user_id=user.id, role="member", status="active"))
        db.commit()
        with pytest.raises(HTTPException, match="seat limit") as error: create_invitation(db, owner, org_id, InvitationCreateRequest(email="fifth@example.test"))
        assert error.value.status_code == 409
        db.add(EntitlementAssignmentModel(id="org_high", subject_type="organization", subject_id=org_id, plan_version_id="plan_org_high", effective_from=datetime(2026,8,24,tzinfo=UTC), source="test")); db.commit()
        assert seat_status(db, org_id)["limit"] == 7
        assert create_invitation(db, owner, org_id, InvitationCreateRequest(email="fifth@example.test")).token
        db.delete(db.get(PlanEntitlementModel, "ent_portfolio_org_seats")); db.commit()
        # Explicit plan still resolves; deleting it proves new operations fail closed.
        db.delete(db.get(EntitlementAssignmentModel, "org_high")); db.commit()
        with pytest.raises(HTTPException, match="entitlement") as error: create_invitation(db, owner, org_id, InvitationCreateRequest(email="blocked@example.test"))
        assert error.value.status_code == 409


def test_default_catalog_identity_and_explicit_assignment_corruption_fail_closed(seats):
    Session, owner_id, org_id = seats
    with Session() as db:
        default_plan = db.get(PlanVersionModel, "plan_portfolio_org_v1")
        default_plan.plan_key = "wrong-org-plan"
        db.commit()
        with pytest.raises(HTTPException, match="entitlement"):
            seat_status(db, org_id)
        default_plan.plan_key = "portfolio-org-v1"
        db.commit()

        db.add(PlanEntitlementModel(id="ent_unexpected_org", plan_version_id=default_plan.id, entitlement_key="limit.unexpected", hard_limit=1))
        db.commit()
        with pytest.raises(HTTPException, match="entitlement"):
            seat_status(db, org_id)
        db.delete(db.get(PlanEntitlementModel, "ent_unexpected_org"))
        db.commit()

        high_plan = db.get(PlanVersionModel, "plan_org_high")
        high_plan.status = "retired"
        db.add(EntitlementAssignmentModel(id="org_bad", subject_type="organization", subject_id=org_id, plan_version_id=high_plan.id, effective_from=datetime(2026, 8, 24, tzinfo=UTC), source="test"))
        db.commit()
        with pytest.raises(HTTPException, match="entitlement"):
            seat_status(db, org_id)
        high_plan.status = "active"
        db.delete(db.get(EntitlementAssignmentModel, "org_bad"))
        db.commit()

        db.add_all([
            EntitlementAssignmentModel(id="org_ambiguous_one", subject_type="organization", subject_id=org_id, plan_version_id="plan_org_high", effective_from=datetime(2025, 8, 24, tzinfo=UTC), source="test"),
            EntitlementAssignmentModel(id="org_ambiguous_two", subject_type="organization", subject_id=org_id, plan_version_id="plan_portfolio_org_v1", effective_from=datetime(2025, 8, 25, tzinfo=UTC), source="test"),
        ])
        db.commit()
        with pytest.raises(HTTPException, match="entitlement"):
            seat_status(db, org_id)


def test_legacy_pending_identity_and_expired_resend_cannot_add_reservation(seats):
    Session, owner_id, org_id = seats
    with Session() as db:
        owner = user_context(db.get(__import__('app.models.user', fromlist=['UserModel']).UserModel, owner_id))
        pending = create_user(db, "same@example.test")
        db.add(OrganizationMembershipModel(id="mbr_same", organization_id=org_id, user_id=pending.id, role="member", status="pending")); db.commit()
        before = seat_status(db, org_id)["consumed"]
        with pytest.raises(HTTPException, match="legacy pending") as error: create_invitation(db, owner, org_id, InvitationCreateRequest(email="same@example.test"))
        assert error.value.status_code == 409 and seat_status(db, org_id)["consumed"] == before
        expired = OrganizationInvitationModel(id="inv_expired_resend", organization_id=org_id, destination_email="expired@example.test", role="member", invited_by_user_id=owner_id, token_hash="d" * 64, status="pending", expires_at=datetime.now(UTC)-timedelta(seconds=1))
        db.add(expired); db.commit()
        with pytest.raises(HTTPException, match="Expired") as error: resend_invitation(db, owner, org_id, expired.id)
        assert error.value.status_code == 409
        for index in range(3):
            user = create_user(db, f"full-{index}@example.test")
            db.add(OrganizationMembershipModel(id=f"mbr_full_{index}", organization_id=org_id, user_id=user.id, role="member", status="active"))
        db.commit()
        assert seat_status(db, org_id)["consumed"] == 5
        with pytest.raises(HTTPException, match="seat limit"):
            create_invitation(db, owner, org_id, InvitationCreateRequest(email="over-capacity@example.test"))


def test_active_members_cannot_be_reinvited_or_reserve_another_seat(seats):
    Session, owner_id, org_id = seats
    with Session() as db:
        owner = user_context(db.get(__import__('app.models.user', fromlist=['UserModel']).UserModel, owner_id))
        admin = create_user(db, "active-admin@example.test")
        member = create_user(db, "active-member@example.test")
        db.add_all([
            OrganizationMembershipModel(id="mbr_active_admin", organization_id=org_id, user_id=admin.id, role="admin", status="active"),
            OrganizationMembershipModel(id="mbr_active_member", organization_id=org_id, user_id=member.id, role="member", status="active"),
        ])
        db.commit()
        before = seat_status(db, org_id)
        users_before = db.query(__import__('app.models.user', fromlist=['UserModel']).UserModel).count()
        for email in (owner.email, admin.email.upper(), member.email):
            with pytest.raises(HTTPException, match="organization member") as error:
                create_invitation(db, owner, org_id, InvitationCreateRequest(email=email))
            assert error.value.status_code == 409
        assert seat_status(db, org_id) == before
        assert db.query(OrganizationInvitationModel).filter_by(organization_id=org_id).count() == 0
        assert db.query(__import__('app.models.user', fromlist=['UserModel']).UserModel).count() == users_before


def test_corrupt_active_member_invitation_cannot_change_roles_or_ownership(seats):
    Session, owner_id, org_id = seats
    with Session() as db:
        owner_record = db.get(__import__('app.models.user', fromlist=['UserModel']).UserModel, owner_id)
        member = create_user(db, "corrupt-active-member@example.test")
        db.add(OrganizationMembershipModel(id="mbr_corrupt_active_member", organization_id=org_id, user_id=member.id, role="member", status="active"))
        owner_token, member_token = "owner-corrupt-token-" + "a" * 40, "member-corrupt-token-" + "b" * 40
        db.add_all([
            OrganizationInvitationModel(id="inv_corrupt_owner", organization_id=org_id, destination_email=owner_record.email, role="member", invited_by_user_id=owner_id, token_hash=hashlib.sha256(owner_token.encode()).hexdigest(), status="pending", expires_at=datetime.now(UTC) + timedelta(days=1)),
            OrganizationInvitationModel(id="inv_corrupt_member", organization_id=org_id, destination_email=member.email, role="admin", invited_by_user_id=owner_id, token_hash=hashlib.sha256(member_token.encode()).hexdigest(), status="pending", expires_at=datetime.now(UTC) + timedelta(days=1)),
        ])
        db.commit()
        before = seat_status(db, org_id)
        for user, token in ((owner_record, owner_token), (member, member_token)):
            with pytest.raises(HTTPException, match="already an active") as error:
                accept_invitation(db, user_context(user), InvitationAcceptRequest(token=token))
            assert error.value.status_code == 409
            db.rollback()
        assert seat_status(db, org_id) == before
        assert db.get(OrganizationMembershipModel, "mbr_owner").role == "owner"
        assert db.get(OrganizationMembershipModel, "mbr_owner").status == "active"
        assert db.get(OrganizationMembershipModel, "mbr_corrupt_active_member").role == "member"
        assert db.get(OrganizationMembershipModel, "mbr_corrupt_active_member").status == "active"
        assert db.get(OrganizationInvitationModel, "inv_corrupt_owner").status == "pending"
        assert db.get(OrganizationInvitationModel, "inv_corrupt_member").status == "pending"


def test_removed_membership_can_be_reactivated_by_a_normal_invitation(seats):
    Session, owner_id, org_id = seats
    with Session() as db:
        owner = user_context(db.get(__import__('app.models.user', fromlist=['UserModel']).UserModel, owner_id))
        removed = create_user(db, "removed-invitation-recipient@example.test")
        db.add(OrganizationMembershipModel(id="mbr_removed_recipient", organization_id=org_id, user_id=removed.id, role="viewer", status="removed"))
        db.commit()
        invitation = create_invitation(db, owner, org_id, InvitationCreateRequest(email=removed.email, role="admin"))
        membership = accept_invitation(db, user_context(removed), InvitationAcceptRequest(token=invitation.token))
        assert membership.id == "mbr_removed_recipient"
        assert membership.role == "admin"
        assert membership.status == "active"
        assert seat_status(db, org_id) == {"limit": 5, "active": 2, "reserved": 0, "consumed": 2, "remaining": 3}


def test_generic_member_updates_cannot_bypass_invitation_activation(seats):
    Session, owner_id, org_id = seats
    with Session() as db:
        owner = user_context(db.get(__import__('app.models.user', fromlist=['UserModel']).UserModel, owner_id))
        removed = create_user(db, "removed-patch@example.test")
        pending = create_user(db, "pending-patch@example.test")
        active = create_user(db, "active-patch@example.test")
        db.add_all([
            OrganizationMembershipModel(id="mbr_removed_patch", organization_id=org_id, user_id=removed.id, role="viewer", status="removed"),
            OrganizationMembershipModel(id="mbr_pending_patch", organization_id=org_id, user_id=pending.id, role="member", status="pending"),
            OrganizationMembershipModel(id="mbr_active_patch", organization_id=org_id, user_id=active.id, role="admin", status="active"),
        ])
        db.commit()

        assert update_member(db, owner, org_id, "mbr_active_patch", MembershipUpdateRequest(role="viewer")).role == "viewer"
        assert update_member(db, owner, org_id, "mbr_active_patch", MembershipUpdateRequest(status="active")).status == "active"
        with pytest.raises(HTTPException, match="invitation") as error:
            update_member(db, owner, org_id, "mbr_active_patch", MembershipUpdateRequest(status="pending"))
        assert error.value.status_code == 409
        db.rollback()
        assert update_member(db, owner, org_id, "mbr_active_patch", MembershipUpdateRequest(status="removed")).status == "removed"
        before = seat_status(db, org_id)
        invitation_count = db.query(OrganizationInvitationModel).filter_by(organization_id=org_id).count()
        user_count = db.query(__import__('app.models.user', fromlist=['UserModel']).UserModel).count()
        for membership_id, request in (
            ("mbr_removed_patch", MembershipUpdateRequest(status="active")),
            ("mbr_pending_patch", MembershipUpdateRequest(status="active")),
            ("mbr_removed_patch", MembershipUpdateRequest(status="pending")),
            ("mbr_pending_patch", MembershipUpdateRequest(role="viewer")),
        ):
            with pytest.raises(HTTPException, match="invitation") as error:
                update_member(db, owner, org_id, membership_id, request)
            assert error.value.status_code == 409
            db.rollback()
        assert update_member(db, owner, org_id, "mbr_removed_patch", MembershipUpdateRequest(status="removed")).status == "removed"
        assert update_member(db, owner, org_id, "mbr_pending_patch", MembershipUpdateRequest(status="removed")).status == "removed"
        assert db.get(OrganizationMembershipModel, "mbr_removed_patch").status == "removed"
        assert seat_status(db, org_id) == {**before, "reserved": 0, "consumed": before["consumed"] - 1, "remaining": before["remaining"] + 1}
        assert db.query(OrganizationInvitationModel).filter_by(organization_id=org_id).count() == invitation_count
        assert db.query(__import__('app.models.user', fromlist=['UserModel']).UserModel).count() == user_count


def test_generic_patch_cannot_reactivate_removed_member_with_or_without_capacity(seats):
    Session, owner_id, org_id = seats
    with Session() as db:
        owner = user_context(db.get(__import__('app.models.user', fromlist=['UserModel']).UserModel, owner_id))
        removed = create_user(db, "full-removed-patch@example.test")
        db.add(OrganizationMembershipModel(id="mbr_full_removed_patch", organization_id=org_id, user_id=removed.id, role="member", status="removed"))
        for index in range(4):
            user = create_user(db, f"full-patch-{index}@example.test")
            db.add(OrganizationMembershipModel(id=f"mbr_full_patch_{index}", organization_id=org_id, user_id=user.id, role="member", status="active"))
        db.commit()

        for expected_consumed in (5, 4):
            before = seat_status(db, org_id)
            assert before["consumed"] == expected_consumed
            with pytest.raises(HTTPException, match="invitation") as error:
                update_member(db, owner, org_id, "mbr_full_removed_patch", MembershipUpdateRequest(status="active"))
            assert error.value.status_code == 409
            db.rollback()
            assert db.get(OrganizationMembershipModel, "mbr_full_removed_patch").status == "removed"
            assert seat_status(db, org_id) == before
            assert db.query(OrganizationInvitationModel).filter_by(organization_id=org_id).count() == 0
            if expected_consumed == 5:
                db.get(OrganizationMembershipModel, "mbr_full_patch_0").status = "removed"
                db.commit()


def test_resend_preserves_one_reservation_and_invalidates_old_token(seats):
    Session, owner_id, org_id = seats
    with Session() as db:
        owner = user_context(db.get(__import__('app.models.user', fromlist=['UserModel']).UserModel, owner_id))
        recipient = create_user(db, "resend-recipient@example.test")
        first = create_invitation(db, owner, org_id, InvitationCreateRequest(email=recipient.email))
        assert seat_status(db, org_id) == {"limit": 5, "active": 1, "reserved": 1, "consumed": 2, "remaining": 3}
        replacement = resend_invitation(db, owner, org_id, first.id)
        assert replacement.id != first.id
        assert db.get(OrganizationInvitationModel, first.id).status == "superseded"
        assert seat_status(db, org_id) == {"limit": 5, "active": 1, "reserved": 1, "consumed": 2, "remaining": 3}
        with pytest.raises(HTTPException, match="invalid"):
            accept_invitation(db, user_context(recipient), InvitationAcceptRequest(token=first.token))


def test_acceptance_converts_reservation_to_one_active_member_without_double_count(seats):
    Session, owner_id, org_id = seats
    with Session() as db:
        owner = user_context(db.get(__import__('app.models.user', fromlist=['UserModel']).UserModel, owner_id))
        recipient = create_user(db, "accept-recipient@example.test")
        invitation = create_invitation(db, owner, org_id, InvitationCreateRequest(email=recipient.email))
        assert seat_status(db, org_id)["consumed"] == 2
        membership = accept_invitation(db, user_context(recipient), InvitationAcceptRequest(token=invitation.token))
        assert membership.status == "active"
        assert seat_status(db, org_id) == {"limit": 5, "active": 2, "reserved": 0, "consumed": 2, "remaining": 3}
        with pytest.raises(HTTPException, match="invalid"):
            accept_invitation(db, user_context(recipient), InvitationAcceptRequest(token=invitation.token))
        assert db.query(OrganizationMembershipModel).filter_by(organization_id=org_id, user_id=recipient.id).count() == 1
        assert seat_status(db, org_id)["consumed"] == 2


def test_revoke_releases_pending_invitation_reservation(seats):
    Session, owner_id, org_id = seats
    with Session() as db:
        owner = user_context(db.get(__import__('app.models.user', fromlist=['UserModel']).UserModel, owner_id))
        invitation = create_invitation(db, owner, org_id, InvitationCreateRequest(email="revoke-recipient@example.test"))
        assert seat_status(db, org_id)["consumed"] == 2
        revoke_invitation(db, owner, org_id, invitation.id)
        assert seat_status(db, org_id) == {"limit": 5, "active": 1, "reserved": 0, "consumed": 1, "remaining": 4}


def _plans(db):
    now = datetime(2026, 8, 24, tzinfo=UTC)
    db.add_all([PlanVersionModel(id="plan_free_v1", plan_key="free-v1", version=1, status="active", effective_from=now), PlanVersionModel(id="plan_portfolio_org_v1", plan_key="portfolio-org-v1", version=1, status="active", effective_from=now), PlanVersionModel(id="plan_org_high", plan_key="test-org-high", version=1, status="active", effective_from=now)])
    db.add_all([PlanEntitlementModel(id="ent_portfolio_org_seats", plan_version_id="plan_portfolio_org_v1", entitlement_key="limit.organization.seats.count", hard_limit=5), PlanEntitlementModel(id="ent_org_high", plan_version_id="plan_org_high", entitlement_key="limit.organization.seats.count", hard_limit=7)])
