from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


WatchlistItemType = Literal["strategy", "protocol", "market", "discovered_item"]
AlertStatus = Literal["open", "acknowledged", "archived"]


class WatchlistItemCreate(BaseModel):
    item_type: WatchlistItemType = "strategy"
    title: str = Field(min_length=3)
    protocol: str | None = None
    market_identifier: str | None = None
    source_url: str | None = None
    rules: dict[str, Any] = Field(default_factory=dict)
    snapshot: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class WatchlistItem(BaseModel):
    id: str
    item_type: WatchlistItemType
    title: str
    protocol: str | None = None
    market_identifier: str | None = None
    source_url: str | None = None
    rules: dict[str, Any]
    snapshot: dict[str, Any]
    enabled: bool
    created_at: datetime
    last_evaluated_at: datetime | None = None


class AlertEvent(BaseModel):
    id: str
    watchlist_item_id: str
    alert_type: str
    severity: Literal["info", "warning", "critical"]
    title: str
    message: str
    trigger_value: float | None = None
    threshold_value: float | None = None
    status: AlertStatus
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class WatchlistItemsResponse(BaseModel):
    items: list[WatchlistItem]


class WatchlistCreateResponse(BaseModel):
    item: WatchlistItem


class WatchlistEvaluationResponse(BaseModel):
    status: Literal["completed"]
    watchlist_item: WatchlistItem
    created_alerts: list[AlertEvent]
    evaluated_rules: list[str]


class AlertEventsResponse(BaseModel):
    items: list[AlertEvent]


class AlertStatusUpdateRequest(BaseModel):
    status: AlertStatus


class AlertStatusUpdateResponse(BaseModel):
    alert: AlertEvent
