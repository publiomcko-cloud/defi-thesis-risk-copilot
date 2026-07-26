from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.security import sanitize_audit_metadata
from app.jobs.constants import JOB_STATUSES, JOB_TRANSITIONS, TERMINAL_JOB_STATUSES
from app.models.job import JobEventModel, JobModel


class JobTransitionError(ValueError):
    """Raised when a caller attempts an invalid or immutable job transition."""


def transition_job(
    db: Session,
    job: JobModel,
    target_status: str,
    *,
    actor_user_id: str | None = None,
    worker_id: str | None = None,
    message: str | None = None,
    metadata: dict | None = None,
) -> JobModel:
    if target_status not in JOB_STATUSES:
        raise JobTransitionError("Unknown job status")
    if job.status in TERMINAL_JOB_STATUSES:
        raise JobTransitionError("Terminal jobs are immutable; create a linked replay job instead")
    if target_status not in JOB_TRANSITIONS[job.status]:
        raise JobTransitionError(f"Cannot transition job from {job.status} to {target_status}")

    now = datetime.now(UTC)
    previous_status = job.status
    job.status = target_status
    job.updated_at = now
    if target_status == "running" and job.started_at is None:
        job.started_at = now
    if target_status == "cancel_requested" and job.cancel_requested_at is None:
        job.cancel_requested_at = now
    if target_status == "completed":
        job.completed_at = now
        job.failed_at = None
    elif target_status in {"failed", "dead_letter"}:
        job.failed_at = now
        job.completed_at = None

    append_job_event(
        db,
        job,
        event_type=f"job.{target_status}",
        message=message or f"Job transitioned from {previous_status} to {target_status}.",
        actor_user_id=actor_user_id,
        worker_id=worker_id,
        metadata={"previous_status": previous_status, **(metadata or {})},
    )
    db.flush()
    return job


def append_job_event(
    db: Session,
    job: JobModel,
    *,
    event_type: str,
    message: str,
    actor_user_id: str | None = None,
    worker_id: str | None = None,
    metadata: dict | None = None,
) -> JobEventModel:
    """Append an ordered, redacted event while holding the parent job row lock."""

    locked_job = db.execute(
        select(JobModel).where(JobModel.id == job.id).with_for_update()
    ).scalars().one_or_none()
    if locked_job is None:
        raise JobTransitionError("Job no longer exists")
    next_sequence = (
        db.execute(
            select(func.coalesce(func.max(JobEventModel.sequence_number), 0)).where(
                JobEventModel.job_id == job.id
            )
        ).scalar_one()
        + 1
    )
    event = JobEventModel(
        id=f"jobevt_{uuid4().hex[:12]}",
        job_id=job.id,
        sequence_number=next_sequence,
        event_type=event_type[:64],
        message=message[:512],
        metadata_json=sanitize_audit_metadata(metadata or {}),
        actor_user_id=actor_user_id,
        worker_id=worker_id,
    )
    db.add(event)
    db.flush()
    return event
