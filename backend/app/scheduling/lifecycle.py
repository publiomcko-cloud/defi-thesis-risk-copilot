from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job import JobModel
from app.models.scheduled_monitoring import MonitoringScheduleOccurrenceModel


_TERMINAL_OCCURRENCE_STATUSES = {"completed", "failed", "denied", "missed", "cancelled"}


def synchronize_schedule_occurrence(
    db: Session,
    job: JobModel,
    status: str,
    *,
    reason: str | None = None,
    now: datetime | None = None,
) -> None:
    """Mirror a controlled Phase 17 terminal transition into schedule history.

    Schedule occurrences never authorize a job transition. They are a durable,
    server-owned history projection for the one supported scheduled job type.
    A target executor may already have recorded a stronger terminal status such
    as ``denied``; a later generic worker failure must not overwrite it.
    """

    if job.job_type != "watchlist.evaluate":
        return
    context = job.input_json.get("_server_context", {}) if isinstance(job.input_json, dict) else {}
    occurrence_id = context.get("schedule_occurrence_id") if isinstance(context, dict) else None
    schedule_id = context.get("schedule_id") if isinstance(context, dict) else None
    if not isinstance(occurrence_id, str) or not isinstance(schedule_id, str):
        return
    occurrence = db.execute(
        select(MonitoringScheduleOccurrenceModel)
        .where(MonitoringScheduleOccurrenceModel.id == occurrence_id)
        .where(MonitoringScheduleOccurrenceModel.schedule_id == schedule_id)
        .where(MonitoringScheduleOccurrenceModel.job_id == job.id)
        .with_for_update()
    ).scalars().one_or_none()
    if occurrence is None:
        return
    if occurrence.status in _TERMINAL_OCCURRENCE_STATUSES and occurrence.status != status:
        return
    timestamp = now or datetime.now(UTC)
    occurrence.status = status
    if reason:
        occurrence.reason = reason[:64]
    occurrence.updated_at = timestamp
    if status in _TERMINAL_OCCURRENCE_STATUSES:
        occurrence.completed_at = timestamp
