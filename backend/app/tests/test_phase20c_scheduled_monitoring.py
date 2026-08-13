from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import create_user, user_context
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db
from app.jobs.errors import JobExecutionError
from app.jobs.schemas import WorkerClaimedJob, WorkerLeaseRequest
from app.jobs.worker_protocol import WorkerIdentity, claim_next_job, recover_expired_jobs, start_job
from app.main import app
from app.models.job import JobModel
from app.models.scheduled_monitoring import MonitoringScheduleModel, MonitoringScheduleOccurrenceModel
from app.models.worker import WorkerCredentialModel, WorkerModel
from app.scheduling.calendar import first_due_after, next_due_after
from app.scheduling.executor import WatchlistEvaluationJobExecutor
from app.scheduling.service import cleanup_expired_schedule_history, dispatch_due_schedules
from app.watchlist.schemas import WatchlistItemCreate
from app.watchlist.service import create_watchlist_item


@pytest.fixture
def schedule_client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_PROVIDER", "legacy_local")
    monkeypatch.setenv("AUTH_SECRET_KEY", "phase20c-test-secret")
    monkeypatch.setenv("JOBS_ENABLED", "true")
    monkeypatch.setenv("WORKER_API_ENABLED", "true")
    monkeypatch.setenv("SCHEDULE_DISPATCH_ENABLED", "true")
    get_settings.cache_clear()
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app), Session
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_schedule_defaults_are_disabled_and_production_dispatch_fails_closed() -> None:
    assert Settings(_env_file=None).schedule_dispatch_enabled is False
    with pytest.raises(ValueError, match="Phase 20C approval"):
        Settings(
            _env_file=None,
            app_env="production",
            jobs_enabled=True,
            worker_api_enabled=True,
            schedule_dispatch_enabled=True,
        )


def test_schedules_are_unavailable_when_authentication_is_deployment_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.setenv("PUBLIC_DEMO_MODE", "false")
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.get("/api/schedules")
    finally:
        get_settings.cache_clear()
    assert response.status_code == 403
    assert response.json()["detail"] == "Monitoring schedules require enabled authentication."


def test_authenticated_owner_can_create_pause_resume_delete_and_export(schedule_client) -> None:
    client, Session = schedule_client
    owner_token, watchlist_id = _create_user_watchlist(Session, "owner")
    headers = _auth(owner_token)

    empty_list = client.get("/api/schedules", headers=headers)
    assert empty_list.status_code == 200
    assert empty_list.json() == {"items": [], "dispatch_enabled": True}

    created = client.post("/api/schedules", headers=headers, json=_payload(watchlist_id, "daily"))
    assert created.status_code == 201
    schedule_id = created.json()["schedule"]["id"]
    assert created.json()["schedule"]["dispatch_enabled"] is True

    paused = client.post(f"/api/schedules/{schedule_id}/pause", headers=headers)
    assert paused.status_code == 200
    assert paused.json()["schedule"]["status"] == "paused"
    resumed = client.post(f"/api/schedules/{schedule_id}/resume", headers=headers)
    assert resumed.status_code == 200
    assert resumed.json()["schedule"]["status"] == "active"

    exported = client.get("/api/account/export", headers=headers)
    assert exported.status_code == 200
    assert exported.json()["monitoring_schedules"][0]["id"] == schedule_id
    assert exported.json()["monitoring_schedule_runs"] == []

    deleted = client.delete(f"/api/schedules/{schedule_id}", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["schedule"]["status"] == "deleted"
    assert client.delete(f"/api/schedules/{schedule_id}", headers=headers).status_code == 200


def test_schedule_api_rejects_anonymous_other_user_and_more_than_five_active(schedule_client) -> None:
    client, Session = schedule_client
    owner_token, watchlist_id = _create_user_watchlist(Session, "owner-limit")
    other_token, _ = _create_user_watchlist(Session, "other-limit")
    assert client.post("/api/schedules", json=_payload(watchlist_id)).status_code == 401
    assert client.post("/api/schedules", headers=_auth(other_token), json=_payload(watchlist_id)).status_code == 404
    invalid_timezone = client.post(
        "/api/schedules",
        headers=_auth(owner_token),
        json={**_payload(watchlist_id), "timezone": "not/a-real-timezone"},
    )
    assert invalid_timezone.status_code == 422

    ids = []
    for _ in range(5):
        response = client.post("/api/schedules", headers=_auth(owner_token), json=_payload(watchlist_id))
        assert response.status_code == 201
        ids.append(response.json()["schedule"]["id"])
    assert client.post("/api/schedules", headers=_auth(owner_token), json=_payload(watchlist_id)).status_code == 409
    assert client.get(f"/api/schedules/{ids[0]}", headers=_auth(other_token)).status_code == 404
    direct_job = client.post(
        "/api/jobs",
        headers={**_auth(owner_token), "Idempotency-Key": "phase20c-direct-job-denied"},
        json={
            "job_type": "watchlist.evaluate",
            "input_schema_version": "watchlist.evaluate.v1",
            "input_json": {"watchlist_item_id": watchlist_id},
        },
    )
    assert direct_job.status_code == 403


def test_dispatch_is_idempotent_coalesces_and_skips_runs_more_than_a_day_late(schedule_client) -> None:
    client, Session = schedule_client
    token, watchlist_id = _create_user_watchlist(Session, "dispatch")
    created = client.post("/api/schedules", headers=_auth(token), json=_payload(watchlist_id, "hourly"))
    schedule_id = created.json()["schedule"]["id"]
    now = datetime(2026, 8, 13, 15, tzinfo=UTC)
    with Session() as db:
        schedule = db.get(MonitoringScheduleModel, schedule_id)
        schedule.next_due_at = now - timedelta(hours=3)
        db.commit()
        first = dispatch_due_schedules(db, now=now)
        second = dispatch_due_schedules(db, now=now)
        occurrences = db.execute(
            select(MonitoringScheduleOccurrenceModel).where(MonitoringScheduleOccurrenceModel.schedule_id == schedule_id)
        ).scalars().all()
        jobs = db.execute(select(JobModel).where(JobModel.job_type == "watchlist.evaluate")).scalars().all()
        assert first.queued == 1
        assert second.queued == 0
        assert len(occurrences) == 1
        assert occurrences[0].reason == "coalesced_missed_runs"
        assert len(jobs) == 1
        assert jobs[0].reserved_cost_microusd == 0

        schedule.next_due_at = now - timedelta(hours=25)
        db.commit()
        skipped = dispatch_due_schedules(db, now=now)
        assert skipped.missed == 1
        missed = db.execute(
            select(MonitoringScheduleOccurrenceModel)
            .where(MonitoringScheduleOccurrenceModel.schedule_id == schedule_id)
            .where(MonitoringScheduleOccurrenceModel.status == "missed")
        ).scalars().one()
        assert missed.reason == "overdue_more_than_24_hours"


def test_disabled_dispatch_preserves_schedule_and_dispatch_revalidates_owner_and_target(schedule_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, Session = schedule_client
    token, watchlist_id = _create_user_watchlist(Session, "revocation")
    schedule_id = client.post("/api/schedules", headers=_auth(token), json=_payload(watchlist_id)).json()["schedule"]["id"]
    now = datetime(2026, 8, 13, 15, tzinfo=UTC)
    with Session() as db:
        schedule = db.get(MonitoringScheduleModel, schedule_id)
        schedule.next_due_at = now - timedelta(minutes=1)
        db.commit()
        monkeypatch.setenv("SCHEDULE_DISPATCH_ENABLED", "false")
        get_settings.cache_clear()
        assert dispatch_due_schedules(db, now=now).status == "disabled"
        assert db.scalar(select(MonitoringScheduleOccurrenceModel.id)) is None

        monkeypatch.setenv("SCHEDULE_DISPATCH_ENABLED", "true")
        get_settings.cache_clear()
        owner = _user_for_token(db, token)
        owner.is_active = False
        owner.account_status = "inactive"
        db.commit()
        denied = dispatch_due_schedules(db, now=now)
        occurrence = db.scalar(select(MonitoringScheduleOccurrenceModel))
        assert denied.denied == 1
        assert occurrence.status == "denied"
        assert occurrence.reason == "authorization_revoked"


def test_dispatch_records_capacity_denial_without_leaking_a_partial_reservation(schedule_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, Session = schedule_client
    token, watchlist_id = _create_user_watchlist(Session, "capacity")
    schedule_id = client.post("/api/schedules", headers=_auth(token), json=_payload(watchlist_id)).json()["schedule"]["id"]
    now = datetime(2026, 8, 13, 15, tzinfo=UTC)
    monkeypatch.setenv("JOB_USER_PENDING_LIMIT", "0")
    get_settings.cache_clear()
    with Session() as db:
        schedule = db.get(MonitoringScheduleModel, schedule_id)
        schedule.next_due_at = now - timedelta(minutes=1)
        db.commit()
        result = dispatch_due_schedules(db, now=now)
        occurrence = db.scalar(select(MonitoringScheduleOccurrenceModel))
        assert result.denied == 1
        assert occurrence.status == "denied"
        assert occurrence.reason == "quota_or_capacity_denied"
        assert db.scalar(select(JobModel.id).where(JobModel.job_type == "watchlist.evaluate")) is None


def test_pause_cancels_pending_work_executor_records_completion_and_retention_cleans_history(schedule_client) -> None:
    client, Session = schedule_client
    token, watchlist_id = _create_user_watchlist(Session, "lifecycle")
    schedule_id = client.post("/api/schedules", headers=_auth(token), json=_payload(watchlist_id)).json()["schedule"]["id"]
    now = datetime(2026, 8, 13, 15, tzinfo=UTC)
    with Session() as db:
        schedule = db.get(MonitoringScheduleModel, schedule_id)
        schedule.next_due_at = now - timedelta(minutes=1)
        db.commit()
        dispatch_due_schedules(db, now=now)
        occurrence = db.scalar(select(MonitoringScheduleOccurrenceModel))
        job = db.get(JobModel, occurrence.job_id)
        assert job.status == "queued"
        claimed = WorkerClaimedJob(
            id=job.id,
            job_type=job.job_type,
            input_schema_version=job.input_schema_version,
            input_json=job.input_json,
            lease_generation=1,
            lease_token="x" * 24,
            lease_expires_at=now + timedelta(minutes=1),
            deadline_at=now + timedelta(minutes=5),
        )
    result = WatchlistEvaluationJobExecutor(session_factory=Session).execute(claimed)
    assert result.result_json["watchlist_item_id"] == watchlist_id
    with Session() as db:
        occurrence = db.scalar(select(MonitoringScheduleOccurrenceModel))
        assert occurrence.status == "completed"
        occurrence.expires_at = now - timedelta(seconds=1)
        db.commit()
        assert cleanup_expired_schedule_history(db, now=now, apply=False)["expired_schedule_occurrences"] == 1
        cleanup_expired_schedule_history(db, now=now, apply=True)
        db.commit()
        assert db.scalar(select(MonitoringScheduleOccurrenceModel.id)) is None

    second = client.post("/api/schedules", headers=_auth(token), json=_payload(watchlist_id)).json()["schedule"]["id"]
    with Session() as db:
        schedule = db.get(MonitoringScheduleModel, second)
        schedule.next_due_at = now - timedelta(minutes=1)
        db.commit()
        dispatch_due_schedules(db, now=now)
    paused = client.post(f"/api/schedules/{second}/pause", headers=_auth(token))
    assert paused.status_code == 200
    with Session() as db:
        job = db.execute(select(JobModel).where(JobModel.job_type == "watchlist.evaluate").order_by(JobModel.created_at.desc())).scalars().first()
        assert job.status == "cancelled"
        occurrence = db.execute(
            select(MonitoringScheduleOccurrenceModel).where(MonitoringScheduleOccurrenceModel.job_id == job.id)
        ).scalars().one()
        assert occurrence.status == "cancelled"


def test_delete_cancels_pending_work_and_execution_revalidates_owner(schedule_client) -> None:
    client, Session = schedule_client
    token, watchlist_id = _create_user_watchlist(Session, "delete-execution")
    schedule_id = client.post("/api/schedules", headers=_auth(token), json=_payload(watchlist_id)).json()["schedule"]["id"]
    now = datetime(2026, 8, 13, 15, tzinfo=UTC)
    with Session() as db:
        schedule = db.get(MonitoringScheduleModel, schedule_id)
        schedule.next_due_at = now - timedelta(minutes=1)
        db.commit()
        dispatch_due_schedules(db, now=now)
        occurrence = db.scalar(select(MonitoringScheduleOccurrenceModel))
        job = db.get(JobModel, occurrence.job_id)
        claimed = WorkerClaimedJob(
            id=job.id,
            job_type=job.job_type,
            input_schema_version=job.input_schema_version,
            input_json=job.input_json,
            lease_generation=1,
            lease_token="x" * 24,
            lease_expires_at=now + timedelta(minutes=1),
            deadline_at=now + timedelta(minutes=5),
        )
        owner = _user_for_token(db, token)
        owner.is_active = False
        owner.account_status = "inactive"
        db.commit()

    with pytest.raises(JobExecutionError, match="Schedule owner is unavailable"):
        WatchlistEvaluationJobExecutor(session_factory=Session).execute(claimed)
    with Session() as db:
        occurrence = db.scalar(select(MonitoringScheduleOccurrenceModel))
        assert occurrence.status == "denied"
        assert occurrence.reason == "authorization_revoked"

    # A second schedule proves delete is distinct from authorization revocation:
    # queued work is cancelled before the worker can claim it.
    second_token, second_target_id = _create_user_watchlist(Session, "delete-pending")
    second_id = client.post("/api/schedules", headers=_auth(second_token), json=_payload(second_target_id)).json()["schedule"]["id"]
    with Session() as db:
        schedule = db.get(MonitoringScheduleModel, second_id)
        schedule.next_due_at = now - timedelta(minutes=1)
        db.commit()
        dispatch_due_schedules(db, now=now)
    assert client.delete(f"/api/schedules/{second_id}", headers=_auth(second_token)).status_code == 200
    with Session() as db:
        occurrence = db.execute(
            select(MonitoringScheduleOccurrenceModel)
            .where(MonitoringScheduleOccurrenceModel.schedule_id == second_id)
        ).scalars().one()
        assert occurrence.status == "cancelled"
        assert db.get(JobModel, occurrence.job_id).status == "cancelled"


def test_account_deletion_disposes_owned_schedules_and_pending_work(schedule_client) -> None:
    client, Session = schedule_client
    token, watchlist_id = _create_user_watchlist(Session, "account-deletion")
    schedule_id = client.post("/api/schedules", headers=_auth(token), json=_payload(watchlist_id)).json()["schedule"]["id"]
    with Session() as db:
        schedule = db.get(MonitoringScheduleModel, schedule_id)
        schedule.next_due_at = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()
        dispatch_due_schedules(db)
    deleted = client.request("DELETE", "/api/account", headers=_auth(token), json={"confirmation": "DELETE"})
    assert deleted.status_code == 200
    with Session() as db:
        schedule = db.get(MonitoringScheduleModel, schedule_id)
        occurrence = db.execute(
            select(MonitoringScheduleOccurrenceModel).where(MonitoringScheduleOccurrenceModel.schedule_id == schedule_id)
        ).scalars().one()
        assert schedule.status == "deleted"
        assert occurrence.status == "cancelled"
        assert db.get(JobModel, occurrence.job_id).status == "cancelled"


def test_worker_loss_recovery_retries_one_schedule_job_without_duplicate_occurrence(schedule_client) -> None:
    client, Session = schedule_client
    token, watchlist_id = _create_user_watchlist(Session, "worker-loss")
    schedule_id = client.post("/api/schedules", headers=_auth(token), json=_payload(watchlist_id)).json()["schedule"]["id"]
    with Session() as db:
        schedule = db.get(MonitoringScheduleModel, schedule_id)
        schedule.next_due_at = datetime.now(UTC) - timedelta(minutes=1)
        worker = WorkerModel(
            id="wrk_phase20c_loss",
            name="phase20c-worker-loss",
            status="active",
            protocol_version="v1",
            allowed_job_types=["watchlist.evaluate"],
            max_concurrency=1,
            last_seen_at=datetime.now(UTC),
        )
        credential = WorkerCredentialModel(
            id="wrkcred_phase20c_loss",
            worker_id=worker.id,
            token_prefix="fixture-worker-loss",
            token_hash="test-only-hash",
            allowed_job_types=["watchlist.evaluate"],
            status="active",
        )
        db.add_all([worker, credential])
        db.commit()
        dispatch_due_schedules(db)
        identity = WorkerIdentity(credential=credential, worker=worker)
        first = claim_next_job(db, identity).job
        assert first is not None
        start_job(
            db,
            identity,
            first.id,
            WorkerLeaseRequest(lease_generation=first.lease_generation, lease_token=first.lease_token),
        )
        lost_job = db.get(JobModel, first.id)
        lost_job.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
        assert recover_expired_jobs(db) == 1
        db.commit()
        recovered = db.get(JobModel, first.id)
        occurrence = db.scalar(select(MonitoringScheduleOccurrenceModel))
        assert recovered.status == "retry_wait"
        assert occurrence.status == "queued"
        assert occurrence.reason == "lease_expired_retry"
        recovered.available_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
        second = claim_next_job(db, identity).job
        assert second is not None
        assert second.id == first.id
        assert second.lease_generation == first.lease_generation + 1
        assert db.scalar(
            select(MonitoringScheduleOccurrenceModel.id).where(
                MonitoringScheduleOccurrenceModel.schedule_id == schedule_id
            )
        ) == occurrence.id


def test_dst_calendar_rules_preserve_elapsed_hourly_and_calendar_daily_wall_time() -> None:
    spring_hourly = next_due_after(datetime(2026, 3, 8, 6, 30, tzinfo=UTC), "hourly", "America/New_York")
    assert spring_hourly == datetime(2026, 3, 8, 7, 30, tzinfo=UTC)
    fall_hourly = next_due_after(datetime(2026, 11, 1, 5, 30, tzinfo=UTC), "hourly", "America/New_York")
    assert fall_hourly == datetime(2026, 11, 1, 6, 30, tzinfo=UTC)
    spring_daily = next_due_after(datetime(2026, 3, 7, 7, 30, tzinfo=UTC), "daily", "America/New_York")
    assert spring_daily == datetime(2026, 3, 8, 7, 30, tzinfo=UTC)
    future = datetime(2026, 8, 14, tzinfo=UTC)
    assert first_due_after(datetime(2026, 8, 13, tzinfo=UTC), "daily", "UTC", future) == future
    assert next_due_after(datetime(2026, 8, 13, 12, tzinfo=UTC), "six_hourly", "UTC") == datetime(2026, 8, 13, 18, tzinfo=UTC)
    assert next_due_after(datetime(2026, 8, 13, 12, tzinfo=UTC), "weekly", "UTC") == datetime(2026, 8, 20, 12, tzinfo=UTC)


def _create_user_watchlist(Session: sessionmaker, label: str) -> tuple[str, str]:
    token = f"phase20c-{label}-token"
    with Session() as db:
        user = create_user(db, f"phase20c-{label}@example.test", token=token)
        item = create_watchlist_item(
            WatchlistItemCreate(
                item_type="strategy",
                title=f"{label} monitoring target",
                protocol="aave",
                rules={"borrow_apy_above_threshold": 0.08},
                snapshot={"borrow_apy": 0.10},
            ),
            db,
            user_context(user, auth_enabled=True),
        ).item
        return token, item.id


def _user_for_token(db, token: str):
    from app.auth.service import user_from_token

    user = user_from_token(db, token)
    assert user is not None
    return user


def _payload(watchlist_id: str, cadence: str = "daily") -> dict[str, str]:
    return {"target_type": "watchlist.evaluate", "target_id": watchlist_id, "cadence": cadence, "timezone": "UTC"}


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
