from app.rag.retriever import RetrievalResult
from app.schemas.reports import SourceReference


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
        key = (metadata["document_title"], metadata["section_title"])
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            SourceReference(
                title=citation_label(result),
                source_type="knowledge_base",
                url=metadata["source_url"],
                protocol=metadata["protocol"],
            )
        )

    return sources


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

        source_url = str(result.metadata.get("source_url", ""))
        if source_url and not (
            source_url.startswith("http://")
            or source_url.startswith("https://")
            or source_url.endswith(".md")
        ):
            issues.append(f"{result.chunk_id} has unrecognized source_url format")

    return issues
