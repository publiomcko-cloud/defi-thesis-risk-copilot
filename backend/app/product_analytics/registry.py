from __future__ import annotations

import json
from dataclasses import dataclass


PURPOSE_PRODUCT_IMPROVEMENT = "product_improvement"
ANALYTICS_SCHEMA_VERSION = 1


class ProductAnalyticsValidationError(ValueError):
    pass


@dataclass(frozen=True)
class EventDefinition:
    dimensions: dict[str, frozenset[str]]


EVENT_DEFINITIONS: dict[str, EventDefinition] = {
    "analysis_completed": EventDefinition(
        dimensions={
            "actor_class": frozenset({"authenticated", "organization_context"}),
            "execution_mode": frozenset({"synchronous", "durable"}),
            "result_class": frozenset({"report_created", "fallback_created"}),
        }
    ),
    "analysis_failed": EventDefinition(
        dimensions={
            "actor_class": frozenset({"authenticated", "organization_context"}),
            "execution_mode": frozenset({"synchronous", "durable"}),
            "failure_class": frozenset({"validation", "quota", "dependency", "internal"}),
        }
    ),
    "thesis_saved": EventDefinition(
        dimensions={
            "actor_class": frozenset({"authenticated", "organization_context"}),
            "visibility_class": frozenset({"private", "organization"}),
        }
    ),
    "watchlist_created": EventDefinition(
        dimensions={
            "actor_class": frozenset({"authenticated", "organization_context"}),
            "visibility_class": frozenset({"private", "organization"}),
        }
    ),
}


def validate_event_metadata(event_name: str, metadata: dict) -> dict[str, str]:
    definition = EVENT_DEFINITIONS.get(event_name)
    if definition is None:
        raise ProductAnalyticsValidationError("Product analytics event is not approved")
    if not isinstance(metadata, dict) or set(metadata) != set(definition.dimensions):
        raise ProductAnalyticsValidationError("Product analytics metadata does not match the event schema")

    normalized: dict[str, str] = {}
    for field, allowed_values in definition.dimensions.items():
        value = metadata.get(field)
        if not isinstance(value, str) or value not in allowed_values:
            raise ProductAnalyticsValidationError("Product analytics metadata contains an undeclared value")
        normalized[field] = value
    if len(json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")) > 512:
        raise ProductAnalyticsValidationError("Product analytics metadata exceeds the approved bound")
    return normalized
