from typing import Literal

from pydantic import BaseModel, Field


class DocumentIngestRequest(BaseModel):
    protocol: str = Field(min_length=2)
    source_url: str | None = None
    title: str | None = None
    content: str | None = None


class DocumentIngestResponse(BaseModel):
    status: Literal["queued"]
    document_id: str
    message: str
