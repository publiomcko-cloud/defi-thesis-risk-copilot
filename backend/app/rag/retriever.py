from dataclasses import dataclass

from app.rag.embeddings import LocalHashEmbeddingProvider, TOKEN_PATTERN, cosine_similarity
from app.rag.vector_store import JsonVectorStore
from app.rag.scope import RetrievalScope


@dataclass(frozen=True)
class RetrievalResult:
    chunk_id: str
    text: str
    metadata: dict
    similarity_score: float


class Retriever:
    def __init__(self, store: JsonVectorStore | None = None) -> None:
        self.store = store or JsonVectorStore()
        self.embedding_provider = LocalHashEmbeddingProvider()

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        protocols: list[str] | None = None,
        scope: RetrievalScope | None = None,
    ) -> list[RetrievalResult]:
        query_embedding = self.embedding_provider.embed(query)
        protocol_filter = {protocol.lower() for protocol in protocols or []}
        results: list[RetrievalResult] = []
        retrieval_scope = scope or RetrievalScope()

        for record in self.store.load():
            metadata = record["metadata"]
            if not retrieval_scope.allows(metadata):
                continue
            if protocol_filter and metadata["protocol"].lower() not in protocol_filter:
                continue
            score = cosine_similarity(query_embedding, record["embedding"])
            score += _section_title_boost(query, metadata["section_title"])
            if score <= 0:
                continue
            results.append(
                RetrievalResult(
                    chunk_id=record["id"],
                    text=record["text"],
                    metadata=metadata,
                    similarity_score=score,
                )
            )

        return sorted(
            results,
            key=lambda result: result.similarity_score,
            reverse=True,
        )[:top_k]


def _section_title_boost(query: str, section_title: str) -> float:
    query_tokens = set(TOKEN_PATTERN.findall(query.lower()))
    section_tokens = set(TOKEN_PATTERN.findall(section_title.lower()))
    if not query_tokens or not section_tokens:
        return 0.0
    overlap = query_tokens & section_tokens
    return 0.25 * len(overlap)
