"""Feature-gated pgvector shadow retrieval with server-derived tenant scope.

This module deliberately has no dependency on the report workflow.  Phase 18E
records comparable durable retrieval evidence while the curated JSON index
continues to produce every analysis report.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from math import sqrt
from time import perf_counter
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import and_, or_, select, text
from sqlalchemy.orm import Session

from app.auth.schemas import UserContext
from app.jobs.cancellation import CancellationContext
from app.knowledge.access import derive_knowledge_access_scope
from app.knowledge.embedding import LocalDeterministicEmbeddingProvider
from app.knowledge.schemas import (
    KnowledgeCitationResponse,
    ShadowRetrievalItemResponse,
    ShadowRetrievalResponse,
)
from app.models.knowledge import (
    KnowledgeChunkEmbeddingModel,
    KnowledgeChunkModel,
    KnowledgeDocumentModel,
    KnowledgeDocumentVersionModel,
    KnowledgeEmbeddingProfileModel,
    KnowledgeRetrievalEventModel,
    KnowledgeSourceModel,
)
from app.rag.retriever import RetrievalResult


SHADOW_RETRIEVER_VERSION = "phase18e.pgvector-shadow.v1"
_MAX_EXCERPT_CHARACTERS = 700
_MAX_CANDIDATES = 80


@dataclass(frozen=True)
class _RetrievedChunk:
    source: KnowledgeSourceModel
    document: KnowledgeDocumentModel
    version: KnowledgeDocumentVersionModel
    chunk: KnowledgeChunkModel
    embedding: KnowledgeChunkEmbeddingModel
    score: float


def retrieve_shadow_knowledge(
    db: Session,
    actor: UserContext,
    *,
    query: str,
    top_k: int | None,
    protocols: list[str],
    request_id: str,
) -> ShadowRetrievalResponse:
    """Retrieve durable chunks without allowing a client to provide tenant scope."""

    settings = get_settings()
    if not settings.knowledge_shadow_retrieval_enabled:
        raise HTTPException(status_code=503, detail="Durable shadow retrieval is disabled")

    normalized_query = query.strip()
    if not normalized_query:
        raise HTTPException(status_code=422, detail="Retrieval query is invalid")
    normalized_protocols = sorted(
        {protocol.strip().lower() for protocol in protocols if protocol.strip()}
    )
    requested_top_k = top_k or settings.knowledge_shadow_retrieval_top_k
    if requested_top_k > settings.knowledge_shadow_retrieval_top_k:
        requested_top_k = settings.knowledge_shadow_retrieval_top_k

    started = perf_counter()
    query_embedding = LocalDeterministicEmbeddingProvider().embed(
        normalized_query, CancellationContext()
    )
    rows = _eligible_embeddings(
        db,
        actor,
        protocol_filter=normalized_protocols,
        query_embedding=query_embedding,
        top_k=_candidate_limit(requested_top_k),
    )
    results = [
        result
        for row in rows
        if (result := _to_retrieved_chunk(row, query_embedding)) is not None
    ]
    # SQLite uses the JSON embedding compatibility field. PostgreSQL is ranked
    # by the pgvector ORDER BY in _eligible_embeddings before this stable score.
    if db.bind is None or db.bind.dialect.name != "postgresql":
        results.sort(key=lambda item: item.score, reverse=True)
    results = results[:requested_top_k]

    items = [
        ShadowRetrievalItemResponse(
            score=round(item.score, 6),
            excerpt=_excerpt(item.chunk.content),
            citation=_citation_for(item),
        )
        for item in results
    ]
    event = KnowledgeRetrievalEventModel(
        id=f"kretr_{uuid4().hex[:12]}",
        request_id=request_id,
        user_id=actor.id,
        # A request can see more than one active organization. Do not record an
        # arbitrary organization as the event's tenant scope.
        organization_id=None,
        query_hash=sha256(normalized_query.encode("utf-8")).hexdigest(),
        filters_json={
            "visibility": ["public", "private", "organization"],
            "protocols": normalized_protocols,
            "organization_scope_count": len(derive_knowledge_access_scope(db, actor).organization_ids),
        },
        retrieved_chunk_ids=[item.citation.chunk_id for item in items],
        scores_json=[item.score for item in items],
        latency_ms=max(0, round((perf_counter() - started) * 1000)),
        retriever_version=SHADOW_RETRIEVER_VERSION,
    )
    db.add(event)
    db.flush()
    return ShadowRetrievalResponse(
        request_id=request_id,
        retrieval_event_id=event.id,
        retriever_version=SHADOW_RETRIEVER_VERSION,
        items=items,
    )


def retrieve_durable_analysis_context(
    db: Session,
    actor: UserContext | None,
    *,
    query: str,
    protocols: list[str] | None = None,
    top_k: int = 4,
) -> list[RetrievalResult]:
    """Return tenant-safe durable report context with exact lineage.

    ``actor`` is a server-authenticated identity, never browser scope data.
    A missing or anonymous actor intentionally receives public rows only.
    """

    normalized_query = query.strip()
    if not normalized_query:
        return []
    requested_top_k = max(1, min(top_k, 20))
    protocol_filter = sorted(
        {item.strip().lower() for item in protocols or [] if item.strip()}
    )
    query_embedding = LocalDeterministicEmbeddingProvider().embed(
        normalized_query, CancellationContext()
    )
    rows = _eligible_embeddings(
        db,
        actor,
        protocol_filter=protocol_filter,
        query_embedding=query_embedding,
        top_k=_candidate_limit(requested_top_k),
    )
    results = [
        item
        for row in rows
        if (item := _to_retrieved_chunk(row, query_embedding)) is not None
    ]
    if db.bind is None or db.bind.dialect.name != "postgresql":
        results.sort(key=lambda item: item.score, reverse=True)
    results = results[:requested_top_k]
    return [
        RetrievalResult(
            chunk_id=item.chunk.id,
            text=item.chunk.content,
            metadata={
                **item.chunk.metadata_json,
                "protocol": item.source.protocol or "unknown",
                "source_url": item.source.canonical_uri
                or item.source.source_uri
                or "knowledge_base/README.md",
                "document_title": item.source.title,
                "section_title": item.chunk.heading_path[-1]
                if item.chunk.heading_path
                else item.source.title,
                "knowledge_scope": item.source.visibility,
                "citation_lineage": _citation_for(item).model_dump(),
            },
            similarity_score=item.score,
        )
        for item in results
    ]


def _eligible_embeddings(
    db: Session,
    actor: UserContext | None,
    *,
    protocol_filter: list[str],
    query_embedding: list[float],
    top_k: int,
) -> list[tuple[KnowledgeSourceModel, KnowledgeDocumentModel, KnowledgeDocumentVersionModel, KnowledgeChunkModel, KnowledgeChunkEmbeddingModel]]:
    """Apply trust, lifecycle, current-version, and tenant filters before ranking."""

    if actor is None or actor.anonymous_session_id or (
        not actor.auth_enabled and not actor.is_admin
    ):
        visibility_filter = KnowledgeSourceModel.visibility == "public"
    else:
        scope = derive_knowledge_access_scope(db, actor)
        visibility_filter = or_(
            KnowledgeSourceModel.visibility == "public",
            and_(
                KnowledgeSourceModel.visibility == "private",
                KnowledgeSourceModel.owner_user_id == scope.user_id,
            ),
            and_(
                KnowledgeSourceModel.visibility == "organization",
                KnowledgeSourceModel.organization_id.in_(scope.organization_ids),
            ),
        )
    statement = (
        select(
            KnowledgeSourceModel,
            KnowledgeDocumentModel,
            KnowledgeDocumentVersionModel,
            KnowledgeChunkModel,
            KnowledgeChunkEmbeddingModel,
        )
        .join(
            KnowledgeDocumentModel,
            KnowledgeDocumentModel.knowledge_source_id == KnowledgeSourceModel.id,
        )
        .join(
            KnowledgeDocumentVersionModel,
            KnowledgeDocumentVersionModel.document_id == KnowledgeDocumentModel.id,
        )
        .join(
            KnowledgeChunkModel,
            KnowledgeChunkModel.document_version_id == KnowledgeDocumentVersionModel.id,
        )
        .join(
            KnowledgeChunkEmbeddingModel,
            KnowledgeChunkEmbeddingModel.knowledge_chunk_id == KnowledgeChunkModel.id,
        )
        .join(
            KnowledgeEmbeddingProfileModel,
            KnowledgeEmbeddingProfileModel.id == KnowledgeChunkEmbeddingModel.embedding_profile_id,
        )
        .where(visibility_filter)
        .where(KnowledgeSourceModel.trust_state == "approved_for_rag")
        .where(KnowledgeSourceModel.status == "ingested")
        .where(KnowledgeSourceModel.deleted_at.is_(None))
        .where(KnowledgeDocumentModel.status == "ready")
        .where(KnowledgeDocumentModel.deleted_at.is_(None))
        .where(KnowledgeDocumentModel.current_version_id == KnowledgeDocumentVersionModel.id)
        .where(KnowledgeDocumentVersionModel.status == "ready")
        .where(KnowledgeDocumentVersionModel.deleted_at.is_(None))
        .where(KnowledgeChunkModel.deleted_at.is_(None))
        .where(
            KnowledgeChunkEmbeddingModel.embedding_generation_id
            == KnowledgeDocumentVersionModel.active_embedding_generation_id
        )
        .where(KnowledgeChunkEmbeddingModel.status == "completed")
        .where(KnowledgeChunkEmbeddingModel.deleted_at.is_(None))
        .where(KnowledgeEmbeddingProfileModel.status == "active")
    )
    if protocol_filter:
        statement = statement.where(KnowledgeSourceModel.protocol.in_(protocol_filter))
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        vector_literal = "[" + ",".join(f"{value:.12g}" for value in query_embedding) + "]"
        statement = statement.order_by(
            text("knowledge_chunk_embeddings.embedding_vector <=> CAST(:query_vector AS vector)")
        ).limit(top_k)
        return list(db.execute(statement, {"query_vector": vector_literal}).all())
    return list(db.execute(statement).all())


def _candidate_limit(top_k: int) -> int:
    """Bound ranking work while allowing corrupt lineage to be discarded."""

    return min(_MAX_CANDIDATES, max(top_k, top_k * 4))


def _to_retrieved_chunk(
    row: tuple[KnowledgeSourceModel, KnowledgeDocumentModel, KnowledgeDocumentVersionModel, KnowledgeChunkModel, KnowledgeChunkEmbeddingModel],
    query_embedding: list[float],
) -> _RetrievedChunk | None:
    source, document, version, chunk, embedding = row
    if not _is_integrity_valid(version, chunk, embedding):
        # Corrupt lineage must never be surfaced as a citation. The data remains
        # available to lifecycle repair tooling but is excluded from retrieval.
        return None
    return _RetrievedChunk(
        source=source,
        document=document,
        version=version,
        chunk=chunk,
        embedding=embedding,
        score=_cosine_similarity(query_embedding, embedding.embedding_json),
    )


def _is_integrity_valid(
    version: KnowledgeDocumentVersionModel,
    chunk: KnowledgeChunkModel,
    embedding: KnowledgeChunkEmbeddingModel,
) -> bool:
    return bool(
        version.checksum
        and len(version.checksum) == 64
        and chunk.content_checksum == sha256(chunk.content.encode("utf-8")).hexdigest()
        and embedding.content_checksum == chunk.content_checksum
    )


def _citation_for(item: _RetrievedChunk) -> KnowledgeCitationResponse:
    citation_material = ":".join(
        [
            item.source.id,
            item.document.id,
            item.version.id,
            item.version.checksum or "",
            item.chunk.id,
            item.chunk.content_checksum,
        ]
    )
    return KnowledgeCitationResponse(
        citation_id=f"kcite_{sha256(citation_material.encode('utf-8')).hexdigest()[:20]}",
        source_id=item.source.id,
        source_title=item.source.title,
        document_id=item.document.id,
        document_version_id=item.version.id,
        document_version_checksum=item.version.checksum or "",
        chunk_id=item.chunk.id,
        chunk_checksum=item.chunk.content_checksum,
        heading_path=item.chunk.heading_path,
    )


def _excerpt(content: str) -> str:
    normalized = " ".join(content.split())
    if len(normalized) <= _MAX_EXCERPT_CHARACTERS:
        return normalized
    return normalized[: _MAX_EXCERPT_CHARACTERS - 3].rstrip() + "..."


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)
