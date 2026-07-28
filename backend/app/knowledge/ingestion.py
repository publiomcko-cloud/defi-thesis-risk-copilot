from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from html.parser import HTMLParser
from io import BytesIO
import re
import unicodedata

from fastapi import HTTPException

from app.core.config import get_settings
from app.jobs.cancellation import CancellationContext
from app.jobs.errors import JobErrorCategory, JobExecutionError


PARSER_VERSION = "phase18c.parser.v1"
CHUNKER_VERSION = "phase18c.chunker.v1"
EMBEDDING_MODEL = "not_configured.phase18c"


@dataclass(frozen=True)
class ExtractedChunk:
    index: int
    heading_path: list[str]
    content: str
    content_checksum: str
    token_count: int


def extract_normalize_and_chunk(
    *,
    content: bytes,
    media_type: str,
    cancellation: CancellationContext,
) -> list[ExtractedChunk]:
    cancellation.raise_if_cancelled()
    text = _extract_text(content, media_type, cancellation)
    normalized = _normalize_text(text)
    if not normalized:
        raise JobExecutionError(
            JobErrorCategory.PERMANENT_INPUT,
            "empty_document",
            "The document did not contain extractable text.",
        )
    encoded = normalized.encode("utf-8")
    if len(encoded) > get_settings().knowledge_ingest_max_text_bytes:
        raise JobExecutionError(
            JobErrorCategory.PERMANENT_INPUT,
            "extracted_text_too_large",
            "The extracted document text exceeds the configured limit.",
        )
    return _chunk_text(normalized, cancellation)


def _extract_text(content: bytes, media_type: str, cancellation: CancellationContext) -> str:
    if media_type in {"text/plain", "text/markdown"}:
        try:
            return content.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise JobExecutionError(
                JobErrorCategory.PERMANENT_INPUT,
                "invalid_utf8_document",
                "The text document is not valid UTF-8.",
            ) from exc
    if media_type == "text/html":
        try:
            parser = _VisibleHtmlTextParser()
            parser.feed(content.decode("utf-8", errors="strict"))
            parser.close()
            return "\n".join(parser.parts)
        except UnicodeDecodeError as exc:
            raise JobExecutionError(
                JobErrorCategory.PERMANENT_INPUT,
                "invalid_utf8_document",
                "The HTML document is not valid UTF-8.",
            ) from exc
    if media_type == "application/pdf":
        return _extract_pdf(content, cancellation)
    raise JobExecutionError(
        JobErrorCategory.PERMANENT_INPUT,
        "unsupported_media_type",
        "The document media type is not supported for ingestion.",
    )


def _extract_pdf(content: bytes, cancellation: CancellationContext) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(content), strict=True)
        if reader.is_encrypted:
            raise JobExecutionError(
                JobErrorCategory.PERMANENT_INPUT,
                "encrypted_pdf",
                "Encrypted PDF files cannot be ingested.",
            )
        if len(reader.pages) > get_settings().knowledge_ingest_max_pdf_pages:
            raise JobExecutionError(
                JobErrorCategory.PERMANENT_INPUT,
                "pdf_page_limit_exceeded",
                "The PDF exceeds the configured page limit.",
            )
        pages: list[str] = []
        for page in reader.pages:
            cancellation.raise_if_cancelled()
            pages.append(page.extract_text() or "")
        return "\n".join(pages)
    except JobExecutionError:
        raise
    except Exception as exc:
        raise JobExecutionError(
            JobErrorCategory.PERMANENT_INPUT,
            "unreadable_pdf",
            "The PDF could not be read safely.",
        ) from exc


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).replace("\r\n", "\n").replace("\r", "\n")
    normalized = "".join(character for character in normalized if character == "\n" or character == "\t" or ord(character) >= 32)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def _chunk_text(text: str, cancellation: CancellationContext) -> list[ExtractedChunk]:
    max_characters = get_settings().knowledge_chunk_max_characters
    chunks: list[ExtractedChunk] = []
    heading_path: list[str] = []
    buffer: list[str] = []

    def append_buffer() -> None:
        cancellation.raise_if_cancelled()
        value = "\n".join(buffer).strip()
        if not value:
            return
        for segment in _split_bounded(value, max_characters):
            chunks.append(
                ExtractedChunk(
                    index=len(chunks),
                    heading_path=list(heading_path),
                    content=segment,
                    content_checksum=sha256(segment.encode("utf-8")).hexdigest(),
                    token_count=len(re.findall(r"\S+", segment)),
                )
            )

    for line in text.splitlines():
        if line.startswith("#") and line.lstrip("#").startswith(" "):
            append_buffer()
            buffer.clear()
            level = len(line) - len(line.lstrip("#"))
            heading = line[level:].strip()
            if heading:
                heading_path[:] = heading_path[: max(0, level - 1)] + [heading]
            continue
        buffer.append(line)
    append_buffer()
    if not chunks:
        raise JobExecutionError(
            JobErrorCategory.PERMANENT_INPUT,
            "empty_document",
            "The document did not contain extractable text.",
        )
    return chunks


def _split_bounded(value: str, maximum: int) -> list[str]:
    parts: list[str] = []
    remaining = value
    while remaining:
        if len(remaining) <= maximum:
            parts.append(remaining)
            break
        breakpoint = remaining.rfind("\n\n", 0, maximum)
        if breakpoint < maximum // 2:
            breakpoint = remaining.rfind(" ", 0, maximum)
        if breakpoint < maximum // 2:
            breakpoint = maximum
        parts.append(remaining[:breakpoint].strip())
        remaining = remaining[breakpoint:].lstrip()
    return [part for part in parts if part]


class _VisibleHtmlTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() in {"script", "style", "noscript", "template"}:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "template"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth and data.strip():
            self.parts.append(data)
