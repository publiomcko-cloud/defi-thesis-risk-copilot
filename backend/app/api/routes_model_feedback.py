"""Minimal report-quality feedback and explicit operator review endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin, require_authenticated_user
from app.auth.schemas import UserContext
from app.db.session import get_db
from app.llm.feedback import (
    create_model_feedback,
    get_model_feedback,
    list_model_feedback,
    list_review_queue,
    review_model_feedback,
)
from app.llm.feedback_schemas import (
    ModelFeedbackCreateRequest,
    ModelFeedbackListResponse,
    ModelFeedbackResponse,
    ModelFeedbackReviewQueueResponse,
    ModelFeedbackReviewRequest,
)


router = APIRouter(prefix="/model-feedback", tags=["model-feedback"])


@router.post("/reports/{report_id}", response_model=ModelFeedbackResponse, status_code=201)
def create_feedback(
    report_id: str,
    request: ModelFeedbackCreateRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> ModelFeedbackResponse:
    return create_model_feedback(db, actor, report_id, request)


@router.get("", response_model=ModelFeedbackListResponse)
def read_feedback(
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> ModelFeedbackListResponse:
    return ModelFeedbackListResponse(items=list_model_feedback(db, actor))


@router.get("/{feedback_id}", response_model=ModelFeedbackResponse)
def read_feedback_item(
    feedback_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> ModelFeedbackResponse:
    return get_model_feedback(db, actor, feedback_id)


@router.get("/admin/review-queue", response_model=ModelFeedbackReviewQueueResponse)
def read_review_queue(
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_admin),
) -> ModelFeedbackReviewQueueResponse:
    return ModelFeedbackReviewQueueResponse(items=list_review_queue(db, actor))


@router.post("/admin/{feedback_id}/review", response_model=ModelFeedbackResponse)
def review_feedback(
    feedback_id: str,
    request: ModelFeedbackReviewRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_admin),
) -> ModelFeedbackResponse:
    return review_model_feedback(db, actor, feedback_id, request.action)
