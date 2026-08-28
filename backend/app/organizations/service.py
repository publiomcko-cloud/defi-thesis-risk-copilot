from __future__ import annotations

import hashlib
import re
from secrets import token_urlsafe
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.policies import (
    can_administer_organization,
    can_manage_members,
    can_manage_organization,
    can_transfer_organization_ownership,
    has_recent_authentication,
    is_organization_lifecycle_owner,
)
from app.auth.schemas import UserContext
from app.auth.service import normalize_email, record_audit_event
from app.jobs.lifecycle import dispose_jobs_for_organization_deletion, revoke_jobs_for_authorization_change
from app.models.organization import OrganizationInvitationModel, OrganizationMembershipModel, OrganizationModel
from app.models.entitlement import EntitlementAssignmentModel, PlanEntitlementModel, PlanVersionModel
from app.models.user import UserModel
from app.knowledge.service import tombstone_knowledge_for_organization
from app.organizations.schemas import (
    MembershipCreateRequest,
    MembershipResponse,
    MembershipUpdateRequest,
    OrganizationCreateRequest,
    OrganizationResponse,
    OrganizationUpdateRequest,
    InvitationAcceptRequest,
    InvitationCreateRequest,
    InvitationTokenResponse,
    InvitationResponse,
    OrganizationExportInvitation,
    OrganizationExportMembership,
    OrganizationExportOrganization,
    OrganizationExportPlan,
    OrganizationExportResponse,
    OrganizationExportSeatProjection,
    OwnershipTransferRequest,
)

ORG_PLAN_ID = "plan_portfolio_org_v1"
ORG_SEAT_KEY = "limit.organization.seats.count"
INVITABLE_ORGANIZATION_ROLES = {"admin", "member", "viewer"}


def seat_status(db: Session, organization_id: str, *, lock: bool = False) -> dict[str, int]:
    query = select(OrganizationModel).where(OrganizationModel.id == organization_id)
    if lock: query = query.with_for_update()
    org = db.execute(query).scalars().one_or_none()
    if org is None: raise HTTPException(status_code=404, detail="Organization not found")
    now = datetime.now(UTC)
    active = db.scalar(select(func.count()).select_from(OrganizationMembershipModel).where(OrganizationMembershipModel.organization_id == organization_id, OrganizationMembershipModel.status == "active")) or 0
    legacy_pending = db.scalar(select(func.count()).select_from(OrganizationMembershipModel).where(OrganizationMembershipModel.organization_id == organization_id, OrganizationMembershipModel.status == "pending")) or 0
    invitations = db.scalar(select(func.count()).select_from(OrganizationInvitationModel).where(OrganizationInvitationModel.organization_id == organization_id, OrganizationInvitationModel.status == "pending", OrganizationInvitationModel.expires_at > now)) or 0
    assignments = db.execute(
        select(EntitlementAssignmentModel)
        .where(
            EntitlementAssignmentModel.subject_type == "organization",
            EntitlementAssignmentModel.subject_id == organization_id,
            EntitlementAssignmentModel.effective_from <= now,
        )
        .where(
            (EntitlementAssignmentModel.effective_until.is_(None))
            | (EntitlementAssignmentModel.effective_until > now)
        )
    ).scalars().all()
    if len(assignments) > 1:
        raise HTTPException(status_code=409, detail="Organization seat entitlement is unavailable")
    plan_id = assignments[0].plan_version_id if assignments else ORG_PLAN_ID
    limit = _organization_seat_limit(db, plan_id, now, require_default_identity=not assignments)
    if limit is None:
        raise HTTPException(status_code=409, detail="Organization seat entitlement is unavailable")
    reserved, consumed = int(legacy_pending + invitations), int(active + legacy_pending + invitations)
    return {"limit": int(limit), "active": int(active), "reserved": reserved, "consumed": consumed, "remaining": max(int(limit) - consumed, 0)}


def _organization_export_plan(
    db: Session,
    organization_id: str,
    now: datetime,
) -> PlanVersionModel:
    assignments = db.execute(
        select(EntitlementAssignmentModel)
        .where(
            EntitlementAssignmentModel.subject_type == "organization",
            EntitlementAssignmentModel.subject_id == organization_id,
            EntitlementAssignmentModel.effective_from <= now,
        )
        .where(
            (EntitlementAssignmentModel.effective_until.is_(None))
            | (EntitlementAssignmentModel.effective_until > now)
        )
    ).scalars().all()
    if len(assignments) > 1:
        raise HTTPException(status_code=409, detail="Organization seat entitlement is unavailable")
    plan_id = assignments[0].plan_version_id if assignments else ORG_PLAN_ID
    if _organization_seat_limit(db, plan_id, now, require_default_identity=not assignments) is None:
        raise HTTPException(status_code=409, detail="Organization seat entitlement is unavailable")
    plan = db.get(PlanVersionModel, plan_id)
    if plan is None:
        raise HTTPException(status_code=409, detail="Organization seat entitlement is unavailable")
    return plan


def _organization_seat_limit(
    db: Session,
    plan_id: str,
    now: datetime,
    *,
    require_default_identity: bool,
) -> int | None:
    plan = db.get(PlanVersionModel, plan_id)
    if plan is None or plan.status != "active" or not _contains_now(plan.effective_from, plan.effective_until, now):
        return None
    if require_default_identity and (
        plan.id != ORG_PLAN_ID
        or plan.plan_key != "portfolio-org-v1"
        or plan.version != 1
    ):
        return None
    entitlements = db.execute(
        select(PlanEntitlementModel).where(PlanEntitlementModel.plan_version_id == plan.id)
    ).scalars().all()
    seat_entitlements = [item for item in entitlements if item.entitlement_key == ORG_SEAT_KEY]
    if len(seat_entitlements) != 1:
        return None
    if require_default_identity and len(entitlements) != 1:
        return None
    limit = seat_entitlements[0].hard_limit
    return limit if isinstance(limit, int) and limit >= 0 else None


def _contains_now(starts_at: datetime, ends_at: datetime | None, now: datetime) -> bool:
    starts_at = _as_utc(starts_at)
    ends_at = _as_utc(ends_at) if ends_at is not None else None
    return starts_at <= now and (ends_at is None or ends_at > now)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def create_organization(
    db: Session,
    actor: UserContext,
    request: OrganizationCreateRequest,
) -> OrganizationResponse:
    slug = _slugify(request.slug or request.name)
    if db.execute(select(OrganizationModel).where(OrganizationModel.slug == slug)).scalars().first():
        raise HTTPException(status_code=409, detail="Organization slug already exists")
    now = datetime.now(UTC)
    org = OrganizationModel(
        id=f"org_{uuid4().hex[:12]}",
        name=request.name,
        slug=slug,
        status="active",
        created_by_user_id=actor.id,
        created_at=now,
        updated_at=now,
    )
    membership = OrganizationMembershipModel(
        id=f"mbr_{uuid4().hex[:12]}",
        organization_id=org.id,
        user_id=actor.id,
        role="owner",
        status="active",
        created_at=now,
        updated_at=now,
    )
    db.add(org)
    db.flush()
    db.add(membership)
    db.commit()
    db.refresh(org)
    record_audit_event(
        db,
        actor.id,
        "organization.created",
        "organization",
        org.id,
        {"slug": org.slug},
    )
    record_audit_event(
        db,
        actor.id,
        "organization.member_added",
        "organization_membership",
        membership.id,
        {"organization_id": org.id, "user_id": actor.id, "role": "owner", "status": "active"},
    )
    return organization_response(org)


def list_organizations(db: Session, actor: UserContext) -> list[OrganizationResponse]:
    if actor.is_admin:
        records = db.execute(
            select(OrganizationModel)
            .where(OrganizationModel.deleted_at.is_(None))
            .order_by(OrganizationModel.created_at.desc())
        ).scalars().all()
    else:
        records = db.execute(
            select(OrganizationModel)
            .join(OrganizationMembershipModel, OrganizationMembershipModel.organization_id == OrganizationModel.id)
            .where(OrganizationMembershipModel.user_id == actor.id)
            .where(OrganizationMembershipModel.status == "active")
            .where(OrganizationModel.deleted_at.is_(None))
            .order_by(OrganizationModel.created_at.desc())
        ).scalars().all()
    return [organization_response(record) for record in records]


def get_organization(db: Session, actor: UserContext, organization_id: str) -> OrganizationResponse:
    org = _get_visible_org(db, actor, organization_id)
    return organization_response(org)


def get_organization_seat_status(
    db: Session,
    actor: UserContext,
    organization_id: str,
) -> dict[str, int]:
    org = _get_visible_org(db, actor, organization_id)
    membership = db.execute(
        select(OrganizationMembershipModel)
        .where(OrganizationMembershipModel.organization_id == org.id)
        .where(OrganizationMembershipModel.user_id == actor.id)
        .where(OrganizationMembershipModel.status == "active")
    ).scalars().one_or_none()
    if membership is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    if org.status == "active" or (org.status == "disabled" and membership.role == "owner"):
        return seat_status(db, org.id)
    raise HTTPException(status_code=404, detail="Organization not found")


def update_organization(
    db: Session,
    actor: UserContext,
    organization_id: str,
    request: OrganizationUpdateRequest,
) -> OrganizationResponse:
    org = _get_visible_org(db, actor, organization_id)
    if request.name is None and request.status is None and not can_manage_organization(db, actor, org.id):
        raise HTTPException(status_code=403, detail="Organization admin role required")
    if request.name is not None:
        if not can_manage_organization(db, actor, org.id):
            raise HTTPException(status_code=403, detail="Organization admin role required")
        org.name = request.name
    if request.status is not None:
        if not is_organization_lifecycle_owner(db, actor, org.id):
            raise HTTPException(status_code=403, detail="Organization owner role required for status changes")
        if request.status != "active":
            revoke_jobs_for_authorization_change(
                db,
                organization_id=org.id,
                reason="organization_disabled",
                now=datetime.now(UTC),
            )
        org.status = request.status
    org.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(org)
    record_audit_event(
        db,
        actor.id,
        "organization.updated",
        "organization",
        org.id,
        {"status": org.status},
    )
    return organization_response(org)


def delete_organization(db: Session, actor: UserContext, organization_id: str) -> OrganizationResponse:
    org = _get_visible_org(db, actor, organization_id)
    if not is_organization_lifecycle_owner(db, actor, org.id):
        raise HTTPException(status_code=403, detail="Organization owner role required")
    org.deleted_at = datetime.now(UTC)
    org.status = "disabled"
    revoked_invitation_count = revoke_pending_invitations_for_organization(db, org.id, now=org.deleted_at)
    tombstone_knowledge_for_organization(db, org.id, now=org.deleted_at)
    dispose_jobs_for_organization_deletion(db, org.id, now=org.deleted_at)
    db.commit()
    db.refresh(org)
    if revoked_invitation_count:
        record_audit_event(
            db,
            actor.id,
            "organization.invitations_revoked",
            "organization",
            org.id,
            {"revoked_count": revoked_invitation_count},
        )
    record_audit_event(db, actor.id, "organization.deleted", "organization", org.id)
    return organization_response(org)


def transfer_organization_ownership(
    db: Session,
    actor: UserContext,
    organization_id: str,
    request: OwnershipTransferRequest,
) -> MembershipResponse:
    org = _get_visible_org(db, actor, organization_id)
    if (
        not actor.is_active
        or not actor.auth_enabled
        or not can_transfer_organization_ownership(db, actor, org.id)
    ):
        raise HTTPException(status_code=403, detail="Organization owner role required")
    if not has_recent_authentication(actor):
        raise HTTPException(status_code=403, detail="Recent authentication required")

    org = db.execute(
        select(OrganizationModel).where(OrganizationModel.id == org.id).with_for_update()
    ).scalars().one()
    if org.status != "active" or org.deleted_at is not None:
        raise HTTPException(status_code=409, detail="Organization is unavailable")
    actor_membership = db.execute(
        select(OrganizationMembershipModel)
        .where(OrganizationMembershipModel.organization_id == org.id)
        .where(OrganizationMembershipModel.user_id == actor.id)
        .with_for_update()
    ).scalars().one_or_none()
    if (
        actor_membership is None
        or actor_membership.status != "active"
        or actor_membership.role != "owner"
    ):
        raise HTTPException(status_code=403, detail="Organization owner role required")
    if request.target_membership_id == actor_membership.id:
        raise HTTPException(status_code=409, detail="Ownership transfer target must be another active member")
    target_membership = db.execute(
        select(OrganizationMembershipModel)
        .where(OrganizationMembershipModel.organization_id == org.id)
        .where(OrganizationMembershipModel.id == request.target_membership_id)
        .with_for_update()
    ).scalars().one_or_none()
    if target_membership is None:
        raise HTTPException(status_code=404, detail="Membership not found")
    if target_membership.status != "active":
        raise HTTPException(status_code=409, detail="Ownership transfer target must be active")

    now = datetime.now(UTC)
    target_membership.role = "owner"
    target_membership.updated_at = now
    actor_membership.role = "admin"
    actor_membership.updated_at = now
    db.commit()
    db.refresh(target_membership)
    record_audit_event(
        db,
        actor.id,
        "organization.ownership_transferred",
        "organization",
        org.id,
        {
            "from_membership_id": actor_membership.id,
            "from_user_id": actor_membership.user_id,
            "to_membership_id": target_membership.id,
            "to_user_id": target_membership.user_id,
            "from_role": "owner",
            "to_role": "owner",
        },
    )
    return membership_response(db, target_membership)


def list_members(db: Session, actor: UserContext, organization_id: str) -> list[MembershipResponse]:
    org = _get_visible_org(db, actor, organization_id)
    records = db.execute(
        select(OrganizationMembershipModel)
        .where(OrganizationMembershipModel.organization_id == org.id)
        .order_by(OrganizationMembershipModel.created_at.asc())
    ).scalars().all()
    return [membership_response(db, record) for record in records]


def add_member(
    db: Session,
    actor: UserContext,
    organization_id: str,
    request: MembershipCreateRequest,
) -> MembershipResponse:
    raise HTTPException(status_code=410, detail="Direct member creation is replaced by organization invitations.")


def create_invitation(
    db: Session,
    actor: UserContext,
    organization_id: str,
    request: InvitationCreateRequest,
) -> InvitationTokenResponse:
    org = _get_visible_org(db, actor, organization_id)
    if not can_manage_members(db, actor, org.id): raise HTTPException(status_code=403, detail="Organization owner/admin role required")
    org = db.execute(select(OrganizationModel).where(OrganizationModel.id == org.id).with_for_update()).scalars().one()
    if org.status != "active": raise HTTPException(status_code=409, detail="Organization is not active")
    email, now = normalize_email(request.email), datetime.now(UTC)
    active_member = _membership_for_normalized_email(db, org.id, email, status="active")
    if active_member is not None:
        raise HTTPException(status_code=409, detail="Invitation cannot be created for this organization member")
    legacy_pending = _membership_for_normalized_email(db, org.id, email, status="pending")
    if legacy_pending is not None:
        raise HTTPException(status_code=409, detail="Resolve the legacy pending membership before inviting this email")
    existing = db.execute(select(OrganizationInvitationModel).where(OrganizationInvitationModel.organization_id == org.id, OrganizationInvitationModel.destination_email == email, OrganizationInvitationModel.status == "pending", OrganizationInvitationModel.expires_at > now)).scalars().one_or_none()
    if existing is not None:
        return invitation_token_response(existing)
    seats = seat_status(db, org.id)
    if seats["consumed"] >= seats["limit"]:
        record_audit_event(db, actor.id, "invitation.seat_limit_denied", "organization", org.id, {"limit": seats["limit"], "consumed": seats["consumed"]})
        raise HTTPException(status_code=409, detail="Organization seat limit reached")
    token = token_urlsafe(48); invitation = OrganizationInvitationModel(id=f"inv_{uuid4().hex[:12]}", organization_id=org.id, destination_email=email, role=request.role, invited_by_user_id=actor.id, token_hash=hashlib.sha256(token.encode()).hexdigest(), status="pending", expires_at=now.replace(microsecond=0) + timedelta(days=7), created_at=now, updated_at=now)
    db.add(invitation); db.commit(); record_audit_event(db, actor.id, "invitation.created", "organization_invitation", invitation.id, {"organization_id": org.id, "role": invitation.role})
    return invitation_token_response(invitation, token)


def accept_invitation(db: Session, actor: UserContext, request: InvitationAcceptRequest) -> MembershipResponse:
    token_hash, now = hashlib.sha256(request.token.encode()).hexdigest(), datetime.now(UTC)
    invitation = db.execute(select(OrganizationInvitationModel).where(OrganizationInvitationModel.token_hash == token_hash).with_for_update()).scalars().one_or_none()
    expires_at = _as_utc(invitation.expires_at) if invitation is not None else None
    if invitation is None or invitation.status != "pending" or expires_at <= now: raise HTTPException(status_code=409, detail="Invitation is invalid or expired")
    if normalize_email(actor.email) != invitation.destination_email: raise HTTPException(status_code=403, detail="Invitation destination does not match authenticated user")
    if invitation.role not in INVITABLE_ORGANIZATION_ROLES:
        raise HTTPException(status_code=409, detail="Invitation is invalid")
    org = db.execute(select(OrganizationModel).where(OrganizationModel.id == invitation.organization_id).with_for_update()).scalars().one()
    if org.status != "active" or org.deleted_at is not None: raise HTTPException(status_code=409, detail="Organization is unavailable")
    membership = db.execute(select(OrganizationMembershipModel).where(OrganizationMembershipModel.organization_id == org.id, OrganizationMembershipModel.user_id == actor.id).with_for_update()).scalars().one_or_none()
    if membership is not None and membership.status == "active":
        raise HTTPException(status_code=409, detail="Invitation recipient is already an active organization member")
    if membership is None:
        membership = OrganizationMembershipModel(id=f"mbr_{uuid4().hex[:12]}", organization_id=org.id, user_id=actor.id, role=invitation.role, status="active", created_at=now, updated_at=now); db.add(membership)
    else: membership.role, membership.status, membership.updated_at = invitation.role, "active", now
    invitation.status, invitation.accepted_at, invitation.updated_at = "accepted", now, now
    db.commit(); record_audit_event(db, actor.id, "invitation.accepted", "organization_invitation", invitation.id, {"organization_id": org.id, "role": invitation.role})
    return membership_response(db, membership)


def list_invitations(db: Session, actor: UserContext, organization_id: str) -> list[InvitationResponse]:
    org = _get_visible_org(db, actor, organization_id)
    if not can_manage_members(db, actor, org.id): raise HTTPException(status_code=403, detail="Organization owner/admin role required")
    return [invitation_response(item) for item in db.execute(select(OrganizationInvitationModel).where(OrganizationInvitationModel.organization_id == org.id).order_by(OrganizationInvitationModel.created_at.desc())).scalars()]


def resend_invitation(
    db: Session,
    actor: UserContext,
    organization_id: str,
    invitation_id: str,
) -> InvitationTokenResponse:
    org = _get_visible_org(db, actor, organization_id)
    if not can_manage_members(db, actor, org.id): raise HTTPException(status_code=403, detail="Organization owner/admin role required")
    invitation = db.execute(select(OrganizationInvitationModel).where(OrganizationInvitationModel.id == invitation_id, OrganizationInvitationModel.organization_id == org.id).with_for_update()).scalars().one_or_none()
    expires_at = _as_utc(invitation.expires_at) if invitation is not None else None
    if invitation is None or invitation.status != "pending" or expires_at <= datetime.now(UTC): raise HTTPException(status_code=409, detail="Expired or invalid invitation cannot be resent")
    now, token = datetime.now(UTC), token_urlsafe(48)
    invitation.status, invitation.updated_at = "superseded", now
    replacement = OrganizationInvitationModel(id=f"inv_{uuid4().hex[:12]}", organization_id=org.id, destination_email=invitation.destination_email, role=invitation.role, invited_by_user_id=actor.id, token_hash=hashlib.sha256(token.encode()).hexdigest(), status="pending", expires_at=now + timedelta(days=7), supersedes_id=invitation.id, created_at=now, updated_at=now)
    db.add(replacement); db.commit(); record_audit_event(db, actor.id, "invitation.resent", "organization_invitation", replacement.id, {"organization_id": org.id, "role": replacement.role})
    return invitation_token_response(replacement, token)


def revoke_invitation(db: Session, actor: UserContext, organization_id: str, invitation_id: str) -> InvitationResponse:
    org = _get_visible_org(db, actor, organization_id)
    if not can_manage_members(db, actor, org.id): raise HTTPException(status_code=403, detail="Organization owner/admin role required")
    invitation = db.execute(select(OrganizationInvitationModel).where(OrganizationInvitationModel.id == invitation_id, OrganizationInvitationModel.organization_id == org.id).with_for_update()).scalars().one_or_none()
    if invitation is None: raise HTTPException(status_code=404, detail="Invitation not found")
    if invitation.status == "pending":
        now = datetime.now(UTC); invitation.status, invitation.revoked_at, invitation.updated_at = "revoked", now, now; db.commit(); record_audit_event(db, actor.id, "invitation.revoked", "organization_invitation", invitation.id, {"organization_id": org.id})
    return invitation_response(invitation)


def invitation_response(record: OrganizationInvitationModel) -> InvitationResponse:
    return InvitationResponse(
        id=record.id,
        organization_id=record.organization_id,
        destination_email=record.destination_email,
        role=record.role,
        status=record.status,
        expires_at=record.expires_at,
        created_at=record.created_at,
    )


def _membership_for_normalized_email(
    db: Session,
    organization_id: str,
    email: str,
    *,
    status: str,
) -> OrganizationMembershipModel | None:
    return db.execute(
        select(OrganizationMembershipModel)
        .join(UserModel)
        .where(OrganizationMembershipModel.organization_id == organization_id)
        .where(OrganizationMembershipModel.status == status)
        .where(func.lower(func.trim(UserModel.email)) == email)
    ).scalars().first()


def invitation_token_response(
    record: OrganizationInvitationModel,
    token: str | None = None,
) -> InvitationTokenResponse:
    return InvitationTokenResponse(**invitation_response(record).model_dump(), token=token)


def revoke_pending_invitations_for_organization(
    db: Session,
    organization_id: str,
    *,
    now: datetime,
) -> int:
    return _revoke_pending_invitations(
        db,
        select(OrganizationInvitationModel).where(
            OrganizationInvitationModel.organization_id == organization_id
        ),
        now=now,
    )


def revoke_pending_invitations_for_account_email(
    db: Session,
    email: str,
    *,
    now: datetime,
) -> int:
    return _revoke_pending_invitations(
        db,
        select(OrganizationInvitationModel).where(
            OrganizationInvitationModel.destination_email == normalize_email(email)
        ),
        now=now,
    )


def _revoke_pending_invitations(
    db: Session,
    query,
    *,
    now: datetime,
) -> int:
    invitations = db.execute(
        query.where(OrganizationInvitationModel.status == "pending").with_for_update()
    ).scalars().all()
    for invitation in invitations:
        invitation.status = "revoked"
        invitation.revoked_at = now
        invitation.updated_at = now
    return len(invitations)


def export_organization(
    db: Session,
    actor: UserContext,
    organization_id: str,
) -> OrganizationExportResponse:
    org = _get_visible_org(db, actor, organization_id)
    if org.status == "active":
        authorized = can_administer_organization(db, actor, org.id)
    elif org.status == "disabled":
        authorized = is_organization_lifecycle_owner(db, actor, org.id)
    else:
        authorized = False
    if not authorized:
        raise HTTPException(status_code=403, detail="Organization export role required")

    memberships = db.execute(
        select(OrganizationMembershipModel)
        .where(OrganizationMembershipModel.organization_id == org.id)
        .order_by(OrganizationMembershipModel.created_at, OrganizationMembershipModel.id)
    ).scalars().all()
    invitations = db.execute(
        select(OrganizationInvitationModel)
        .where(OrganizationInvitationModel.organization_id == org.id)
        .order_by(OrganizationInvitationModel.created_at, OrganizationInvitationModel.id)
    ).scalars().all()
    seats = seat_status(db, org.id)
    plan = _organization_export_plan(db, org.id, datetime.now(UTC))
    response = OrganizationExportResponse(
        organization=OrganizationExportOrganization(
            id=org.id,
            name=org.name,
            slug=org.slug,
            status=org.status,
            created_at=org.created_at,
            updated_at=org.updated_at,
        ),
        memberships=[
            OrganizationExportMembership(
                id=item.id,
                user_id=item.user_id,
                email=_member_email(db, item.user_id),
                role=item.role,
                status=item.status,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in memberships
        ],
        invitations=[
            OrganizationExportInvitation(
                id=item.id,
                destination_email=item.destination_email,
                role=item.role,
                status=item.status,
                expires_at=item.expires_at,
                created_at=item.created_at,
                accepted_at=item.accepted_at,
                revoked_at=item.revoked_at,
                supersedes_id=item.supersedes_id,
            )
            for item in invitations
        ],
        seat_projection=OrganizationExportSeatProjection(**seats),
        plan=OrganizationExportPlan(id=plan.id, key=plan.plan_key, version=plan.version),
    )
    record_audit_event(
        db,
        actor.id,
        "organization.exported",
        "organization",
        org.id,
        {"membership_count": len(memberships), "invitation_count": len(invitations)},
    )
    return response


def _member_email(db: Session, user_id: str) -> str:
    user = db.get(UserModel, user_id)
    return user.email if user is not None else ""


def update_member(
    db: Session,
    actor: UserContext,
    organization_id: str,
    membership_id: str,
    request: MembershipUpdateRequest,
) -> MembershipResponse:
    org = _get_visible_org(db, actor, organization_id)
    if not can_manage_members(db, actor, org.id):
        raise HTTPException(status_code=403, detail="Organization owner/admin role required")
    membership = _get_membership(db, org.id, membership_id)
    if request.role == "owner":
        raise HTTPException(status_code=409, detail="Use ownership transfer to change an active owner")
    if (
        membership.role == "owner"
        and (request.role is not None or request.status is not None)
    ):
        record_audit_event(
            db,
            actor.id,
            "organization.member_removal_blocked",
            "organization_membership",
            membership.id,
            {"organization_id": org.id, "reason": "ownership_transfer_required"},
        )
        raise HTTPException(status_code=409, detail="Use ownership transfer to change an active owner")
    if _would_remove_final_owner(db, membership, request.role, request.status):
        record_audit_event(
            db,
            actor.id,
            "organization.member_removal_blocked",
            "organization_membership",
            membership.id,
            {"organization_id": org.id, "reason": "final_active_owner"},
        )
        raise HTTPException(status_code=409, detail="Cannot remove the final active organization owner")
    _validate_generic_membership_update(membership, request)
    next_role = request.role if request.role is not None else membership.role
    next_status = request.status if request.status is not None else membership.status
    if next_status != "active" or next_role not in {"owner", "admin", "member"}:
        revoke_jobs_for_authorization_change(
            db,
            user_id=membership.user_id,
            organization_id=org.id,
            reason="organization_membership_revoked",
            now=datetime.now(UTC),
        )
    if request.role is not None:
        membership.role = request.role
    if request.status is not None:
        membership.status = request.status
    membership.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(membership)
    action = (
        "organization.member_removed"
        if membership.status == "removed"
        else "organization.member_updated"
    )
    record_audit_event(
        db,
        actor.id,
        action,
        "organization_membership",
        membership.id,
        {
            "organization_id": org.id,
            "user_id": membership.user_id,
            "role": membership.role,
            "status": membership.status,
        },
    )
    return membership_response(db, membership)


def remove_member(db: Session, actor: UserContext, organization_id: str, membership_id: str) -> MembershipResponse:
    return update_member(
        db,
        actor,
        organization_id,
        membership_id,
        MembershipUpdateRequest(status="removed"),
    )


def organization_response(record: OrganizationModel) -> OrganizationResponse:
    return OrganizationResponse(
        id=record.id,
        name=record.name,
        slug=record.slug,
        status=record.status,
        created_by_user_id=record.created_by_user_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def membership_response(db: Session, record: OrganizationMembershipModel) -> MembershipResponse:
    user = db.get(UserModel, record.user_id)
    return MembershipResponse(
        id=record.id,
        organization_id=record.organization_id,
        user_id=record.user_id,
        email=user.email if user else "",
        role=record.role,
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _get_visible_org(db: Session, actor: UserContext, organization_id: str) -> OrganizationModel:
    org = db.get(OrganizationModel, organization_id)
    if org is None or org.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Organization not found")
    if actor.is_admin:
        return org
    membership = db.execute(
        select(OrganizationMembershipModel)
        .where(OrganizationMembershipModel.organization_id == organization_id)
        .where(OrganizationMembershipModel.user_id == actor.id)
        .where(OrganizationMembershipModel.status == "active")
    ).scalars().first()
    if membership is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


def _get_membership(db: Session, organization_id: str, membership_id: str) -> OrganizationMembershipModel:
    membership = db.execute(
        select(OrganizationMembershipModel)
        .where(OrganizationMembershipModel.organization_id == organization_id)
        .where(OrganizationMembershipModel.id == membership_id)
        .with_for_update()
    ).scalars().first()
    if membership is None:
        raise HTTPException(status_code=404, detail="Membership not found")
    return membership


def _would_remove_final_owner(
    db: Session,
    membership: OrganizationMembershipModel,
    new_role: str | None,
    new_status: str | None,
) -> bool:
    remains_owner = (new_role or membership.role) == "owner" and (new_status or membership.status) == "active"
    if remains_owner:
        return False
    if membership.role != "owner" or membership.status != "active":
        return False
    active_owner_count = db.execute(
        select(func.count())
        .select_from(OrganizationMembershipModel)
        .where(OrganizationMembershipModel.organization_id == membership.organization_id)
        .where(OrganizationMembershipModel.role == "owner")
        .where(OrganizationMembershipModel.status == "active")
    ).scalar_one()
    return active_owner_count <= 1


def _validate_generic_membership_update(
    membership: OrganizationMembershipModel,
    request: MembershipUpdateRequest,
) -> None:
    """Keep activation and reactivation behind authenticated invitation acceptance."""

    if membership.status == "active":
        if request.status == "pending":
            raise HTTPException(
                status_code=409,
                detail="Use the organization invitation workflow to manage membership activation",
            )
        return

    if request.role is not None:
        raise HTTPException(
            status_code=409,
            detail="Use the organization invitation workflow to change a non-active membership",
        )
    if request.status == "active":
        raise HTTPException(
            status_code=409,
            detail="Use the organization invitation workflow to activate a membership",
        )
    if membership.status == "removed" and request.status == "pending":
        raise HTTPException(
            status_code=409,
            detail="Use the organization invitation workflow to manage membership activation",
        )


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or f"org-{uuid4().hex[:8]}"
