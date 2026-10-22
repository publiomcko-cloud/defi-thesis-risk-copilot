"""Canonicalize the small set of citation destinations rendered by reports."""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlsplit, urlunsplit


_INTERNAL_MARKDOWN = re.compile(r"^(?:docs|knowledge_base)/[A-Za-z0-9._/-]+\.md$")


def normalize_citation_url(value: object) -> str | None:
    """Return an approved public HTTPS or repository Markdown reference.

    This is a display policy, not a fetch policy. Callers that fetch URLs must
    also resolve and reject private IP destinations at connection time.
    """

    if not isinstance(value, str) or not value or len(value) > 2_048:
        return None
    if value != value.strip() or any(ord(char) < 32 or ord(char) == 127 for char in value):
        return None
    if "\\" in value:
        return None
    if _INTERNAL_MARKDOWN.fullmatch(value):
        if any(part in {"", ".", ".."} for part in value.split("/")):
            return None
        return value
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() != "https" or not parsed.hostname:
            return None
        if parsed.username is not None or parsed.password is not None:
            return None
        if parsed.fragment and any(ord(char) < 32 for char in parsed.fragment):
            return None
        host = parsed.hostname.rstrip(".").lower()
        if not host or host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
            return None
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address is not None and not address.is_global:
            return None
        port = parsed.port
        if port is not None and not 1 <= port <= 65_535:
            return None
        normalized_host = f"[{host}]" if address is not None and address.version == 6 else host
        netloc = normalized_host if port in (None, 443) else f"{normalized_host}:{port}"
        return urlunsplit(("https", netloc, parsed.path or "/", parsed.query, parsed.fragment))
    except (ValueError, UnicodeError):
        return None


def curated_source_reference(value: object) -> str | None:
    """Canonicalize repository-relative paths from the sealed public corpus.

    Curated corpus records store their path relative to ``knowledge_base``.
    Prefix only those otherwise-unrecognized relative paths, then run the same
    strict display validator used by every report surface.
    """

    normalized = normalize_citation_url(value)
    if normalized is not None:
        return normalized
    if not isinstance(value, str) or not value or value.startswith(("/", "\\")):
        return None
    return normalize_citation_url(f"knowledge_base/{value}")
