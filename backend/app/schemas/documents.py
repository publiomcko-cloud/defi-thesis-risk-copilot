from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DocumentIngestRequest(BaseModel):
    protocol: str = Field(min_length=2, max_length=64)
    source_url: str | None = Field(default=None, max_length=2048)
    title: str | None = Field(default=None, max_length=255)
    content: str | None = Field(default=None, max_length=100_000)

    model_config = ConfigDict(extra="forbid")


class DocumentIngestResponse(BaseModel):
    status: Literal["queued"]
    document_id: str
    message: str
