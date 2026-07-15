from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.schemas import AuditEventResponse, UserContext, UserResponse, UserRole
from app.auth.security import hash_token, redact_sensitive
from app.core.config import get_settings
from app.models.access_audit_event import AccessAuditEventModel
from app.models.user import UserModel


def ensure_bootstrap_admin(db: Session) -> UserModel | None:
    settings = get_settings()
    if not settings.admin_email:
        return None
    existing = db.execute(select(UserModel).where(UserModel.email == settings.admin_email)).scalars().first()
    token = settings.admin_bootstrap_token or settings.admin_password
    token_hash = hash_token(token) if token else None
    if existing is None:
        existing = UserModel(
            id=f"user_{uuid4().hex[:12]}",
            email=settings.admin_email,
            role="admin",
            is_active=True,
            access_token_hash=token_hash,
        )
        db.add(existing)
    elif token_hash and existing.access_token_hash != token_hash:
        existing.access_token_hash = token_hash
        existing.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(existing)
    return existing


def create_user(
    db: Session,
    email: str,
    role: UserRole = "common",
    token: str | None = None,
    is_active: bool = True,
) -> UserModel:
    record = UserModel(
        id=f"user_{uuid4().hex[:12]}",
        email=email,
        role=role,
        is_active=is_active,
        access_token_hash=hash_token(token) if token else None,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def user_from_token(db: Session, token: str) -> UserModel | None:
    token_hash = hash_token(token)
    return db.execute(select(UserModel).where(UserModel.access_token_hash == token_hash)).scalars().first()


def user_context(record: UserModel, auth_enabled: bool = True) -> UserContext:
    return UserContext(
        id=record.id,
        email=record.email,
        role=record.role,
        is_active=record.is_active,
        auth_enabled=auth_enabled,
    )


def demo_admin_context() -> UserContext:
    """Local-development identity used only when auth and public demo are disabled."""

    return UserContext(
        id="demo_admin",
        email="demo-admin@example.local",
        role="admin",
        is_active=True,
        auth_enabled=False,
    )


def demo_common_context() -> UserContext:
    """Read-only identity for unauthenticated hosted portfolio visitors."""

    return UserContext(
        id="public_demo_user",
        email="public-demo@example.local",
        role="common",
        is_active=True,
        auth_enabled=False,
    )


def user_response(record: UserModel) -> UserResponse:
    return UserResponse(
        id=record.id,
        email=record.email,
        role=record.role,
        is_active=record.is_active,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def record_audit_event(
    db: Session,
    actor_user_id: str | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    metadata: dict | None = None,
) -> AccessAuditEventModel:
    event = AccessAuditEventModel(
        id=f"audit_{uuid4().hex[:12]}",
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata_json=redact_sensitive(metadata or {}),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def audit_event_response(record: AccessAuditEventModel) -> AuditEventResponse:
    return AuditEventResponse(
        id=record.id,
        actor_user_id=record.actor_user_id,
        action=record.action,
        resource_type=record.resource_type,
        resource_id=record.resource_id,
        metadata_json=record.metadata_json,
        created_at=record.created_at,
    )
