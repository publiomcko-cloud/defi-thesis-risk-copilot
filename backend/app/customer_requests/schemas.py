from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CustomerRequestType = Literal[
    "support",
    "feedback",
    "abuse_report",
    "privacy_access_export",
    "privacy_deletion",
]
CustomerRequestWorkflowState = Literal["open", "in_progress", "resolved", "closed"]
CustomerRequestVerificationState = Literal["not_required", "authenticated"]


class CustomerRequestCreateRequest(BaseModel):
    request_type: CustomerRequestType
    subject: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=4000)
    organization_id: str | None = Field(default=None, min_length=1, max_length=64)

    model_config = ConfigDict(extra="forbid")


class CustomerRequestResponse(BaseModel):
    id: str
    request_type: CustomerRequestType
    subject: str
    description: str
    organization_id: str | None
    workflow_state: CustomerRequestWorkflowState
    verification_state: CustomerRequestVerificationState
    resolution_code: str | None
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None


class CustomerRequestsResponse(BaseModel):
    items: list[CustomerRequestResponse]
