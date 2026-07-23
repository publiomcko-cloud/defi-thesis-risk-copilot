from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


Visibility = Literal["private", "organization"]


class ThesisCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    strategy_text: str = Field(min_length=10, max_length=10000)
    protocols: list[str] = Field(default_factory=list, max_length=20)
    assumptions: dict[str, Any] = Field(default_factory=dict)
    organization_id: str | None = None
    visibility: Visibility = "private"

    model_config = ConfigDict(extra="forbid")


class ThesisUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)
    strategy_text: str | None = Field(default=None, min_length=10, max_length=10000)
    protocols: list[str] | None = Field(default=None, max_length=20)
    assumptions: dict[str, Any] | None = None
    visibility: Visibility | None = None

    model_config = ConfigDict(extra="forbid")


class ThesisResponse(BaseModel):
    id: str
    owner_user_id: str
    organization_id: str | None = None
    title: str
    strategy_text: str
    protocols: list[str]
    assumptions: dict[str, Any]
    visibility: str
    created_at: datetime
    updated_at: datetime


class ThesesResponse(BaseModel):
    items: list[ThesisResponse]
