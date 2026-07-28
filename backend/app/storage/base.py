from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol


class StorageError(RuntimeError):
    """Base class for sanitized private-storage failures."""


class StorageConfigurationError(StorageError):
    pass


class ObjectNotFoundError(StorageError):
    pass


class ObjectConflictError(StorageError):
    pass


@dataclass(frozen=True)
class ObjectMetadata:
    key: str
    size_bytes: int
    content_type: str
    checksum: str | None = None


@dataclass(frozen=True)
class ObjectPayload:
    metadata: ObjectMetadata
    content: bytes


class PrivateObjectStorage(Protocol):
    def put_create_only(
        self,
        *,
        key: str,
        content: bytes,
        content_type: str,
        expected_checksum: str | None = None,
    ) -> ObjectMetadata: ...

    def get_bounded(self, *, key: str, max_bytes: int) -> ObjectPayload: ...

    def head(self, *, key: str) -> ObjectMetadata: ...

    def delete(self, *, key: str) -> None: ...

    def signed_download_url(self, *, key: str, expires_in: timedelta) -> str: ...
