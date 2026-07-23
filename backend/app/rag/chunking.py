from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256

from app.rag.loaders import LoadedDocument


@dataclass(frozen=True)
class TextChunk:
    id: str
    text: str
    metadata: dict


def chunk_markdown_document(document: LoadedDocument) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    current_section = document.title
    current_lines: list[str] = []

    for line in document.content.splitlines():
        if line.startswith("## "):
            _append_chunk(document, current_section, current_lines, chunks)
            current_section = line[3:].strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    _append_chunk(document, current_section, current_lines, chunks)
    return chunks


def _append_chunk(
    document: LoadedDocument,
    section_title: str,
    lines: list[str],
    chunks: list[TextChunk],
) -> None:
    text = "\n".join(lines).strip()
    if not text:
        return
    if text == f"# {document.title}":
        return

    digest = sha256(
        f"{document.source_url}:{section_title}:{text}".encode("utf-8")
    ).hexdigest()
    chunks.append(
        TextChunk(
            id=digest[:24],
            text=text,
            metadata={
                "protocol": document.protocol,
                "source_url": document.source_url,
                "document_title": document.title,
                "knowledge_scope": "public_curated",
                "organization_id": None,
                "storage_status": "indexed_global",
                "section_title": section_title,
                "ingestion_date": datetime.now(UTC).date().isoformat(),
                "content_type": "markdown",
                "risk_category": _infer_risk_category(text),
            },
        )
    )


def _infer_risk_category(text: str) -> str:
    lowered = text.lower()
    for category in (
        "liquidation",
        "oracle",
        "liquidity",
        "maturity",
        "borrow",
        "composability",
    ):
        if category in lowered:
            return category
    return "protocol"
