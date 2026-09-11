from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.policies import has_org_role
from app.auth.schemas import UserContext
from app.models.report import ReportModel
from app.models.research_intelligence import ThesisAssumptionModel, ThesisCatalystModel
from app.models.saved_thesis import SavedThesisModel
from app.product_analytics.service import emit_product_event_safely
from app.quotas.service import RESOURCE_SAVED_THESES, enforce_resource_count_limit
from app.research_intelligence.service import (
    append_material_revision,
    create_initial_revision,
    dispose_research_intelligence_for_thesis,
    prepare_material_mutation,
)
from app.theses.schemas import ThesisCreateRequest, ThesisResponse, ThesisUpdateRequest
from app.theses.policies import can_read_saved_thesis, can_update_saved_thesis


def create_thesis(db: Session, actor: UserContext, request: ThesisCreateRequest) -> ThesisResponse:
    enforce_resource_count_limit(db, actor, RESOURCE_SAVED_THESES)
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
    create_initial_revision(db, record, actor.id)
    db.commit()
    db.refresh(record)
    response = thesis_response(record)
    emit_product_event_safely(
        db,
        owner_user_id=actor.id,
        event_name="thesis_saved",
        metadata={
            "actor_class": "organization_context" if record.visibility == "organization" else "authenticated",
            "visibility_class": record.visibility,
        },
        source_boundary=record.id,
        occurred_at=record.created_at,
    )
    return response


def list_theses(db: Session, actor: UserContext) -> list[ThesisResponse]:
    records = db.execute(
        select(SavedThesisModel)
        .where(SavedThesisModel.deleted_at.is_(None))
        .order_by(SavedThesisModel.created_at.desc())
    ).scalars().all()
    return [thesis_response(record) for record in records if can_read_saved_thesis(db, actor, record)]


def get_thesis(db: Session, actor: UserContext, thesis_id: str) -> ThesisResponse:
    record = db.get(SavedThesisModel, thesis_id)
    if record is None or not can_read_saved_thesis(db, actor, record):
        raise HTTPException(status_code=404, detail="Thesis not found")
    return thesis_response(record)


def update_thesis(
    db: Session,
    actor: UserContext,
    thesis_id: str,
    request: ThesisUpdateRequest,
) -> ThesisResponse:
    record = db.execute(
        select(SavedThesisModel).where(SavedThesisModel.id == thesis_id).with_for_update()
    ).scalars().one_or_none()
    if record is None or not can_update_saved_thesis(db, actor, record):
        raise HTTPException(status_code=404, detail="Thesis not found")
    target_visibility, target_organization_id = _validated_destination_scope(db, actor, record, request)
    prepare_material_mutation(db, record, expected_revision=request.expected_revision)
    # The baseline is now durable in this transaction, before mutable saved
    # thesis fields are touched. This preserves exact pre-21D content at rev 1.
    if request.title is not None:
        record.title = request.title
    if request.strategy_text is not None:
        record.strategy_text = request.strategy_text
    if request.protocols is not None:
        record.protocols = [protocol.lower() for protocol in request.protocols]
    if request.assumptions is not None:
        record.assumptions_json = request.assumptions
    if request.visibility is not None:
        record.visibility = target_visibility
        record.organization_id = target_organization_id
    record.updated_at = datetime.now(UTC)
    append_material_revision(
        db,
        record,
        actor_user_id=actor.id,
        change_reason=request.change_reason or "Thesis updated",
        expected_revision=request.expected_revision,
    )
    db.commit()
    db.refresh(record)
    return thesis_response(record)


def delete_thesis(db: Session, actor: UserContext, thesis_id: str) -> ThesisResponse:
    record = db.execute(
        select(SavedThesisModel).where(SavedThesisModel.id == thesis_id).with_for_update()
    ).scalars().one_or_none()
    if record is None or not can_update_saved_thesis(db, actor, record):
        raise HTTPException(status_code=404, detail="Thesis not found")
    dispose_research_intelligence_for_thesis(db, record.id)
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


def _validated_destination_scope(
    db: Session,
    actor: UserContext,
    thesis: SavedThesisModel,
    request: ThesisUpdateRequest,
) -> tuple[str, str | None]:
    """Validate a requested scope move while the saved-thesis row is locked."""

    if request.visibility is None:
        if "organization_id" in request.model_fields_set:
            raise HTTPException(status_code=422, detail="organization_id requires an explicit visibility change")
        return thesis.visibility, thesis.organization_id

    if request.visibility == "private":
        if "organization_id" in request.model_fields_set and request.organization_id is not None:
            raise HTTPException(status_code=422, detail="private visibility cannot include organization_id")
        target_organization_id: str | None = None
    else:
        target_organization_id = request.organization_id or thesis.organization_id
        if not target_organization_id:
            raise HTTPException(status_code=422, detail="organization_id is required for organization visibility")

    scope_changed = (
        request.visibility != thesis.visibility
        or target_organization_id != thesis.organization_id
    )
    if not scope_changed:
        return request.visibility, target_organization_id
    if request.expected_revision is None:
        raise HTTPException(status_code=422, detail="expected_revision is required for a visibility change")

    if request.visibility == "private":
        # An organization member can edit the shared thesis, but only the
        # historical owner has authority to create the resulting private row.
        if thesis.owner_user_id != actor.id:
            raise HTTPException(status_code=404, detail="Thesis not found")
    elif not has_org_role(db, actor.id, target_organization_id, {"owner", "admin", "member"}):
        raise HTTPException(status_code=404, detail="Thesis not found")

    if _has_incompatible_authoritative_evidence(
        db,
        thesis.id,
        target_visibility=request.visibility,
        target_organization_id=target_organization_id,
        target_owner_user_id=thesis.owner_user_id,
    ):
        raise HTTPException(
            status_code=409,
            detail="Authoritative evidence is incompatible with the destination thesis scope",
        )
    return request.visibility, target_organization_id


def _has_incompatible_authoritative_evidence(
    db: Session,
    thesis_id: str,
    *,
    target_visibility: str,
    target_organization_id: str | None,
    target_owner_user_id: str,
) -> bool:
    evidence_sets = list(
        db.scalars(
            select(ThesisAssumptionModel.evidence_references).where(
                ThesisAssumptionModel.thesis_id == thesis_id
            )
        )
    )
    evidence_sets.extend(
        db.scalars(
            select(ThesisCatalystModel.evidence_references).where(
                ThesisCatalystModel.thesis_id == thesis_id
            )
        )
    )
    for evidence_references in evidence_sets:
        for evidence in evidence_references or []:
            if not isinstance(evidence, dict) or evidence.get("classification") != "authoritative_lineage":
                continue
            report_id = evidence.get("report_id")
            report = db.get(ReportModel, report_id) if isinstance(report_id, str) else None
            if report is None:
                return True
            if target_visibility == "private":
                if report.visibility != "private" or report.owner_user_id != target_owner_user_id:
                    return True
            elif (
                report.visibility != "organization"
                or not target_organization_id
                or report.organization_id != target_organization_id
            ):
                return True
    return False
