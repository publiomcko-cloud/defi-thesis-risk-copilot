from __future__ import annotations

from datetime import timedelta

import httpx
import pytest

from app.storage.base import StorageError
from app.storage.supabase import SupabasePrivateObjectStorage


OBJECT_KEY = (
    "knowledge/private/user_1/sources/ksrc_1/documents/"
    "kdoc_1/versions/kver_1/original"
)


def _adapter(handler) -> SupabasePrivateObjectStorage:
    return SupabasePrivateObjectStorage(
        supabase_url="https://project.supabase.co",
        service_role_key="phase18-storage-secret",
        bucket="private-knowledge",
        timeout_seconds=1,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def test_supabase_head_uses_object_info_endpoint() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            headers={"content-length": "42", "content-type": "text/markdown"},
        )

    metadata = _adapter(handler).head(key=OBJECT_KEY)

    assert metadata.size_bytes == 42
    assert metadata.content_type == "text/markdown"
    assert len(requests) == 1
    assert requests[0].method == "HEAD"
    assert requests[0].url.path == (
        "/storage/v1/object/info/private-knowledge/knowledge/private/user_1/"
        "sources/ksrc_1/documents/kdoc_1/versions/kver_1/original"
    )


def test_supabase_signed_url_accepts_only_expected_private_object_path() -> None:
    def valid_handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "signedURL": (
                    "/object/sign/private-knowledge/knowledge/private/user_1/"
                    "sources/ksrc_1/documents/kdoc_1/versions/kver_1/original?token=test"
                )
            },
        )

    signed = _adapter(valid_handler).signed_download_url(
        key=OBJECT_KEY,
        expires_in=timedelta(minutes=5),
    )
    assert signed.startswith(
        "https://project.supabase.co/storage/v1/object/sign/private-knowledge/"
    )

    def wrong_path_handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"signedURL": "/object/public/other-bucket/file"})

    with pytest.raises(StorageError, match="invalid signed URL"):
        _adapter(wrong_path_handler).signed_download_url(
            key=OBJECT_KEY,
            expires_in=timedelta(minutes=5),
        )


def test_supabase_signed_url_sanitizes_malformed_provider_response() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json")

    with pytest.raises(StorageError, match="invalid signed URL"):
        _adapter(handler).signed_download_url(
            key=OBJECT_KEY,
            expires_in=timedelta(minutes=5),
        )
