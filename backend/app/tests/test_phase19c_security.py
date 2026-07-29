from __future__ import annotations

import asyncio
from contextlib import contextmanager

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.knowledge.upload_scanner import UploadScanError, require_clean_upload
from app.main import create_app


async def _asgi_status_for_body(app, chunks: list[bytes], content_length: str | None) -> int:
    """Send raw ASGI frames to prove middleware counts received bytes."""

    pending = list(chunks)
    sent: list[dict] = []

    async def receive() -> dict:
        if pending:
            return {"type": "http.request", "body": pending.pop(0), "more_body": bool(pending)}
        return {"type": "http.disconnect"}

    async def send(message: dict) -> None:
        sent.append(message)

    headers = [(b"host", b"api.example.test")]
    if content_length is not None:
        headers.append((b"content-length", content_length.encode()))
    await app(
        {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "https",
            "path": "/api/analyze",
            "raw_path": b"/api/analyze",
            "query_string": b"",
            "headers": headers,
            "client": ("198.51.100.10", 12345),
            "server": ("api.example.test", 443),
        },
        receive,
        send,
    )
    return next(message["status"] for message in sent if message["type"] == "http.response.start")


def test_api_uses_exact_cors_origins_security_headers_and_origin_checks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://app.example.test")
    monkeypatch.setenv("SECURITY_HSTS_ENABLED", "true")
    monkeypatch.setenv("API_MAX_REQUEST_BYTES", "12")
    get_settings.cache_clear()
    try:
        with TestClient(create_app()) as client:
            response = client.get("/health")
            preflight = client.options(
                "/api/analyze",
                headers={
                    "Origin": "https://app.example.test",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type,x-correlation-id",
                },
            )
            rejected_preflight = client.options(
                "/api/analyze",
                headers={
                    "Origin": "https://untrusted.example.test",
                    "Access-Control-Request-Method": "POST",
                },
            )
            forged = client.post("/api/analyze", headers={"Origin": "https://untrusted.example.test"})
            allowed = client.post("/api/analyze", headers={"Origin": "https://app.example.test"})
            oversized = client.post("/api/analyze", content=b"0123456789abc")
    finally:
        get_settings.cache_clear()

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"
    assert preflight.headers["access-control-allow-origin"] == "https://app.example.test"
    assert "access-control-allow-origin" not in rejected_preflight.headers
    assert forged.status_code == 403
    assert allowed.status_code != 403
    assert oversized.status_code == 413


def test_api_measures_chunked_and_misleading_content_length_bodies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_MAX_REQUEST_BYTES", "5")
    get_settings.cache_clear()
    try:
        app = create_app()
        chunked_status = asyncio.run(_asgi_status_for_body(app, [b"123", b"456"], None))
        misleading_status = asyncio.run(_asgi_status_for_body(app, [b"123456"], "1"))
        accepted_status = asyncio.run(_asgi_status_for_body(app, [b"12", b"34"], "1"))
    finally:
        get_settings.cache_clear()

    assert chunked_status == 413
    assert misleading_status == 413
    # The body guard accepted all four actual bytes; request-schema validation
    # may reject the empty/non-JSON analysis payload after that point.
    assert accepted_status != 413


def test_security_configuration_rejects_unsafe_origin_and_unscanned_production_storage() -> None:
    with pytest.raises(ValidationError, match="FRONTEND_ORIGIN"):
        Settings(frontend_origin="https://app.example.test/path")
    with pytest.raises(ValidationError, match="KNOWLEDGE_UPLOAD_SCANNING_REQUIRED"):
        Settings(
            app_env="production",
            knowledge_storage_enabled=True,
            supabase_url="https://project.supabase.co",
            supabase_service_role_key="test-service-role-key",
        )
    with pytest.raises(ValidationError, match="KNOWLEDGE_UPLOAD_SCANNER_URL"):
        Settings(
            knowledge_storage_enabled=True,
            knowledge_upload_scanning_required=True,
            knowledge_upload_scanner_url="file:///tmp/scanner",
        )


def test_required_upload_scanner_accepts_only_clean_bounded_json(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, limit: int) -> bytes:
            captured["read_limit"] = limit
            return b'{"status":"clean"}'

    class Opener:
        @contextmanager
        def open(self, request, timeout: float):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            captured["headers"] = {key.lower(): value for key, value in request.header_items()}
            yield Response()

    monkeypatch.setattr("app.knowledge.upload_scanner.build_opener", lambda *_handlers: Opener())
    settings = Settings(
        knowledge_storage_enabled=True,
        knowledge_upload_scanning_required=True,
        knowledge_upload_scanner_url="https://scanner.internal.test/scan",
        knowledge_upload_scanner_timeout_seconds=3,
    )
    require_clean_upload(content=b"# bounded upload", media_type="text/markdown", settings=settings)

    assert captured["url"] == "https://scanner.internal.test/scan"
    assert captured["timeout"] == 3
    assert captured["read_limit"] == 8_192
    assert captured["headers"] and "x-content-sha256" in captured["headers"]

    class UnsafeResponse(Response):
        def read(self, limit: int) -> bytes:
            return b'{"status":"infected"}'

    class UnsafeOpener(Opener):
        @contextmanager
        def open(self, request, timeout: float):
            yield UnsafeResponse()

    monkeypatch.setattr("app.knowledge.upload_scanner.build_opener", lambda *_handlers: UnsafeOpener())
    with pytest.raises(UploadScanError, match="did not mark upload clean"):
        require_clean_upload(content=b"# unsafe", media_type="text/markdown", settings=settings)


def test_upload_service_fails_closed_when_a_required_scanner_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KNOWLEDGE_STORAGE_ENABLED", "true")
    monkeypatch.setenv("KNOWLEDGE_UPLOAD_SCANNING_REQUIRED", "true")
    monkeypatch.setenv("KNOWLEDGE_UPLOAD_SCANNER_URL", "https://scanner.internal.test/scan")
    get_settings.cache_clear()
    monkeypatch.setattr(
        "app.knowledge.service.require_clean_upload",
        lambda **_kwargs: (_ for _ in ()).throw(UploadScanError("unavailable")),
    )
    try:
        from app.knowledge.service import _require_clean_upload

        with pytest.raises(HTTPException) as rejected:
            _require_clean_upload(content=b"# blocked", media_type="text/markdown")
    finally:
        get_settings.cache_clear()

    assert rejected.value.status_code == 503
    assert rejected.value.detail == "Knowledge upload security scan is unavailable"
