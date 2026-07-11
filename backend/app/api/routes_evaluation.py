from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.evaluation.evaluator import evaluate_discovered_item
from app.evaluation.review_queue import list_review_items, update_review_status
from app.evaluation.schemas import (
    EvaluateDiscoveredItemResponse,
    ReviewItemsResponse,
    ReviewStatusUpdateRequest,
    ReviewStatusUpdateResponse,
)

router = APIRouter(tags=["evaluation"])


@router.post(
    "/evaluation/discovered-items/{discovered_item_id}/evaluate",
    response_model=EvaluateDiscoveredItemResponse,
)
def evaluate_item(
    discovered_item_id: str,
    db: Session = Depends(get_db),
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
) -> ReviewStatusUpdateResponse:
    return ReviewStatusUpdateResponse(
        review_item=update_review_status(
            review_item_id,
            request.status,
            request.reviewer_notes,
            db,
        )
    )
