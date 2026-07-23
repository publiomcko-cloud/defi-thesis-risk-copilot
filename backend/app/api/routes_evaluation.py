from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.schemas import UserContext
from app.auth.service import record_audit_event
from app.db.session import get_db
from app.discovery.schemas import IngestToRagResponse
from app.evaluation.evaluator import evaluate_discovered_item
from app.evaluation.review_queue import list_review_items, update_review_status
from app.evaluation.schemas import (
    EvaluateDiscoveredItemResponse,
    ReviewItemsResponse,
    ReviewStatusUpdateRequest,
    ReviewStatusUpdateResponse,
)
from app.knowledge_base.ingestion_service import ingest_review_item_to_rag

router = APIRouter(tags=["evaluation"])


@router.post(
    "/evaluation/discovered-items/{discovered_item_id}/evaluate",
    response_model=EvaluateDiscoveredItemResponse,
)
def evaluate_item(
    discovered_item_id: str,
    db: Session = Depends(get_db),
    _: UserContext = Depends(require_admin),
) -> EvaluateDiscoveredItemResponse:
    return evaluate_discovered_item(discovered_item_id, db)


@router.get("/evaluation/review-items", response_model=ReviewItemsResponse)
def get_review_items(
    status: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> ReviewItemsResponse:
    return ReviewItemsResponse(items=list_review_items(db, status=status, limit=limit))


@router.patch(
    "/evaluation/review-items/{review_item_id}",
    response_model=ReviewStatusUpdateResponse,
)
def patch_review_item(
    review_item_id: str,
    request: ReviewStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(require_admin),
) -> ReviewStatusUpdateResponse:
    review_item = update_review_status(
        review_item_id,
        request.status,
        request.reviewer_notes,
        db,
    )
    if request.status in {"approved_for_rag", "rejected", "archived", "needs_more_data"}:
        record_audit_event(
            db,
            current_user.id,
            f"review_item.{request.status}",
            "review_item",
            review_item_id,
            {"reviewer_notes": request.reviewer_notes},
        )
    return ReviewStatusUpdateResponse(review_item=review_item)


@router.post(
    "/evaluation/review-items/{review_item_id}/ingest-to-rag",
    response_model=IngestToRagResponse,
)
def ingest_review_item(
    review_item_id: str,
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(require_admin),
) -> IngestToRagResponse:
    ingestion, refreshed_chunk_count = ingest_review_item_to_rag(
        review_item_id,
        db,
        ingested_by=current_user.id,
    )
    record_audit_event(
        db,
        current_user.id,
        "review_item.ingest_to_rag",
        "review_item",
        review_item_id,
        {"generated_markdown_path": ingestion.generated_markdown_path},
    )
    return IngestToRagResponse(
        status="ingested",
        ingestion=ingestion,
        refreshed_chunk_count=refreshed_chunk_count,
    )
