from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_authenticated_user, require_user
from app.auth.schemas import (
    AccountDeleteRequest,
    AccountDeleteResponse,
    AccountExportResponse,
    AccountResponse,
    AuthLogoutResponse,
    MfaAuditEventRequest,
    UserContext,
)
from app.auth.security import constant_time_equal
from app.auth.service import record_audit_event, user_response
from app.db.session import get_db
from app.jobs.lifecycle import dispose_jobs_for_account_deletion
from app.models.artifact import ArtifactModel
from app.models.access_audit_event import AccessAuditEventModel
from app.models.alert_event import AlertEventModel
from app.models.consent_record import ConsentRecordModel
from app.models.organization import OrganizationMembershipModel
from app.models.job import JobEventModel, JobModel
from app.models.report import ReportModel
from app.models.saved_thesis import SavedThesisModel
from app.models.user import UserModel
from app.models.watchlist_item import WatchlistItemModel
from app.quotas.service import usage_summary
from app.core.config import get_settings

router = APIRouter(tags=["auth"])


@router.get("/auth/me", response_model=UserContext)
def read_current_user(current_user: UserContext = Depends(require_user)) -> UserContext:
    return current_user


@router.post("/auth/logout", response_model=AuthLogoutResponse)
def logout(response: Response) -> AuthLogoutResponse:
    settings = get_settings()
    response.delete_cookie(settings.session_cookie_name)
    response.delete_cookie(settings.anonymous_session_cookie_name)
    return AuthLogoutResponse(status="logged_out")


@router.get("/account", response_model=AccountResponse)
def get_account(
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(require_authenticated_user),
) -> AccountResponse:
    user = _current_user_record(db, current_user)
    memberships = db.execute(
        select(OrganizationMembershipModel).where(OrganizationMembershipModel.user_id == current_user.id)
    ).scalars().all()
    return AccountResponse(
        user=user_response(user),
        memberships=[
            {
                "id": item.id,
                "organization_id": item.organization_id,
                "role": item.role,
                "status": item.status,
            }
            for item in memberships
        ],
    )


@router.get("/account/export", response_model=AccountExportResponse)
def export_account(
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(require_authenticated_user),
) -> AccountExportResponse:
    user = _current_user_record(db, current_user)
    reports = db.execute(
        select(ReportModel).where(ReportModel.owner_user_id == current_user.id)
    ).scalars().all()
    jobs = db.execute(
        select(JobModel)
        .where(JobModel.owner_user_id == current_user.id)
        .where(JobModel.deleted_at.is_(None))
        .order_by(JobModel.created_at.desc())
    ).scalars().all()
    job_ids = [item.id for item in jobs]
    job_events = (
        db.execute(
            select(JobEventModel)
            .where(JobEventModel.job_id.in_(job_ids))
            .order_by(JobEventModel.job_id, JobEventModel.sequence_number)
        ).scalars().all()
        if job_ids
        else []
    )
    artifacts = (
        db.execute(
            select(ArtifactModel)
            .where(ArtifactModel.owner_user_id == current_user.id)
            .where(ArtifactModel.deleted_at.is_(None))
            .order_by(ArtifactModel.created_at.desc())
        ).scalars().all()
    )
    theses = db.execute(
        select(SavedThesisModel).where(SavedThesisModel.owner_user_id == current_user.id)
    ).scalars().all()
    watchlists = db.execute(
        select(WatchlistItemModel).where(WatchlistItemModel.owner_user_id == current_user.id)
    ).scalars().all()
    alerts = []
    for item in watchlists:
        alerts.extend(
            db.execute(
                select(AlertEventModel).where(AlertEventModel.watchlist_item_id == item.id)
            ).scalars().all()
        )
    consents = db.execute(
        select(ConsentRecordModel).where(ConsentRecordModel.user_id == current_user.id)
    ).scalars().all()
    audits = db.execute(
        select(AccessAuditEventModel)
        .where(AccessAuditEventModel.actor_user_id == current_user.id)
        .limit(100)
    ).scalars().all()
    memberships = db.execute(
        select(OrganizationMembershipModel).where(OrganizationMembershipModel.user_id == current_user.id)
    ).scalars().all()
    response = AccountExportResponse(
        exported_at=datetime.now(UTC),
        profile=user_response(user).model_dump(mode="json"),
        memberships=[
            {"organization_id": item.organization_id, "role": item.role, "status": item.status}
            for item in memberships
        ],
        saved_theses=[
            {
                "id": item.id,
                "title": item.title,
                "strategy_text": item.strategy_text,
                "protocols": item.protocols,
                "visibility": item.visibility,
            }
            for item in theses
        ],
        reports=[
            {"id": item.id, "title": item.title, "risk_rating": item.risk_rating, "created_at": item.created_at}
            for item in reports
        ],
        watchlists=[
            {"id": item.id, "title": item.title, "rules": item.rules_json, "snapshot": item.snapshot_json}
            for item in watchlists
        ],
        alerts=[
            {"id": item.id, "watchlist_item_id": item.watchlist_item_id, "alert_type": item.alert_type, "status": item.status}
            for item in alerts
        ],
        jobs=[
            {
                "id": item.id,
                "job_type": item.job_type,
                "status": item.status,
                "attempt_count": item.attempt_count,
                "max_attempts": item.max_attempts,
                "progress_percent": item.progress_percent,
                "result_resource_type": item.result_resource_type,
                "result_resource_id": item.result_resource_id,
                "error_code": item.error_code,
                "error_summary": item.error_summary,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
            for item in jobs
        ],
        job_events=[
            {
                "job_id": item.job_id,
                "sequence_number": item.sequence_number,
                "event_type": item.event_type,
                "message": item.message,
                "created_at": item.created_at,
            }
            for item in job_events
        ],
        artifacts=[
            {
                "id": item.id,
                "job_id": item.job_id,
                "artifact_type": item.artifact_type,
                "status": item.status,
                "resource_type": item.resource_type,
                "resource_id": item.resource_id,
                "content_type": item.content_type,
                "size_bytes": item.size_bytes,
                "created_at": item.created_at,
            }
            for item in artifacts
        ],
        consents=[
            {
                "document_type": item.document_type,
                "document_version": item.document_version,
                "accepted_at": item.accepted_at,
                "withdrawn_at": item.withdrawn_at,
            }
            for item in consents
        ],
        audit_events=[
            {
                "action": item.action,
                "resource_type": item.resource_type,
                "resource_id": item.resource_id,
                "created_at": item.created_at,
            }
            for item in audits
        ],
    )
    record_audit_event(db, current_user.id, "account.exported", "user", current_user.id)
    return response


@router.delete("/account", response_model=AccountDeleteResponse)
def delete_account(
    request: AccountDeleteRequest,
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(require_authenticated_user),
) -> AccountDeleteResponse:
    user = _current_user_record(db, current_user)
    active_owner_memberships = db.execute(
        select(OrganizationMembershipModel)
        .where(OrganizationMembershipModel.user_id == current_user.id)
        .where(OrganizationMembershipModel.role == "owner")
        .where(OrganizationMembershipModel.status == "active")
    ).scalars().all()
    for membership in active_owner_memberships:
        owner_count = db.execute(
            select(OrganizationMembershipModel)
            .where(OrganizationMembershipModel.organization_id == membership.organization_id)
            .where(OrganizationMembershipModel.role == "owner")
            .where(OrganizationMembershipModel.status == "active")
        ).scalars().all()
        if len(owner_count) <= 1:
            record_audit_event(
                db,
                current_user.id,
                "account.deletion_blocked",
                "organization",
                membership.organization_id,
                {"reason": "final_active_owner"},
            )
            raise HTTPException(
                status_code=409,
                detail="Transfer or remove final organization ownership before deleting the account.",
            )
    now = datetime.now(UTC)
    user.account_status = "deleted"
    user.is_active = False
    user.deleted_at = now
    user.email = f"deleted-{user.id}@deleted.local"
    user.updated_at = now
    dispose_jobs_for_account_deletion(db, current_user.id, now=now)
    db.commit()
    record_audit_event(db, current_user.id, "account.deletion_requested", "user", current_user.id)
    return AccountDeleteResponse(
        status="pending_provider_deletion",
        message="Application account disabled. External Supabase identity deletion requires a configured server-side provider deletion job.",
    )


@router.get("/usage")
def get_usage(
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(require_authenticated_user),
) -> dict:
    return usage_summary(db, current_user)


@router.get("/consents")
def get_consents(
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(require_authenticated_user),
) -> dict:
    records = db.execute(
        select(ConsentRecordModel).where(ConsentRecordModel.user_id == current_user.id)
    ).scalars().all()
    return {"items": [_consent_payload(record) for record in records]}


@router.post("/consents")
def post_consent(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(require_authenticated_user),
) -> dict:
    document_type = payload.get("document_type")
    settings = get_settings()
    document_version = (
        settings.current_terms_version
        if document_type == "terms"
        else settings.current_privacy_version
        if document_type == "privacy"
        else ""
    )
    if document_type not in {"terms", "privacy"}:
        raise HTTPException(status_code=422, detail="Invalid consent document")
    existing = db.execute(
        select(ConsentRecordModel)
        .where(ConsentRecordModel.user_id == current_user.id)
        .where(ConsentRecordModel.document_type == document_type)
        .where(ConsentRecordModel.document_version == document_version)
        .where(ConsentRecordModel.withdrawn_at.is_(None))
    ).scalars().first()
    if existing is not None:
        return {"consent": _consent_payload(existing)}
    record = ConsentRecordModel(
        id=f"consent_{uuid4().hex[:12]}",
        user_id=current_user.id,
        document_type=document_type,
        document_version=document_version,
        accepted_at=datetime.now(UTC),
        metadata_json={"source": "api"},
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    record_audit_event(
        db,
        current_user.id,
        "consent.accepted",
        "consent_record",
        record.id,
        {"document_type": record.document_type, "document_version": record.document_version},
    )
    return {"consent": _consent_payload(record)}


@router.post("/auth/mfa/audit")
def record_mfa_audit_event(
    payload: MfaAuditEventRequest,
    x_bff_audit_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(require_authenticated_user),
) -> dict:
    secret = get_settings().bff_audit_secret
    if not secret or not x_bff_audit_key or not constant_time_equal(x_bff_audit_key, secret):
        raise HTTPException(status_code=403, detail="BFF audit authorization required")
    event = record_audit_event(
        db,
        current_user.id,
        payload.action,
        "mfa_factor",
        payload.factor_id,
    )
    return {"id": event.id, "status": "recorded"}


def _current_user_record(db: Session, current_user: UserContext) -> UserModel:
    user = db.get(UserModel, current_user.id)
    if user is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return user


def _consent_payload(record: ConsentRecordModel) -> dict:
    return {
        "id": record.id,
        "document_type": record.document_type,
        "document_version": record.document_version,
        "accepted_at": record.accepted_at,
        "withdrawn_at": record.withdrawn_at,
    }
