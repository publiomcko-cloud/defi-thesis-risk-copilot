from app.rag.retriever import RetrievalResult
from app.rag.source_urls import normalize_citation_url
from app.schemas.reports import CitationLineageReference, SourceReference


REQUIRED_CITATION_METADATA = ("document_title", "section_title", "protocol", "source_url")


def citation_label(result: RetrievalResult) -> str:
    metadata = result.metadata
    return (
        f"{metadata['document_title']} - {metadata['section_title']} "
        f"({metadata['protocol']})"
    )


def results_to_sources(results: list[RetrievalResult]) -> list[SourceReference]:
    sources: list[SourceReference] = []
    seen: set[tuple[str, str]] = set()

    for result in results:
        metadata = result.metadata
        url = normalize_citation_url(metadata.get("source_url"))
        if url is None:
            continue
        key = (metadata["document_title"], metadata["section_title"])
        if key in seen:
            continue
        seen.add(key)
        lineage = _citation_lineage(metadata)
        sources.append(
            SourceReference(
                title=citation_label(result),
                source_type="knowledge_base",
                url=url,
                protocol=metadata["protocol"],
                citation_lineage=lineage,
            )
        )

    return sources


def _citation_lineage(metadata: dict) -> CitationLineageReference | None:
    value = metadata.get("citation_lineage")
    if not isinstance(value, dict):
        return None
    try:
        return CitationLineageReference.model_validate(value)
    except ValueError:
        # Legacy JSON and malformed metadata retain their usable public source
        # reference but must never masquerade as exact durable lineage.
        return None


def validate_retrieval_citations(results: list[RetrievalResult]) -> list[str]:
    issues: list[str] = []
    seen_chunk_ids: set[str] = set()

    for result in results:
        if result.chunk_id in seen_chunk_ids:
            issues.append(f"duplicate chunk citation: {result.chunk_id}")
        seen_chunk_ids.add(result.chunk_id)

        for key in REQUIRED_CITATION_METADATA:
            if not result.metadata.get(key):
                issues.append(f"{result.chunk_id} missing citation metadata: {key}")

        if normalize_citation_url(result.metadata.get("source_url")) is None:
            issues.append(f"{result.chunk_id} has unrecognized source_url format")

    return issues
