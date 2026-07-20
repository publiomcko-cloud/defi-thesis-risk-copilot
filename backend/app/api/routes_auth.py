from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_user
from app.auth.schemas import (
    AccountDeleteRequest,
    AccountDeleteResponse,
    AccountExportResponse,
    AccountResponse,
    AuthLogoutResponse,
    UserContext,
)
from app.auth.service import user_response
from app.db.session import get_db
from app.models.access_audit_event import AccessAuditEventModel
from app.models.alert_event import AlertEventModel
from app.models.consent_record import ConsentRecordModel
from app.models.organization import OrganizationMembershipModel
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
    current_user: UserContext = Depends(require_user),
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
    current_user: UserContext = Depends(require_user),
) -> AccountExportResponse:
    user = _current_user_record(db, current_user)
    reports = db.execute(
        select(ReportModel).where(ReportModel.owner_user_id == current_user.id)
    ).scalars().all()
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
    return AccountExportResponse(
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


@router.delete("/account", response_model=AccountDeleteResponse)
def delete_account(
    request: AccountDeleteRequest,
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(require_user),
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
    db.commit()
    return AccountDeleteResponse(
        status="pending_provider_deletion",
        message="Application account disabled. External Supabase identity deletion requires a configured server-side provider deletion job.",
    )


@router.get("/usage")
def get_usage(
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(require_user),
) -> dict:
    return usage_summary(db, current_user)


@router.get("/consents")
def get_consents(
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(require_user),
) -> dict:
    records = db.execute(
        select(ConsentRecordModel).where(ConsentRecordModel.user_id == current_user.id)
    ).scalars().all()
    return {"items": [_consent_payload(record) for record in records]}


@router.post("/consents")
def post_consent(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(require_user),
) -> dict:
    document_type = payload.get("document_type")
    document_version = payload.get("document_version")
    if document_type not in {"terms", "privacy"} or not isinstance(document_version, str):
        raise HTTPException(status_code=422, detail="Invalid consent document")
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
    return {"consent": _consent_payload(record)}


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
