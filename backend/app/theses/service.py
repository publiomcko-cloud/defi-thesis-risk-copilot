from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.policies import can_read_resource, can_update_resource, has_org_role
from app.auth.schemas import UserContext
from app.models.saved_thesis import SavedThesisModel
from app.theses.schemas import ThesisCreateRequest, ThesisResponse, ThesisUpdateRequest


def create_thesis(db: Session, actor: UserContext, request: ThesisCreateRequest) -> ThesisResponse:
    if request.visibility == "organization":
        if not request.organization_id or not has_org_role(db, actor.id, request.organization_id, {"owner", "admin", "member"}):
            raise HTTPException(status_code=403, detail="Organization membership required")
    now = datetime.now(UTC)
    record = SavedThesisModel(
        id=f"thesis_{uuid4().hex[:12]}",
        owner_user_id=actor.id,
        organization_id=request.organization_id if request.visibility == "organization" else None,
        title=request.title,
        strategy_text=request.strategy_text,
        protocols=[protocol.lower() for protocol in request.protocols],
        assumptions_json=request.assumptions,
        visibility=request.visibility,
        created_at=now,
        updated_at=now,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return thesis_response(record)


def list_theses(db: Session, actor: UserContext) -> list[ThesisResponse]:
    records = db.execute(
        select(SavedThesisModel)
        .where(SavedThesisModel.deleted_at.is_(None))
        .order_by(SavedThesisModel.created_at.desc())
    ).scalars().all()
    return [thesis_response(record) for record in records if can_read_resource(actor, record, db)]


def get_thesis(db: Session, actor: UserContext, thesis_id: str) -> ThesisResponse:
    record = db.get(SavedThesisModel, thesis_id)
    if record is None or not can_read_resource(actor, record, db):
        raise HTTPException(status_code=404, detail="Thesis not found")
    return thesis_response(record)


def update_thesis(
    db: Session,
    actor: UserContext,
    thesis_id: str,
    request: ThesisUpdateRequest,
) -> ThesisResponse:
    record = db.get(SavedThesisModel, thesis_id)
    if record is None or not can_update_resource(actor, record, db):
        raise HTTPException(status_code=404, detail="Thesis not found")
    if request.title is not None:
        record.title = request.title
    if request.strategy_text is not None:
        record.strategy_text = request.strategy_text
    if request.protocols is not None:
        record.protocols = [protocol.lower() for protocol in request.protocols]
    if request.assumptions is not None:
        record.assumptions_json = request.assumptions
    if request.visibility is not None:
        if request.visibility == "organization" and not record.organization_id:
            raise HTTPException(status_code=422, detail="organization_id is required for organization visibility")
        record.visibility = request.visibility
    record.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(record)
    return thesis_response(record)


def delete_thesis(db: Session, actor: UserContext, thesis_id: str) -> ThesisResponse:
    record = db.get(SavedThesisModel, thesis_id)
    if record is None or not can_update_resource(actor, record, db):
        raise HTTPException(status_code=404, detail="Thesis not found")
    record.deleted_at = datetime.now(UTC)
    db.commit()
    db.refresh(record)
    return thesis_response(record)


def thesis_response(record: SavedThesisModel) -> ThesisResponse:
    return ThesisResponse(
        id=record.id,
        owner_user_id=record.owner_user_id,
        organization_id=record.organization_id,
        title=record.title,
        strategy_text=record.strategy_text,
        protocols=record.protocols,
        assumptions=record.assumptions_json,
        visibility=record.visibility,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )
