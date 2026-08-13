from __future__ import annotations

from pydantic import BaseModel, Field


class MonitoringAlertResponse(BaseModel):
    key: str
    severity: str
    summary: str
    runbook_id: str


class OperationsMonitoringResponse(BaseModel):
    status: str
    checked_at: str
    monitoring_mode: str
    alert_delivery: str
    monitoring_window_hours: int = Field(ge=1)
    database_ready: bool
    json_fallback_ready: bool
    queue_depth: int = Field(ge=0)
    oldest_queue_age_seconds: int | None = Field(default=None, ge=0)
    leased_or_running_jobs: int = Field(ge=0)
    dead_letter_jobs: int = Field(ge=0)
    active_workers: int = Field(ge=0)
    stale_workers: int = Field(ge=0)
    overdue_active_workers: int = Field(ge=0)
    provider_cleanup_failures: int = Field(ge=0)
    active_monitoring_schedules: int = Field(ge=0)
    due_monitoring_schedules: int = Field(ge=0)
    schedule_dispatch_enabled: bool
    retrieval_events: int = Field(ge=0)
    retrieval_empty_rate_percent: float | None = Field(default=None, ge=0, le=100)
    retrieval_average_latency_ms: float | None = Field(default=None, ge=0)
    retrieval_max_latency_ms: int | None = Field(default=None, ge=0)
    knowledge_storage_state: str
    pgvector_primary_enabled: bool
    slo_targets: dict[str, str]
    alerts: list[MonitoringAlertResponse]
