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

from app.auth.service import create_user, sync_supabase_user
from app.auth.supabase import verify_supabase_jwt
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.analysis_request import AnalysisRequestModel
from app.models.anonymous_session import AnonymousSessionModel
from app.models.consent_record import ConsentRecordModel
from app.models.organization import OrganizationMembershipModel, OrganizationModel
from app.models.report import ReportModel
from app.models.saved_thesis import SavedThesisModel
from app.models.watchlist_item import WatchlistItemModel
from app.quotas.service import ACTION_ANALYSIS, consume_quota
from app.auth.supabase import SupabaseClaims
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


def test_private_resource_ignores_stale_organization_id(phase16_client) -> None:
    client, Session = phase16_client
    now = datetime.now(UTC)
    with Session() as db:
        alice = create_user(db, "private-owner@example.test", token="private-owner-token")
        bob = create_user(db, "org-member@example.test", token="org-member-token")
        org = OrganizationModel(
            id="org_stale_private",
            name="Stale Org",
            slug="stale-org",
            status="active",
            created_by_user_id=alice.id,
            created_at=now,
            updated_at=now,
        )
        membership = OrganizationMembershipModel(
            id="member_stale_private",
            organization_id=org.id,
            user_id=bob.id,
            role="member",
            status="active",
            created_at=now,
            updated_at=now,
        )
        analysis = AnalysisRequestModel(
            id="analysis_stale_org",
            strategy_description="Private strategy with stale org id",
            protocols=["morpho"],
            manual_inputs_json={},
            analysis_depth="standard",
            owner_user_id=alice.id,
            organization_id=org.id,
            visibility="private",
        )
        report = ReportModel(
            id="report_stale_org",
            analysis_request_id=analysis.id,
            title="Private With Stale Org",
            risk_rating="Moderate",
            summary="Private summary",
            report_markdown="# Private",
            report_json=_report_json("report_stale_org"),
            owner_user_id=alice.id,
            organization_id=org.id,
            visibility="private",
        )
        db.add_all([org, membership, analysis, report])
        db.commit()

    assert client.get("/api/reports/report_stale_org", headers=_auth("org-member-token")).status_code == 404
    assert client.get("/api/reports/report_stale_org", headers=_auth("private-owner-token")).status_code == 200


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


def test_supabase_jwt_rejects_invalid_claims_and_signature(monkeypatch) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
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
    base_payload = {
        "sub": "supabase-user-1",
        "email": "user@example.test",
        "email_verified": True,
        "iss": settings.supabase_jwt_issuer,
        "aud": "authenticated",
        "exp": int(time.time()) + 300,
    }

    bad_tokens = [
        "not.a.jwt",
        _signed_jwt(private_key, {**base_payload, "exp": int(time.time()) - 1}),
        _signed_jwt(private_key, {**base_payload, "iss": "https://wrong.example"}),
        _signed_jwt(private_key, {**base_payload, "aud": "wrong"}),
        _signed_jwt(other_key, base_payload),
    ]

    for token in bad_tokens:
        with pytest.raises(Exception):
            verify_supabase_jwt(token, settings)


def test_admin_mfa_requires_aal2_without_blocking_ordinary_users(
    phase16_client,
    monkeypatch,
) -> None:
    client, Session = phase16_client
    monkeypatch.setenv("AUTH_PROVIDER", "supabase")
    monkeypatch.setenv("ADMIN_MFA_REQUIRED", "true")
    get_settings.cache_clear()

    with Session() as db:
        admin = create_user(db, "mfa-admin@example.test")
        admin.auth_provider = "supabase"
        admin.auth_subject = "mfa-admin-subject"
        admin.platform_role = "admin"
        admin.role = "admin"
        user = create_user(db, "mfa-user@example.test")
        user.auth_provider = "supabase"
        user.auth_subject = "mfa-user-subject"
        db.commit()

    def claims_for_token(token: str, _settings: Settings) -> SupabaseClaims:
        is_admin = token.startswith("admin-")
        return SupabaseClaims(
            subject="mfa-admin-subject" if is_admin else "mfa-user-subject",
            email="mfa-admin@example.test" if is_admin else "mfa-user@example.test",
            email_verified=True,
            issuer="https://project.supabase.co/auth/v1",
            audience="authenticated",
            expires_at=int(time.time()) + 300,
            raw={"aal": "aal2" if token == "admin-aal2" else "aal1"},
        )

    monkeypatch.setattr("app.auth.dependencies.verify_supabase_jwt", claims_for_token)

    denied = client.get("/api/admin/audit-events", headers=_auth("admin-aal1"))
    allowed = client.get("/api/admin/audit-events", headers=_auth("admin-aal2"))
    ordinary = client.get("/api/auth/me", headers=_auth("user-aal1"))

    assert denied.status_code == 403
    assert denied.json()["detail"] == "Administrator MFA required"
    assert allowed.status_code == 200
    assert ordinary.status_code == 200
    assert ordinary.json()["platform_role"] == "user"


def test_anonymous_report_isolation_and_expiration(phase16_client, monkeypatch) -> None:
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("PUBLIC_DEMO_MODE", "true")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    monkeypatch.setenv("ANONYMOUS_RETENTION_HOURS", "1")
    get_settings.cache_clear()
    client, Session = phase16_client
    now = datetime.now(UTC)
    with Session() as db:
        db.add_all(
            [
                AnonymousSessionModel(
                    id="anon_a",
                    status="active",
                    created_at=now,
                    last_seen_at=now,
                    expires_at=now + timedelta(hours=1),
                ),
                AnonymousSessionModel(
                    id="anon_expired",
                    status="active",
                    created_at=now - timedelta(hours=2),
                    last_seen_at=now - timedelta(hours=2),
                    expires_at=now - timedelta(minutes=1),
                ),
            ]
        )
        analysis = AnalysisRequestModel(
            id="analysis_anon",
            strategy_description="Anonymous strategy",
            protocols=["pendle"],
            manual_inputs_json={},
            analysis_depth="standard",
            visibility="private",
            anonymous_session_id="anon_a",
            expires_at=now + timedelta(hours=1),
        )
        report = ReportModel(
            id="report_anon",
            analysis_request_id=analysis.id,
            title="Anon Report",
            risk_rating="Moderate",
            summary="Anon summary",
            report_markdown="# Anon",
            report_json=_report_json("report_anon"),
            visibility="private",
            anonymous_session_id="anon_a",
            expires_at=now + timedelta(hours=1),
        )
        db.add_all([analysis, report])
        db.commit()

    client.cookies.set("defi_copilot_anon", "anon_a")
    assert client.get("/api/reports/report_anon").status_code == 200
    client.cookies.clear()
    assert client.get("/api/reports/report_anon").status_code == 404
    client.cookies.clear()
    client.cookies.set("defi_copilot_anon", "anon_expired")
    assert client.get("/api/reports/report_anon").status_code == 404


def test_watchlist_resource_count_quota(phase16_client, monkeypatch) -> None:
    monkeypatch.setenv("QUOTA_FREE_WATCHLISTS", "1")
    get_settings.cache_clear()
    client, Session = phase16_client
    with Session() as db:
        create_user(db, "watch@example.test", token="watch-token")
    payload = {
        "item_type": "market",
        "title": "Borrow watch",
        "rules": {"borrow_apy_above_threshold": 0.05},
        "snapshot": {"borrow_apy": 0.07},
    }
    first = client.post("/api/watchlist/items", json=payload, headers=_auth("watch-token"))
    second = client.post("/api/watchlist/items", json={**payload, "title": "Borrow watch 2"}, headers=_auth("watch-token"))
    assert first.status_code == 200
    assert second.status_code == 429


def test_public_demo_durable_mutations_require_authenticated_user(phase16_client, monkeypatch) -> None:
    client, Session = phase16_client
    monkeypatch.setenv("PUBLIC_DEMO_MODE", "true")
    monkeypatch.setenv("AUTH_ENABLED", "false")
    get_settings.cache_clear()
    thesis_payload = {
        "title": "Public blocked thesis",
        "strategy_text": "A sufficiently long public demo strategy text.",
        "protocols": ["pendle"],
        "assumptions": {},
        "visibility": "private",
    }
    blocked = client.post("/api/theses", json=thesis_payload)
    assert blocked.status_code == 403

    monkeypatch.setenv("AUTH_ENABLED", "true")
    get_settings.cache_clear()
    with Session() as db:
        create_user(db, "hybrid-user@example.test", token="hybrid-user-token")
    allowed = client.post("/api/theses", json=thesis_payload, headers=_auth("hybrid-user-token"))
    assert allowed.status_code == 200


def test_signup_consent_versions_are_server_owned(phase16_client, monkeypatch) -> None:
    monkeypatch.setenv("AUTH_PROVIDER", "supabase")
    monkeypatch.setenv("CURRENT_TERMS_VERSION", "terms-server-version")
    monkeypatch.setenv("CURRENT_PRIVACY_VERSION", "privacy-server-version")
    get_settings.cache_clear()
    _, Session = phase16_client
    claims = SupabaseClaims(
        subject="supabase-consent-user",
        email="consent@example.test",
        email_verified=True,
        issuer="https://project.supabase.co/auth/v1",
        audience="authenticated",
        expires_at=int(time.time()) + 300,
        raw={
            "user_metadata": {
                "accepted_terms_version": "client-forged-terms",
                "accepted_privacy_version": "client-forged-privacy",
            }
        },
    )
    with Session() as db:
        user = sync_supabase_user(db, claims)
        versions = {
            record.document_type: record.document_version
            for record in db.query(ConsentRecordModel).filter(ConsentRecordModel.user_id == user.id).all()
        }
    assert versions == {"terms": "terms-server-version", "privacy": "privacy-server-version"}


def test_cleanup_anonymizes_deleted_user_and_removes_expired_watchlist(phase16_client, monkeypatch) -> None:
    _, Session = phase16_client
    old = datetime.now(UTC) - timedelta(days=90)
    with Session() as db:
        user = create_user(db, "delete-me@example.test", token="delete-token")
        user_id = user.id
        user.deleted_at = old
        user.account_status = "deleted"
        watch = WatchlistItemModel(
            id="watch_expired",
            item_type="market",
            title="Expired watch",
            rules_json={},
            snapshot_json={},
            visibility="private",
            owner_user_id=user.id,
            expires_at=datetime.now(UTC) - timedelta(minutes=1),
        )
        db.add(watch)
        db.commit()
    monkeypatch.setattr("scripts.cleanup_expired_data.SessionLocal", Session)
    cleanup_expired_data(dry_run=False)
    with Session() as db:
        from app.models.user import UserModel

        user = db.get(UserModel, user_id)
        assert user.email.endswith("@deleted.local")
        assert user.access_token_hash is None
        assert db.get(WatchlistItemModel, "watch_expired") is None


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _report_json(report_id: str) -> dict:
    return {
        "report_id": report_id,
        "status": "completed",
        "risk_rating": "Moderate",
        "executive_summary": "Summary",
        "strategy_description": "Strategy",
        "protocols": ["pendle"],
        "assumptions": [],
        "missing_data": [],
        "sections": [],
        "sources": [],
        "disclaimer": "Educational only.",
    }


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
