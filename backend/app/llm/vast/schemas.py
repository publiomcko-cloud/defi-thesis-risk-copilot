from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


VastSessionStatus = Literal[
    "idle",
    "searching_offer",
    "renting_instance",
    "booting",
    "starting_model_server",
    "health_checking",
    "ready",
    "serving_request",
    "cleanup",
    "destroyed",
    "offer_not_found",
    "rent_failed",
    "boot_timeout",
    "container_failed",
    "model_health_failed",
    "request_failed",
    "cleanup_failed",
]

TERMINAL_STATUSES = {
    "destroyed",
    "offer_not_found",
    "rent_failed",
    "boot_timeout",
    "container_failed",
    "model_health_failed",
    "request_failed",
    "cleanup_failed",
}

ACTIVE_STATUSES = {
    "searching_offer",
    "renting_instance",
    "booting",
    "starting_model_server",
    "health_checking",
    "ready",
    "serving_request",
    "cleanup",
}


class VastOffer(BaseModel):
    id: str
    gpu_name: str
    hourly_cost_usd: float
    gpu_ram_gb: float
    disk_gb: float | None = None
    verified: bool | None = None
    rentable: bool = True
    public_endpoint_url: str | None = None
    metadata: dict = Field(default_factory=dict)


class VastConfigResponse(BaseModel):
    enabled: bool
    dry_run: bool
    api_base_url: str
    credential_name: str
    has_env_api_key: bool
    max_hourly_cost_usd: float
    max_session_minutes: int
    max_active_instances: int
    gpu_allowlist: list[str]
    min_gpu_ram_gb: int
    disk_gb: int
    require_verified: bool
    auto_destroy: bool
    idle_timeout_seconds: int
    image: str
    model: str
    container_port: int
    startup_timeout_seconds: int
    poll_interval_seconds: int


class VastConfigUpdateRequest(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class VastStartSessionRequest(BaseModel):
    model: str | None = Field(default=None, max_length=255)
    image: str | None = Field(default=None, max_length=512)
    allow_remote_gpu: bool = False
    warm_instance: bool = False


class VastTestPromptRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=5000)


class VastTestPromptResponse(BaseModel):
    session: "VastSessionResponse"
    output: str
    provider: str
    model: str


class VastSessionResponse(BaseModel):
    id: str
    status: str
    provider: str
    vast_instance_id: str | None
    vast_contract_id: str | None
    offer_id: str | None
    model: str
    image: str
    gpu_name: str | None
    hourly_cost_usd: float | None
    max_runtime_minutes: int
    container_port: int
    public_endpoint_url: str | None
    health_status: str | None
    last_error: str | None
    created_by: str
    created_at: datetime
    ready_at: datetime | None
    last_used_at: datetime | None
    destroyed_at: datetime | None
    cleanup_attempted_at: datetime | None
    metadata_json: dict


class VastSessionListResponse(BaseModel):
    items: list[VastSessionResponse]


class VastSessionActionResponse(BaseModel):
    session: VastSessionResponse


class VastCleanupResponse(BaseModel):
    cleaned_count: int
    failed_count: int
    sessions: list[VastSessionResponse]
