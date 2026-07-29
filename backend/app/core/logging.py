import json
import logging
from datetime import UTC, datetime
from typing import Any

from app.core.observability import current_log_context, redact_value


class SafeJsonFormatter(logging.Formatter):
    """Emit structured operational logs without exception payloads or secrets."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_value(record.getMessage()),
        }
        payload.update(current_log_context())
        for key in ("event", "correlation_id", "request_id", "operation", "job_id", "method", "path", "status_code", "duration_ms", "exception_type"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = redact_value(value, field_name=key)
        fields = getattr(record, "observability", None)
        if isinstance(fields, dict):
            payload["fields"] = redact_value(fields)
        # Do not serialize a traceback: exception messages can contain request or
        # provider data. The safe exception class is enough for 19A diagnostics.
        if record.exc_info and "exception_type" not in payload:
            payload["exception_type"] = record.exc_info[0].__name__
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def configure_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    root.setLevel(level)
    if not root.handlers:
        handler = logging.StreamHandler()
        root.addHandler(handler)
    for handler in root.handlers:
        handler.setFormatter(SafeJsonFormatter())
