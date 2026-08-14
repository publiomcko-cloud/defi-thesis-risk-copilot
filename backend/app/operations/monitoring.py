"""Read-only Phase 19D aggregate monitoring and local alert evaluation.

This module intentionally has no exporter, webhook, pager, or tenant detail.
Operators may inspect safe aggregates first, then later phases can attach an
approved delivery channel with its own access, retention, and outage policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.jobs.control_service import job_operations_summary
from app.models.job import JobModel
from app.models.knowledge import KnowledgeRetrievalEventModel
from app.models.scheduled_monitoring import MonitoringScheduleModel
from app.models.worker import WorkerModel
from app.operations.schemas import MonitoringAlertResponse, OperationsMonitoringResponse
from app.rag.vector_store import JsonVectorStore


_PENDING_JOB_STATUSES = ("queued", "retry_wait")
_RUNNING_JOB_STATUSES = ("leased", "running", "cancel_requested")


@dataclass(frozen=True)
class _Alert:
    key: str
    severity: str
    summary: str
    runbook_id: str


def operations_monitoring_snapshot(
    db: Session,
    settings: Settings | None = None,
    *,
    now: datetime | None = None,
) -> OperationsMonitoringResponse:
    """Return bounded operational aggregates without identifiers or content."""
    settings = settings or get_settings()
    now = now or datetime.now(UTC)
    database_ready = _database_ready(db)
    json_fallback_ready = JsonVectorStore().path.exists()
    operations = job_operations_summary(db)
    oldest_queue_created_at = db.execute(
        select(func.min(JobModel.created_at))
        .where(JobModel.deleted_at.is_(None))
        .where(JobModel.status.in_(_PENDING_JOB_STATUSES))
    ).scalar_one()
    oldest_queue_age_seconds = _age_seconds(oldest_queue_created_at, now)
    overdue_active_workers = _overdue_active_workers(db, settings, now)
    retrieval = _retrieval_metrics(db, settings, now)
    storage_state = _knowledge_storage_state(settings)
    active_monitoring_schedules = int(
        db.execute(
            select(func.count())
            .select_from(MonitoringScheduleModel)
            .where(MonitoringScheduleModel.status == "active")
            .where(MonitoringScheduleModel.deleted_at.is_(None))
        ).scalar_one()
        or 0
    )
    due_monitoring_schedules = int(
        db.execute(
            select(func.count())
            .select_from(MonitoringScheduleModel)
            .where(MonitoringScheduleModel.status == "active")
            .where(MonitoringScheduleModel.deleted_at.is_(None))
            .where(MonitoringScheduleModel.next_due_at <= now)
        ).scalar_one()
        or 0
    )
    alerts = _evaluate_alerts(
        settings,
        database_ready=database_ready,
        json_fallback_ready=json_fallback_ready,
        queue_depth=operations.queued_jobs,
        oldest_queue_age_seconds=oldest_queue_age_seconds,
        dead_letter_jobs=operations.dead_letter_jobs,
        stale_workers=operations.stale_workers + overdue_active_workers,
        provider_cleanup_failures=operations.provider_cleanup_failures,
        retrieval_events=retrieval.events,
        retrieval_empty_rate_percent=retrieval.empty_rate_percent,
        retrieval_max_latency_ms=retrieval.max_latency_ms,
    ) if settings.operations_alert_evaluation_enabled else []
    status = "ready" if database_ready and json_fallback_ready else "degraded"
    if any(alert.severity == "critical" for alert in alerts):
        status = "degraded"
    return OperationsMonitoringResponse(
        status=status,
        checked_at=now.isoformat(),
        monitoring_mode="local_aggregate" if settings.operations_monitoring_enabled else "disabled",
        alert_delivery="not_implemented",
        monitoring_window_hours=settings.operations_monitoring_window_hours,
        database_ready=database_ready,
        json_fallback_ready=json_fallback_ready,
        queue_depth=operations.queued_jobs,
        oldest_queue_age_seconds=oldest_queue_age_seconds,
        leased_or_running_jobs=operations.leased_or_running_jobs,
        dead_letter_jobs=operations.dead_letter_jobs,
        active_workers=operations.active_workers,
        stale_workers=operations.stale_workers,
        overdue_active_workers=overdue_active_workers,
        provider_cleanup_failures=operations.provider_cleanup_failures,
        active_monitoring_schedules=active_monitoring_schedules,
        due_monitoring_schedules=due_monitoring_schedules,
        schedule_dispatch_enabled=settings.schedule_dispatch_enabled,
        retrieval_events=retrieval.events,
        retrieval_empty_rate_percent=retrieval.empty_rate_percent,
        retrieval_average_latency_ms=retrieval.average_latency_ms,
        retrieval_max_latency_ms=retrieval.max_latency_ms,
        knowledge_storage_state=storage_state,
        pgvector_primary_enabled=settings.knowledge_pgvector_primary_enabled,
        slo_targets={
            "availability": "99.5% measured by approved external synthetics",
            "queue_age": f"under {settings.operations_alert_queue_age_seconds}s",
            "retrieval_latency": f"under {settings.operations_alert_retrieval_latency_ms}ms",
            "retrieval_empty_rate": f"under {settings.operations_alert_retrieval_empty_rate_percent:g}%",
        },
        alerts=[
            MonitoringAlertResponse(
                key=alert.key,
                severity=alert.severity,
                summary=alert.summary,
                runbook_id=alert.runbook_id,
            )
            for alert in alerts
        ],
    )


@dataclass(frozen=True)
class _RetrievalMetrics:
    events: int
    empty_rate_percent: float | None
    average_latency_ms: float | None
    max_latency_ms: int | None


def _retrieval_metrics(db: Session, settings: Settings, now: datetime) -> _RetrievalMetrics:
    since = now - timedelta(hours=settings.operations_monitoring_window_hours)
    rows = db.execute(
        select(KnowledgeRetrievalEventModel.latency_ms, KnowledgeRetrievalEventModel.retrieved_chunk_ids)
        .where(KnowledgeRetrievalEventModel.created_at >= since)
        .order_by(KnowledgeRetrievalEventModel.created_at.desc())
        .limit(settings.operations_monitoring_event_limit)
    ).all()
    if not rows:
        return _RetrievalMetrics(events=0, empty_rate_percent=None, average_latency_ms=None, max_latency_ms=None)
    latencies = [int(row.latency_ms) for row in rows]
    empty = sum(1 for row in rows if not row.retrieved_chunk_ids)
    return _RetrievalMetrics(
        events=len(rows),
        empty_rate_percent=round(empty * 100 / len(rows), 2),
        average_latency_ms=round(sum(latencies) / len(latencies), 2),
        max_latency_ms=max(latencies),
    )


def _overdue_active_workers(db: Session, settings: Settings, now: datetime) -> int:
    threshold = now - timedelta(seconds=settings.worker_stale_seconds)
    return int(
        db.execute(
            select(func.count())
            .select_from(WorkerModel)
            .where(WorkerModel.status == "active")
            .where(WorkerModel.last_seen_at.is_not(None))
            .where(WorkerModel.last_seen_at < threshold)
        ).scalar_one()
        or 0
    )


def _database_ready(db: Session) -> bool:
    try:
        db.execute(text("select 1"))
        return True
    except Exception:
        return False


def _knowledge_storage_state(settings: Settings) -> str:
    if not settings.knowledge_storage_enabled:
        return "disabled"
    if settings.knowledge_pgvector_primary_enabled:
        return "pgvector_primary"
    if settings.knowledge_shadow_retrieval_enabled:
        return "shadow"
    return "storage_only"


def _age_seconds(value: datetime | None, now: datetime) -> int | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return max(0, int((now - value).total_seconds()))


def _evaluate_alerts(
    settings: Settings,
    *,
    database_ready: bool,
    json_fallback_ready: bool,
    queue_depth: int,
    oldest_queue_age_seconds: int | None,
    dead_letter_jobs: int,
    stale_workers: int,
    provider_cleanup_failures: int,
    retrieval_events: int,
    retrieval_empty_rate_percent: float | None,
    retrieval_max_latency_ms: int | None,
) -> list[_Alert]:
    alerts: list[_Alert] = []

    def add(condition: bool, key: str, severity: str, summary: str, runbook_id: str) -> None:
        if condition and all(existing.key != key for existing in alerts):
            alerts.append(_Alert(key=key, severity=severity, summary=summary, runbook_id=runbook_id))

    add(not database_ready, "database_unready", "critical", "Database readiness check failed.", "operations.database")
    add(not json_fallback_ready, "json_fallback_missing", "critical", "JSON RAG fallback is unavailable.", "operations.retrieval")
    add(queue_depth >= settings.operations_alert_queue_depth, "queue_depth", "warning", "Queued work exceeded the configured threshold.", "operations.queue")
    add(
        oldest_queue_age_seconds is not None
        and oldest_queue_age_seconds >= settings.operations_alert_queue_age_seconds,
        "queue_age",
        "warning",
        "Oldest queued work exceeded the configured age threshold.",
        "operations.queue",
    )
    add(dead_letter_jobs >= settings.operations_alert_dead_letter_count, "dead_letters", "warning", "Dead-letter jobs require review.", "operations.jobs")
    add(stale_workers >= settings.operations_alert_stale_worker_count, "stale_workers", "warning", "Worker freshness threshold exceeded.", "operations.workers")
    add(provider_cleanup_failures > 0, "provider_cleanup", "warning", "Provider cleanup failures require review.", "operations.providers")
    add(
        retrieval_events > 0
        and retrieval_empty_rate_percent is not None
        and retrieval_empty_rate_percent >= settings.operations_alert_retrieval_empty_rate_percent,
        "retrieval_empty_rate",
        "warning",
        "Retrieval empty-rate threshold exceeded.",
        "operations.retrieval",
    )
    add(
        retrieval_events > 0
        and retrieval_max_latency_ms is not None
        and retrieval_max_latency_ms >= settings.operations_alert_retrieval_latency_ms,
        "retrieval_latency",
        "warning",
        "Retrieval latency threshold exceeded.",
        "operations.retrieval",
    )
    return alerts
