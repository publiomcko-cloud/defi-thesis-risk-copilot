from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


OrganizationRole = Literal["owner", "admin", "member", "viewer"]
AssignableOrganizationRole = Literal["admin", "member", "viewer"]
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


class OrganizationSeatStatusResponse(BaseModel):
    limit: int
    active: int
    reserved: int
    consumed: int
    remaining: int


class MembershipCreateRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    role: AssignableOrganizationRole = "member"

    model_config = ConfigDict(extra="forbid")


class MembershipUpdateRequest(BaseModel):
    role: AssignableOrganizationRole | None = None
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


class OwnershipTransferRequest(BaseModel):
    target_membership_id: str = Field(min_length=1, max_length=64)

    model_config = ConfigDict(extra="forbid")


class InvitationCreateRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    role: Literal["admin", "member", "viewer"] = "member"
    model_config = ConfigDict(extra="forbid")


class InvitationAcceptRequest(BaseModel):
    token: str = Field(min_length=32, max_length=512)
    model_config = ConfigDict(extra="forbid")


class InvitationResponse(BaseModel):
    id: str
    organization_id: str
    destination_email: str
    role: Literal["admin", "member", "viewer"]
    status: str
    expires_at: datetime
    created_at: datetime


class InvitationTokenResponse(InvitationResponse):
    token: str | None = None


class InvitationsResponse(BaseModel):
    items: list[InvitationResponse]


class OrganizationExportOrganization(BaseModel):
    id: str
    name: str
    slug: str
    status: str
    created_at: datetime
    updated_at: datetime


class OrganizationExportMembership(BaseModel):
    id: str
    user_id: str
    email: str
    role: OrganizationRole
    status: str
    created_at: datetime
    updated_at: datetime


class OrganizationExportInvitation(BaseModel):
    id: str
    destination_email: str
    role: Literal["admin", "member", "viewer"]
    status: str
    expires_at: datetime
    created_at: datetime
    accepted_at: datetime | None
    revoked_at: datetime | None
    supersedes_id: str | None


class OrganizationExportSeatProjection(BaseModel):
    limit: int
    active: int
    reserved: int
    consumed: int
    remaining: int


class OrganizationExportPlan(BaseModel):
    id: str
    key: str
    version: int


class OrganizationExportResponse(BaseModel):
    organization: OrganizationExportOrganization
    memberships: list[OrganizationExportMembership]
    invitations: list[OrganizationExportInvitation]
    seat_projection: OrganizationExportSeatProjection
    plan: OrganizationExportPlan
