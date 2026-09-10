from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.simulation.schemas import SimulationRequest


ResearchOrigin = Literal["deterministic", "user_recorded", "model_assisted"]
ThesisStatus = Literal["draft", "active", "challenged", "invalidated", "archived"]
AssumptionState = Literal["active", "weakened", "invalidated", "resolved"]
CatalystStatus = Literal["upcoming", "occurred", "missed", "cancelled", "unknown"]
DatePrecision = Literal["exact", "month", "window", "unknown"]


class EvidenceReferenceRequest(BaseModel):
    report_id: str | None = Field(default=None, min_length=1, max_length=64)
    citation_ids: list[str] = Field(default_factory=list, max_length=24)
    unverified_reference: str | None = Field(default=None, min_length=1, max_length=255)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def require_classification(self) -> "EvidenceReferenceRequest":
        if self.report_id is None and self.unverified_reference is None:
            raise ValueError("An evidence reference must be report-backed or explicitly unverified")
        if self.report_id is None and self.citation_ids:
            raise ValueError("citation_ids require report_id")
        return self


class ThesisRevisionResponse(BaseModel):
    id: str
    thesis_id: str
    revision_number: int
    title: str
    strategy_text: str
    protocols: list[str]
    assumptions_snapshot: dict
    explicit_assumption_ids: list[str]
    status: ThesisStatus
    actor_user_id: str | None
    origin: Literal["user_recorded", "legacy_baseline", "server_recorded"]
    change_reason: str | None
    created_at: datetime
    origin_type: Literal["user_recorded"] = "user_recorded"


class ThesisHistoryResponse(BaseModel):
    items: list[ThesisRevisionResponse]


class ThesisStatusUpdateRequest(BaseModel):
    status: ThesisStatus
    expected_revision: int | None = Field(default=None, ge=1)
    change_reason: str | None = Field(default=None, min_length=1, max_length=240)

    model_config = ConfigDict(extra="forbid")


class ResearchAssumptionCreateRequest(BaseModel):
    statement: str = Field(min_length=3, max_length=4000)
    state: AssumptionState = "active"
    evidence_references: list[EvidenceReferenceRequest] = Field(default_factory=list, max_length=24)

    model_config = ConfigDict(extra="forbid")


class ResearchAssumptionUpdateRequest(ResearchAssumptionCreateRequest):
    expected_revision: int = Field(ge=1)


class ResearchAssumptionResponse(BaseModel):
    id: str
    thesis_id: str
    revision_number: int
    statement: str
    state: AssumptionState
    evidence_references: list[dict]
    supersedes_record_id: str | None
    actor_user_id: str | None
    created_at: datetime
    origin_type: Literal["user_recorded"] = "user_recorded"


class ResearchAssumptionsResponse(BaseModel):
    items: list[ResearchAssumptionResponse]


class CatalystCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    expected_date: date | None = None
    window_start: date | None = None
    window_end: date | None = None
    date_precision: DatePrecision = "unknown"
    status: CatalystStatus = "upcoming"
    uncertainty: str | None = Field(default=None, max_length=512)
    evidence_references: list[EvidenceReferenceRequest] = Field(default_factory=list, max_length=24)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_date_shape(self) -> "CatalystCreateRequest":
        if self.date_precision == "exact" and self.expected_date is None:
            raise ValueError("exact date precision requires expected_date")
        if self.date_precision == "month" and self.expected_date is None:
            raise ValueError("month date precision requires expected_date")
        if self.date_precision == "window":
            if self.window_start is None or self.window_end is None or self.window_start > self.window_end:
                raise ValueError("window date precision requires an ordered date window")
        if self.date_precision == "unknown" and any((self.expected_date, self.window_start, self.window_end)):
            raise ValueError("unknown date precision cannot include a date")
        return self


class CatalystUpdateRequest(CatalystCreateRequest):
    expected_revision: int = Field(ge=1)


class CatalystResponse(BaseModel):
    id: str
    thesis_id: str
    title: str
    description: str | None
    expected_date: date | None
    window_start: date | None
    window_end: date | None
    date_precision: DatePrecision
    status: CatalystStatus
    uncertainty: str | None
    evidence_references: list[dict]
    revision_number: int
    actor_user_id: str | None
    created_at: datetime
    updated_at: datetime
    origin_type: Literal["user_recorded"] = "user_recorded"


class CatalystsResponse(BaseModel):
    items: list[CatalystResponse]


class ReportComparisonRequest(BaseModel):
    left_report_id: str = Field(min_length=1, max_length=64)
    right_report_id: str = Field(min_length=1, max_length=64)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def distinct_reports(self) -> "ReportComparisonRequest":
        if self.left_report_id == self.right_report_id:
            raise ValueError("Reports must be distinct")
        return self


class ReportComparisonResponse(BaseModel):
    id: str
    left_report_id: str
    right_report_id: str
    created_at: datetime
    schema_version: str
    changes: dict
    uncertainty: list[str]
    origin_type: Literal["deterministic"] = "deterministic"


class SourceStalenessResponse(BaseModel):
    report_id: str
    items: list[dict]
    origin_type: Literal["deterministic"] = "deterministic"


class ScenarioComparisonRequest(BaseModel):
    left: SimulationRequest
    right: SimulationRequest

    model_config = ConfigDict(extra="forbid")


class ScenarioComparisonResponse(BaseModel):
    changes: list[dict]
    missing_data: list[str]
    disclaimer: str
    origin_type: Literal["deterministic"] = "deterministic"


class MonitoringQuestionsResponse(BaseModel):
    thesis_id: str
    questions: list[str]
    uncertainty: list[str]
    origin_type: Literal["deterministic"] = "deterministic"
