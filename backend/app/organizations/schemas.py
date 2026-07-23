from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


OrganizationRole = Literal["owner", "admin", "member", "viewer"]
MembershipStatus = Literal["active", "pending", "removed"]


class OrganizationCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str | None = Field(default=None, min_length=2, max_length=128)

    model_config = ConfigDict(extra="forbid")


class OrganizationUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    status: Literal["active", "disabled"] | None = None

    model_config = ConfigDict(extra="forbid")


class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    status: str
    created_by_user_id: str
    created_at: datetime
    updated_at: datetime


class OrganizationsResponse(BaseModel):
    items: list[OrganizationResponse]


class MembershipCreateRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    role: OrganizationRole = "member"

    model_config = ConfigDict(extra="forbid")


class MembershipUpdateRequest(BaseModel):
    role: OrganizationRole | None = None
    status: MembershipStatus | None = None

    model_config = ConfigDict(extra="forbid")


class MembershipResponse(BaseModel):
    id: str
    organization_id: str
    user_id: str
    email: str
    role: OrganizationRole
    status: str
    created_at: datetime
    updated_at: datetime


class MembershipsResponse(BaseModel):
    items: list[MembershipResponse]
