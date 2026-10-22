from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.rag.source_urls import normalize_citation_url


class ResearchQuestionRequest(BaseModel):
    question: str = Field(min_length=10, max_length=2_000)

    model_config = ConfigDict(extra="forbid")


class ResearchRunLimits(BaseModel):
    max_passes: int = Field(ge=1, le=2)
    max_model_calls: int = Field(ge=1, le=2)
    max_tool_invocations: int = Field(ge=4, le=8)
    max_documents: int = Field(ge=1, le=8)
    token_budget: int = Field(ge=512, le=12_000)
    cost_ceiling_microusd: int = Field(ge=0)
    wall_time_seconds: int = Field(ge=5, le=25)

    model_config = ConfigDict(extra="forbid")


class ResearchToolTrace(BaseModel):
    tool: Literal["protocol_retrieval", "market_observation", "deterministic_risk", "report_synthesis"]
    pass_number: int = Field(ge=1, le=2)
    input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    output_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: Literal["completed", "fallback"]

    model_config = ConfigDict(extra="forbid")


class ResearchSourceObservation(BaseModel):
    source_id: str = Field(min_length=1, max_length=128)
    source_version_id: str | None = Field(default=None, max_length=128)
    source_version_checksum: str | None = Field(default=None, max_length=128)
    title: str = Field(min_length=1, max_length=255)
    source_type: str = Field(min_length=1, max_length=64)
    url: str | None = Field(default=None, max_length=2_048)
    protocol: str | None = Field(default=None, max_length=64)
    status: Literal["retrieved", "live", "cached", "manual", "manual_fallback", "unavailable"]
    observed_at: datetime
    source_timestamp: datetime | None = None
    freshness_note: str = Field(max_length=256)

    @field_validator("url", mode="before")
    @classmethod
    def safe_url(cls, value):
        return normalize_citation_url(value) if value is not None else None

    model_config = ConfigDict(extra="forbid")


class ResearchRunMetadata(BaseModel):
    run_id: str = Field(min_length=1, max_length=64)
    thesis_id: str = Field(min_length=1, max_length=64)
    question: str = Field(min_length=1, max_length=2_000)
    status: Literal["completed", "completed_with_gaps"]
    started_at: datetime
    completed_at: datetime
    elapsed_ms: int = Field(ge=0, le=120_000)
    pass_count: int = Field(ge=1, le=2)
    model_call_count: int = Field(ge=0, le=2)
    tool_invocation_count: int = Field(ge=1, le=8)
    source_document_count: int = Field(ge=0, le=8)
    limits: ResearchRunLimits
    tools: list[ResearchToolTrace] = Field(max_length=8)
    sources: list[ResearchSourceObservation] = Field(max_length=32)
    evidence_gaps: list[str] = Field(max_length=32)
    llm_used: bool
    llm_outcome: str = Field(max_length=64)
    llm_fallback_reason: str | None = Field(default=None, max_length=64)
    model_provider: str | None = Field(default=None, max_length=64)
    model_key: str | None = Field(default=None, max_length=128)
    route_version_id: str | None = Field(default=None, max_length=64)
    evaluation_run_id: str | None = Field(default=None, max_length=64)
    prompt_checksum: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    input_tokens: int | None = Field(default=None, ge=0, le=10_000_000)
    output_tokens: int | None = Field(default=None, ge=0, le=10_000_000)
    total_tokens: int | None = Field(default=None, ge=0, le=10_000_000)
    cost_microusd: int | None = Field(default=None, ge=0)
    provider_call_state: Literal[
        "not_attempted", "rejected_before_transmission", "response_received_rejected", "uncertain", "output_accepted"
    ] = "not_attempted"
    usage_status: Literal["not_applicable", "known", "partial", "unknown"] = "not_applicable"

    model_config = ConfigDict(extra="forbid")


class ResearchRunSummary(BaseModel):
    run_id: str
    thesis_id: str
    status: Literal["running", "completed", "failed", "interrupted", "uncertain"]
    question: str
    report_id: str | None = None
    error_code: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    metadata: ResearchRunMetadata | None = None
    idempotency_key: str = Field(min_length=8, max_length=128)
    provider_call_state: Literal[
        "not_attempted", "rejected_before_transmission", "response_received_rejected", "uncertain", "output_accepted"
    ] | None = None
    usage_status: Literal["not_applicable", "known", "partial", "unknown"] | None = None
    outcome_certainty: Literal["known_failure", "uncertain"] | None = None


class ResearchRunsResponse(BaseModel):
    items: list[ResearchRunSummary]
