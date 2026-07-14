from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.schemas import UserContext
from app.auth.service import create_user
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.llm.vast.client import VastClientError, select_offer
from app.llm.vast.lifecycle import cleanup_sessions, destroy_session, start_session
from app.llm.vast.schemas import VastOffer
from app.main import app
from app.models.access_audit_event import AccessAuditEventModel
from app.models.vast_session import VastSessionModel


@pytest.fixture()
def vast_client(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_SECRET_KEY", "test-auth-secret")
    monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", "test-credential-key")
    monkeypatch.setenv("ADMIN_EMAIL", "bootstrap-admin@example.test")
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "bootstrap-token")
    monkeypatch.setenv("VAST_ENABLED", "true")
    monkeypatch.setenv("VAST_DRY_RUN", "true")
    monkeypatch.setenv("VAST_MODEL", "llama-test")
    monkeypatch.setenv("VAST_IMAGE", "ghcr.io/example/openai-server:latest")
    monkeypatch.setenv("VAST_MAX_ACTIVE_INSTANCES", "1")
    get_settings.cache_clear()

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    with Session() as db:
        create_user(db, "admin@example.test", role="admin", token="admin-token")
        create_user(db, "common@example.test", role="common", token="common-token")

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app), Session
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_vast_endpoints_require_admin(vast_client) -> None:
    client, _ = vast_client

    missing = client.get("/api/admin/vast/config")
    common = client.get("/api/admin/vast/config", headers=_auth("common-token"))
    admin = client.get("/api/admin/vast/config", headers=_auth("admin-token"))

    assert missing.status_code == 401
    assert common.status_code == 403
    assert admin.status_code == 200


def test_vast_disabled_returns_safe_error(vast_client, monkeypatch) -> None:
    client, _ = vast_client
    monkeypatch.setenv("VAST_ENABLED", "false")
    get_settings.cache_clear()

    response = client.post("/api/admin/vast/sessions/start", headers=_auth("admin-token"), json={})

    assert response.status_code == 400
    assert response.json()["detail"] == "Vast.ai provider is disabled"


def test_dry_run_lifecycle_reaches_ready_without_real_api_call(vast_client) -> None:
    client, Session = vast_client

    response = client.post("/api/admin/vast/sessions/start", headers=_auth("admin-token"), json={})

    assert response.status_code == 200
    session = response.json()["session"]
    assert session["status"] == "ready"
    assert session["metadata_json"]["dry_run"] is True
    assert session["public_endpoint_url"] == "http://dry-run-vast.local:8000"
    assert "api_key" not in str(session).lower()
    with Session() as db:
        actions = {event.action for event in db.query(AccessAuditEventModel).all()}
        assert {
            "vast.session_start_requested",
            "vast.offer_selected",
            "vast.instance_rented",
            "vast.model_health_ready",
        }.issubset(actions)


def test_offer_selection_enforces_cost_gpu_ram_disk_and_verified(monkeypatch) -> None:
    monkeypatch.setenv("VAST_MAX_HOURLY_COST_USD", "0.50")
    monkeypatch.setenv("VAST_GPU_ALLOWLIST", "RTX_4090")
    monkeypatch.setenv("VAST_MIN_GPU_RAM_GB", "16")
    monkeypatch.setenv("VAST_DISK_GB", "40")
    monkeypatch.setenv("VAST_REQUIRE_VERIFIED", "true")
    get_settings.cache_clear()
    settings = get_settings()

    offers = [
        VastOffer(id="too_expensive", gpu_name="RTX_4090", hourly_cost_usd=0.9, gpu_ram_gb=24, disk_gb=80, verified=True),
        VastOffer(id="wrong_gpu", gpu_name="A5000", hourly_cost_usd=0.2, gpu_ram_gb=24, disk_gb=80, verified=True),
        VastOffer(id="low_ram", gpu_name="RTX_4090", hourly_cost_usd=0.2, gpu_ram_gb=8, disk_gb=80, verified=True),
        VastOffer(id="unverified", gpu_name="RTX_4090", hourly_cost_usd=0.2, gpu_ram_gb=24, disk_gb=80, verified=False),
        VastOffer(id="winner", gpu_name="RTX_4090", hourly_cost_usd=0.3, gpu_ram_gb=24, disk_gb=80, verified=True),
    ]

    assert select_offer(offers, settings).id == "winner"


def test_no_acceptable_offer_returns_offer_not_found(vast_client) -> None:
    _, Session = vast_client
    actor = _actor()
    with Session() as db:
        session = start_session(db, actor, client=NoOfferClient())

    assert session.status == "offer_not_found"
    assert session.last_error == "No acceptable Vast.ai offer found"


def test_max_active_instance_limit_is_enforced(vast_client) -> None:
    client, Session = vast_client
    with Session() as db:
        db.add(
            VastSessionModel(
                id="vast_existing",
                status="ready",
                provider="vast_ai",
                model="llama",
                image="image",
                max_runtime_minutes=30,
                container_port=8000,
                created_by="user_admin",
            )
        )
        db.commit()

    response = client.post("/api/admin/vast/sessions/start", headers=_auth("admin-token"), json={})

    assert response.status_code == 409


def test_failed_startup_triggers_cleanup_and_audit(vast_client) -> None:
    _, Session = vast_client
    actor = _actor()
    with Session() as db:
        session = start_session(db, actor, client=RentFailClient())
        events = db.query(AccessAuditEventModel).all()

    assert session.status == "destroyed"
    assert session.last_error == "rent failed"
    assert any(event.action == "vast.failure_state" for event in events)


def test_destroy_is_idempotent(vast_client) -> None:
    _, Session = vast_client
    actor = _actor()
    with Session() as db:
        session = start_session(db, actor)
        first = destroy_session(db, actor, session.id)
        second = destroy_session(db, actor, session.id)

    assert first.status == "destroyed"
    assert second.status == "destroyed"


def test_cleanup_handles_stale_sessions(vast_client) -> None:
    _, Session = vast_client
    actor = _actor()
    with Session() as db:
        db.add(
            VastSessionModel(
                id="vast_stale",
                status="booting",
                provider="vast_ai",
                vast_instance_id="stale_instance",
                model="llama",
                image="image",
                max_runtime_minutes=30,
                container_port=8000,
                created_by=actor.id,
                created_at=datetime.now(UTC) - timedelta(hours=1),
            )
        )
        db.commit()
        result = cleanup_sessions(db, actor)

    assert result.cleaned_count == 1
    assert result.sessions[0].status == "destroyed"


def test_test_prompt_uses_dry_run_provider_and_auto_destroy(vast_client) -> None:
    client, _ = vast_client
    started = client.post("/api/admin/vast/sessions/start", headers=_auth("admin-token"), json={})
    session_id = started.json()["session"]["id"]

    response = client.post(
        f"/api/admin/vast/sessions/{session_id}/test-prompt",
        headers=_auth("admin-token"),
        json={"prompt": "Say hello safely."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "vast_ephemeral"
    assert "Dry-run Vast.ai model response" in payload["output"]
    assert payload["session"]["status"] == "destroyed"


def test_raw_api_key_is_never_returned(vast_client, monkeypatch) -> None:
    client, _ = vast_client
    monkeypatch.setenv("VAST_API_KEY", "vast-secret-key-123")
    get_settings.cache_clear()

    config = client.get("/api/admin/vast/config", headers=_auth("admin-token")).json()

    assert config["has_env_api_key"] is True
    assert "vast-secret-key-123" not in str(config)


def test_deterministic_fallback_still_works_without_vast(monkeypatch) -> None:
    from app.llm.providers import get_llm_provider

    monkeypatch.setenv("LLM_PROVIDER", "disabled")
    monkeypatch.setenv("VAST_ENABLED", "false")
    get_settings.cache_clear()

    assert get_llm_provider(get_settings()) is None


def test_local_and_openai_compatible_provider_selection_still_work(monkeypatch) -> None:
    from app.llm.providers import get_llm_provider

    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2")
    get_settings.cache_clear()
    assert get_llm_provider(get_settings()).name == "ollama"

    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("OPENAI_COMPATIBLE_BASE_URL", "http://localhost:8001/v1")
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "test-key")
    get_settings.cache_clear()
    assert get_llm_provider(get_settings()).name == "openai_compatible"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _actor() -> UserContext:
    return UserContext(id="user_admin", email="admin@example.test", role="admin", auth_enabled=True)


class NoOfferClient:
    def search_offers(self):
        return []

    def rent_instance(self, offer, image, model, disk_gb):
        raise AssertionError("rent_instance should not be called")

    def get_instance_status(self, instance_id):
        raise AssertionError("get_instance_status should not be called")

    def destroy_instance(self, instance_id):
        return {"destroyed": True}


class RentFailClient:
    def search_offers(self):
        return [
            VastOffer(
                id="offer",
                gpu_name="RTX_4090",
                hourly_cost_usd=0.25,
                gpu_ram_gb=24,
                disk_gb=80,
                verified=True,
            )
        ]

    def rent_instance(self, offer, image, model, disk_gb):
        raise VastClientError("rent failed")

    def get_instance_status(self, instance_id):
        raise AssertionError("get_instance_status should not be called")

    def destroy_instance(self, instance_id):
        return {"destroyed": True}
