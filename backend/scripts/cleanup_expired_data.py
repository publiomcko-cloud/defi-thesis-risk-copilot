from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.analysis_request import AnalysisRequestModel
from app.models.anonymous_session import AnonymousSessionModel
from app.models.alert_event import AlertEventModel
from app.models.artifact import ArtifactModel
from app.models.job import JobAttemptModel, JobEventModel, JobModel
from app.models.report import ReportModel
from app.models.saved_thesis import SavedThesisModel
from app.models.user import UserModel
from app.models.watchlist_item import WatchlistItemModel
from app.models.worker import WorkerCredentialModel
from app.jobs.constants import TERMINAL_JOB_STATUSES


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean expired anonymous and soft-deleted data.")
    parser.add_argument("--dry-run", action="store_true", help="Report eligible row counts without deleting.")
    args = parser.parse_args()
    counts = cleanup_expired_data(dry_run=args.dry_run)
    print(counts)
    return 0


def cleanup_expired_data(dry_run: bool = False) -> dict[str, int]:
    settings = get_settings()
    now = datetime.now(UTC)
    deleted_cutoff = now - timedelta(days=settings.deleted_account_retention_days)
    job_event_cutoff = now - timedelta(days=settings.job_event_retention_days)
    terminal_job_cutoff = now - timedelta(days=settings.job_terminal_retention_days)
    counts: dict[str, int] = {}
    with SessionLocal() as db:
        counts["expired_anonymous_sessions"] = _count(
            db,
            select(AnonymousSessionModel).where(AnonymousSessionModel.expires_at <= now),
        )
        counts["expired_reports"] = _count(
            db,
            select(ReportModel)
            .where(ReportModel.visibility != "public_demo")
            .where(ReportModel.expires_at.is_not(None))
            .where(ReportModel.expires_at <= now),
        )
        counts["expired_analysis_requests"] = _count(
            db,
            select(AnalysisRequestModel)
            .where(AnalysisRequestModel.visibility != "public_demo")
            .where(AnalysisRequestModel.expires_at.is_not(None))
            .where(AnalysisRequestModel.expires_at <= now),
        )
        counts["expired_watchlists"] = _count(
            db,
            select(WatchlistItemModel)
            .where(WatchlistItemModel.visibility != "public_demo")
            .where(WatchlistItemModel.expires_at.is_not(None))
            .where(WatchlistItemModel.expires_at <= now),
        )
        counts["soft_deleted_theses"] = _count(
            db,
            select(SavedThesisModel)
            .where(SavedThesisModel.deleted_at.is_not(None))
            .where(SavedThesisModel.deleted_at <= deleted_cutoff),
        )
        counts["deleted_users_ready_for_retention"] = _count(
            db,
            select(UserModel)
            .where(UserModel.deleted_at.is_not(None))
            .where(UserModel.deleted_at <= deleted_cutoff),
        )
        terminal_jobs = (
            select(JobModel)
            .where(JobModel.status.in_(TERMINAL_JOB_STATUSES))
            .where(JobModel.updated_at <= terminal_job_cutoff)
        )
        counts["terminal_jobs_ready_for_retention"] = _count(db, terminal_jobs)
        counts["expired_job_events"] = _count(
            db,
            select(JobEventModel).where(JobEventModel.created_at <= job_event_cutoff),
        )
        counts["expired_worker_credentials"] = _count(
            db,
            select(WorkerCredentialModel)
            .where(WorkerCredentialModel.status == "active")
            .where(WorkerCredentialModel.expires_at.is_not(None))
            .where(WorkerCredentialModel.expires_at <= now),
        )
        counts["expired_artifacts"] = _count(
            db,
            select(ArtifactModel)
            .where(ArtifactModel.retention_until.is_not(None))
            .where(ArtifactModel.retention_until <= now)
            .where(ArtifactModel.deleted_at.is_(None)),
        )
        if dry_run:
            return counts
        expired_watchlist_ids = [
            item.id
            for item in db.execute(
                select(WatchlistItemModel)
                .where(WatchlistItemModel.visibility != "public_demo")
                .where(WatchlistItemModel.expires_at.is_not(None))
                .where(WatchlistItemModel.expires_at <= now)
            ).scalars().all()
        ]
        if expired_watchlist_ids:
            db.execute(delete(AlertEventModel).where(AlertEventModel.watchlist_item_id.in_(expired_watchlist_ids)))
        db.execute(delete(AnonymousSessionModel).where(AnonymousSessionModel.expires_at <= now))
        db.execute(
            delete(ReportModel)
            .where(ReportModel.visibility != "public_demo")
            .where(ReportModel.expires_at.is_not(None))
            .where(ReportModel.expires_at <= now)
        )
        db.execute(
            delete(AnalysisRequestModel)
            .where(AnalysisRequestModel.visibility != "public_demo")
            .where(AnalysisRequestModel.expires_at.is_not(None))
            .where(AnalysisRequestModel.expires_at <= now)
        )
        db.execute(
            delete(WatchlistItemModel)
            .where(WatchlistItemModel.visibility != "public_demo")
            .where(WatchlistItemModel.expires_at.is_not(None))
            .where(WatchlistItemModel.expires_at <= now)
        )
        db.execute(
            delete(SavedThesisModel)
            .where(SavedThesisModel.deleted_at.is_not(None))
            .where(SavedThesisModel.deleted_at <= deleted_cutoff)
        )
        deleted_users = db.execute(
            select(UserModel)
            .where(UserModel.deleted_at.is_not(None))
            .where(UserModel.deleted_at <= deleted_cutoff)
        ).scalars().all()
        for user in deleted_users:
            user.email = f"deleted-{user.id}@deleted.local"
            user.auth_subject = None
            user.access_token_hash = None
            user.account_status = "deleted"
            user.is_active = False
            user.updated_at = now
        expiring_credentials = db.execute(
            select(WorkerCredentialModel)
            .where(WorkerCredentialModel.status == "active")
            .where(WorkerCredentialModel.expires_at.is_not(None))
            .where(WorkerCredentialModel.expires_at <= now)
        ).scalars().all()
        for credential in expiring_credentials:
            credential.status = "expired"
            credential.revoked_at = now
        expiring_artifacts = db.execute(
            select(ArtifactModel)
            .where(ArtifactModel.retention_until.is_not(None))
            .where(ArtifactModel.retention_until <= now)
            .where(ArtifactModel.deleted_at.is_(None))
        ).scalars().all()
        for artifact in expiring_artifacts:
            artifact.status = "deleted"
            artifact.deleted_at = now
            artifact.updated_at = now
        terminal_job_ids = [item.id for item in db.execute(terminal_jobs).scalars().all()]
        if terminal_job_ids:
            db.execute(delete(ArtifactModel).where(ArtifactModel.job_id.in_(terminal_job_ids)))
            db.execute(delete(JobAttemptModel).where(JobAttemptModel.job_id.in_(terminal_job_ids)))
            db.execute(delete(JobEventModel).where(JobEventModel.job_id.in_(terminal_job_ids)))
            db.execute(delete(JobModel).where(JobModel.id.in_(terminal_job_ids)))
        db.execute(delete(JobEventModel).where(JobEventModel.created_at <= job_event_cutoff))
        db.commit()
    return counts


def _count(db, statement) -> int:
    return len(db.execute(statement).scalars().all())


if __name__ == "__main__":
    raise SystemExit(main())
