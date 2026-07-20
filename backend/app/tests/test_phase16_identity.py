from __future__ import annotations

import base64
import json
import time
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.primitives.hashes import SHA256
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import create_user
from app.auth.supabase import verify_supabase_jwt
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.analysis_request import AnalysisRequestModel
from app.models.report import ReportModel
from app.models.saved_thesis import SavedThesisModel
from app.quotas.service import ACTION_ANALYSIS, consume_quota
from scripts.cleanup_expired_data import cleanup_expired_data


@pytest.fixture
def phase16_client(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_PROVIDER", "legacy_local")
    monkeypatch.setenv("AUTH_SECRET_KEY", "phase16-secret")
    monkeypatch.setenv("APP_ENV", "development")
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


def test_user_cannot_read_another_users_private_report(phase16_client) -> None:
    client, Session = phase16_client
    with Session() as db:
        alice = create_user(db, "alice@example.test", token="alice-token")
        bob = create_user(db, "bob@example.test", token="bob-token")
        analysis = AnalysisRequestModel(
            id="analysis_private",
            strategy_description="Private Morpho strategy",
            protocols=["morpho"],
            manual_inputs_json={},
            analysis_depth="standard",
            owner_user_id=alice.id,
            visibility="private",
        )
        report = ReportModel(
            id="report_private",
            analysis_request_id=analysis.id,
            title="Private Report",
            risk_rating="Moderate",
            summary="Private summary",
            report_markdown="# Private",
            report_json={
                "report_id": "report_private",
                "protocols": ["morpho"],
                "risk_rating": "Moderate",
                "risk_score": 40,
                "executive_summary": "Private summary",
                "strategy_description": "Private Morpho strategy",
                "sections": [],
                "sources": [],
                "missing_data": [],
                "assumptions": [],
                "disclaimer": "Educational only, not financial advice.",
            },
            owner_user_id=alice.id,
            visibility="private",
        )
        db.add_all([analysis, report])
        db.commit()

    bob_response = client.get("/api/reports/report_private", headers=_auth("bob-token"))
    alice_response = client.get("/api/reports/report_private", headers=_auth("alice-token"))

    assert bob_response.status_code == 404
    assert alice_response.status_code == 200


def test_organization_final_owner_cannot_be_removed(phase16_client) -> None:
    client, _ = phase16_client
    with phase16_client[1]() as db:
        create_user(db, "owner@example.test", token="owner-token")

    org = client.post("/api/organizations", json={"name": "Risk Lab"}, headers=_auth("owner-token"))
    assert org.status_code == 200
    org_id = org.json()["id"]
    members = client.get(f"/api/organizations/{org_id}/members", headers=_auth("owner-token")).json()["items"]
    response = client.delete(
        f"/api/organizations/{org_id}/members/{members[0]['id']}",
        headers=_auth("owner-token"),
    )

    assert response.status_code == 409


def test_quota_boundary_and_exceeded(phase16_client, monkeypatch) -> None:
    monkeypatch.setenv("QUOTA_FREE_ANALYSES_PER_DAY", "1")
    get_settings.cache_clear()
    _, Session = phase16_client
    with Session() as db:
        user = create_user(db, "quota@example.test", token="quota-token")
        actor = app.dependency_overrides[get_db]  # keeps lint from treating fixture as unused magic
        del actor
        from app.auth.service import user_context

        context = user_context(user)
        first = consume_quota(db, context, ACTION_ANALYSIS)
        assert first["remaining"] == 0
        with pytest.raises(Exception):
            consume_quota(db, context, ACTION_ANALYSIS)


def test_cleanup_dry_run_does_not_remove_public_demo_records(phase16_client, monkeypatch) -> None:
    _, Session = phase16_client
    with Session() as db:
        user = create_user(db, "cleanup@example.test", token="cleanup-token")
        thesis = SavedThesisModel(
            id="thesis_old",
            owner_user_id=user.id,
            title="Old thesis",
            strategy_text="A sufficiently long strategy text.",
            protocols=[],
            assumptions_json={},
            visibility="private",
            deleted_at=datetime.now(UTC) - timedelta(days=90),
        )
        db.add(thesis)
        db.commit()
    monkeypatch.setattr("scripts.cleanup_expired_data.SessionLocal", Session)
    counts = cleanup_expired_data(dry_run=True)
    with Session() as db:
        assert db.get(SavedThesisModel, "thesis_old") is not None
    assert counts["soft_deleted_theses"] == 1


def test_supabase_jwt_validation_with_jwks(monkeypatch) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_numbers = private_key.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "kid": "test-key",
        "n": _b64int(public_numbers.n),
        "e": _b64int(public_numbers.e),
    }
    settings = Settings(
        auth_enabled=True,
        auth_provider="supabase",
        supabase_jwks_url="https://example.test/.well-known/jwks.json",
        supabase_jwt_issuer="https://project.supabase.co/auth/v1",
        supabase_jwt_audience="authenticated",
    )

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"keys": [jwk]}

    monkeypatch.setattr("app.auth.supabase.httpx.get", lambda *args, **kwargs: FakeResponse())
    token = _signed_jwt(
        private_key,
        {
            "sub": "supabase-user-1",
            "email": "USER@Example.Test",
            "email_verified": True,
            "iss": settings.supabase_jwt_issuer,
            "aud": "authenticated",
            "exp": int(time.time()) + 300,
        },
    )

    claims = verify_supabase_jwt(token, settings)

    assert claims.subject == "supabase-user-1"
    assert claims.email == "user@example.test"
    assert claims.email_verified is True


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _signed_jwt(private_key, payload: dict) -> str:
    header = {"alg": "RS256", "kid": "test-key", "typ": "JWT"}
    signing_input = f"{_b64json(header)}.{_b64json(payload)}".encode("ascii")
    signature = private_key.sign(signing_input, PKCS1v15(), SHA256())
    return f"{signing_input.decode('ascii')}.{_b64(signature)}"


def _b64json(value: dict) -> str:
    return _b64(json.dumps(value, separators=(",", ":")).encode("utf-8"))


def _b64int(value: int) -> str:
    return _b64(value.to_bytes((value.bit_length() + 7) // 8, "big"))


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")
