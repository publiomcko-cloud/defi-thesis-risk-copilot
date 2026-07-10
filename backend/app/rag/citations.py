from app.rag.retriever import RetrievalResult
from app.schemas.reports import SourceReference


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
