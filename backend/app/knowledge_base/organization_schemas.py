from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class OrganizationKnowledgeSourceCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    protocol: str = Field(min_length=2, max_length=64)
    source_type: str = Field(default="documentation", min_length=2, max_length=64)
    source_url: HttpUrl
    approval_confirmed: Literal[True]
    approval_notes: str | None = Field(default=None, max_length=2_000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("source_url")
    @classmethod
    def reject_url_credentials(cls, value: HttpUrl) -> HttpUrl:
        if value.username or value.password:
            raise ValueError("source_url must not contain credentials")
        return value


class OrganizationKnowledgeSourceResponse(BaseModel):
    id: str
    organization_id: str
    title: str
    protocol: str
    source_type: str
    source_url: str
    provenance_hash: str
    approval_status: Literal["approved"]
    approval_notes: str | None
    storage_status: Literal["metadata_only"]
    status: Literal["active", "disabled"]
    approved_by_user_id: str
    approved_at: datetime
    created_at: datetime
    updated_at: datetime


class OrganizationKnowledgeSourcesResponse(BaseModel):
    items: list[OrganizationKnowledgeSourceResponse]
