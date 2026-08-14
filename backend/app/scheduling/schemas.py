from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.scheduling.calendar import get_timezone


ScheduleCadence = Literal["hourly", "six_hourly", "daily", "weekly"]
ScheduleStatus = Literal["active", "paused", "deleted"]
ScheduleOccurrenceStatus = Literal[
    "claimed",
    "queued",
    "running",
    "completed",
    "failed",
    "denied",
    "missed",
    "cancel_requested",
    "cancelled",
]


class MonitoringScheduleCreateRequest(BaseModel):
    target_type: Literal["watchlist.evaluate"]
    target_id: str = Field(min_length=7, max_length=64, pattern=r"^watch_[A-Za-z0-9_-]+$")
    cadence: ScheduleCadence
    timezone: str = Field(min_length=1, max_length=64)

    model_config = ConfigDict(extra="forbid")

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        get_timezone(value)
        return value


class MonitoringScheduleResponse(BaseModel):
    id: str
    target_type: Literal["watchlist.evaluate"]
    target_id: str
    cadence: ScheduleCadence
    timezone: str
    status: ScheduleStatus
    next_due_at: datetime
    paused_at: datetime | None
    last_dispatched_at: datetime | None
    created_at: datetime
    updated_at: datetime
    dispatch_enabled: bool


class MonitoringSchedulesResponse(BaseModel):
    items: list[MonitoringScheduleResponse]
    dispatch_enabled: bool


class MonitoringScheduleRunResponse(BaseModel):
    id: str
    scheduled_for: datetime
    status: ScheduleOccurrenceStatus
    reason: str | None
    job_id: str | None
    job_status: str | None
    claimed_at: datetime | None
    dispatched_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class MonitoringScheduleRunsResponse(BaseModel):
    items: list[MonitoringScheduleRunResponse]


class MonitoringScheduleActionResponse(BaseModel):
    schedule: MonitoringScheduleResponse


class MonitoringScheduleDispatchSummary(BaseModel):
    status: Literal["disabled", "completed"]
    claimed: int = Field(ge=0)
    queued: int = Field(ge=0)
    denied: int = Field(ge=0)
    missed: int = Field(ge=0)
    failures: int = Field(ge=0)
