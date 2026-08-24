from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.schemas import UserContext
from app.core.config import get_settings
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


def can_use_platform_admin_emergency_path(user: UserContext) -> bool:
    return user.is_admin


def can_administer_organization(db: Session, user: UserContext, organization_id: str) -> bool:
    return has_org_role(db, user.id, organization_id, MANAGE_ORG_ROLES)


def can_manage_organization(db: Session, user: UserContext, organization_id: str) -> bool:
    return can_use_platform_admin_emergency_path(user) or can_administer_organization(db, user, organization_id)


def can_manage_members(db: Session, user: UserContext, organization_id: str) -> bool:
    return can_manage_organization(db, user, organization_id)


def is_organization_owner(db: Session, user: UserContext, organization_id: str) -> bool:
    return has_org_role(db, user.id, organization_id, {"owner"})


def can_transfer_organization_ownership(db: Session, user: UserContext, organization_id: str) -> bool:
    return is_organization_owner(db, user, organization_id)


def has_recent_authentication(user: UserContext, *, now: datetime | None = None) -> bool:
    settings = get_settings()
    authenticated_at = user.authenticated_at
    if authenticated_at is None:
        return False
    if user.auth_provider == "legacy_local":
        if settings.app_env == "production" or not settings.ownership_transfer_legacy_local_recent_auth_enabled:
            return False
    elif user.auth_provider != "supabase":
        return False
    authenticated_at = authenticated_at.replace(tzinfo=UTC) if authenticated_at.tzinfo is None else authenticated_at
    current_time = now or datetime.now(UTC)
    maximum_age = timedelta(seconds=settings.ownership_transfer_recent_auth_seconds)
    return authenticated_at <= current_time and authenticated_at >= current_time - maximum_age


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
