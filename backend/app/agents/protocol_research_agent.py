from app.rag.retriever import RetrievalResult, Retriever


def retrieve_protocol_context(
    strategy_description: str,
    protocols: list[str],
    top_k: int = 4,
) -> list[RetrievalResult]:
    protocol_filter = [protocol for protocol in protocols if protocol != "unknown"]
    return Retriever().retrieve(
        strategy_description,
        top_k=top_k,
        protocols=protocol_filter,
    )
