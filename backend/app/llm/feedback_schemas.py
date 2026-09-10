"""Bounded API contracts for report-quality feedback."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


FeedbackCategory = Literal[
    "helpful",
    "incorrect",
    "missing_source",
    "bad_citation",
    "unclear",
    "entity_error",
    "unsafe",
]
FeedbackReviewState = Literal["submitted", "reviewed", "approved_for_dataset", "rejected"]
FeedbackReviewAction = Literal["reviewed", "approved_for_dataset", "rejected"]


class ModelFeedbackCreateRequest(BaseModel):
    category: FeedbackCategory
    comment: str | None = Field(default=None, max_length=1000)

    model_config = ConfigDict(extra="forbid")


class ModelFeedbackReviewRequest(BaseModel):
    action: FeedbackReviewAction

    model_config = ConfigDict(extra="forbid")


class ModelFeedbackResponse(BaseModel):
    id: str
    report_id: str
    model_run_provenance_id: str | None
    category: FeedbackCategory
    comment: str | None
    review_state: FeedbackReviewState
    dataset_review_reference: str | None
    created_at: datetime
    reviewed_at: datetime | None


class ModelFeedbackListResponse(BaseModel):
    items: list[ModelFeedbackResponse]


class ModelFeedbackReviewQueueItem(BaseModel):
    id: str
    report_id: str
    model_run_provenance_id: str | None
    category: FeedbackCategory
    review_state: FeedbackReviewState
    created_at: datetime
    reviewed_at: datetime | None


class ModelFeedbackReviewQueueResponse(BaseModel):
    items: list[ModelFeedbackReviewQueueItem]
