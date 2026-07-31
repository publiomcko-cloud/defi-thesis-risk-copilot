from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import create_user
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.product_analytics import (
    PrivacyPreferenceDecisionModel,
    PrivacyPreferenceModel,
    ProductAnalyticsEventModel,
)
from app.models.saved_thesis import SavedThesisModel
from app.models.user import UserModel
from app.product_analytics.registry import ProductAnalyticsValidationError
from app.product_analytics.service import record_product_event
from scripts.cleanup_expired_data import cleanup_expired_data


@pytest.fixture
def analytics_client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_PROVIDER", "legacy_local")
    monkeypatch.setenv("AUTH_SECRET_KEY", "phase20b-test-secret")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("PRODUCT_ANALYTICS_ENABLED", "true")
    monkeypatch.setenv("PRODUCT_ANALYTICS_POLICY_VERSION", "phase20b-test-v1")
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


def test_product_analytics_defaults_off_and_production_activation_fails_closed() -> None:
    assert Settings(_env_file=None).product_analytics_enabled is False
    with pytest.raises(ValidationError, match="qualified privacy/legal approval"):
        Settings(_env_file=None, app_env="production", product_analytics_enabled=True)


def test_preferences_are_authenticated_default_off_and_strict(analytics_client) -> None:
    client, Session = analytics_client
    assert client.get("/api/account/privacy-preferences").status_code == 401
    assert client.patch(
        "/api/account/privacy-preferences",
        json={"purpose": "product_improvement", "enabled": True},
    ).status_code == 401

    with Session() as db:
        create_user(db, "phase20b-default@example.test", token="phase20b-default-token")

    response = client.get(
        "/api/account/privacy-preferences",
        headers=_auth("phase20b-default-token"),
    )
    assert response.status_code == 200
    assert response.json()["items"] == [
        {
            "purpose": "product_improvement",
            "enabled": False,
            "policy_version": "phase20b-test-v1",
            "collection_enabled": True,
            "requires_reconsent": False,
            "updated_at": None,
        }
    ]
    extra = client.patch(
        "/api/account/privacy-preferences",
        headers={**_auth("phase20b-default-token"), "Idempotency-Key": "decision-extra-001"},
        json={"purpose": "product_improvement", "enabled": True, "email": "forbidden@example.test"},
    )
    assert extra.status_code == 422


def test_opt_in_idempotency_withdrawal_reconsent_and_event_deduplication(
    analytics_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, Session = analytics_client
    with Session() as db:
        user = create_user(db, "phase20b-consent@example.test", token="phase20b-consent-token")
        user_id = user.id
    headers = {**_auth("phase20b-consent-token"), "Idempotency-Key": "decision-grant-001"}

    grant = client.patch(
        "/api/account/privacy-preferences",
        headers=headers,
        json={"purpose": "product_improvement", "enabled": True},
    )
    replay = client.patch(
        "/api/account/privacy-preferences",
        headers=headers,
        json={"purpose": "product_improvement", "enabled": True},
    )
    assert grant.status_code == 200
    assert grant.json()["decision"] == "grant"
    assert grant.json()["duplicate"] is False
    assert replay.status_code == 200
    assert replay.json()["duplicate"] is True

    with Session() as db:
        assert record_product_event(
            db,
            owner_user_id=user_id,
            event_name="analysis_completed",
            metadata={
                "actor_class": "authenticated",
                "execution_mode": "synchronous",
                "result_class": "report_created",
            },
            source_boundary="report-source-001",
        ) is True
        assert record_product_event(
            db,
            owner_user_id=user_id,
            event_name="analysis_completed",
            metadata={
                "actor_class": "authenticated",
                "execution_mode": "synchronous",
                "result_class": "report_created",
            },
            source_boundary="report-source-001",
        ) is False
        assert db.scalar(select(func.count()).select_from(ProductAnalyticsEventModel)) == 1

    withdraw = client.patch(
        "/api/account/privacy-preferences",
        headers={**_auth("phase20b-consent-token"), "Idempotency-Key": "withdraw-test"},
        json={"purpose": "product_improvement", "enabled": False},
    )
    assert withdraw.status_code == 200
    assert withdraw.json()["decision"] == "withdraw"
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(ProductAnalyticsEventModel)) == 0
        assert record_product_event(
            db,
            owner_user_id=user_id,
            event_name="analysis_failed",
            metadata={
                "actor_class": "authenticated",
                "execution_mode": "synchronous",
                "failure_class": "internal",
            },
            source_boundary="failed-source-001",
        ) is False

    regrant = client.patch(
        "/api/account/privacy-preferences",
        headers={**_auth("phase20b-consent-token"), "Idempotency-Key": "decision-grant-002"},
        json={"purpose": "product_improvement", "enabled": True},
    )
    assert regrant.status_code == 200
    monkeypatch.setenv("PRODUCT_ANALYTICS_POLICY_VERSION", "phase20b-test-v2")
    get_settings.cache_clear()
    stale = client.get(
        "/api/account/privacy-preferences",
        headers=_auth("phase20b-consent-token"),
    ).json()["items"][0]
    assert stale["enabled"] is False
    assert stale["requires_reconsent"] is True
    with Session() as db:
        assert record_product_event(
            db,
            owner_user_id=user_id,
            event_name="thesis_saved",
            metadata={"actor_class": "authenticated", "visibility_class": "private"},
            source_boundary="stale-policy-source",
        ) is False


def test_only_approved_bounded_metadata_can_be_persisted(analytics_client) -> None:
    _client, Session = analytics_client
    with Session() as db:
        user = create_user(db, "phase20b-metadata@example.test", token="phase20b-metadata-token")
        with pytest.raises(ProductAnalyticsValidationError, match="not approved"):
            record_product_event(
                db,
                owner_user_id=user.id,
                event_name="page_viewed",
                metadata={"actor_class": "authenticated"},
                source_boundary="unknown-event",
            )
        with pytest.raises(ProductAnalyticsValidationError, match="does not match"):
            record_product_event(
                db,
                owner_user_id=user.id,
                event_name="thesis_saved",
                metadata={
                    "actor_class": "authenticated",
                    "visibility_class": "private",
                    "url": "https://private.example.test/thesis/secret",
                },
                source_boundary="extra-field",
            )
        with pytest.raises(ProductAnalyticsValidationError, match="undeclared value"):
            record_product_event(
                db,
                owner_user_id=user.id,
                event_name="analysis_failed",
                metadata={
                    "actor_class": "authenticated",
                    "execution_mode": "synchronous",
                    "failure_class": "user_email@example.test",
                },
                source_boundary="unbounded-value",
            )
        assert db.scalar(select(func.count()).select_from(ProductAnalyticsEventModel)) == 0


def test_primary_product_remains_available_when_analytics_flag_is_disabled(
    analytics_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, Session = analytics_client
    with Session() as db:
        user = create_user(db, "phase20b-disabled@example.test", token="phase20b-disabled-token")
        user_id = user.id
    headers = _auth("phase20b-disabled-token")
    assert client.patch(
        "/api/account/privacy-preferences",
        headers={**headers, "Idempotency-Key": "decision-disabled-001"},
        json={"purpose": "product_improvement", "enabled": True},
    ).status_code == 200
    monkeypatch.setenv("PRODUCT_ANALYTICS_ENABLED", "false")
    get_settings.cache_clear()
    created = client.post(
        "/api/theses",
        headers=headers,
        json={
            "title": "Analytics-disabled thesis",
            "strategy_text": "The primary action remains available while optional analytics is disabled.",
            "protocols": ["aave"],
            "visibility": "private",
        },
    )
    assert created.status_code == 200
    with Session() as db:
        assert db.get(SavedThesisModel, created.json()["id"]) is not None
        assert db.scalar(
            select(func.count()).select_from(ProductAnalyticsEventModel).where(
                ProductAnalyticsEventModel.owner_user_id == user_id
            )
        ) == 0


def test_primary_actions_emit_only_after_opt_in_and_survive_analytics_failure(
    analytics_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, Session = analytics_client
    with Session() as db:
        user = create_user(db, "phase20b-actions@example.test", token="phase20b-actions-token")
        user_id = user.id
        create_user(db, "phase20b-no-consent@example.test", token="phase20b-no-consent-token")
    headers = _auth("phase20b-actions-token")
    assert client.patch(
        "/api/account/privacy-preferences",
        headers={**headers, "Idempotency-Key": "decision-actions-001"},
        json={"purpose": "product_improvement", "enabled": True},
    ).status_code == 200

    thesis = client.post(
        "/api/theses",
        headers=headers,
        json={
            "title": "Consent-safe thesis",
            "strategy_text": "A sufficiently detailed private lending strategy for testing.",
            "protocols": ["aave"],
            "visibility": "private",
        },
    )
    watchlist = client.post(
        "/api/watchlist/items",
        headers=headers,
        json={"item_type": "protocol", "title": "Aave monitor", "protocol": "aave"},
    )
    without_consent = client.post(
        "/api/theses",
        headers=_auth("phase20b-no-consent-token"),
        json={
            "title": "No analytics thesis",
            "strategy_text": "Another sufficiently detailed private lending strategy.",
            "protocols": ["morpho"],
            "visibility": "private",
        },
    )
    assert thesis.status_code == 200
    assert watchlist.status_code == 200
    assert without_consent.status_code == 200
    with Session() as db:
        events = db.execute(
            select(ProductAnalyticsEventModel).where(ProductAnalyticsEventModel.owner_user_id == user_id)
        ).scalars().all()
        assert {event.event_name for event in events} == {"thesis_saved", "watchlist_created"}
        assert all(set(event.dimensions_json) == {"visibility_class"} for event in events)
        assert all("email" not in str(event.dimensions_json).lower() for event in events)

    monkeypatch.setattr(
        "app.product_analytics.service.record_product_event",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("synthetic analytics outage")),
    )
    resilient = client.post(
        "/api/theses",
        headers=headers,
        json={
            "title": "Primary action survives",
            "strategy_text": "This private thesis must commit despite optional analytics failure.",
            "protocols": ["aave"],
            "visibility": "private",
        },
    )
    assert resilient.status_code == 200
    with Session() as db:
        assert db.get(SavedThesisModel, resilient.json()["id"]) is not None


def test_export_is_tenant_safe_and_account_deletion_stops_collection(
    analytics_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, Session = analytics_client
    with Session() as db:
        owner = create_user(db, "phase20b-export@example.test", token="phase20b-export-token")
        other = create_user(db, "phase20b-other@example.test", token="phase20b-other-token")
        owner_id = owner.id
        other_id = other.id
    for token, suffix in (("phase20b-export-token", "owner"), ("phase20b-other-token", "other")):
        assert client.patch(
            "/api/account/privacy-preferences",
            headers={**_auth(token), "Idempotency-Key": f"decision-export-{suffix}"},
            json={"purpose": "product_improvement", "enabled": True},
        ).status_code == 200
    with Session() as db:
        for user_id, suffix in ((owner_id, "owner"), (other_id, "other")):
            assert record_product_event(
                db,
                owner_user_id=user_id,
                event_name="watchlist_created",
                metadata={"actor_class": "authenticated", "visibility_class": "private"},
                source_boundary=f"private-resource-{suffix}",
            ) is True

    exported = client.get("/api/account/export", headers=_auth("phase20b-export-token"))
    assert exported.status_code == 200
    payload = exported.json()
    assert len(payload["privacy_preferences"]) == 1
    assert len(payload["privacy_preference_decisions"]) == 1
    assert len(payload["product_analytics_events"]) == 1
    analytics_payload = {
        "preferences": payload["privacy_preferences"],
        "decisions": payload["privacy_preference_decisions"],
        "events": payload["product_analytics_events"],
    }
    serialized = str(analytics_payload)
    assert owner_id not in serialized
    assert other_id not in serialized
    assert "private-resource" not in serialized
    assert "@example.test" not in serialized
    assert "event_key" not in serialized

    deleted = client.request(
        "DELETE",
        "/api/account",
        headers=_auth("phase20b-export-token"),
        json={"confirmation": "DELETE"},
    )
    assert deleted.status_code == 200
    with Session() as db:
        assert db.scalar(
            select(func.count()).select_from(ProductAnalyticsEventModel).where(
                ProductAnalyticsEventModel.owner_user_id == owner_id
            )
        ) == 0
        assert db.scalar(
            select(func.count()).select_from(PrivacyPreferenceModel).where(
                PrivacyPreferenceModel.user_id == owner_id
            )
        ) == 0
        assert db.scalar(
            select(func.count()).select_from(PrivacyPreferenceDecisionModel).where(
                PrivacyPreferenceDecisionModel.user_id == owner_id
            )
        ) == 1
        deleted_user = db.get(UserModel, owner_id)
        deleted_user.deleted_at = datetime.now(UTC) - timedelta(days=31)
        db.commit()
    monkeypatch.setattr("scripts.cleanup_expired_data.SessionLocal", Session)
    cleanup_expired_data(dry_run=False)
    with Session() as db:
        assert db.scalar(
            select(func.count()).select_from(PrivacyPreferenceDecisionModel).where(
                PrivacyPreferenceDecisionModel.user_id == owner_id
            )
        ) == 0


def test_retention_cleanup_and_append_only_guards(
    analytics_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, Session = analytics_client
    with Session() as db:
        user = create_user(db, "phase20b-retention@example.test", token="phase20b-retention-token")
        user_id = user.id
    assert client.patch(
        "/api/account/privacy-preferences",
        headers={**_auth("phase20b-retention-token"), "Idempotency-Key": "decision-retention-001"},
        json={"purpose": "product_improvement", "enabled": True},
    ).status_code == 200
    now = datetime.now(UTC)
    with Session() as db:
        preference = db.execute(
            select(PrivacyPreferenceModel).where(PrivacyPreferenceModel.user_id == user_id)
        ).scalars().one()
        decision = db.get(PrivacyPreferenceDecisionModel, preference.latest_decision_id)
        db.add(
            ProductAnalyticsEventModel(
                id="pae_expired_phase20b",
                event_name="analysis_failed",
                schema_version=1,
                purpose="product_improvement",
                owner_user_id=user_id,
                actor_class="authenticated",
                dimensions_json={"execution_mode": "synchronous", "failure_class": "internal"},
                event_key="pae_expired_phase20b_key",
                policy_version=preference.policy_version,
                decision_id=decision.id,
                occurred_at=now - timedelta(days=31),
                received_at=now - timedelta(days=31),
                expires_at=now - timedelta(seconds=1),
            )
        )
        db.commit()
        decision.decision = "deny"
        with pytest.raises(ValueError, match="append-only"):
            db.commit()
        db.rollback()
        event = db.get(ProductAnalyticsEventModel, "pae_expired_phase20b")
        event.actor_class = "organization_context"
        with pytest.raises(ValueError, match="append-only"):
            db.commit()
        db.rollback()

    monkeypatch.setattr("scripts.cleanup_expired_data.SessionLocal", Session)
    dry_run = cleanup_expired_data(dry_run=True)
    assert dry_run["expired_product_analytics_events"] == 1
    with Session() as db:
        assert db.get(ProductAnalyticsEventModel, "pae_expired_phase20b") is not None
    cleanup_expired_data(dry_run=False)
    with Session() as db:
        assert db.get(ProductAnalyticsEventModel, "pae_expired_phase20b") is None


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
