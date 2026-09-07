"""Tenant-safe report feedback and explicit dataset-review workflow."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.auth.policies import can_read_resource
from app.auth.schemas import UserContext
from app.auth.service import record_audit_event
from app.llm.feedback_schemas import (
    ModelFeedbackCreateRequest,
    ModelFeedbackResponse,
    ModelFeedbackReviewQueueItem,
)
from app.models.model_governance import ModelFeedbackModel, ModelRunProvenanceModel
from app.models.report import ReportModel


def create_model_feedback(
    db: Session,
    actor: UserContext,
    report_id: str,
    request: ModelFeedbackCreateRequest,
) -> ModelFeedbackResponse:
    report = _accessible_report(db, actor, report_id)
    comment = _normalized_comment(request.comment)
    run = db.execute(
        select(ModelRunProvenanceModel).where(ModelRunProvenanceModel.report_id == report.id)
    ).scalars().one_or_none()
    record = ModelFeedbackModel(
        id=f"modelfeedback_{uuid4().hex}",
        report_id=report.id,
        model_run_provenance_id=run.id if run else None,
        owner_user_id=actor.id,
        organization_id=report.organization_id,
        category=request.category,
        comment=comment,
        review_state="submitted",
        created_at=datetime.now(UTC),
    )
    db.add(record)
    db.flush()
    record_audit_event(
        db,
        actor.id,
        "model_feedback.created",
        "model_feedback",
        record.id,
        {"category": record.category, "review_state": record.review_state},
        commit=False,
    )
    db.commit()
    db.refresh(record)
    return feedback_response(record)


def list_model_feedback(db: Session, actor: UserContext) -> list[ModelFeedbackResponse]:
    records = db.execute(
        select(ModelFeedbackModel)
        .where(ModelFeedbackModel.owner_user_id == actor.id)
        .order_by(ModelFeedbackModel.created_at.desc(), ModelFeedbackModel.id.desc())
    ).scalars().all()
    return [
        feedback_response(record)
        for record in records
        if (report := db.get(ReportModel, record.report_id)) is not None and can_read_resource(actor, report, db)
    ]


def get_model_feedback(db: Session, actor: UserContext, feedback_id: str) -> ModelFeedbackResponse:
    record = _owned_feedback(db, actor.id, feedback_id)
    _accessible_report(db, actor, record.report_id)
    return feedback_response(record)


def list_review_queue(db: Session, actor: UserContext) -> list[ModelFeedbackReviewQueueItem]:
    _require_platform_admin(actor)
    records = db.execute(
        select(ModelFeedbackModel)
        .where(ModelFeedbackModel.review_state.in_({"submitted", "reviewed"}))
        .order_by(ModelFeedbackModel.created_at.asc(), ModelFeedbackModel.id.asc())
    ).scalars().all()
    # The operator queue deliberately excludes comment text and cannot expose a
    # report body; it is a review-state control surface, not a tenant bypass.
    return [review_queue_item(record) for record in records]


def review_model_feedback(
    db: Session,
    actor: UserContext,
    feedback_id: str,
    action: str,
) -> ModelFeedbackResponse:
    _require_platform_admin(actor)
    record = db.execute(
        select(ModelFeedbackModel).where(ModelFeedbackModel.id == feedback_id).with_for_update()
    ).scalars().one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Model feedback not found")
    if record.review_state == action:
        return feedback_response(record)
    if record.review_state in {"approved_for_dataset", "rejected"}:
        raise HTTPException(status_code=409, detail="Model feedback review is already final")

    now = datetime.now(UTC)
    record.review_state = action
    record.reviewed_by_user_id = actor.id
    record.reviewed_at = now
    record.dataset_review_reference = (
        f"feedback_case_{record.id.removeprefix('modelfeedback_')}" if action == "approved_for_dataset" else None
    )
    record_audit_event(
        db,
        actor.id,
        f"model_feedback.{action}",
        "model_feedback",
        record.id,
        {"category": record.category, "review_state": record.review_state},
        commit=False,
    )
    db.commit()
    db.refresh(record)
    return feedback_response(record)


def export_model_feedback(db: Session, owner_user_id: str) -> list[dict]:
    records = db.execute(
        select(ModelFeedbackModel)
        .where(ModelFeedbackModel.owner_user_id == owner_user_id)
        .order_by(ModelFeedbackModel.created_at, ModelFeedbackModel.id)
    ).scalars().all()
    return [
        {
            "id": record.id,
            "report_id": record.report_id,
            "model_run_provenance_id": record.model_run_provenance_id,
            "organization_id": record.organization_id,
            "category": record.category,
            "comment": record.comment,
            "review_state": record.review_state,
            "dataset_review_reference": record.dataset_review_reference,
            "created_at": record.created_at,
            "reviewed_at": record.reviewed_at,
        }
        for record in records
    ]


def dispose_model_feedback_for_account(db: Session, owner_user_id: str) -> int:
    """Remove user-owned free text in the existing account-deletion transaction."""

    return db.execute(
        delete(ModelFeedbackModel).where(ModelFeedbackModel.owner_user_id == owner_user_id)
    ).rowcount or 0


def clear_model_feedback_organization_context(db: Session, organization_id: str) -> int:
    """Keep owner-safe feedback records while removing a deleted org reference."""

    return db.execute(
        update(ModelFeedbackModel)
        .where(ModelFeedbackModel.organization_id == organization_id)
        .values(organization_id=None)
    ).rowcount or 0


def feedback_response(record: ModelFeedbackModel) -> ModelFeedbackResponse:
    return ModelFeedbackResponse(
        id=record.id,
        report_id=record.report_id,
        model_run_provenance_id=record.model_run_provenance_id,
        category=record.category,
        comment=record.comment,
        review_state=record.review_state,
        dataset_review_reference=record.dataset_review_reference,
        created_at=record.created_at,
        reviewed_at=record.reviewed_at,
    )


def review_queue_item(record: ModelFeedbackModel) -> ModelFeedbackReviewQueueItem:
    return ModelFeedbackReviewQueueItem(
        id=record.id,
        report_id=record.report_id,
        model_run_provenance_id=record.model_run_provenance_id,
        category=record.category,
        review_state=record.review_state,
        created_at=record.created_at,
        reviewed_at=record.reviewed_at,
    )


def _accessible_report(db: Session, actor: UserContext, report_id: str) -> ReportModel:
    report = db.get(ReportModel, report_id)
    if report is None or not can_read_resource(actor, report, db):
        raise HTTPException(status_code=404, detail="Report not found")
    return report


def _owned_feedback(db: Session, owner_user_id: str, feedback_id: str) -> ModelFeedbackModel:
    record = db.execute(
        select(ModelFeedbackModel)
        .where(ModelFeedbackModel.id == feedback_id)
        .where(ModelFeedbackModel.owner_user_id == owner_user_id)
    ).scalars().one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Model feedback not found")
    return record


def _normalized_comment(comment: str | None) -> str | None:
    if comment is None:
        return None
    normalized = comment.strip()
    if not normalized:
        raise HTTPException(status_code=422, detail="Feedback comment cannot be blank")
    return normalized


def _require_platform_admin(actor: UserContext) -> None:
    if not actor.is_admin:
        raise HTTPException(status_code=403, detail="Platform admin authority is required")
