from __future__ import annotations

from datetime import UTC, datetime
from secrets import token_urlsafe
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.schemas import UserContext
from app.auth.security import constant_time_equal, hash_worker_token
from app.auth.service import record_audit_event
from app.jobs.constants import SUPPORTED_JOB_TYPES
from app.jobs.schemas import (
    WorkerCredentialCreateRequest,
    WorkerCredentialIssuedResponse,
    WorkerCredentialResponse,
    WorkerRegistrationRequest,
    WorkerResponse,
)
from app.models.worker import WorkerCredentialModel, WorkerModel


def register_worker(
    db: Session,
    actor: UserContext,
    request: WorkerRegistrationRequest,
) -> WorkerResponse:
    _require_platform_admin(actor)
    existing = db.execute(select(WorkerModel).where(WorkerModel.name == request.name)).scalars().first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Worker name already exists")
    now = datetime.now(UTC)
    worker = WorkerModel(
        id=f"worker_{uuid4().hex[:12]}",
        name=request.name,
        status="active",
        protocol_version=request.protocol_version,
        software_version=request.software_version,
        capabilities_json=request.capabilities_json,
        allowed_job_types=request.allowed_job_types,
        organization_id=request.organization_id,
        max_concurrency=request.max_concurrency,
        created_at=now,
        updated_at=now,
    )
    db.add(worker)
    db.flush()
    record_audit_event(
        db,
        actor.id,
        "worker.registered",
        "worker",
        worker.id,
        {"name": worker.name, "allowed_job_types": worker.allowed_job_types},
    )
    return worker_response(worker)


def list_workers(db: Session) -> list[WorkerResponse]:
    records = db.execute(select(WorkerModel).order_by(WorkerModel.created_at.desc())).scalars().all()
    return [worker_response(record) for record in records]


def disable_worker(db: Session, actor: UserContext, worker_id: str) -> WorkerResponse:
    _require_platform_admin(actor)
    worker = _worker_or_404(db, worker_id)
    now = datetime.now(UTC)
    worker.status = "disabled"
    worker.disabled_at = now
    worker.updated_at = now
    db.flush()
    record_audit_event(db, actor.id, "worker.disabled", "worker", worker.id)
    return worker_response(worker)


def issue_worker_credential(
    db: Session,
    actor: UserContext,
    worker_id: str,
    request: WorkerCredentialCreateRequest,
    *,
    rotated_from_id: str | None = None,
) -> WorkerCredentialIssuedResponse:
    _require_platform_admin(actor)
    worker = _worker_or_404(db, worker_id)
    if worker.status != "active":
        raise HTTPException(status_code=409, detail="Worker is not active")
    scopes = request.allowed_job_types or list(worker.allowed_job_types)
    if not set(scopes).issubset(set(worker.allowed_job_types)):
        raise HTTPException(status_code=422, detail="Credential scope exceeds worker job-type scope")
    if request.expires_at is not None and _utc(request.expires_at) <= datetime.now(UTC):
        raise HTTPException(status_code=422, detail="Credential expiration must be in the future")

    token, prefix = _new_worker_token(db)
    credential = WorkerCredentialModel(
        id=f"workercred_{uuid4().hex[:12]}",
        worker_id=worker.id,
        token_prefix=prefix,
        token_hash=hash_worker_token(token),
        allowed_job_types=scopes,
        status="active",
        expires_at=request.expires_at,
        rotated_from_id=rotated_from_id,
        created_by_user_id=actor.id,
    )
    db.add(credential)
    db.flush()
    record_audit_event(
        db,
        actor.id,
        "worker_credential.issued",
        "worker_credential",
        credential.id,
        {"worker_id": worker.id, "allowed_job_types": scopes, "expires_at": credential.expires_at},
    )
    return WorkerCredentialIssuedResponse(credential=credential_response(credential), token=token)


def list_worker_credentials(db: Session, worker_id: str) -> list[WorkerCredentialResponse]:
    _worker_or_404(db, worker_id)
    records = db.execute(
        select(WorkerCredentialModel)
        .where(WorkerCredentialModel.worker_id == worker_id)
        .order_by(WorkerCredentialModel.created_at.desc())
    ).scalars().all()
    return [credential_response(record) for record in records]


def rotate_worker_credential(
    db: Session,
    actor: UserContext,
    credential_id: str,
    request: WorkerCredentialCreateRequest,
    *,
    revoke_previous: bool = False,
) -> WorkerCredentialIssuedResponse:
    _require_platform_admin(actor)
    previous = _credential_or_404(db, credential_id)
    issued = issue_worker_credential(
        db,
        actor,
        previous.worker_id,
        request,
        rotated_from_id=previous.id,
    )
    if revoke_previous:
        _revoke_credential(db, actor, previous)
    record_audit_event(
        db,
        actor.id,
        "worker_credential.rotated",
        "worker_credential",
        issued.credential.id,
        {"worker_id": previous.worker_id, "rotated_from_id": previous.id, "previous_revoked": revoke_previous},
    )
    return issued


def revoke_worker_credential(
    db: Session,
    actor: UserContext,
    credential_id: str,
) -> WorkerCredentialResponse:
    _require_platform_admin(actor)
    credential = _credential_or_404(db, credential_id)
    _revoke_credential(db, actor, credential)
    return credential_response(credential)


def verify_worker_credential(
    db: Session,
    token: str,
    *,
    required_job_type: str | None = None,
) -> WorkerCredentialModel | None:
    if not token.startswith("wrk_") or len(token) < 24:
        return None
    prefix = token[:24]
    credential = db.execute(
        select(WorkerCredentialModel).where(WorkerCredentialModel.token_prefix == prefix)
    ).scalars().one_or_none()
    if credential is None or not constant_time_equal(credential.token_hash, hash_worker_token(token)):
        return None
    now = datetime.now(UTC)
    if credential.status != "active" or credential.revoked_at is not None:
        return None
    if credential.expires_at is not None and _utc(credential.expires_at) <= now:
        credential.status = "expired"
        credential.revoked_at = now
        db.flush()
        return None
    worker = db.get(WorkerModel, credential.worker_id)
    if worker is None or worker.status not in {"active", "stale"}:
        return None
    if required_job_type is not None and (
        required_job_type not in SUPPORTED_JOB_TYPES or required_job_type not in credential.allowed_job_types
    ):
        return None
    credential.last_used_at = now
    if worker.status == "stale":
        worker.status = "active"
    worker.last_seen_at = now
    worker.updated_at = now
    db.flush()
    return credential


def worker_response(record: WorkerModel) -> WorkerResponse:
    return WorkerResponse(
        id=record.id,
        name=record.name,
        status=record.status,
        protocol_version=record.protocol_version,
        software_version=record.software_version,
        capabilities_json=record.capabilities_json,
        allowed_job_types=record.allowed_job_types,
        organization_id=record.organization_id,
        max_concurrency=record.max_concurrency,
        last_seen_at=record.last_seen_at,
        disabled_at=record.disabled_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def credential_response(record: WorkerCredentialModel) -> WorkerCredentialResponse:
    return WorkerCredentialResponse(
        id=record.id,
        worker_id=record.worker_id,
        token_prefix=record.token_prefix,
        allowed_job_types=record.allowed_job_types,
        status=record.status,
        expires_at=record.expires_at,
        last_used_at=record.last_used_at,
        rotated_from_id=record.rotated_from_id,
        revoked_at=record.revoked_at,
        created_by_user_id=record.created_by_user_id,
        created_at=record.created_at,
    )


def _revoke_credential(db: Session, actor: UserContext, credential: WorkerCredentialModel) -> None:
    if credential.status != "revoked":
        credential.status = "revoked"
        credential.revoked_at = datetime.now(UTC)
        db.flush()
        record_audit_event(
            db,
            actor.id,
            "worker_credential.revoked",
            "worker_credential",
            credential.id,
            {"worker_id": credential.worker_id},
        )


def _new_worker_token(db: Session) -> tuple[str, str]:
    for _ in range(4):
        token = f"wrk_{token_urlsafe(32)}"
        prefix = token[:24]
        collision = db.execute(
            select(WorkerCredentialModel.id).where(WorkerCredentialModel.token_prefix == prefix)
        ).first()
        if collision is None:
            return token, prefix
    raise RuntimeError("Could not allocate a unique worker credential prefix")


def _worker_or_404(db: Session, worker_id: str) -> WorkerModel:
    worker = db.get(WorkerModel, worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker not found")
    return worker


def _credential_or_404(db: Session, credential_id: str) -> WorkerCredentialModel:
    credential = db.get(WorkerCredentialModel, credential_id)
    if credential is None:
        raise HTTPException(status_code=404, detail="Worker credential not found")
    return credential


def _require_platform_admin(actor: UserContext) -> None:
    if not actor.is_admin:
        raise HTTPException(status_code=403, detail="Platform administrator role required")


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
