from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.schemas import AuditEventResponse, UserContext, UserResponse, UserRole
from app.auth.security import hash_token, sanitize_audit_metadata
from app.auth.supabase import SupabaseClaims
from app.core.config import get_settings
from app.models.access_audit_event import AccessAuditEventModel
from app.models.consent_record import ConsentRecordModel
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
            platform_role="admin",
            account_status="active",
            auth_provider="legacy_local",
            email_verified_at=datetime.now(UTC),
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
        email=normalize_email(email),
        role=role,
        platform_role="admin" if role == "admin" else "user",
        account_status="active" if is_active else "inactive",
        auth_provider="legacy_local",
        email_verified_at=datetime.now(UTC) if is_active else None,
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


def sync_supabase_user(db: Session, claims: SupabaseClaims) -> UserModel:
    settings = get_settings()
    now = datetime.now(UTC)
    record = db.execute(
        select(UserModel).where(UserModel.auth_subject == claims.subject)
    ).scalars().first()
    normalized_email = normalize_email(claims.email)
    verified_at = now if claims.email_verified else None
    if record is None:
        record = db.execute(select(UserModel).where(UserModel.email == normalized_email)).scalars().first()
        if record is not None and record.auth_provider != "pending_invitation":
            raise ValueError("Email is already linked to a different local account")
    if record is None:
        record = UserModel(
            id=f"user_{uuid4().hex[:12]}",
            email=normalized_email,
            role="common",
            platform_role="user",
            account_status="active",
            plan=settings.default_user_plan,
            auth_provider="supabase",
            auth_subject=claims.subject,
            email_verified_at=verified_at,
            is_active=True,
            last_login_at=now,
        )
        db.add(record)
    else:
        record.email = normalized_email
        record.auth_provider = "supabase"
        record.auth_subject = claims.subject
        record.is_active = True
        record.account_status = "active"
        if verified_at is not None:
            record.email_verified_at = verified_at
        record.last_login_at = now
        record.updated_at = now
    db.commit()
    _record_signup_consents(db, record, claims.raw)
    db.refresh(record)
    return record


def user_context(record: UserModel, auth_enabled: bool = True) -> UserContext:
    return UserContext(
        id=record.id,
        email=record.email,
        role=record.role,
        platform_role=record.platform_role,
        plan=record.plan,
        is_active=record.is_active and record.account_status == "active" and record.deleted_at is None,
        auth_enabled=auth_enabled,
        auth_provider=record.auth_provider,
        auth_subject=record.auth_subject,
        email_verified=record.email_verified_at is not None,
    )


def demo_admin_context() -> UserContext:
    """Local-development identity used only when auth and public demo are disabled."""

    return UserContext(
        id="demo_admin",
        email="demo-admin@example.local",
        role="admin",
        platform_role="admin",
        plan="admin",
        is_active=True,
        auth_enabled=False,
        email_verified=True,
    )


def demo_common_context() -> UserContext:
    """Read-only identity for unauthenticated hosted portfolio visitors."""

    return UserContext(
        id="public_demo_user",
        email="public-demo@example.local",
        role="common",
        platform_role="user",
        plan="anonymous",
        is_active=True,
        auth_enabled=False,
        email_verified=True,
    )


def user_response(record: UserModel) -> UserResponse:
    return UserResponse(
        id=record.id,
        email=record.email,
        role=record.role,
        platform_role=record.platform_role,
        account_status=record.account_status,
        plan=record.plan,
        is_active=record.is_active,
        auth_provider=record.auth_provider,
        email_verified_at=record.email_verified_at,
        last_login_at=record.last_login_at,
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
        metadata_json=sanitize_audit_metadata(metadata or {}),
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


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _record_signup_consents(db: Session, record: UserModel, claims: dict) -> None:
    settings = get_settings()
    metadata = claims.get("user_metadata") if isinstance(claims.get("user_metadata"), dict) else {}
    for document_type, (keys, version) in {
        "terms": (("accepted_terms", "accepted_terms_version"), settings.current_terms_version),
        "privacy": (("accepted_privacy", "accepted_privacy_version"), settings.current_privacy_version),
    }.items():
        accepted = any(bool(metadata.get(key)) for key in keys)
        if not accepted or not version:
            continue
        existing = db.execute(
            select(ConsentRecordModel)
            .where(ConsentRecordModel.user_id == record.id)
            .where(ConsentRecordModel.document_type == document_type)
            .where(ConsentRecordModel.document_version == version)
            .where(ConsentRecordModel.withdrawn_at.is_(None))
        ).scalars().first()
        if existing is None:
            consent = ConsentRecordModel(
                id=f"consent_{uuid4().hex[:12]}",
                user_id=record.id,
                document_type=document_type,
                document_version=version,
                accepted_at=datetime.now(UTC),
                metadata_json={"source": "supabase_signup_metadata", "version_source": "server_config"},
            )
            db.add(consent)
            db.commit()
            record_audit_event(
                db,
                record.id,
                "consent.accepted",
                "consent_record",
                consent.id,
                {"document_type": document_type, "document_version": version, "source": "signup"},
            )
