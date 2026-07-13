from dataclasses import dataclass
from typing import Any

from app.core.config import get_settings
from app.rag.embeddings import LocalHashEmbeddingProvider, TOKEN_PATTERN, cosine_similarity
from app.rag.reranker import freshness_score, rerank_results, source_quality_score
from app.rag.retriever import RetrievalResult
from app.rag.semantic_embeddings import get_semantic_embedding_provider
from app.rag.vector_store import JsonVectorStore


@dataclass(frozen=True)
class HybridRetrievalWeights:
    keyword: float = 0.45
    vector: float = 0.45
    metadata: float = 0.10


class HybridRetriever:
    def __init__(
        self,
        store: JsonVectorStore | None = None,
        semantic_enabled: bool | None = None,
        weights: HybridRetrievalWeights | None = None,
    ) -> None:
        settings = get_settings()
        self.store = store or JsonVectorStore()
        self.keyword_provider = LocalHashEmbeddingProvider()
        self.semantic_enabled = (
            settings.rag_semantic_enabled if semantic_enabled is None else semantic_enabled
        )
        self.semantic_provider = get_semantic_embedding_provider(settings.rag_embedding_provider)
        self.weights = weights or HybridRetrievalWeights(
            keyword=settings.rag_hybrid_keyword_weight,
            vector=settings.rag_hybrid_vector_weight,
            metadata=settings.rag_hybrid_metadata_weight,
        )

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        protocols: list[str] | None = None,
        metadata_filters: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        keyword_query = self.keyword_provider.embed(query)
        semantic_query = self.semantic_provider.embed(query) if self.semantic_enabled else {}
        protocol_filter = {protocol.lower() for protocol in protocols or []}
        filters = metadata_filters or {}
        results: list[RetrievalResult] = []

        for record in self.store.load():
            metadata = record["metadata"]
            if protocol_filter and str(metadata.get("protocol", "")).lower() not in protocol_filter:
                continue
            if not _matches_filters(metadata, filters):
                continue

            keyword_score = cosine_similarity(keyword_query, record["embedding"])
            vector_score = keyword_score
            if self.semantic_enabled:
                semantic_embedding = record.get("semantic_embedding")
                if semantic_embedding is None:
                    semantic_embedding = self.semantic_provider.embed(record["text"])
                vector_score = cosine_similarity(semantic_query, semantic_embedding)

            metadata_score = _metadata_retrieval_score(query, metadata)
            score = (
                keyword_score * self.weights.keyword
                + vector_score * self.weights.vector
                + metadata_score * self.weights.metadata
            )
            if score <= 0:
                continue
            enriched_metadata = {
                **metadata,
                "retrieval_scores": {
                    "keyword": round(keyword_score, 6),
                    "vector": round(vector_score, 6),
                    "metadata": round(metadata_score, 6),
                    "source_quality": round(source_quality_score(metadata), 6),
                    "freshness": round(freshness_score(metadata), 6),
                },
            }
            results.append(
                RetrievalResult(
                    chunk_id=record["id"],
                    text=record["text"],
                    metadata=enriched_metadata,
                    similarity_score=score,
                )
            )

        return rerank_results(query, results)[:top_k]


def _matches_filters(metadata: dict, filters: dict[str, Any]) -> bool:
    for key, expected in filters.items():
        if expected is None:
            continue
        actual = metadata.get(key)
        if isinstance(expected, (list, tuple, set)):
            allowed = {str(item).lower() for item in expected}
            if str(actual).lower() not in allowed:
                return False
        elif str(actual).lower() != str(expected).lower():
            return False
    return True


def _metadata_retrieval_score(query: str, metadata: dict) -> float:
    query_tokens = set(TOKEN_PATTERN.findall(query.lower()))
    section_tokens = set(TOKEN_PATTERN.findall(str(metadata.get("section_title", "")).lower()))
    risk_category = str(metadata.get("risk_category", "")).lower()
    score = 0.0
    score += min(len(query_tokens & section_tokens) * 0.2, 0.8)
    if risk_category and risk_category in query_tokens:
        score += 0.4
    score += source_quality_score(metadata) * 0.35
    score += freshness_score(metadata) * 0.25
    return score
