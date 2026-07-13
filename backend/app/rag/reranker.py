from dataclasses import replace
from datetime import UTC, date, datetime

from app.rag.embeddings import TOKEN_PATTERN
from app.rag.retriever import RetrievalResult


QUALITY_SCORE_BY_TYPE = {
    "markdown": 0.75,
    "protocol_docs": 0.9,
    "risk_note": 0.8,
    "governance": 0.65,
}


def rerank_results(query: str, results: list[RetrievalResult]) -> list[RetrievalResult]:
    query_tokens = set(TOKEN_PATTERN.findall(query.lower()))
    reranked = [
        replace(
            result,
            similarity_score=result.similarity_score + _metadata_score(query_tokens, result.metadata),
        )
        for result in results
    ]
    return sorted(reranked, key=lambda result: result.similarity_score, reverse=True)


def source_quality_score(metadata: dict) -> float:
    explicit = metadata.get("source_quality_score")
    if isinstance(explicit, (int, float)):
        return max(min(float(explicit), 1.0), 0.0)
    content_type = str(metadata.get("content_type", "markdown"))
    return QUALITY_SCORE_BY_TYPE.get(content_type, 0.6)


def freshness_score(metadata: dict, today: date | None = None) -> float:
    ingestion_date = metadata.get("ingestion_date")
    if not ingestion_date:
        return 0.5
    try:
        parsed = date.fromisoformat(str(ingestion_date))
    except ValueError:
        return 0.4

    days_old = ((today or datetime.now(UTC).date()) - parsed).days
    if days_old <= 30:
        return 1.0
    if days_old <= 180:
        return 0.8
    if days_old <= 365:
        return 0.6
    return 0.35


def _metadata_score(query_tokens: set[str], metadata: dict) -> float:
    section_title = str(metadata.get("section_title", "")).lower()
    risk_category = str(metadata.get("risk_category", "")).lower()
    title_tokens = set(TOKEN_PATTERN.findall(section_title))
    title_overlap = len(query_tokens & title_tokens) * 0.08
    category_boost = 0.12 if risk_category and risk_category in query_tokens else 0.0
    quality_boost = source_quality_score(metadata) * 0.06
    freshness_boost = freshness_score(metadata) * 0.04
    return title_overlap + category_boost + quality_boost + freshness_boost
