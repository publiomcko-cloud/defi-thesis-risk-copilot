from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class MarketDataRequest(BaseModel):
    protocols: list[str] = Field(default_factory=list, max_length=10)
    market_url: str | None = Field(default=None, max_length=2048)
    manual_inputs: dict[str, Any] = Field(default_factory=dict, max_length=30)

    model_config = ConfigDict(extra="forbid")


class MarketDataResponse(BaseModel):
    status: Literal["completed", "partial", "mocked"]
    source: str
    data: dict[str, Any]
    missing_fields: list[str]
    assumptions: list[str]
