"""Sanitized restore-drill manifests for Phase 19E.

This is intentionally verification tooling, not a backup implementation. It
never serializes report text, strategy inputs, source content, storage keys,
checksums, user identities, or credentials. An approved database/object-storage
provider remains responsible for creating and restoring encrypted backups.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.analysis_request import AnalysisRequestModel
from app.models.artifact import ArtifactModel
from app.models.job import JobModel
from app.models.knowledge import (
    KnowledgeChunkEmbeddingModel,
    KnowledgeChunkModel,
    KnowledgeDocumentModel,
    KnowledgeDocumentVersionModel,
    KnowledgeEmbeddingGenerationModel,
    KnowledgeSourceModel,
)
from app.models.report import ReportModel


MANIFEST_FORMAT = "phase19e.sanitized-restore-manifest.v1"


class SanitizedRestoreManifest(BaseModel):
    format_version: str = MANIFEST_FORMAT
    generated_at: datetime
    schema_revision: str | None = None
    fingerprint_salt: str = Field(min_length=16, max_length=128)
    resource_counts: dict[str, int]
    metadata_fingerprints: dict[str, list[str]]
    limitations: list[str]


class RestoreVerification(BaseModel):
    passed: bool
    expected_schema_revision: str | None
    observed_schema_revision: str | None
    mismatched_collections: list[str]


def create_sanitized_restore_manifest(
    db: Session,
    *,
    now: datetime | None = None,
    fingerprint_salt: str | None = None,
) -> SanitizedRestoreManifest:
    """Capture safe metadata evidence suitable for an isolated restore drill."""

    salt = fingerprint_salt or secrets.token_hex(16)
    collections = _collections(db, salt)
    return SanitizedRestoreManifest(
        generated_at=now or datetime.now(UTC),
        schema_revision=_schema_revision(db),
        fingerprint_salt=salt,
        resource_counts={name: len(values) for name, values in collections.items()},
        metadata_fingerprints={name: sorted(values) for name, values in collections.items()},
        limitations=[
            "Metadata-only verification; this manifest is not a database or object-storage backup.",
            "No report text, strategy input, source content, storage key, checksum, user identity, or credential is included.",
            "Run verification only against an approved isolated restore target; Alembic downgrade is not data recovery.",
        ],
    )


def verify_sanitized_restore_manifest(
    manifest: SanitizedRestoreManifest,
    db: Session,
) -> RestoreVerification:
    """Compare a restored target's safe metadata shape to an expected manifest."""

    observed = create_sanitized_restore_manifest(db, fingerprint_salt=manifest.fingerprint_salt)
    mismatched = [
        name
        for name in sorted(set(manifest.resource_counts) | set(observed.resource_counts))
        if manifest.resource_counts.get(name) != observed.resource_counts.get(name)
        or manifest.metadata_fingerprints.get(name) != observed.metadata_fingerprints.get(name)
    ]
    schema_matches = manifest.schema_revision == observed.schema_revision
    if not schema_matches:
        mismatched.append("schema_revision")
    return RestoreVerification(
        passed=not mismatched,
        expected_schema_revision=manifest.schema_revision,
        observed_schema_revision=observed.schema_revision,
        mismatched_collections=mismatched,
    )


def _collections(db: Session, salt: str) -> dict[str, list[str]]:
    return {
        "analysis_requests": [
            _fingerprint(salt, "analysis_request", row.id, row.visibility, row.analysis_depth, bool(row.deleted_at))
            for row in db.execute(select(AnalysisRequestModel)).scalars()
        ],
        "reports": [
            _fingerprint(salt, "report", row.id, row.risk_rating, row.visibility, bool(row.deleted_at), bool(row.source_job_id))
            for row in db.execute(select(ReportModel)).scalars()
        ],
        "jobs": [
            _fingerprint(salt, "job", row.id, row.job_type, row.status, row.visibility, row.priority_class)
            for row in db.execute(select(JobModel)).scalars()
        ],
        "artifacts": [
            _fingerprint(
                salt,
                "artifact",
                row.id,
                row.artifact_type,
                row.status,
                row.visibility,
                bool(row.storage_backend and row.storage_key),
                bool(row.deleted_at),
            )
            for row in db.execute(select(ArtifactModel)).scalars()
        ],
        "knowledge_sources": [
            _fingerprint(salt, "knowledge_source", row.id, row.visibility, row.source_type, row.status, row.trust_state, bool(row.deleted_at))
            for row in db.execute(select(KnowledgeSourceModel)).scalars()
        ],
        "knowledge_documents": [
            _fingerprint(salt, "knowledge_document", row.id, row.media_type, row.status, bool(row.current_version_id), bool(row.deleted_at))
            for row in db.execute(select(KnowledgeDocumentModel)).scalars()
        ],
        "knowledge_versions": [
            _fingerprint(
                salt,
                "knowledge_version",
                row.id,
                row.version_number,
                row.status,
                row.size_bytes,
                row.parser_version,
                row.chunker_version,
                bool(row.storage_key),
                bool(row.active_embedding_generation_id),
                bool(row.deleted_at),
            )
            for row in db.execute(select(KnowledgeDocumentVersionModel)).scalars()
        ],
        "knowledge_chunks": [
            _fingerprint(salt, "knowledge_chunk", row.id, row.chunk_index, row.token_count, bool(row.deleted_at))
            for row in db.execute(select(KnowledgeChunkModel)).scalars()
        ],
        "embedding_generations": [
            _fingerprint(
                salt,
                "embedding_generation",
                row.id,
                row.status,
                row.expected_chunk_count,
                row.completed_chunk_count,
                bool(row.deleted_at),
            )
            for row in db.execute(select(KnowledgeEmbeddingGenerationModel)).scalars()
        ],
        "chunk_embeddings": [
            _fingerprint(salt, "chunk_embedding", row.id, row.status, row.dimensions, bool(row.deleted_at))
            for row in db.execute(select(KnowledgeChunkEmbeddingModel)).scalars()
        ],
    }


def _fingerprint(salt: str, collection: str, row_id: str, *metadata: Any) -> str:
    encoded = "|".join([salt, collection, row_id, *[str(value) for value in metadata]]).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _schema_revision(db: Session) -> str | None:
    try:
        return db.execute(text("select version_num from alembic_version")).scalar_one_or_none()
    except Exception:
        return None
