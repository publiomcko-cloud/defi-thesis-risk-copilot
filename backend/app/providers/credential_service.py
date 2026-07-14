import base64
import hashlib
from datetime import UTC, datetime
from uuid import uuid4

from cryptography.fernet import Fernet
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.schemas import UserContext
from app.auth.service import record_audit_event
from app.core.config import get_settings
from app.models.api_credential import ApiCredentialModel
from app.providers.schemas import (
    ProviderCredentialCreateRequest,
    ProviderCredentialMetadata,
    ProviderCredentialUpdateRequest,
)


def create_provider_credential(
    request: ProviderCredentialCreateRequest,
    db: Session,
    actor: UserContext,
) -> ProviderCredentialMetadata:
    encrypted = encrypt_secret(request.secret)
    record = ApiCredentialModel(
        id=f"cred_{uuid4().hex[:12]}",
        provider=request.provider,
        name=request.name,
        secret_encrypted=encrypted,
        secret_last4=request.secret[-4:],
        enabled=request.enabled,
        created_by=actor.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    record_audit_event(
        db,
        actor.id,
        "credential.created",
        "api_credential",
        record.id,
        {"provider": record.provider, "name": record.name, "secret_last4": record.secret_last4},
    )
    return _metadata(record)


def list_provider_credentials(db: Session) -> list[ProviderCredentialMetadata]:
    records = db.execute(select(ApiCredentialModel).order_by(ApiCredentialModel.created_at.desc())).scalars().all()
    return [_metadata(record) for record in records]


def get_enabled_credential_secret(
    db: Session,
    provider: str,
    name: str,
) -> str | None:
    record = db.execute(
        select(ApiCredentialModel).where(
            ApiCredentialModel.provider == provider,
            ApiCredentialModel.name == name,
            ApiCredentialModel.enabled.is_(True),
        )
    ).scalars().first()
    if record is None:
        return None
    record.last_used_at = datetime.now(UTC)
    db.commit()
    return decrypt_secret(record.secret_encrypted)


def update_provider_credential(
    credential_id: str,
    request: ProviderCredentialUpdateRequest,
    db: Session,
    actor: UserContext,
) -> ProviderCredentialMetadata:
    record = db.get(ApiCredentialModel, credential_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Provider credential not found")
    if request.name is not None:
        record.name = request.name
    if request.secret is not None:
        record.secret_encrypted = encrypt_secret(request.secret)
        record.secret_last4 = request.secret[-4:]
    if request.enabled is not None:
        record.enabled = request.enabled
    record.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(record)
    record_audit_event(
        db,
        actor.id,
        "credential.updated",
        "api_credential",
        record.id,
        {"provider": record.provider, "enabled": record.enabled, "secret_last4": record.secret_last4},
    )
    return _metadata(record)


def disable_provider_credential(
    credential_id: str,
    db: Session,
    actor: UserContext,
) -> ProviderCredentialMetadata:
    record = db.get(ApiCredentialModel, credential_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Provider credential not found")
    record.enabled = False
    record.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(record)
    record_audit_event(
        db,
        actor.id,
        "credential.disabled",
        "api_credential",
        record.id,
        {"provider": record.provider, "enabled": record.enabled},
    )
    return _metadata(record)


def encrypt_secret(secret: str) -> str:
    fernet = _fernet()
    return fernet.encrypt(secret.encode("utf-8")).decode("ascii")


def decrypt_secret(secret_encrypted: str) -> str:
    fernet = _fernet()
    return fernet.decrypt(secret_encrypted.encode("ascii")).decode("utf-8")


def _fernet() -> Fernet:
    key = get_settings().credential_encryption_key
    if not key:
        raise HTTPException(
            status_code=500,
            detail="CREDENTIAL_ENCRYPTION_KEY is required for database-backed secret storage",
        )
    derived_key = base64.urlsafe_b64encode(hashlib.sha256(key.encode("utf-8")).digest())
    return Fernet(derived_key)


def _metadata(record: ApiCredentialModel) -> ProviderCredentialMetadata:
    return ProviderCredentialMetadata(
        id=record.id,
        provider=record.provider,
        name=record.name,
        secret_last4=record.secret_last4,
        enabled=record.enabled,
        created_by=record.created_by,
        created_at=record.created_at,
        updated_at=record.updated_at,
        last_used_at=record.last_used_at,
    )
