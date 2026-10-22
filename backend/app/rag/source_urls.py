"""Canonicalize the shared, display-only citation URL policy."""

from __future__ import annotations

import re
from urllib.parse import unquote, urlsplit


_INTERNAL_MARKDOWN = re.compile(r"^(?:docs|knowledge_base)/[A-Za-z0-9._/-]+\.md$")
_SCHEME = re.compile(r"^https://", re.IGNORECASE)
_HOST_LABEL = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")
_NUMERIC_TLD = re.compile(r"^(?:[0-9]+|0[xX][0-9A-Fa-f]*)$")
_PATH_CHARS = re.compile(r"^[A-Za-z0-9\-._~!$&'()*+,;=:@/%]*$")
_QUERY_FRAGMENT_CHARS = re.compile(r"^[A-Za-z0-9\-._~!$&'()*+,;=:@/?%]*$")
_PERCENT_ESCAPE = re.compile(r"%[0-9A-Fa-f]{2}")


def normalize_citation_url(value: object) -> str | None:
    """Return one canonical public-HTTPS or approved Markdown display target.

    Hosts must be ASCII DNS names. IP literals, IDNs (including punycode),
    credentials, trailing dots, malformed ports, and ambiguous path encoding
    are rejected so Python and WHATWG URL parsing have the same accepted set.
    This policy does not authorize network fetching.
    """

    if not isinstance(value, str) or not value or len(value) > 2_048:
        return None
    if value != value.strip() or any(ord(char) < 33 or ord(char) > 126 for char in value):
        return None
    if "\\" in value:
        return None
    before_fragment, has_fragment, fragment_value = value.partition("#")
    if has_fragment and not fragment_value:
        return None
    before_fragment_query, has_query, query_value = before_fragment.partition("?")
    if has_query and not query_value:
        return None
    if _INTERNAL_MARKDOWN.fullmatch(value):
        if any(part in {"", ".", ".."} for part in value.split("/")):
            return None
        return value
    if not _SCHEME.match(value):
        return None

    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() != "https" or not parsed.netloc:
            return None
        authority = parsed.netloc
        if "@" in authority or "%" in authority or "[" in authority or "]" in authority:
            return None
        if authority.count(":") > 1:
            return None
        if ":" in authority:
            host, port_text = authority.rsplit(":", 1)
            if not port_text or not port_text.isascii() or not port_text.isdigit():
                return None
            port = int(port_text)
            if not 1 <= port <= 65_535:
                return None
        else:
            host, port = authority, None

        host = host.lower()
        if not host or host.endswith(".") or len(host) > 253:
            return None
        labels = host.split(".")
        if len(labels) < 2 or not labels[-1].isalpha():
            return None
        if any(
            not _HOST_LABEL.fullmatch(label)
            or label.lower().startswith("xn--")
            for label in labels
        ):
            return None
        if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
            return None
        # WHATWG URL parsing treats these suffix forms as IPv4 candidates,
        # including decimal, octal, hexadecimal, and shortened spellings.
        if _NUMERIC_TLD.fullmatch(labels[-1]):
            return None

        path = parsed.path or "/"
        query = parsed.query
        fragment = parsed.fragment
        if not _PATH_CHARS.fullmatch(path):
            return None
        if not _QUERY_FRAGMENT_CHARS.fullmatch(query) or not _QUERY_FRAGMENT_CHARS.fullmatch(fragment):
            return None
        components = (path, query, fragment)
        if any(not _valid_percent_escapes(component) for component in components):
            return None
        if _has_ambiguous_path_segments(path):
            return None

        port_suffix = f":{port}" if port not in (None, 443) else ""
        query_suffix = f"?{query}" if query else ""
        fragment_suffix = f"#{fragment}" if fragment else ""
        return f"https://{host}{port_suffix}{path}{query_suffix}{fragment_suffix}"
    except (ValueError, UnicodeError):
        return None


def _valid_percent_escapes(value: str) -> bool:
    index = 0
    while index < len(value):
        if value[index] != "%":
            index += 1
            continue
        match = _PERCENT_ESCAPE.match(value, index)
        if match is None:
            return False
        byte = int(match.group()[1:], 16)
        if byte < 0x20 or byte == 0x7F:
            return False
        index = match.end()
    return True


def _has_ambiguous_path_segments(path: str) -> bool:
    for segment in path.split("/"):
        try:
            decoded = unquote(segment, errors="strict")
        except UnicodeError:
            return True
        if decoded in {".", ".."} or "/" in decoded or "\\" in decoded or "%" in decoded:
            return True
    return False


def curated_source_reference(value: object) -> str | None:
    """Canonicalize repository-relative paths from the sealed public corpus."""

    normalized = normalize_citation_url(value)
    if normalized is not None:
        return normalized
    if not isinstance(value, str) or not value or value.startswith(("/", "\\")):
        return None
    return normalize_citation_url(f"knowledge_base/{value}")
