from datetime import datetime
from typing import Literal

from pydantic import BaseModel


UserRole = Literal["admin", "common"]


class UserContext(BaseModel):
    id: str
    email: str
    role: UserRole
    is_active: bool = True
    auth_enabled: bool = True


class UserResponse(BaseModel):
    id: str
    email: str
    role: UserRole
    is_active: bool
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
