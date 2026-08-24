from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import create_user, user_context
from app.db.base import Base
from app.models.entitlement import EntitlementAssignmentModel, PlanEntitlementModel, PlanVersionModel
from app.models.organization import OrganizationInvitationModel, OrganizationMembershipModel, OrganizationModel
from app.organizations.schemas import InvitationCreateRequest
from app.organizations.service import create_invitation, seat_status, resend_invitation
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


def _plans(db):
    now = datetime(2026, 8, 24, tzinfo=UTC)
    db.add_all([PlanVersionModel(id="plan_free_v1", plan_key="free-v1", version=1, status="active", effective_from=now), PlanVersionModel(id="plan_portfolio_org_v1", plan_key="portfolio-org-v1", version=1, status="active", effective_from=now), PlanVersionModel(id="plan_org_high", plan_key="test-org-high", version=1, status="active", effective_from=now)])
    db.add_all([PlanEntitlementModel(id="ent_portfolio_org_seats", plan_version_id="plan_portfolio_org_v1", entitlement_key="limit.organization.seats.count", hard_limit=5), PlanEntitlementModel(id="ent_org_high", plan_version_id="plan_org_high", entitlement_key="limit.organization.seats.count", hard_limit=7)])
