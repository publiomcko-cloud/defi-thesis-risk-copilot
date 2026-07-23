from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.schemas import UserContext
from app.models.organization import OrganizationMembershipModel, OrganizationModel


class ScopedResource(Protocol):
    owner_user_id: str | None
    organization_id: str | None
    visibility: str
    anonymous_session_id: str | None
    deleted_at: datetime | None
    expires_at: datetime | None


READ_ORG_ROLES = {"owner", "admin", "member", "viewer"}
WRITE_ORG_ROLES = {"owner", "admin", "member"}
MANAGE_ORG_ROLES = {"owner", "admin"}


def can_access_admin(user: UserContext) -> bool:
    return user.is_admin


def can_read_resource(user: UserContext | None, resource: ScopedResource, db: Session) -> bool:
    if _deleted_or_expired(resource):
        return False
    if resource.visibility == "public_demo":
        return True
    if user is None:
        return False
    if user.is_admin and not user.auth_enabled:
        return True
    if resource.owner_user_id and resource.owner_user_id == user.id:
        return True
    if resource.anonymous_session_id and resource.anonymous_session_id == user.anonymous_session_id:
        return True
    if resource.visibility == "organization" and resource.organization_id:
        return has_org_role(db, user.id, resource.organization_id, READ_ORG_ROLES)
    return user.is_admin and resource.visibility != "private"


def can_update_resource(user: UserContext, resource: ScopedResource, db: Session) -> bool:
    if _deleted_or_expired(resource) or resource.visibility == "public_demo":
        return False
    if resource.owner_user_id and resource.owner_user_id == user.id:
        return True
    if resource.anonymous_session_id and resource.anonymous_session_id == user.anonymous_session_id:
        return True
    if resource.visibility == "organization" and resource.organization_id:
        return has_org_role(db, user.id, resource.organization_id, WRITE_ORG_ROLES)
    return False


def can_manage_organization(db: Session, user: UserContext, organization_id: str) -> bool:
    return user.is_admin or has_org_role(db, user.id, organization_id, MANAGE_ORG_ROLES)


def can_manage_members(db: Session, user: UserContext, organization_id: str) -> bool:
    return can_manage_organization(db, user, organization_id)


def can_manage_knowledge_base(db: Session, user: UserContext, organization_id: str | None) -> bool:
    if organization_id is None:
        return user.is_admin
    return has_org_role(db, user.id, organization_id, MANAGE_ORG_ROLES)


def has_org_role(
    db: Session,
    user_id: str,
    organization_id: str,
    allowed_roles: set[str],
) -> bool:
    membership = db.execute(
        select(OrganizationMembershipModel)
        .join(OrganizationModel, OrganizationModel.id == OrganizationMembershipModel.organization_id)
        .where(OrganizationMembershipModel.user_id == user_id)
        .where(OrganizationMembershipModel.organization_id == organization_id)
        .where(OrganizationMembershipModel.status == "active")
        .where(OrganizationModel.status == "active")
        .where(OrganizationModel.deleted_at.is_(None))
    ).scalars().first()
    return membership is not None and membership.role in allowed_roles


def _deleted_or_expired(resource: ScopedResource) -> bool:
    now = datetime.now(UTC)
    expires_at = resource.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return bool(resource.deleted_at or (expires_at and expires_at <= now))
