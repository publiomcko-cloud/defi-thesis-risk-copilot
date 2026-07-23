from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.analysis_request import AnalysisRequestModel
from app.models.anonymous_session import AnonymousSessionModel
from app.models.alert_event import AlertEventModel
from app.models.report import ReportModel
from app.models.saved_thesis import SavedThesisModel
from app.models.user import UserModel
from app.models.watchlist_item import WatchlistItemModel


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
        db.commit()
    return counts


def _count(db, statement) -> int:
    return len(db.execute(statement).scalars().all())


if __name__ == "__main__":
    raise SystemExit(main())
