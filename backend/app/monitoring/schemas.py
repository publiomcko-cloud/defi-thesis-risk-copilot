from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


DiscoveredItemStatus = Literal[
    "needs_review",
    "approved_for_rag",
    "rejected",
    "needs_more_data",
    "archived",
]


class SourceWatch(BaseModel):
    id: str
    source: str
    source_type: str
    protocol: str | None = None
    url: str | None = None
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)


class RawDiscoveredItem(BaseModel):
    source: str
    source_type: str
    title: str
    url: str | None = None
    protocol: str | None = None
    chain: str | None = None
    asset: str | None = None
    market_identifier: str | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class DiscoveredItem(BaseModel):
    id: str
    source: str
    source_type: str
    title: str
    url: str | None = None
    protocol: str | None = None
    chain: str | None = None
    asset: str | None = None
    market_identifier: str | None = None
    discovered_at: datetime
    last_seen_at: datetime
    raw_payload: dict[str, Any]
    status: DiscoveredItemStatus = "needs_review"


class MonitoringRunRequest(BaseModel):
    source: str | None = None
    protocol: str | None = None


class MonitoringFailure(BaseModel):
    source_watch_id: str
    source: str
    error: str


class MonitoringRunResponse(BaseModel):
    status: Literal["completed", "partial"]
    watches_checked: int
    created_count: int
    duplicate_count: int
    failed_count: int
    failures: list[MonitoringFailure]
    discovered_items: list[DiscoveredItem]


class DiscoveredItemsResponse(BaseModel):
    items: list[DiscoveredItem]
