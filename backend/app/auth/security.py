import hashlib
import hmac
import re
from typing import Any

from app.core.config import get_settings


SECRET_PATTERNS = ("secret", "token", "key", "password", "credential")


def hash_token(token: str) -> str:
    settings = get_settings()
    salt = settings.auth_secret_key or "local-dev-auth"
    return hmac.new(salt.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()


def constant_time_equal(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)


def redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if _looks_sensitive(key) else redact_sensitive(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, str):
        return _redact_secret_like_string(value)
    return value


def _looks_sensitive(key: str) -> bool:
    lowered = key.lower()
    return any(pattern in lowered for pattern in SECRET_PATTERNS)


def _redact_secret_like_string(value: str) -> str:
    if len(value) < 16:
        return value
    if re.search(r"(sk-|api[_-]?key|token|secret)", value, flags=re.IGNORECASE):
        return "[REDACTED]"
    return value
