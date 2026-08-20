from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine

from app.auth.service import create_user, user_context
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.notification import NotificationModel, NotificationPreferenceModel
from app.models.user import UserModel
from app.notifications.registry import CATEGORIES, SEVERITIES, TEMPLATES
from app.notifications.schemas import NotificationPreferenceUpdateRequest
from app.notifications.service import (
    cleanup_expired_notifications,
    emit_notification_intent,
    emit_job_notification,
    emit_schedule_notification,
    emit_watchlist_alert_notification,
    get_or_create_preferences,
    list_notifications,
    update_preferences,
)
from app.watchlist.schemas import WatchlistItemCreate
from app.watchlist.service import create_watchlist_item, evaluate_watchlist_item


@pytest.fixture
def notification_client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_PROVIDER", "legacy_local")
    monkeypatch.setenv("AUTH_SECRET_KEY", "phase20d-test-secret")
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


def test_notification_registry_is_closed_and_code_owned() -> None:
    assert set(CATEGORIES) == {"monitoring.risk_alert", "schedule.status", "job.status", "account.lifecycle"}
    assert set(SEVERITIES) == {"informational", "warning", "critical"}
    assert all(template.category in CATEGORIES for template in TEMPLATES.values())
    assert all(template.severity in SEVERITIES for template in TEMPLATES.values())
    assert all(template.title and len(template.title) <= 120 for template in TEMPLATES.values())
    assert all(template.body and len(template.body) <= 240 for template in TEMPLATES.values())
    assert all(template.path.startswith("/") and ".." not in template.path for template in TEMPLATES.values())


def test_preferences_defaults_timezone_quiet_hours_digest_and_minimum_severity(notification_client) -> None:
    _client, Session = notification_client
    with Session() as db:
        user = create_user(db, "phase20d-preferences@example.test", token="phase20d-pref")
        preference = get_or_create_preferences(db, user.id)
        assert preference.category_enabled_json["monitoring.risk_alert"] is False
        assert preference.category_enabled_json["account.lifecycle"] is True

        response = update_preferences(
            db,
            user.id,
            NotificationPreferenceUpdateRequest(
                categories={"monitoring.risk_alert": True, "account.lifecycle": False},
                minimum_severity={"monitoring.risk_alert": "warning"},
                timezone="America/New_York",
                quiet_hours_start="22:00",
                quiet_hours_end="07:00",
                daily_digest_enabled=True,
            ),
        )
        assert response.categories["monitoring.risk_alert"] is True
        assert response.categories["account.lifecycle"] is True
        assert response.minimum_severity["monitoring.risk_alert"] == "warning"
        assert response.timezone == "America/New_York"
        assert response.quiet_hours_start == "22:00"
        assert response.quiet_hours_end == "07:00"
        assert response.daily_digest_enabled is True

        cleared = update_preferences(
            db,
            user.id,
            NotificationPreferenceUpdateRequest(quiet_hours_start=None, quiet_hours_end=None),
        )
        assert cleared.quiet_hours_start is None
        assert cleared.quiet_hours_end is None

        with pytest.raises(Exception):
            update_preferences(db, user.id, NotificationPreferenceUpdateRequest(timezone="not/a-zone"))


def test_deterministic_idempotency_and_policy_suppression(notification_client) -> None:
    _client, Session = notification_client
    with Session() as db:
        user = create_user(db, "phase20d-idempotent@example.test", token="phase20d-idem")
        first, duplicate = emit_notification_intent(
            db,
            owner_user_id=user.id,
            template_id="job.status.completed",
            source_id="job_same",
            idempotency_key="job:job_same:completed",
            occurred_at=datetime(2026, 8, 14, 12, tzinfo=UTC),
        )
        second, second_duplicate = emit_notification_intent(
            db,
            owner_user_id=user.id,
            template_id="job.status.completed",
            source_id="job_same",
            idempotency_key="job:job_same:completed",
            occurred_at=datetime(2026, 8, 14, 12, tzinfo=UTC),
        )
        assert first is not None
        assert duplicate is False
        assert second_duplicate is True
        assert second is not None
        rows = db.execute(select(NotificationModel).where(NotificationModel.owner_user_id == user.id)).scalars().all()
        assert len(rows) == 1
        assert rows[0].policy_outcome == "suppressed_by_preference"
        assert rows[0].available_at is None


def test_policy_composes_category_threshold_quiet_hours_and_digest(notification_client) -> None:
    _client, Session = notification_client
    with Session() as db:
        user = create_user(db, "phase20d-policy@example.test", token="test-only-policy-auth")
        timestamp = datetime(2026, 8, 14, 23, 30, tzinfo=UTC)
        update_preferences(
            db,
            user.id,
            NotificationPreferenceUpdateRequest(
                categories={"monitoring.risk_alert": False, "job.status": True},
                minimum_severity={"job.status": "critical"},
                quiet_hours_start="22:00",
                quiet_hours_end="10:00",
                daily_digest_enabled=True,
            ),
        )
        critical_risk, _ = emit_notification_intent(
            db, owner_user_id=user.id, template_id="monitoring.risk_alert.critical", source_id="risk-a",
            idempotency_key="risk:a", occurred_at=timestamp,
        )
        low_job, _ = emit_notification_intent(
            db, owner_user_id=user.id, template_id="job.status.completed", source_id="job-a",
            idempotency_key="job:a", occurred_at=timestamp,
        )
        mandatory, _ = emit_notification_intent(
            db, owner_user_id=user.id, template_id="account.lifecycle.exported", source_id=user.id,
            idempotency_key="account:a", occurred_at=timestamp,
        )
        assert critical_risk is not None and critical_risk.policy_outcome == "suppressed_by_preference"
        assert low_job is not None and low_job.policy_outcome == "suppressed_by_preference"
        assert mandatory is not None and mandatory.policy_outcome == "mandatory" and mandatory.available_at == timestamp

        update_preferences(
            db, user.id,
            NotificationPreferenceUpdateRequest(categories={"monitoring.risk_alert": True}, daily_digest_enabled=True),
        )
        digest, _ = emit_notification_intent(
            db, owner_user_id=user.id, template_id="monitoring.risk_alert.critical", source_id="risk-b",
            idempotency_key="risk:b", occurred_at=timestamp,
        )
        assert digest is not None and digest.policy_outcome == "delayed_digest"
        # The 09:00 digest boundary lies in 22:00-10:00 quiet hours, so it moves to 10:00.
        assert digest.available_at == datetime(2026, 8, 15, 10, tzinfo=UTC)


def test_source_projection_helpers_are_idempotent_and_skip_noisy_states(notification_client) -> None:
    _client, Session = notification_client
    with Session() as db:
        user = create_user(db, "phase20d-source-idempotency@example.test", token="test-only-source-auth")
        timestamp = datetime.now(UTC)
        emit_job_notification(db, owner_user_id=user.id, organization_id=None, job_id="job-terminal", status="completed", occurred_at=timestamp)
        emit_job_notification(db, owner_user_id=user.id, organization_id=None, job_id="job-terminal", status="completed", occurred_at=timestamp)
        emit_job_notification(db, owner_user_id=user.id, organization_id=None, job_id="job-terminal", status="retry_wait", occurred_at=timestamp)
        emit_job_notification(db, owner_user_id=user.id, organization_id=None, job_id="job-terminal", status="dead_letter", occurred_at=timestamp)
        emit_schedule_notification(db, owner_user_id=user.id, occurrence_id="occurrence-a", status="queued", occurred_at=timestamp)
        emit_schedule_notification(db, owner_user_id=user.id, occurrence_id="occurrence-a", status="queued", occurred_at=timestamp)
        emit_schedule_notification(db, owner_user_id=user.id, occurrence_id="occurrence-a", status="missed", occurred_at=timestamp)
        emit_watchlist_alert_notification(db, owner_user_id=user.id, alert_id="alert-a", severity="warning", occurred_at=timestamp)
        emit_watchlist_alert_notification(db, owner_user_id=user.id, alert_id="alert-a", severity="warning", occurred_at=timestamp)
        db.commit()
        rows = db.execute(select(NotificationModel).where(NotificationModel.owner_user_id == user.id)).scalars().all()
        assert {(row.source_type, row.idempotency_key) for row in rows} == {
            ("job", "job:job-terminal:completed"),
            ("job", "job:job-terminal:dead_letter"),
            ("monitoring_schedule_occurrence", "schedule_occurrence:occurrence-a:queued"),
            ("monitoring_schedule_occurrence", "schedule_occurrence:occurrence-a:missed"),
            ("alert_event", "alert_event:alert-a:opened"),
        }


def test_inbox_visibility_and_keyset_pagination(notification_client) -> None:
    client, Session = notification_client
    auth_value = "test-only-visibility-auth"
    timestamp = datetime.now(UTC).replace(microsecond=0)
    with Session() as db:
        user = create_user(db, "phase20d-visibility@example.test", token=auth_value)
        for index in range(3):
            emit_notification_intent(
                db, owner_user_id=user.id, template_id="account.lifecycle.exported", source_id=user.id,
                idempotency_key=f"account:page:{index}", occurred_at=timestamp, commit=False,
            )
        delayed, _ = emit_notification_intent(
            db, owner_user_id=user.id, template_id="job.status.completed", source_id="job-delayed",
            idempotency_key="job:delayed", occurred_at=timestamp, commit=False,
        )
        assert delayed is not None
        delayed.available_at = timestamp + timedelta(hours=1)
        delayed_id = delayed.id
        suppressed, _ = emit_notification_intent(
            db, owner_user_id=user.id, template_id="job.status.failed", source_id="job-suppressed",
            idempotency_key="job:suppressed", occurred_at=timestamp, commit=False,
        )
        assert suppressed is not None and suppressed.available_at is None
        suppressed_id = suppressed.id
        expired, _ = emit_notification_intent(
            db, owner_user_id=user.id, template_id="account.lifecycle.exported", source_id=user.id,
            idempotency_key="account:expired", occurred_at=timestamp, commit=False,
        )
        assert expired is not None
        expired.expires_at = timestamp - timedelta(seconds=1)
        expired_id = expired.id
        db.commit()

        first, cursor = list_notifications(db, user.id, limit=2)
        second, terminal_cursor = list_notifications(db, user.id, limit=2, cursor=cursor)
        assert len(first) == 2 and len(second) == 1 and terminal_cursor is None
        assert {row.id for row in first}.isdisjoint({row.id for row in second})

    headers = _auth(auth_value)
    assert client.get(f"/api/notifications/{delayed_id}", headers=headers).status_code == 404
    assert client.post(f"/api/notifications/{delayed_id}/read", headers=headers).status_code == 404
    assert client.get(f"/api/notifications/{suppressed_id}", headers=headers).status_code == 404
    assert client.post(f"/api/notifications/{suppressed_id}/unread", headers=headers).status_code == 404
    assert client.get(f"/api/notifications/{expired_id}", headers=headers).status_code == 404
    assert client.post("/api/notifications/mark-all-read", headers=headers).json()["updated_count"] == 3
    assert client.get("/api/notifications?cursor=not-a-cursor", headers=headers).status_code == 422


def test_authenticated_api_isolates_notifications_and_lifecycle_state(notification_client) -> None:
    client, Session = notification_client
    owner_auth_value = "test-only-owner-auth"
    other_auth_value = "test-only-other-auth"
    with Session() as db:
        owner = create_user(db, "phase20d-owner@example.test", token=owner_auth_value)
        other = create_user(db, "phase20d-other@example.test", token=other_auth_value)
        other_id = other.id
        emit_notification_intent(
            db,
            owner_user_id=owner.id,
            template_id="account.lifecycle.exported",
            source_id=owner.id,
            idempotency_key="account:owner:export:audit_1",
            occurred_at=datetime.now(UTC),
            commit=True,
        )
        notification_id = db.execute(select(NotificationModel.id).where(NotificationModel.owner_user_id == owner.id)).scalar_one()

    assert client.get("/api/notifications").status_code == 401
    owner_list = client.get("/api/notifications", headers=_auth(owner_auth_value))
    assert owner_list.status_code == 200
    assert owner_list.json()["items"][0]["id"] == notification_id
    assert client.get(f"/api/notifications/{notification_id}", headers=_auth(other_auth_value)).status_code == 404
    assert client.post(f"/api/notifications/{notification_id}/read", headers=_auth(other_auth_value)).status_code == 404
    assert client.post("/api/notifications", headers=_auth(owner_auth_value), json={"owner_user_id": other_id, "category": "job.status"}).status_code == 405

    read = client.post(f"/api/notifications/{notification_id}/read", headers=_auth(owner_auth_value))
    assert read.status_code == 200
    assert read.json()["notification"]["read_at"] is not None
    assert client.post(f"/api/notifications/{notification_id}/read", headers=_auth(owner_auth_value)).status_code == 200
    unread = client.post(f"/api/notifications/{notification_id}/unread", headers=_auth(owner_auth_value))
    assert unread.status_code == 200
    assert unread.json()["notification"]["read_at"] is None
    assert client.post("/api/notifications/mark-all-read", headers=_auth(owner_auth_value)).status_code == 200


def test_source_projection_export_cleanup_and_account_deletion(notification_client) -> None:
    client, Session = notification_client
    token = "phase20d-source"
    user_id = ""
    with Session() as db:
        user = create_user(db, "phase20d-source@example.test", token=token)
        user_id = user.id
        update_preferences(
            db,
            user.id,
            NotificationPreferenceUpdateRequest(categories={"monitoring.risk_alert": True}),
        )
        item = create_watchlist_item(
            WatchlistItemCreate(
                item_type="strategy",
                title="Phase 20D risk target",
                protocol="aave",
                rules={"borrow_apy_above_threshold": 0.08},
                snapshot={"borrow_apy": 0.11},
            ),
            db,
            user_context(user, auth_enabled=True),
        ).item
        evaluation = evaluate_watchlist_item(item.id, db, user_context(user, auth_enabled=True))
        assert len(evaluation.created_alerts) == 1
        notification = db.execute(select(NotificationModel).where(NotificationModel.owner_user_id == user.id)).scalars().one()
        assert notification.category == "monitoring.risk_alert"
        assert notification.source_id == evaluation.created_alerts[0].id
        notification.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
        assert cleanup_expired_notifications(db, apply=True) == 1
        assert db.execute(select(NotificationModel)).scalars().all() == []

    exported = client.get("/api/account/export", headers=_auth(token))
    assert exported.status_code == 200
    assert "notification_preferences" in exported.json()
    assert "notifications" in exported.json()
    assert client.request("DELETE", "/api/account", headers=_auth(token), json={"confirmation": "DELETE"}).status_code == 200
    with Session() as db:
        deleted_user = db.get(UserModel, user_id)
        assert deleted_user is not None
        assert deleted_user.account_status == "deleted"
        assert deleted_user.is_active is False
        assert db.execute(select(NotificationModel)).scalars().all() == []
        assert db.execute(select(NotificationPreferenceModel)).scalars().all() == []


def test_quiet_hours_dst_inputs_are_timezone_aware(notification_client) -> None:
    _client, Session = notification_client
    with Session() as db:
        user = create_user(db, "phase20d-dst@example.test", token="phase20d-dst")
        update_preferences(
            db,
            user.id,
            NotificationPreferenceUpdateRequest(
                categories={"job.status": True},
                timezone="America/New_York",
                quiet_hours_start="01:00",
                quiet_hours_end="04:00",
            ),
        )
        forward, _ = emit_notification_intent(
            db,
            owner_user_id=user.id,
            template_id="job.status.completed",
            source_id="job_dst_forward",
            idempotency_key="job:dst:forward",
            occurred_at=datetime(2026, 3, 8, 7, 30, tzinfo=UTC),
        )
        backward, _ = emit_notification_intent(
            db,
            owner_user_id=user.id,
            template_id="job.status.failed",
            source_id="job_dst_backward",
            idempotency_key="job:dst:backward",
            occurred_at=datetime(2026, 11, 1, 6, 30, tzinfo=UTC),
        )
        assert forward is not None and forward.policy_outcome == "delayed_quiet_hours"
        assert backward is not None and backward.policy_outcome == "delayed_quiet_hours"
        assert forward.available_at is not None
        assert backward.available_at is not None


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
