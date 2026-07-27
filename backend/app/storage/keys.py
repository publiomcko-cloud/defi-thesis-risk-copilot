from __future__ import annotations

import re

from app.models.knowledge import (
    KnowledgeDocumentModel,
    KnowledgeDocumentVersionModel,
    KnowledgeSourceModel,
)
from app.storage.base import StorageConfigurationError


_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")


def build_version_object_key(
    source: KnowledgeSourceModel,
    document: KnowledgeDocumentModel,
    version: KnowledgeDocumentVersionModel,
) -> str:
    if document.knowledge_source_id != source.id or version.document_id != document.id:
        raise StorageConfigurationError("Knowledge object lineage is invalid")
    scope_kind, scope_id = _source_scope(source)
    parts = (
        "knowledge",
        scope_kind,
        scope_id,
        "sources",
        source.id,
        "documents",
        document.id,
        "versions",
        version.id,
        "original",
    )
    for part in parts:
        if not _IDENTIFIER.fullmatch(part):
            raise StorageConfigurationError("Knowledge object identifier is invalid")
    return "/".join(parts)


def validate_knowledge_object_key(key: str) -> str:
    parts = key.split("/")
    if (
        len(parts) != 10
        or parts[0] != "knowledge"
        or parts[3] != "sources"
        or parts[5] != "documents"
        or parts[7] != "versions"
        or parts[9] != "original"
        or parts[1] not in {"public", "private", "organization"}
        or any(not _IDENTIFIER.fullmatch(part) for part in parts)
    ):
        raise StorageConfigurationError("Knowledge object key is invalid")
    return key


def _source_scope(source: KnowledgeSourceModel) -> tuple[str, str]:
    if source.visibility == "public" and source.owner_user_id is None and source.organization_id is None:
        return "public", "global"
    if source.visibility == "private" and source.owner_user_id and source.organization_id is None:
        return "private", source.owner_user_id
    if source.visibility == "organization" and source.organization_id:
        return "organization", source.organization_id
    raise StorageConfigurationError("Knowledge source scope is invalid")
