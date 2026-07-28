from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.auth.schemas import UserContext
from app.knowledge.shadow_retriever import retrieve_durable_analysis_context
from app.knowledge.public_retriever import retrieve_public_durable_context
from app.rag.hybrid_retriever import HybridRetriever
from app.rag.retriever import RetrievalResult, Retriever
from app.rag.scope import RetrievalScope


def retrieve_protocol_context(
    strategy_description: str,
    protocols: list[str],
    top_k: int = 4,
    scope: RetrievalScope | None = None,
    db: Session | None = None,
    actor: UserContext | None = None,
) -> list[RetrievalResult]:
    protocol_filter = [protocol for protocol in protocols if protocol != "unknown"]
    settings = get_settings()
    # The old JSON index remains an automatic rollback/fallback when durable
    # retrieval has no eligible content or its database operation is unavailable.
    # Authenticated scope is derived from ``actor`` in the server process.
    if settings.knowledge_pgvector_primary_enabled and db is not None:
        try:
            if actor is None or actor.anonymous_session_id or (
                not actor.auth_enabled and not actor.is_admin
            ):
                durable_results = retrieve_public_durable_context(
                    db,
                    strategy_description,
                    protocols=protocol_filter,
                    top_k=top_k,
                )
            else:
                durable_results = retrieve_durable_analysis_context(
                    db,
                    actor,
                    query=strategy_description,
                    protocols=protocol_filter,
                    top_k=top_k,
                )
        except (SQLAlchemyError, ValueError):
            durable_results = []
        if durable_results:
            return durable_results
    if settings.rag_semantic_enabled:
        return HybridRetriever(semantic_enabled=True).retrieve(
            strategy_description,
            top_k=top_k,
            protocols=protocol_filter,
            scope=scope,
        )
    return Retriever().retrieve(
        strategy_description,
        top_k=top_k,
        protocols=protocol_filter,
        scope=scope,
    )
