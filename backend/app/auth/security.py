import hashlib
import hmac
import re
from typing import Any

from app.core.config import get_settings


SECRET_PATTERNS = (
    "secret",
    "token",
    "key",
    "password",
    "credential",
    "cookie",
    "authorization",
    "email",
    "request_body",
    "raw_body",
    "verification_code",
)
MAX_AUDIT_METADATA_KEYS = 20
MAX_AUDIT_METADATA_ITEMS = 20
MAX_AUDIT_METADATA_DEPTH = 4
MAX_AUDIT_STRING_LENGTH = 256


def hash_token(token: str) -> str:
    settings = get_settings()
    salt = settings.auth_secret_key or "local-dev-auth"
    return hmac.new(salt.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()


def hash_worker_token(token: str) -> str:
    """Hash worker-only credentials in a domain separate from user tokens."""
    settings = get_settings()
    pepper = settings.worker_token_pepper or settings.auth_secret_key or "local-dev-worker"
    return hmac.new(
        pepper.encode("utf-8"),
        f"worker:{token}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def hash_job_lease_token(token: str) -> str:
    """Hash an ephemeral lease secret in a domain distinct from worker credentials."""
    settings = get_settings()
    pepper = settings.worker_token_pepper or settings.auth_secret_key or "local-dev-worker"
    return hmac.new(
        pepper.encode("utf-8"),
        f"job-lease:{token}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


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


def sanitize_audit_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Redact and bound event metadata before it reaches durable audit storage."""
    return _sanitize_value(redact_sensitive(metadata), depth=0)


def _looks_sensitive(key: str) -> bool:
    lowered = key.lower()
    return any(pattern in lowered for pattern in SECRET_PATTERNS)


def _redact_secret_like_string(value: str) -> str:
    if re.search(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", value):
        return "[REDACTED]"
    if len(value) < 16:
        return value
    if re.search(r"(sk-|api[_-]?key|token|secret)", value, flags=re.IGNORECASE):
        return "[REDACTED]"
    return value


def _sanitize_value(value: Any, *, depth: int) -> Any:
    if depth >= MAX_AUDIT_METADATA_DEPTH:
        return "[TRUNCATED]"
    if isinstance(value, dict):
        items = list(value.items())[:MAX_AUDIT_METADATA_KEYS]
        sanitized = {
            str(key)[:64]: _sanitize_value(item, depth=depth + 1)
            for key, item in items
        }
        if len(value) > MAX_AUDIT_METADATA_KEYS:
            sanitized["_truncated"] = True
        return sanitized
    if isinstance(value, list):
        sanitized_items = [
            _sanitize_value(item, depth=depth + 1)
            for item in value[:MAX_AUDIT_METADATA_ITEMS]
        ]
        if len(value) > MAX_AUDIT_METADATA_ITEMS:
            sanitized_items.append("[TRUNCATED]")
        return sanitized_items
    if isinstance(value, str):
        return value[:MAX_AUDIT_STRING_LENGTH]
    if isinstance(value, (bool, float, int)) or value is None:
        return value
    return "[UNSUPPORTED]"
