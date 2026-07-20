from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


UserRole = Literal["admin", "common"]
PlatformRole = Literal["admin", "user"]
AccountStatus = Literal["active", "inactive", "deleted"]
OrganizationRole = Literal["owner", "admin", "member", "viewer"]


class UserContext(BaseModel):
    id: str
    email: str
    role: UserRole
    platform_role: PlatformRole = "user"
    plan: str = "free"
    is_active: bool = True
    auth_enabled: bool = True
    auth_provider: str = "legacy_local"
    auth_subject: str | None = None
    email_verified: bool = False
    anonymous_session_id: str | None = None

    @property
    def is_admin(self) -> bool:
        return self.role == "admin" or self.platform_role == "admin"


class UserResponse(BaseModel):
    id: str
    email: str
    role: UserRole
    platform_role: PlatformRole = "user"
    account_status: AccountStatus = "active"
    plan: str = "free"
    is_active: bool
    auth_provider: str = "legacy_local"
    email_verified_at: datetime | None = None
    last_login_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AuditEventResponse(BaseModel):
    id: str
    actor_user_id: str | None
    action: str
    resource_type: str
    resource_id: str | None
    metadata_json: dict
    created_at: datetime


class AuditEventsResponse(BaseModel):
    items: list[AuditEventResponse]


class AuthLogoutResponse(BaseModel):
    status: Literal["logged_out"]


class AccountResponse(BaseModel):
    user: UserResponse
    memberships: list[dict] = Field(default_factory=list)


class AccountExportResponse(BaseModel):
    format_version: str = "phase16.account_export.v1"
    exported_at: datetime
    profile: dict
    memberships: list[dict]
    saved_theses: list[dict]
    reports: list[dict]
    watchlists: list[dict]
    alerts: list[dict]
    consents: list[dict]
    audit_events: list[dict]


class AccountDeleteRequest(BaseModel):
    confirmation: Literal["DELETE"]

    model_config = ConfigDict(extra="forbid")


class AccountDeleteResponse(BaseModel):
    status: Literal["deleted", "pending_provider_deletion"]
    message: str
