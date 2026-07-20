from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import create_user
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.demo.seed_data import seed_demo_data
from app.main import app
from app.models.alert_event import AlertEventModel
from app.models.discovered_item import DiscoveredItemModel
from app.models.knowledge_base_ingestion import KnowledgeBaseIngestionModel
from app.models.report import ReportModel
from app.models.vast_session import VastSessionModel
from app.models.watchlist_item import WatchlistItemModel


@pytest.fixture()
def demo_client(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("AUTH_SECRET_KEY", "test-auth-secret")
    monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", "test-credential-key")
    monkeypatch.setenv("ADMIN_EMAIL", "bootstrap-admin@example.test")
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "bootstrap-token")
    monkeypatch.setenv("PUBLIC_DEMO_MODE", "false")
    monkeypatch.setenv("VAST_ENABLED", "false")
    monkeypatch.setenv("VAST_DRY_RUN", "true")
    monkeypatch.setattr("app.demo.seed_data.EXAMPLE_REPORTS_DIR", tmp_path / "examples")
    get_settings.cache_clear()

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    event.listen(engine, "connect", _enable_sqlite_foreign_keys)
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
        yield TestClient(app), Session, tmp_path / "examples"
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_demo_seed_works_in_local_auth_disabled_mode(demo_client, monkeypatch) -> None:
    client, _, examples_dir = demo_client
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.setenv("PUBLIC_DEMO_MODE", "false")
    get_settings.cache_clear()

    response = client.post("/api/demo/seed")

    assert response.status_code == 200
    payload = response.json()
    assert payload["seeded"] is True
    assert payload["counts"]["reports"] == 5
    assert (examples_dir / "pendle_pt_loop_report.md").exists()


def test_demo_seed_requires_admin_when_auth_enabled(demo_client, monkeypatch) -> None:
    client, _, _ = demo_client
    monkeypatch.setenv("AUTH_ENABLED", "true")
    get_settings.cache_clear()

    missing = client.post("/api/demo/seed")
    common = client.post("/api/demo/seed", headers=_auth("common-token"))
    admin = client.post("/api/demo/seed", headers=_auth("admin-token"))

    assert missing.status_code == 401
    assert common.status_code == 403
    assert admin.status_code == 200


def test_demo_seed_is_idempotent_and_records_are_marked_demo(demo_client, monkeypatch) -> None:
    client, Session, _ = demo_client
    monkeypatch.setenv("AUTH_ENABLED", "false")
    get_settings.cache_clear()

    first = client.post("/api/demo/seed").json()
    second = client.post("/api/demo/seed").json()

    assert first["counts"] == second["counts"]
    with Session() as db:
        assert db.query(ReportModel).count() == 5
        discovered = db.get(DiscoveredItemModel, "demo_disc_aurora_lend")
        assert discovered.raw_payload["demo"] is True
        ingestion = db.get(KnowledgeBaseIngestionModel, "demo_kbi_aurora_lend")
        assert ingestion.status == "ingested"
        watch = db.get(WatchlistItemModel, "demo_watch_pendle_loop")
        assert watch.snapshot_json["demo"] is True
        alert = db.get(AlertEventModel, "demo_alert_pendle_liquidity")
        assert alert.metadata_json["demo"] is True
        vast = db.get(VastSessionModel, "demo_vast_dry_run")
        assert vast.metadata_json["no_real_rental"] is True


def test_demo_status_and_scenarios_are_useful(demo_client, monkeypatch) -> None:
    client, _, _ = demo_client
    monkeypatch.setenv("AUTH_ENABLED", "false")
    get_settings.cache_clear()
    client.post("/api/demo/seed")

    status = client.get("/api/demo/status")
    scenarios = client.get("/api/demo/scenarios")
    report = client.get("/api/reports/demo_report_pendle_pt_loop")

    assert status.status_code == 200
    assert status.json()["counts"]["alert_events"] == 1
    assert len(scenarios.json()) >= 4
    assert report.status_code == 200
    assert "not financial" in report.json()["disclaimer"].lower()


def test_demo_data_requires_no_external_keys_or_live_vast(demo_client, monkeypatch) -> None:
    client, _, _ = demo_client
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "")
    monkeypatch.setenv("VAST_API_KEY", "")
    monkeypatch.setenv("VAST_ENABLED", "false")
    get_settings.cache_clear()

    response = client.post("/api/demo/seed")

    assert response.status_code == 200
    payload_text = str(response.json()).lower()
    assert "api_key" not in payload_text
    assert "real vast" not in payload_text


def test_public_demo_seed_endpoint_is_blocked_and_runtime_seed_skips_file_writes(
    demo_client,
    monkeypatch,
) -> None:
    client, Session, examples_dir = demo_client
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.setenv("PUBLIC_DEMO_MODE", "true")
    get_settings.cache_clear()

    response = client.post("/api/demo/seed")
    assert response.status_code == 403

    with Session() as db:
        first = seed_demo_data(db)
        second = seed_demo_data(db)

    assert first.counts == second.counts
    assert not (examples_dir / "pendle_pt_loop_report.md").exists()


def test_deployment_status_returns_safe_public_demo_metadata(demo_client, monkeypatch) -> None:
    client, Session, _ = demo_client
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.setenv("PUBLIC_DEMO_MODE", "true")
    monkeypatch.setenv("APP_ENV", "portfolio_demo")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:secret@example.supabase.co:6543/postgres")
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "sk-secret-value")
    monkeypatch.setenv("VAST_API_KEY", "vast-secret-value")
    monkeypatch.setenv("LLM_SYNTHESIS_ENABLED", "false")
    monkeypatch.setenv("LLM_PROVIDER", "disabled")
    monkeypatch.setenv("VAST_ENABLED", "false")
    monkeypatch.setenv("VAST_DRY_RUN", "true")
    get_settings.cache_clear()

    with Session() as db:
        seed_demo_data(db, write_examples=False)

    response = client.get("/api/deployment/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["public_demo_mode"] is True
    assert payload["app_environment"] == "portfolio_demo"
    assert payload["database_connected"] is True
    assert payload["demo_seeded"] is True
    assert payload["llm_synthesis_enabled"] is False
    assert payload["llm_provider"] == "disabled"
    assert payload["vast_enabled"] is False
    assert payload["vast_dry_run"] is True
    payload_text = str(payload).lower()
    assert "secret" not in payload_text
    assert "supabase" not in payload_text
    assert "postgresql" not in payload_text


def test_public_demo_blocks_provider_credential_mutation(demo_client, monkeypatch) -> None:
    client, _, _ = demo_client
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.setenv("PUBLIC_DEMO_MODE", "true")
    get_settings.cache_clear()

    response = client.post(
        "/api/admin/provider-credentials",
        json={
            "provider": "openai_compatible",
            "name": "public-demo-secret",
            "secret": "sk-should-not-store",
            "enabled": True,
        },
    )

    assert response.status_code == 403
    assert "public demo mode" in response.json()["detail"].lower()


def test_public_demo_blocks_real_vast_start(demo_client, monkeypatch) -> None:
    client, _, _ = demo_client
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.setenv("PUBLIC_DEMO_MODE", "true")
    monkeypatch.setenv("VAST_ENABLED", "true")
    monkeypatch.setenv("VAST_DRY_RUN", "false")
    get_settings.cache_clear()

    response = client.post(
        "/api/admin/vast/sessions/start",
        json={"allow_remote_gpu": True, "warm_instance": False},
    )

    assert response.status_code == 403
    assert "public demo mode" in response.json()["detail"].lower()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
