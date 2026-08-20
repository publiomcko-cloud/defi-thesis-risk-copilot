from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.notifications.registry import CATEGORIES, SEVERITIES


NotificationCategory = Literal["monitoring.risk_alert", "schedule.status", "job.status", "account.lifecycle"]
NotificationSeverity = Literal["informational", "warning", "critical"]


class NotificationPreferenceResponse(BaseModel):
    categories: dict[NotificationCategory, bool]
    minimum_severity: dict[NotificationCategory, NotificationSeverity]
    timezone: str
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    daily_digest_enabled: bool
    mandatory_categories: list[NotificationCategory]


class NotificationPreferenceUpdateRequest(BaseModel):
    categories: dict[NotificationCategory, bool] | None = None
    minimum_severity: dict[NotificationCategory, NotificationSeverity] | None = None
    timezone: str | None = Field(default=None, max_length=64)
    quiet_hours_start: str | None = Field(default=None, pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")
    quiet_hours_end: str | None = Field(default=None, pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")
    daily_digest_enabled: bool | None = None

    model_config = ConfigDict(extra="forbid")

    def supplied(self, field: str) -> bool:
        """Distinguish an omitted PATCH field from an explicit JSON null."""

        return field in self.model_fields_set

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, value):
        if value is not None and any(key not in CATEGORIES for key in value):
            raise ValueError("Unsupported notification category")
        return value

    @field_validator("minimum_severity")
    @classmethod
    def validate_severities(cls, value):
        if value is not None and (
            any(key not in CATEGORIES for key in value) or any(severity not in SEVERITIES for severity in value.values())
        ):
            raise ValueError("Unsupported notification severity")
        return value


class NotificationResponse(BaseModel):
    id: str
    category: NotificationCategory
    severity: NotificationSeverity
    title: str
    body: str
    source_type: str
    source_id: str
    navigation: dict
    policy_outcome: str
    available_at: datetime | None
    read_at: datetime | None
    created_at: datetime
    expires_at: datetime


class NotificationsResponse(BaseModel):
    items: list[NotificationResponse]
    next_cursor: str | None = None


class NotificationUnreadCountResponse(BaseModel):
    unread_count: int


class NotificationActionResponse(BaseModel):
    notification: NotificationResponse


class NotificationMarkAllReadResponse(BaseModel):
    updated_count: int
