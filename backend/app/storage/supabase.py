from __future__ import annotations

from datetime import timedelta
from hashlib import sha256
from urllib.parse import quote, urljoin

import httpx

from app.storage.base import (
    ObjectConflictError,
    ObjectMetadata,
    ObjectNotFoundError,
    ObjectPayload,
    StorageConfigurationError,
    StorageError,
)
from app.storage.keys import validate_knowledge_object_key


class SupabasePrivateObjectStorage:
    def __init__(
        self,
        *,
        supabase_url: str,
        service_role_key: str,
        bucket: str,
        timeout_seconds: float,
        client: httpx.Client | None = None,
    ) -> None:
        if not supabase_url.startswith("https://") or not service_role_key or not bucket:
            raise StorageConfigurationError("Private Supabase Storage is not configured")
        self._base_url = f"{supabase_url.rstrip('/')}/storage/v1/"
        self._bucket = bucket
        self._service_role_key = service_role_key
        self._client = client or httpx.Client(timeout=timeout_seconds)

    def put_create_only(
        self,
        *,
        key: str,
        content: bytes,
        content_type: str,
        expected_checksum: str | None = None,
    ) -> ObjectMetadata:
        key = validate_knowledge_object_key(key)
        checksum = sha256(content).hexdigest()
        if expected_checksum is not None and checksum != expected_checksum:
            raise StorageError("Private object checksum does not match")
        response = self._request(
            "POST",
            self._object_path("object", key),
            content=content,
            headers={"content-type": content_type, "x-upsert": "false"},
        )
        self._raise_for_status(response)
        return ObjectMetadata(
            key=key,
            size_bytes=len(content),
            content_type=content_type,
            checksum=checksum,
        )

    def get_bounded(self, *, key: str, max_bytes: int) -> ObjectPayload:
        if max_bytes < 0:
            raise StorageError("Private object download limit is invalid")
        key = validate_knowledge_object_key(key)
        response = self._request("GET", self._object_path("object/authenticated", key))
        self._raise_for_status(response)
        content = response.content
        if len(content) > max_bytes:
            raise StorageError("Private object exceeds the allowed download size")
        return ObjectPayload(
            metadata=ObjectMetadata(
                key=key,
                size_bytes=len(content),
                content_type=response.headers.get("content-type", "application/octet-stream"),
                checksum=sha256(content).hexdigest(),
            ),
            content=content,
        )

    def head(self, *, key: str) -> ObjectMetadata:
        key = validate_knowledge_object_key(key)
        response = self._request("HEAD", self._object_path("object/authenticated", key))
        self._raise_for_status(response)
        try:
            size_bytes = int(response.headers.get("content-length", "0"))
        except ValueError as exc:
            raise StorageError("Private object metadata is invalid") from exc
        return ObjectMetadata(
            key=key,
            size_bytes=size_bytes,
            content_type=response.headers.get("content-type", "application/octet-stream"),
        )

    def delete(self, *, key: str) -> None:
        key = validate_knowledge_object_key(key)
        response = self._request("DELETE", self._object_path("object", key))
        if response.status_code == 404:
            return
        self._raise_for_status(response)

    def signed_download_url(self, *, key: str, expires_in: timedelta) -> str:
        key = validate_knowledge_object_key(key)
        seconds = int(expires_in.total_seconds())
        if seconds < 1 or seconds > 3600:
            raise StorageError("Signed download expiry must be between 1 and 3600 seconds")
        response = self._request(
            "POST",
            self._object_path("object/sign", key),
            json={"expiresIn": seconds},
        )
        self._raise_for_status(response)
        signed_path = response.json().get("signedURL")
        if not isinstance(signed_path, str) or not signed_path.startswith("/"):
            raise StorageError("Private storage returned an invalid signed URL")
        return urljoin(self._base_url, signed_path.lstrip("/"))

    def _object_path(self, endpoint: str, key: str) -> str:
        encoded_key = "/".join(quote(part, safe="") for part in key.split("/"))
        return f"{endpoint}/{quote(self._bucket, safe='')}/{encoded_key}"

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        headers = {
            "authorization": f"Bearer {self._service_role_key}",
            "apikey": self._service_role_key,
            **kwargs.pop("headers", {}),
        }
        try:
            return self._client.request(
                method,
                urljoin(self._base_url, path),
                headers=headers,
                **kwargs,
            )
        except httpx.HTTPError as exc:
            raise StorageError("Private storage request failed") from exc

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.status_code == 404:
            raise ObjectNotFoundError("Private object not found")
        if response.status_code in {409, 412}:
            raise ObjectConflictError("Private object already exists")
        if response.is_error:
            raise StorageError("Private storage request failed")
