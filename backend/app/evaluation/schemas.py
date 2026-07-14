from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.monitoring.schemas import DiscoveredItemStatus


class EvaluationResult(BaseModel):
    id: str
    discovered_item_id: str
    report_id: str
    risk_rating: str
    risk_score: int
    confidence: str
    risk_summary: str
    missing_data: list[str]
    sources: list[dict]
    created_at: datetime


class ReviewItem(BaseModel):
    id: str
    discovered_item_id: str
    evaluation_result_id: str
    status: DiscoveredItemStatus
    reviewer_notes: str | None = None
    prepared_for_rag: bool
    knowledge_base_ingestion: dict | None = None
    created_at: datetime
    updated_at: datetime
    discovered_item: dict
    evaluation_result: EvaluationResult


class EvaluateDiscoveredItemResponse(BaseModel):
    status: Literal["completed"]
    evaluation_result: EvaluationResult
    review_item: ReviewItem


class ReviewItemsResponse(BaseModel):
    items: list[ReviewItem]


class ReviewStatusUpdateRequest(BaseModel):
    status: DiscoveredItemStatus
    reviewer_notes: str | None = Field(default=None, max_length=2000)


class ReviewStatusUpdateResponse(BaseModel):
    review_item: ReviewItem
