from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.evaluation.schemas import EvaluationResult, ReviewItem
from app.models.discovered_item import DiscoveredItemModel
from app.models.evaluation_result import EvaluationResultModel
from app.models.review_item import ReviewItemModel

REVIEW_STATUSES = {
    "needs_review",
    "approved_for_rag",
    "rejected",
    "needs_more_data",
    "archived",
}


def upsert_review_item(
    discovered_item: DiscoveredItemModel,
    evaluation_result: EvaluationResultModel,
    db: Session,
) -> ReviewItem:
    existing = db.execute(
        select(ReviewItemModel).where(
            ReviewItemModel.discovered_item_id == discovered_item.id
        )
    ).scalars().first()

    if existing is None:
        existing = ReviewItemModel(
            id=f"review_{uuid4().hex[:12]}",
            discovered_item_id=discovered_item.id,
            evaluation_result_id=evaluation_result.id,
            status="needs_review",
            prepared_for_rag=False,
        )
        db.add(existing)
    else:
        existing.evaluation_result_id = evaluation_result.id
        existing.updated_at = datetime.now(UTC)

    discovered_item.status = existing.status
    db.flush()
    return _review_schema(existing, discovered_item, evaluation_result)


def list_review_items(
    db: Session,
    status: str | None = None,
    limit: int = 100,
) -> list[ReviewItem]:
    statement = select(ReviewItemModel).order_by(ReviewItemModel.updated_at.desc())
    if status:
        statement = statement.where(ReviewItemModel.status == status)
    records = db.execute(statement.limit(limit)).scalars().all()
    return [_review_item_from_record(record, db) for record in records]


def update_review_status(
    review_item_id: str,
    status: str,
    reviewer_notes: str | None,
    db: Session,
) -> ReviewItem:
    if status not in REVIEW_STATUSES:
        raise HTTPException(status_code=422, detail="Unsupported review status")

    record = db.get(ReviewItemModel, review_item_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Review item not found")

    discovered_item = db.get(DiscoveredItemModel, record.discovered_item_id)
    if discovered_item is None:
        raise HTTPException(status_code=404, detail="Discovered item not found")

    record.status = status
    record.reviewer_notes = reviewer_notes
    record.prepared_for_rag = status == "approved_for_rag"
    record.updated_at = datetime.now(UTC)
    discovered_item.status = status
    db.commit()
    db.refresh(record)
    return _review_item_from_record(record, db)


def _review_item_from_record(record: ReviewItemModel, db: Session) -> ReviewItem:
    discovered_item = db.get(DiscoveredItemModel, record.discovered_item_id)
    evaluation_result = db.get(EvaluationResultModel, record.evaluation_result_id)
    if discovered_item is None or evaluation_result is None:
        raise HTTPException(status_code=500, detail="Review queue record is incomplete")
    return _review_schema(record, discovered_item, evaluation_result)


def _review_schema(
    review: ReviewItemModel,
    discovered_item: DiscoveredItemModel,
    evaluation_result: EvaluationResultModel,
) -> ReviewItem:
    return ReviewItem(
        id=review.id,
        discovered_item_id=review.discovered_item_id,
        evaluation_result_id=review.evaluation_result_id,
        status=review.status,
        reviewer_notes=review.reviewer_notes,
        prepared_for_rag=review.prepared_for_rag,
        created_at=review.created_at,
        updated_at=review.updated_at,
        discovered_item={
            "id": discovered_item.id,
            "source": discovered_item.source,
            "source_type": discovered_item.source_type,
            "title": discovered_item.title,
            "url": discovered_item.url,
            "protocol": discovered_item.protocol,
            "chain": discovered_item.chain,
            "asset": discovered_item.asset,
            "market_identifier": discovered_item.market_identifier,
            "status": discovered_item.status,
        },
        evaluation_result=EvaluationResult(
            id=evaluation_result.id,
            discovered_item_id=evaluation_result.discovered_item_id,
            report_id=evaluation_result.report_id,
            risk_rating=evaluation_result.risk_rating,
            risk_score=evaluation_result.risk_score,
            confidence=evaluation_result.confidence,
            risk_summary=evaluation_result.risk_summary,
            missing_data=evaluation_result.missing_data_json,
            sources=evaluation_result.sources_json,
            created_at=evaluation_result.created_at,
        ),
    )
