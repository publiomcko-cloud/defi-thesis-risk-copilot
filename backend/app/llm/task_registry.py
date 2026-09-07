"""Closed, code-owned taxonomy for model-assisted work.

Registering a task is intentionally different from implementing or enabling it.
Only ``report_synthesis`` is an implemented runtime task in checkpoint 21A.
"""

from dataclasses import dataclass


class ModelTaskRegistryError(ValueError):
    """Raised when a caller asks for a task outside the approved taxonomy."""


@dataclass(frozen=True)
class ModelTaskDefinition:
    key: str
    version: str
    output_schema_class: str
    may_include_retrieved_or_private_content: bool
    deterministic_validation_policy: str
    fallback_policy: str
    runtime_implemented: bool = False


_TASKS = (
    ModelTaskDefinition(
        key="report_synthesis",
        version="v1",
        output_schema_class="report_synthesis.output.v1",
        may_include_retrieved_or_private_content=True,
        deterministic_validation_policy="strict_json_and_restore_deterministic_report_fields.v1",
        fallback_policy="deterministic_report.v1",
        runtime_implemented=True,
    ),
    ModelTaskDefinition(
        key="strategy_parsing",
        version="v1",
        output_schema_class="strategy_parsing.output.v1",
        may_include_retrieved_or_private_content=False,
        deterministic_validation_policy="not_implemented.v1",
        fallback_policy="disabled.v1",
    ),
    ModelTaskDefinition(
        key="source_classification",
        version="v1",
        output_schema_class="source_classification.output.v1",
        may_include_retrieved_or_private_content=True,
        deterministic_validation_policy="not_implemented.v1",
        fallback_policy="disabled.v1",
    ),
    ModelTaskDefinition(
        key="retrieval_reranking",
        version="v1",
        output_schema_class="retrieval_reranking.output.v1",
        may_include_retrieved_or_private_content=True,
        deterministic_validation_policy="not_implemented.v1",
        fallback_policy="disabled.v1",
    ),
    ModelTaskDefinition(
        key="entity_extraction",
        version="v1",
        output_schema_class="entity_extraction.output.v1",
        may_include_retrieved_or_private_content=True,
        deterministic_validation_policy="not_implemented.v1",
        fallback_policy="disabled.v1",
    ),
    ModelTaskDefinition(
        key="scenario_explanation",
        version="v1",
        output_schema_class="scenario_explanation.output.v1",
        may_include_retrieved_or_private_content=True,
        deterministic_validation_policy="not_implemented.v1",
        fallback_policy="disabled.v1",
    ),
    ModelTaskDefinition(
        key="research_summarization",
        version="v1",
        output_schema_class="research_summarization.output.v1",
        may_include_retrieved_or_private_content=True,
        deterministic_validation_policy="not_implemented.v1",
        fallback_policy="disabled.v1",
    ),
)

TASK_DEFINITIONS = {definition.key: definition for definition in _TASKS}
TASK_KEYS = frozenset(TASK_DEFINITIONS)


def get_model_task_definition(task_key: str) -> ModelTaskDefinition:
    """Return a task definition or fail closed for unknown browser/server input."""

    definition = TASK_DEFINITIONS.get(task_key)
    if definition is None:
        raise ModelTaskRegistryError("Unknown model task")
    return definition
