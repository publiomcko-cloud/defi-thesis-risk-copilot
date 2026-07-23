from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.policies import can_manage_members, can_manage_organization
from app.auth.schemas import UserContext
from app.auth.service import normalize_email, record_audit_event
from app.models.organization import OrganizationMembershipModel, OrganizationModel
from app.models.user import UserModel
from app.organizations.schemas import (
    MembershipCreateRequest,
    MembershipResponse,
    MembershipUpdateRequest,
    OrganizationCreateRequest,
    OrganizationResponse,
    OrganizationUpdateRequest,
)


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
    db.add_all([org, membership])
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


def update_organization(
    db: Session,
    actor: UserContext,
    organization_id: str,
    request: OrganizationUpdateRequest,
) -> OrganizationResponse:
    org = _get_visible_org(db, actor, organization_id)
    if not can_manage_organization(db, actor, org.id):
        raise HTTPException(status_code=403, detail="Organization admin role required")
    if request.name is not None:
        org.name = request.name
    if request.status is not None:
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
    if not can_manage_organization(db, actor, org.id):
        raise HTTPException(status_code=403, detail="Organization admin role required")
    org.deleted_at = datetime.now(UTC)
    org.status = "disabled"
    db.commit()
    db.refresh(org)
    record_audit_event(db, actor.id, "organization.deleted", "organization", org.id)
    return organization_response(org)


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
    org = _get_visible_org(db, actor, organization_id)
    if not can_manage_members(db, actor, org.id):
        raise HTTPException(status_code=403, detail="Organization owner/admin role required")
    email = normalize_email(request.email)
    user = db.execute(select(UserModel).where(UserModel.email == email)).scalars().first()
    pending = False
    if user is None:
        user = UserModel(
            id=f"user_{uuid4().hex[:12]}",
            email=email,
            role="common",
            platform_role="user",
            account_status="pending_invitation",
            plan="free",
            auth_provider="pending_invitation",
            is_active=False,
        )
        db.add(user)
        db.flush()
        pending = True
    existing = db.execute(
        select(OrganizationMembershipModel)
        .where(OrganizationMembershipModel.organization_id == org.id)
        .where(OrganizationMembershipModel.user_id == user.id)
    ).scalars().first()
    now = datetime.now(UTC)
    if existing is None:
        existing = OrganizationMembershipModel(
            id=f"mbr_{uuid4().hex[:12]}",
            organization_id=org.id,
            user_id=user.id,
            role=request.role,
            status="pending" if pending else "active",
            created_at=now,
            updated_at=now,
        )
        db.add(existing)
    else:
        existing.role = request.role
        existing.status = "pending" if pending else "active"
        existing.updated_at = now
    db.commit()
    db.refresh(existing)
    record_audit_event(
        db,
        actor.id,
        "organization.member_added",
        "organization_membership",
        existing.id,
        {
            "organization_id": org.id,
            "user_id": existing.user_id,
            "role": existing.role,
            "status": existing.status,
        },
    )
    return membership_response(db, existing)


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


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or f"org-{uuid4().hex[:8]}"
