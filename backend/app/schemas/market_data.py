from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class MarketDataRequest(BaseModel):
    protocols: list[str] = Field(default_factory=list)
    market_url: str | None = None
    manual_inputs: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class MarketDataResponse(BaseModel):
    status: Literal["completed", "partial", "mocked"]
    source: str
    data: dict[str, Any]
    missing_fields: list[str]
    assumptions: list[str]
