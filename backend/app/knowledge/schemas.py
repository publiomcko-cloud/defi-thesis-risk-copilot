from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


KnowledgeVisibility = Literal["public", "private", "organization"]
KnowledgeTrustState = Literal[
    "needs_review",
    "approved_for_rag",
    "rejected",
    "archived",
]


class KnowledgeSourceCreateRequest(BaseModel):
    visibility: KnowledgeVisibility
    title: str = Field(min_length=1, max_length=255)
    source_type: str = Field(min_length=1, max_length=64)
    organization_id: str | None = Field(default=None, max_length=64)
    source_uri: str | None = Field(default=None, max_length=2048)
    canonical_uri: str | None = Field(default=None, max_length=2048)
    protocol: str | None = Field(default=None, max_length=64)
    chain: str | None = Field(default=None, max_length=64)

    model_config = ConfigDict(extra="forbid")


class KnowledgeSourceUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    protocol: str | None = Field(default=None, min_length=1, max_length=64)
    chain: str | None = Field(default=None, min_length=1, max_length=64)
    trust_state: KnowledgeTrustState | None = None

    model_config = ConfigDict(extra="forbid")


class KnowledgeSourceResponse(BaseModel):
    id: str
    owner_user_id: str | None
    organization_id: str | None
    visibility: KnowledgeVisibility
    source_type: str
    source_uri: str | None
    canonical_uri: str | None
    title: str
    protocol: str | None
    chain: str | None
    status: str
    trust_state: str
    approved_by_user_id: str | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class KnowledgeSourcesResponse(BaseModel):
    items: list[KnowledgeSourceResponse]


class KnowledgeDocumentVersionResponse(BaseModel):
    id: str
    version_number: int
    checksum: str | None
    size_bytes: int
    status: str
    parser_version: str | None
    chunker_version: str | None
    embedding_model: str | None
    embedding_dimensions: int | None
    created_at: datetime
    superseded_at: datetime | None
    deleted_at: datetime | None


class KnowledgeDocumentResponse(BaseModel):
    id: str
    knowledge_source_id: str
    current_version_id: str | None
    filename: str
    media_type: str
    status: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    versions: list[KnowledgeDocumentVersionResponse] = Field(default_factory=list)
