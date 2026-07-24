from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.jobs.constants import TERMINAL_JOB_STATUSES
from app.jobs.state import transition_job
from app.models.artifact import ArtifactModel
from app.models.analysis_request import AnalysisRequestModel
from app.models.job import JobModel
from app.models.report import ReportModel
from app.models.worker import WorkerCredentialModel, WorkerModel


def dispose_jobs_for_account_deletion(db: Session, user_id: str, *, now: datetime | None = None) -> int:
    return _dispose_jobs(
        db,
        select(JobModel).where(JobModel.owner_user_id == user_id),
        reason="owner_account_deleted",
        now=now,
    )


def dispose_jobs_for_organization_deletion(
    db: Session,
    organization_id: str,
    *,
    now: datetime | None = None,
) -> int:
    disposed = _dispose_jobs(
        db,
        select(JobModel).where(JobModel.organization_id == organization_id),
        reason="organization_deleted",
        now=now,
    )
    timestamp = now or datetime.now(UTC)
    for worker in db.execute(
        select(WorkerModel).where(WorkerModel.organization_id == organization_id)
    ).scalars().all():
        worker.status = "disabled"
        worker.disabled_at = timestamp
        worker.updated_at = timestamp
        for credential in db.execute(
            select(WorkerCredentialModel).where(WorkerCredentialModel.worker_id == worker.id)
        ).scalars().all():
            if credential.status == "active":
                credential.status = "revoked"
                credential.revoked_at = timestamp
    db.flush()
    return disposed


def revoke_jobs_for_authorization_change(
    db: Session,
    *,
    user_id: str | None = None,
    organization_id: str | None = None,
    reason: str,
    now: datetime | None = None,
) -> int:
    """Revoke only active execution; preserve completed organization resources."""

    statement = select(JobModel).where(JobModel.deleted_at.is_(None)).where(
        JobModel.status.in_({"queued", "retry_wait", "leased", "running"})
    )
    if organization_id is not None:
        statement = statement.where(JobModel.organization_id == organization_id)
    if user_id is not None:
        statement = statement.where(JobModel.owner_user_id == user_id)
    timestamp = now or datetime.now(UTC)
    affected = 0
    for job in db.execute(statement).scalars().all():
        if job.status in {"queued", "retry_wait"}:
            transition_job(
                db,
                job,
                "failed",
                message="Job authorization was revoked before worker execution.",
                metadata={"reason": reason},
            )
            job.error_code = "authorization_revoked"
            job.error_summary = "Job authorization was revoked before worker execution."
            mark_job_artifacts_incomplete(db, job.id, now=timestamp)
            from app.jobs.control_service import _release_capacity

            _release_capacity(db, job)
        else:
            transition_job(
                db,
                job,
                "cancel_requested",
                message="Job authorization was revoked during controlled execution.",
                metadata={"reason": reason},
            )
            job.error_code = "authorization_revoked"
            job.error_summary = "Job authorization was revoked during controlled execution."
        job.updated_at = timestamp
        affected += 1
    db.flush()
    return affected


def _dispose_jobs(db: Session, statement, *, reason: str, now: datetime | None) -> int:
    timestamp = now or datetime.now(UTC)
    records = db.execute(statement.where(JobModel.deleted_at.is_(None))).scalars().all()
    for job in records:
        if job.status not in TERMINAL_JOB_STATUSES:
            target = "cancel_requested" if job.status in {"leased", "running"} else "failed"
            transition_job(
                db,
                job,
                target,
                message="Job access was revoked before completion.",
                metadata={"reason": reason},
            )
            if target == "failed":
                job.error_code = "authorization_revoked"
                job.error_summary = "Job access was revoked before execution."
                from app.jobs.control_service import _release_capacity

                _release_capacity(db, job)
        # Running work remains recoverable until its worker acknowledges cancellation.
        # Marking it deleted here would hide it from lease-expiry recovery and could strand
        # a provider cleanup operation.
        if job.status in TERMINAL_JOB_STATUSES:
            job.deleted_at = timestamp
        job.updated_at = timestamp
        _dispose_job_artifacts(db, job.id, timestamp)
        _dispose_job_results(db, job, timestamp)
    db.flush()
    return len(records)


def mark_job_artifacts_incomplete(db: Session, job_id: str, *, now: datetime | None = None) -> None:
    """Preserve only an honest incomplete marker for non-durable job outputs."""

    timestamp = now or datetime.now(UTC)
    for artifact in db.execute(
        select(ArtifactModel)
        .where(ArtifactModel.job_id == job_id)
        .where(ArtifactModel.deleted_at.is_(None))
        .where(ArtifactModel.status.in_({"pending_storage", "incomplete"}))
    ).scalars().all():
        artifact.status = "incomplete"
        artifact.updated_at = timestamp


def _dispose_job_artifacts(db: Session, job_id: str, timestamp: datetime) -> None:
    for artifact in db.execute(
        select(ArtifactModel).where(ArtifactModel.job_id == job_id)
    ).scalars().all():
        artifact.status = "deleted" if artifact.status == "available" else "incomplete"
        artifact.deleted_at = timestamp
        artifact.updated_at = timestamp


def _dispose_job_results(db: Session, job: JobModel, timestamp: datetime) -> None:
    if job.result_resource_type != "report" or not job.result_resource_id:
        return
    report = db.get(ReportModel, job.result_resource_id)
    if report is not None and report.owner_user_id == job.owner_user_id:
        report.deleted_at = timestamp
    request = db.execute(
        select(AnalysisRequestModel).where(AnalysisRequestModel.source_job_id == job.id)
    ).scalars().one_or_none()
    if request is not None and request.owner_user_id == job.owner_user_id:
        request.deleted_at = timestamp
