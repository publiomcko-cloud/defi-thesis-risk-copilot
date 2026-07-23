from __future__ import annotations

import json
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.config import get_settings
from app.jobs.constants import SUPPORTED_JOB_TYPES


JobStatus = Literal[
    "queued",
    "leased",
    "running",
    "retry_wait",
    "completed",
    "failed",
    "cancel_requested",
    "cancelled",
    "dead_letter",
]
WorkerStatus = Literal["active", "disabled", "stale", "revoked"]
ArtifactStatus = Literal["pending_storage", "incomplete", "available", "deleted"]


class JobInputEnvelope(BaseModel):
    job_type: Literal["analysis.generate", "vast.session.start"]
    input_schema_version: str = Field(min_length=1, max_length=32)
    input_json: dict = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def enforce_input_size(self) -> "JobInputEnvelope":
        _enforce_json_bytes(self.input_json, get_settings().job_max_input_bytes, "input_json")
        return self


class JobSubmissionRequest(JobInputEnvelope):
    """Authenticated control-plane submission with server-derived ownership."""

    organization_id: str | None = Field(default=None, min_length=1, max_length=64)


class JobSubmissionResponse(BaseModel):
    job: "JobResponse"
    idempotent_replay: bool = False


class JobsResponse(BaseModel):
    items: list["JobResponse"]


class JobEventsResponse(BaseModel):
    items: list["JobEventResponse"]
    next_after_sequence: int | None = Field(default=None, ge=0)


class JobResultEnvelope(BaseModel):
    result_schema_version: str = Field(min_length=1, max_length=32)
    result_json: dict = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def enforce_result_size(self) -> "JobResultEnvelope":
        _enforce_json_bytes(self.result_json, get_settings().job_max_result_bytes, "result_json")
        return self


class WorkerRegistrationRequest(BaseModel):
    name: str = Field(min_length=3, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
    protocol_version: str = Field(min_length=1, max_length=32)
    software_version: str | None = Field(default=None, max_length=64)
    capabilities_json: dict = Field(default_factory=dict)
    allowed_job_types: list[str] = Field(min_length=1, max_length=8)
    organization_id: str | None = Field(default=None, max_length=64)
    max_concurrency: int = Field(default=1, ge=1, le=32)

    model_config = ConfigDict(extra="forbid")

    @field_validator("allowed_job_types")
    @classmethod
    def validate_job_types(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value) or not set(value).issubset(SUPPORTED_JOB_TYPES):
            raise ValueError("allowed_job_types must be distinct supported job types")
        return value

    @model_validator(mode="after")
    def enforce_capabilities_size(self) -> "WorkerRegistrationRequest":
        _enforce_json_bytes(self.capabilities_json, 8_192, "capabilities_json")
        return self


class WorkerCredentialCreateRequest(BaseModel):
    allowed_job_types: list[str] | None = Field(default=None, max_length=8)
    expires_at: datetime | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("allowed_job_types")
    @classmethod
    def validate_job_types(cls, value: list[str] | None) -> list[str] | None:
        if value is not None and (not value or len(set(value)) != len(value) or not set(value).issubset(SUPPORTED_JOB_TYPES)):
            raise ValueError("allowed_job_types must be distinct supported job types")
        return value


class WorkerCredentialRotateRequest(WorkerCredentialCreateRequest):
    revoke_previous: bool = False


class WorkerResponse(BaseModel):
    id: str
    name: str
    status: WorkerStatus
    protocol_version: str
    software_version: str | None
    capabilities_json: dict
    allowed_job_types: list[str]
    organization_id: str | None
    max_concurrency: int
    last_seen_at: datetime | None
    disabled_at: datetime | None
    created_at: datetime
    updated_at: datetime


class WorkerCredentialResponse(BaseModel):
    id: str
    worker_id: str
    token_prefix: str
    allowed_job_types: list[str]
    status: Literal["active", "revoked", "expired"]
    expires_at: datetime | None
    last_used_at: datetime | None
    rotated_from_id: str | None
    revoked_at: datetime | None
    created_by_user_id: str | None
    created_at: datetime


class WorkerCredentialIssuedResponse(BaseModel):
    credential: WorkerCredentialResponse
    token: str = Field(min_length=24)


class WorkerCredentialsResponse(BaseModel):
    items: list[WorkerCredentialResponse]


class WorkersResponse(BaseModel):
    items: list[WorkerResponse]


class JobResponse(BaseModel):
    id: str
    job_type: str
    status: JobStatus
    owner_user_id: str | None
    organization_id: str | None
    visibility: Literal["private", "organization"]
    progress_percent: int = Field(ge=0, le=100)
    progress_message: str | None
    attempt_count: int = Field(ge=0)
    max_attempts: int = Field(gt=0)
    result_resource_type: str | None
    result_resource_id: str | None
    queue_expires_at: datetime | None
    deadline_at: datetime | None
    replay_of_job_id: str | None
    created_at: datetime
    updated_at: datetime


class JobEventResponse(BaseModel):
    id: str
    job_id: str
    sequence_number: int = Field(ge=1)
    event_type: str
    message: str
    metadata_json: dict
    actor_user_id: str | None
    worker_id: str | None
    created_at: datetime


class ArtifactResponse(BaseModel):
    id: str
    job_id: str
    artifact_type: str
    status: ArtifactStatus
    owner_user_id: str | None
    organization_id: str | None
    visibility: Literal["private", "organization"]
    resource_type: str | None
    resource_id: str | None
    storage_backend: str | None
    storage_key: str | None
    content_type: str | None
    size_bytes: int | None = Field(default=None, ge=0)
    checksum: str | None
    retention_until: datetime | None
    created_at: datetime
    updated_at: datetime


def _enforce_json_bytes(value: dict, maximum: int, field_name: str) -> None:
    try:
        encoded = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must contain JSON-compatible values") from exc
    if len(encoded) > maximum:
        raise ValueError(f"{field_name} exceeds the configured size limit")
