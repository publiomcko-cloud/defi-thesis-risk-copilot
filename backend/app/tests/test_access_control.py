from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.auth.service import create_user
from app.models.access_audit_event import AccessAuditEventModel
from app.models.discovered_item import DiscoveredItemModel
from app.models.evaluation_result import EvaluationResultModel
from app.models.review_item import ReviewItemModel


@pytest.fixture()
def auth_client(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_SECRET_KEY", "test-auth-secret")
    monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", "test-credential-key")
    monkeypatch.setenv("ADMIN_EMAIL", "bootstrap-admin@example.test")
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "bootstrap-token")
    get_settings.cache_clear()

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    with Session() as db:
        create_user(db, "admin@example.test", role="admin", token="admin-token")
        create_user(db, "common@example.test", role="common", token="common-token")
        create_user(db, "inactive@example.test", role="common", token="inactive-token", is_active=False)

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


def test_require_user_accepts_valid_user_and_rejects_inactive(auth_client) -> None:
    client, _ = auth_client

    admin = client.get("/api/auth/me", headers=_auth("admin-token"))
    inactive = client.get("/api/auth/me", headers=_auth("inactive-token"))

    assert admin.status_code == 200
    assert admin.json()["role"] == "admin"
    assert inactive.status_code == 403


def test_require_admin_accepts_admin_and_rejects_common(auth_client) -> None:
    client, _ = auth_client

    admin_response = client.get("/api/admin/provider-credentials", headers=_auth("admin-token"))
    common_response = client.get("/api/admin/provider-credentials", headers=_auth("common-token"))

    assert admin_response.status_code == 200
    assert common_response.status_code == 403


def test_admin_can_create_list_update_and_disable_credential_without_secret_leak(auth_client) -> None:
    client, Session = auth_client

    created = client.post(
        "/api/admin/provider-credentials",
        headers=_auth("admin-token"),
        json={
            "provider": "openai_compatible",
            "name": "Local model gateway",
            "secret": "sk-test-secret-1234",
            "enabled": True,
        },
    )

    assert created.status_code == 200
    payload = created.json()["credential"]
    assert payload["secret_last4"] == "1234"
    assert "secret" not in payload
    assert "secret_encrypted" not in payload

    credential_id = payload["id"]
    listed = client.get("/api/admin/provider-credentials", headers=_auth("admin-token")).json()
    assert listed["items"][0]["id"] == credential_id
    assert "sk-test-secret-1234" not in str(listed)

    updated = client.patch(
        f"/api/admin/provider-credentials/{credential_id}",
        headers=_auth("admin-token"),
        json={"enabled": False, "secret": "rotated-secret-9999"},
    )
    disabled = client.delete(
        f"/api/admin/provider-credentials/{credential_id}",
        headers=_auth("admin-token"),
    )

    assert updated.status_code == 200
    assert updated.json()["credential"]["secret_last4"] == "9999"
    assert disabled.status_code == 200
    assert disabled.json()["credential"]["enabled"] is False

    with Session() as db:
        events = db.query(AccessAuditEventModel).all()
        assert {event.action for event in events} >= {
            "credential.created",
            "credential.updated",
            "credential.disabled",
        }
        assert "sk-test-secret-1234" not in str([event.metadata_json for event in events])


def test_common_user_cannot_manage_credentials(auth_client) -> None:
    client, _ = auth_client

    response = client.post(
        "/api/admin/provider-credentials",
        headers=_auth("common-token"),
        json={
            "provider": "coingecko",
            "name": "CoinGecko",
            "secret": "coingecko-secret",
            "enabled": True,
        },
    )

    assert response.status_code == 403


def test_secret_storage_fails_closed_without_encryption_key(auth_client, monkeypatch) -> None:
    client, _ = auth_client
    monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", "")
    get_settings.cache_clear()

    response = client.post(
        "/api/admin/provider-credentials",
        headers=_auth("admin-token"),
        json={
            "provider": "vast_ai",
            "name": "Vast placeholder",
            "secret": "vast-secret",
            "enabled": True,
        },
    )

    assert response.status_code == 500
    assert "CREDENTIAL_ENCRYPTION_KEY" in response.json()["detail"]


def test_common_user_cannot_ingest_approved_review_item(auth_client) -> None:
    client, Session = auth_client
    with Session() as db:
        review_item_id = _seed_approved_review_item(db)

    response = client.post(
        f"/api/evaluation/review-items/{review_item_id}/ingest-to-rag",
        headers=_auth("common-token"),
    )

    assert response.status_code == 403


def test_admin_can_ingest_approved_review_item_and_audit_is_recorded(
    auth_client,
    monkeypatch,
    tmp_path: Path,
) -> None:
    client, Session = auth_client
    with Session() as db:
        review_item_id = _seed_approved_review_item(db)

    def fake_ingest(review_item_id, db, ingested_by="system"):
        from app.discovery.schemas import KnowledgeBaseIngestionRecord

        return (
            KnowledgeBaseIngestionRecord(
                id="kbi_test",
                review_item_id=review_item_id,
                generated_markdown_path=str(tmp_path / "review.md"),
                ingested_at=datetime.now(UTC),
                ingested_by=ingested_by,
                source_url="https://example.com/docs",
                protocol="example",
                status="ingested",
            ),
            3,
        )

    monkeypatch.setattr("app.api.routes_evaluation.ingest_review_item_to_rag", fake_ingest)

    response = client.post(
        f"/api/evaluation/review-items/{review_item_id}/ingest-to-rag",
        headers=_auth("admin-token"),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ingested"
    with Session() as db:
        event = db.query(AccessAuditEventModel).filter_by(action="review_item.ingest_to_rag").one()
        assert event.resource_id == review_item_id


def test_auth_disabled_preserves_demo_behavior(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_ENABLED", "false")
    get_settings.cache_clear()

    with TestClient(app) as client:
        response = client.get("/api/admin/provider-credentials")

    assert response.status_code == 200


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _seed_approved_review_item(db) -> str:
    discovered = DiscoveredItemModel(
        id="disc_auth_ingest",
        discovery_key="auth_ingest_key",
        source="manual",
        source_type="documentation",
        title="Auth ingest docs",
        url="https://example.com/docs",
        protocol="example",
        chain="ethereum",
        raw_payload={},
        status="approved_for_rag",
    )
    evaluation = EvaluationResultModel(
        id="eval_auth_ingest",
        discovered_item_id=discovered.id,
        report_id="report_auth_ingest",
        risk_rating="Moderate",
        risk_score=4,
        confidence="medium",
        risk_summary="Auth ingestion test summary.",
        missing_data_json=[],
        sources_json=[],
        report_json={"assumptions": []},
    )
    review = ReviewItemModel(
        id="review_auth_ingest",
        discovered_item_id=discovered.id,
        evaluation_result_id=evaluation.id,
        status="approved_for_rag",
        reviewer_notes="Approved.",
        prepared_for_rag=True,
    )
    db.add(discovered)
    db.add(evaluation)
    db.add(review)
    db.commit()
    return review.id
