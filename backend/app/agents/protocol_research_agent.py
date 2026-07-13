from app.core.config import get_settings
from app.rag.hybrid_retriever import HybridRetriever
from app.rag.retriever import RetrievalResult, Retriever


def retrieve_protocol_context(
    strategy_description: str,
    protocols: list[str],
    top_k: int = 4,
) -> list[RetrievalResult]:
    protocol_filter = [protocol for protocol in protocols if protocol != "unknown"]
    settings = get_settings()
    if settings.rag_semantic_enabled:
        return HybridRetriever(semantic_enabled=True).retrieve(
            strategy_description,
            top_k=top_k,
            protocols=protocol_filter,
        )
    return Retriever().retrieve(
        strategy_description,
        top_k=top_k,
        protocols=protocol_filter,
    )
