"""Public-only durable retrieval for the guarded Phase 18G cutover.

No caller-controlled tenant scope is accepted here.  Private and organization
knowledge remain on the authenticated shadow/tenant path until later gates.
"""

from __future__ import annotations

from dataclasses import replace

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.jobs.cancellation import CancellationContext
from app.knowledge.embedding import LocalDeterministicEmbeddingProvider
from app.knowledge.shadow_retriever import _citation_for, _to_retrieved_chunk
from app.models.knowledge import (
    KnowledgeChunkEmbeddingModel,
    KnowledgeChunkModel,
    KnowledgeDocumentModel,
    KnowledgeDocumentVersionModel,
    KnowledgeEmbeddingProfileModel,
    KnowledgeSourceModel,
)
from app.rag.retriever import RetrievalResult
from app.rag.embeddings import TOKEN_PATTERN


_MIN_RELEVANT_SIMILARITY = 0.1


def retrieve_public_durable_context(
    db: Session,
    query: str,
    *,
    protocols: list[str] | None = None,
    top_k: int = 4,
) -> list[RetrievalResult]:
    """Return only approved, current, integrity-valid public curated chunks."""

    normalized_query = query.strip()
    if not normalized_query:
        return []
    requested_top_k = max(1, min(top_k, 20))
    candidate_limit = min(80, max(requested_top_k, requested_top_k * 4))
    protocol_filter = sorted({item.strip().lower() for item in protocols or [] if item.strip()})
    query_embedding = LocalDeterministicEmbeddingProvider().embed(
        normalized_query, CancellationContext()
    )
    statement = (
        select(
            KnowledgeSourceModel,
            KnowledgeDocumentModel,
            KnowledgeDocumentVersionModel,
            KnowledgeChunkModel,
            KnowledgeChunkEmbeddingModel,
        )
        .join(KnowledgeDocumentModel, KnowledgeDocumentModel.knowledge_source_id == KnowledgeSourceModel.id)
        .join(KnowledgeDocumentVersionModel, KnowledgeDocumentVersionModel.document_id == KnowledgeDocumentModel.id)
        .join(KnowledgeChunkModel, KnowledgeChunkModel.document_version_id == KnowledgeDocumentVersionModel.id)
        .join(KnowledgeChunkEmbeddingModel, KnowledgeChunkEmbeddingModel.knowledge_chunk_id == KnowledgeChunkModel.id)
        .join(KnowledgeEmbeddingProfileModel, KnowledgeEmbeddingProfileModel.id == KnowledgeChunkEmbeddingModel.embedding_profile_id)
        .where(KnowledgeSourceModel.visibility == "public")
        .where(KnowledgeSourceModel.source_type == "curated_markdown")
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
        ).limit(candidate_limit)
        rows = db.execute(statement, {"query_vector": vector_literal}).all()
    else:
        rows = db.execute(statement).all()

    durable_results = [
        _with_query_heading_score(item, normalized_query)
        for row in rows
        if (item := _to_retrieved_chunk(row, query_embedding)) is not None
    ]
    durable_results = [item for item in durable_results if item.score >= _MIN_RELEVANT_SIMILARITY]
    # PostgreSQL narrows candidates with pgvector first. Re-sort that bounded
    # set after applying the explicit heading signal so SQLite and PostgreSQL
    # use the same final ranking contract.
    durable_results.sort(key=lambda item: item.score, reverse=True)
    durable_results = durable_results[:requested_top_k]
    return [
        RetrievalResult(
            chunk_id=item.chunk.id,
            text=item.chunk.content,
            metadata={
                **item.chunk.metadata_json,
                "protocol": item.source.protocol or "unknown",
                "source_url": item.source.canonical_uri or item.source.source_uri or "knowledge_base/README.md",
                "document_title": item.source.title,
                "section_title": item.chunk.heading_path[-1] if item.chunk.heading_path else item.source.title,
                "knowledge_scope": "public_curated",
                "citation_lineage": _citation_for(item).model_dump(),
            },
            similarity_score=item.score,
        )
        for item in durable_results
    ]


def _with_query_heading_score(item, query: str):
    """Use explicit section overlap as a small, inspectable ranking signal."""

    query_tokens = set(TOKEN_PATTERN.findall(query.lower()))
    heading_tokens = set(
        TOKEN_PATTERN.findall(" ".join(item.chunk.heading_path).lower())
    )
    return replace(item, score=item.score + 0.25 * len(query_tokens & heading_tokens))
