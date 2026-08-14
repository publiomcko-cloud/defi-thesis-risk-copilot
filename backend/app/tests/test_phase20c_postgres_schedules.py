from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import sessionmaker

from app.auth.schemas import UserContext
from app.auth.service import create_user, user_context
from app.core.config import get_settings
from app.db.session import create_database_engine
from app.jobs.control_service import _release_capacity
from app.jobs.constants import TERMINAL_JOB_STATUSES
from app.jobs.schemas import WorkerLeaseRequest
from app.jobs.worker_protocol import WorkerIdentity, claim_next_job, recover_expired_jobs, start_job
from app.models.alert_event import AlertEventModel
from app.models.job import JobCapacityReservationModel, JobModel
from app.models.scheduled_monitoring import MonitoringScheduleModel, MonitoringScheduleOccurrenceModel
from app.models.usage_quota import UsageQuotaModel
from app.models.user import UserModel
from app.models.watchlist_item import WatchlistItemModel
from app.models.worker import WorkerCredentialModel, WorkerModel
from app.quotas.service import (
    ACTION_SCHEDULED_WATCHLIST_EVALUATION,
    SCHEDULED_WATCHLIST_EVALUATIONS_PER_DAY,
    _day_window,
)
from app.scheduling.executor import WatchlistEvaluationJobExecutor
from app.scheduling.schemas import MonitoringScheduleCreateRequest
from app.scheduling.service import create_schedule, delete_schedule, dispatch_due_schedules, pause_schedule
from app.watchlist.schemas import WatchlistItemCreate
from app.watchlist.service import create_watchlist_item


pytestmark = pytest.mark.postgres_integration


@pytest.fixture(scope="module")
def postgres_sessions() -> sessionmaker:
    if os.getenv("RUN_POSTGRES_INTEGRATION") != "true":
        pytest.skip("PostgreSQL schedule tests require RUN_POSTGRES_INTEGRATION=true")
    engine = create_database_engine()
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL schedule tests require a PostgreSQL DATABASE_URL")
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture(autouse=True)
def schedule_dispatch_enabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("JOBS_ENABLED", "true")
    monkeypatch.setenv("WORKER_API_ENABLED", "true")
    monkeypatch.setenv("SCHEDULE_DISPATCH_ENABLED", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_postgres_concurrent_dispatch_claims_one_occurrence_and_job(postgres_sessions: sessionmaker) -> None:
    user_id, actor, schedule_id = _create_due_schedule(postgres_sessions, "one-winner")
    now = datetime(2026, 8, 13, 15, tzinfo=UTC)
    barrier = Barrier(2)

    def dispatch() -> int:
        with postgres_sessions() as db:
            barrier.wait()
            return dispatch_due_schedules(db, now=now).queued

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(lambda _: dispatch(), range(2)))
        assert sum(outcomes) == 1
        with postgres_sessions() as db:
            occurrences = db.execute(
                select(MonitoringScheduleOccurrenceModel).where(
                    MonitoringScheduleOccurrenceModel.schedule_id == schedule_id
                )
            ).scalars().all()
            jobs = db.execute(
                select(JobModel).where(JobModel.job_type == "watchlist.evaluate").where(JobModel.owner_user_id == user_id)
            ).scalars().all()
            assert len(occurrences) == 1
            assert occurrences[0].status == "queued"
            assert len(jobs) == 1
            assert occurrences[0].job_id == jobs[0].id
    finally:
        _cleanup_schedule_user(postgres_sessions, user_id)


def test_postgres_pause_racing_dispatch_leaves_no_active_scheduled_work(postgres_sessions: sessionmaker) -> None:
    user_id, actor, schedule_id = _create_due_schedule(postgres_sessions, "pause-race")
    now = datetime(2026, 8, 13, 15, tzinfo=UTC)
    barrier = Barrier(2)

    def dispatch() -> None:
        with postgres_sessions() as db:
            barrier.wait()
            dispatch_due_schedules(db, now=now)

    def pause() -> None:
        with postgres_sessions() as db:
            barrier.wait()
            pause_schedule(db, actor, schedule_id, now=now)

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(dispatch)
            second = executor.submit(pause)
            first.result()
            second.result()
        with postgres_sessions() as db:
            schedule = db.get(MonitoringScheduleModel, schedule_id)
            assert schedule.status == "paused"
            jobs = db.execute(
                select(JobModel)
                .join(MonitoringScheduleOccurrenceModel, MonitoringScheduleOccurrenceModel.job_id == JobModel.id)
                .where(MonitoringScheduleOccurrenceModel.schedule_id == schedule_id)
            ).scalars().all()
            assert len(jobs) <= 1
            assert all(job.status in TERMINAL_JOB_STATUSES for job in jobs)
    finally:
        _cleanup_schedule_user(postgres_sessions, user_id)


def test_postgres_delete_racing_dispatch_leaves_no_executable_scheduled_work(postgres_sessions: sessionmaker) -> None:
    user_id, actor, schedule_id = _create_due_schedule(postgres_sessions, "delete-race")
    now = datetime(2026, 8, 13, 15, tzinfo=UTC)
    barrier = Barrier(2)

    def dispatch() -> None:
        with postgres_sessions() as db:
            barrier.wait()
            dispatch_due_schedules(db, now=now)

    def delete_schedule_lifecycle() -> None:
        with postgres_sessions() as db:
            barrier.wait()
            delete_schedule(db, actor, schedule_id, now=now)

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(dispatch)
            second = executor.submit(delete_schedule_lifecycle)
            first.result()
            second.result()
        with postgres_sessions() as db:
            schedule = db.get(MonitoringScheduleModel, schedule_id)
            assert schedule.status == "deleted"
            jobs = db.execute(
                select(JobModel)
                .join(MonitoringScheduleOccurrenceModel, MonitoringScheduleOccurrenceModel.job_id == JobModel.id)
                .where(MonitoringScheduleOccurrenceModel.schedule_id == schedule_id)
            ).scalars().all()
            assert len(jobs) <= 1
            assert all(job.status in TERMINAL_JOB_STATUSES for job in jobs)
    finally:
        _cleanup_schedule_user(postgres_sessions, user_id)


def test_postgres_concurrent_dispatch_cannot_exceed_scheduled_daily_quota(postgres_sessions: sessionmaker) -> None:
    user_id, actor, schedule_id = _create_due_schedule(postgres_sessions, "quota-race")
    now = datetime(2026, 8, 13, 15, tzinfo=UTC)
    barrier = Barrier(2)
    try:
        with postgres_sessions() as db:
            first = db.get(MonitoringScheduleModel, schedule_id)
            second = create_schedule(
                db,
                actor,
                MonitoringScheduleCreateRequest(
                    target_type="watchlist.evaluate",
                    target_id=first.target_id,
                    cadence="hourly",
                    timezone="UTC",
                ),
                now=now - timedelta(hours=2),
            ).schedule
            db.get(MonitoringScheduleModel, second.id).next_due_at = now - timedelta(minutes=1)
            period_start, period_end = _day_window()
            db.add(
                UsageQuotaModel(
                    id=f"quota_phase20c_{uuid4().hex[:12]}",
                    subject_type="user",
                    subject_id=user_id,
                    plan=actor.plan,
                    action=ACTION_SCHEDULED_WATCHLIST_EVALUATION,
                    period_start=period_start,
                    period_end=period_end,
                    used=SCHEDULED_WATCHLIST_EVALUATIONS_PER_DAY - 1,
                    limit=SCHEDULED_WATCHLIST_EVALUATIONS_PER_DAY,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
            )
            db.commit()

        def dispatch() -> tuple[int, int]:
            with postgres_sessions() as db:
                barrier.wait()
                outcome = dispatch_due_schedules(db, now=now)
                return outcome.queued, outcome.denied

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(lambda _: dispatch(), range(2)))
        assert sum(item[0] for item in outcomes) == 1
        assert sum(item[1] for item in outcomes) == 1
        with postgres_sessions() as db:
            jobs = db.execute(
                select(JobModel)
                .where(JobModel.job_type == "watchlist.evaluate")
                .where(JobModel.owner_user_id == user_id)
            ).scalars().all()
            occurrences = db.execute(
                select(MonitoringScheduleOccurrenceModel)
                .join(MonitoringScheduleModel, MonitoringScheduleModel.id == MonitoringScheduleOccurrenceModel.schedule_id)
                .where(MonitoringScheduleModel.owner_user_id == user_id)
            ).scalars().all()
            quota = db.execute(
                select(UsageQuotaModel)
                .where(UsageQuotaModel.subject_id == user_id)
                .where(UsageQuotaModel.action == ACTION_SCHEDULED_WATCHLIST_EVALUATION)
            ).scalars().one()
            assert len(jobs) == 1
            assert quota.used == SCHEDULED_WATCHLIST_EVALUATIONS_PER_DAY
            assert {item.status for item in occurrences} == {"queued", "denied"}
            assert {item.reason for item in occurrences if item.status == "denied"} == {"scheduled_run_quota_exceeded"}
    finally:
        _cleanup_schedule_user(postgres_sessions, user_id)


def test_postgres_executor_success_is_not_terminal_until_control_plane_and_recovery_is_truthful(
    postgres_sessions: sessionmaker,
) -> None:
    user_id, _actor, schedule_id = _create_due_schedule(postgres_sessions, "completion-recovery")
    worker_id = f"wrk_phase20c_{uuid4().hex[:12]}"
    try:
        with postgres_sessions() as db:
            dispatch_due_schedules(db, now=datetime(2026, 8, 13, 15, tzinfo=UTC))
            identity = _add_schedule_worker(db, worker_id)
            claimed = _claim_and_start_schedule_job(db, identity)

        WatchlistEvaluationJobExecutor(session_factory=postgres_sessions).execute(claimed)
        with postgres_sessions() as db:
            occurrence = db.scalar(
                select(MonitoringScheduleOccurrenceModel).where(MonitoringScheduleOccurrenceModel.job_id == claimed.id)
            )
            assert occurrence.status == "running"
            assert occurrence.completed_at is None
            job = db.get(JobModel, claimed.id)
            job.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
            db.commit()
            assert recover_expired_jobs(db) == 1
            db.commit()
            assert db.get(JobModel, claimed.id).status == "retry_wait"
            occurrence = db.scalar(
                select(MonitoringScheduleOccurrenceModel).where(MonitoringScheduleOccurrenceModel.job_id == claimed.id)
            )
            assert occurrence.status == "queued"
            assert occurrence.reason == "lease_expired_retry"
            quota = db.execute(
                select(UsageQuotaModel)
                .where(UsageQuotaModel.subject_id == user_id)
                .where(UsageQuotaModel.action == ACTION_SCHEDULED_WATCHLIST_EVALUATION)
            ).scalars().one()
            assert quota.used == 1

            job = db.get(JobModel, claimed.id)
            job.available_at = datetime.now(UTC) - timedelta(seconds=1)
            db.commit()
            retry_claim = _claim_and_start_schedule_job(db, _worker_identity(db, worker_id))

        WatchlistEvaluationJobExecutor(session_factory=postgres_sessions).execute(retry_claim)
        with postgres_sessions() as db:
            job = db.get(JobModel, retry_claim.id)
            job.max_attempts = job.attempt_count
            job.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
            db.commit()
            assert recover_expired_jobs(db) == 1
            db.commit()
            assert db.get(JobModel, retry_claim.id).status == "dead_letter"
            occurrence = db.scalar(
                select(MonitoringScheduleOccurrenceModel).where(MonitoringScheduleOccurrenceModel.job_id == retry_claim.id)
            )
            assert occurrence.status == "failed"
            assert occurrence.reason == "lease_expired"
            assert occurrence.completed_at is not None
            quota = db.execute(
                select(UsageQuotaModel)
                .where(UsageQuotaModel.subject_id == user_id)
                .where(UsageQuotaModel.action == ACTION_SCHEDULED_WATCHLIST_EVALUATION)
            ).scalars().one()
            assert quota.used == 1
    finally:
        _cleanup_schedule_user(postgres_sessions, user_id, worker_id=worker_id)


def _create_due_schedule(postgres_sessions: sessionmaker, label: str) -> tuple[str, UserContext, str]:
    suffix = uuid4().hex[:12]
    now = datetime(2026, 8, 13, 15, tzinfo=UTC)
    with postgres_sessions() as db:
        user = create_user(db, f"phase20c-{label}-{suffix}@example.test", token=f"token-{suffix}")
        actor = user_context(user, auth_enabled=True)
        target = create_watchlist_item(
            WatchlistItemCreate(
                item_type="strategy",
                title=f"Phase 20C {label}",
                protocol="aave",
                rules={"borrow_apy_above_threshold": 0.08},
                snapshot={"borrow_apy": 0.1},
            ),
            db,
            actor,
        ).item
        schedule = create_schedule(
            db,
            actor,
            MonitoringScheduleCreateRequest(
                target_type="watchlist.evaluate",
                target_id=target.id,
                cadence="hourly",
                timezone="UTC",
            ),
            now=now - timedelta(hours=2),
        ).schedule
        record = db.get(MonitoringScheduleModel, schedule.id)
        record.next_due_at = now - timedelta(hours=1)
        db.commit()
        return user.id, actor, schedule.id


def _cleanup_schedule_user(postgres_sessions: sessionmaker, user_id: str, *, worker_id: str | None = None) -> None:
    with postgres_sessions() as db:
        schedule_ids = db.execute(
            select(MonitoringScheduleModel.id).where(MonitoringScheduleModel.owner_user_id == user_id)
        ).scalars().all()
        if schedule_ids:
            job_ids = db.execute(
                select(MonitoringScheduleOccurrenceModel.job_id)
                .where(MonitoringScheduleOccurrenceModel.schedule_id.in_(schedule_ids))
                .where(MonitoringScheduleOccurrenceModel.job_id.is_not(None))
            ).scalars().all()
            db.execute(
                delete(MonitoringScheduleOccurrenceModel).where(
                    MonitoringScheduleOccurrenceModel.schedule_id.in_(schedule_ids)
                )
            )
            db.execute(delete(MonitoringScheduleModel).where(MonitoringScheduleModel.id.in_(schedule_ids)))
            if job_ids:
                for job in db.execute(select(JobModel).where(JobModel.id.in_(job_ids))).scalars().all():
                    _release_capacity(db, job)
                db.execute(delete(JobModel).where(JobModel.id.in_(job_ids)))
        watchlist_ids = db.execute(
            select(WatchlistItemModel.id).where(WatchlistItemModel.owner_user_id == user_id)
        ).scalars().all()
        if watchlist_ids:
            db.execute(delete(AlertEventModel).where(AlertEventModel.watchlist_item_id.in_(watchlist_ids)))
            db.execute(delete(WatchlistItemModel).where(WatchlistItemModel.id.in_(watchlist_ids)))
        db.execute(
            delete(JobCapacityReservationModel).where(
                (JobCapacityReservationModel.scope_type == "user")
                & (JobCapacityReservationModel.scope_id == user_id)
            )
        )
        db.execute(delete(UsageQuotaModel).where(UsageQuotaModel.subject_id == user_id))
        if worker_id is not None:
            db.execute(delete(WorkerCredentialModel).where(WorkerCredentialModel.worker_id == worker_id))
            db.execute(delete(WorkerModel).where(WorkerModel.id == worker_id))
        db.execute(delete(UserModel).where(UserModel.id == user_id))
        db.commit()


def _add_schedule_worker(db, worker_id: str) -> WorkerIdentity:
    worker = WorkerModel(
        id=worker_id,
        name=worker_id,
        status="active",
        protocol_version="v1",
        allowed_job_types=["watchlist.evaluate"],
        max_concurrency=1,
        last_seen_at=datetime.now(UTC),
    )
    credential = WorkerCredentialModel(
        id=f"{worker_id}_cred",
        worker_id=worker_id,
        token_prefix="phase20c-postgres",
        token_hash="test-only-hash",
        allowed_job_types=["watchlist.evaluate"],
        status="active",
    )
    db.add(worker)
    db.flush()
    db.add(credential)
    db.commit()
    return WorkerIdentity(credential=credential, worker=worker)


def _worker_identity(db, worker_id: str) -> WorkerIdentity:
    worker = db.get(WorkerModel, worker_id)
    credential = db.get(WorkerCredentialModel, f"{worker_id}_cred")
    assert worker is not None and credential is not None
    return WorkerIdentity(credential=credential, worker=worker)


def _claim_and_start_schedule_job(db, identity: WorkerIdentity):
    claimed = claim_next_job(db, identity).job
    assert claimed is not None
    start_job(
        db,
        identity,
        claimed.id,
        WorkerLeaseRequest(lease_generation=claimed.lease_generation, lease_token=claimed.lease_token),
    )
    return claimed
