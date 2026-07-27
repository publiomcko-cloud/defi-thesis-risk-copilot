from __future__ import annotations

from datetime import timedelta
from hashlib import sha256

from app.storage.base import (
    ObjectConflictError,
    ObjectMetadata,
    ObjectNotFoundError,
    ObjectPayload,
    StorageError,
)
from app.storage.keys import validate_knowledge_object_key


class InMemoryPrivateObjectStorage:
    def __init__(self) -> None:
        self._objects: dict[str, ObjectPayload] = {}

    def put_create_only(
        self,
        *,
        key: str,
        content: bytes,
        content_type: str,
        expected_checksum: str | None = None,
    ) -> ObjectMetadata:
        key = validate_knowledge_object_key(key)
        if key in self._objects:
            raise ObjectConflictError("Private object already exists")
        checksum = sha256(content).hexdigest()
        if expected_checksum is not None and checksum != expected_checksum:
            raise StorageError("Private object checksum does not match")
        metadata = ObjectMetadata(
            key=key,
            size_bytes=len(content),
            content_type=content_type,
            checksum=checksum,
        )
        self._objects[key] = ObjectPayload(metadata=metadata, content=bytes(content))
        return metadata

    def get_bounded(self, *, key: str, max_bytes: int) -> ObjectPayload:
        key = validate_knowledge_object_key(key)
        payload = self._objects.get(key)
        if payload is None:
            raise ObjectNotFoundError("Private object not found")
        if max_bytes < 0 or payload.metadata.size_bytes > max_bytes:
            raise StorageError("Private object exceeds the allowed download size")
        return payload

    def head(self, *, key: str) -> ObjectMetadata:
        key = validate_knowledge_object_key(key)
        payload = self._objects.get(key)
        if payload is None:
            raise ObjectNotFoundError("Private object not found")
        return payload.metadata

    def delete(self, *, key: str) -> None:
        key = validate_knowledge_object_key(key)
        self._objects.pop(key, None)

    def signed_download_url(self, *, key: str, expires_in: timedelta) -> str:
        validate_knowledge_object_key(key)
        raise StorageError("In-memory storage does not expose download URLs")
