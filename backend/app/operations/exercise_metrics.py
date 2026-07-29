"""Safe aggregate metrics for isolated Phase 19 exercises.

The file is intentionally opt-in and is only consumed by the fixed exercise
runner.  It never records URLs, payloads, identities, response bodies, or
exception text.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Mapping


METRICS_ENVIRONMENT_VARIABLE = "PHASE19_EXERCISE_METRICS_FILE"
_MAX_METRICS_BYTES = 8_192
_SAFE_VALUE_TYPES = (bool, int, float, str)


def record_exercise_metrics(metrics: Mapping[str, object]) -> None:
    """Atomically write bounded aggregate metrics when the runner opted in."""
    destination = os.getenv(METRICS_ENVIRONMENT_VARIABLE)
    if not destination:
        return
    safe_metrics = validate_exercise_metrics(metrics)
    path = Path(destination)
    encoded = json.dumps(safe_metrics, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(encoded) > _MAX_METRICS_BYTES:
        raise ValueError("Phase 19 exercise metrics exceed the safe evidence limit")
    temporary_path = path.with_suffix(".tmp")
    temporary_path.write_bytes(encoded)
    temporary_path.replace(path)


def load_exercise_metrics(path: Path) -> dict[str, bool | int | float | str]:
    """Read only the bounded, aggregate metric format emitted by fixed tests."""
    if not path.exists():
        return {}
    raw = path.read_bytes()
    if len(raw) > _MAX_METRICS_BYTES:
        raise ValueError("Phase 19 exercise metrics exceed the safe evidence limit")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("Phase 19 exercise metrics are invalid") from exc
    if not isinstance(value, dict):
        raise ValueError("Phase 19 exercise metrics must be an object")
    return validate_exercise_metrics(value)


def validate_exercise_metrics(metrics: Mapping[str, object]) -> dict[str, bool | int | float | str]:
    """Limit evidence to short aggregate keys and primitive, non-sensitive values."""
    if len(metrics) > 32:
        raise ValueError("Phase 19 exercise metrics contain too many fields")
    validated: dict[str, bool | int | float | str] = {}
    for key, value in metrics.items():
        if not isinstance(key, str) or not key.replace("_", "").isalnum() or len(key) > 64:
            raise ValueError("Phase 19 exercise metric key is invalid")
        if not isinstance(value, _SAFE_VALUE_TYPES) or isinstance(value, str) and len(value) > 64:
            raise ValueError("Phase 19 exercise metric value is invalid")
        if isinstance(value, float) and (value != value or value in {float("inf"), float("-inf")}):
            raise ValueError("Phase 19 exercise metric value is invalid")
        validated[key] = value
    return validated
