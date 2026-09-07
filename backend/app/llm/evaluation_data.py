"""Checked-in, public/synthetic model-evaluation dataset metadata only."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from importlib.resources import files


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    category: str
    retrieval_fixture: str
    expected_result: str
    expected_failure_class: str | None


@dataclass(frozen=True)
class EvaluationDatasetDefinition:
    dataset_id: str
    task_key: str
    task_version: str
    dataset_version: str
    purpose: str
    checksum: str
    cases: tuple[EvaluationCase, ...]


def report_synthesis_public_dataset() -> EvaluationDatasetDefinition:
    """Load the immutable checked-in corpus without putting its contents in SQL."""

    raw = files("app.llm").joinpath("evaluation_data/report_synthesis_public_v2.json").read_text()
    payload = json.loads(raw)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    cases = tuple(
        EvaluationCase(
            case_id=_bounded_case_text(case, "id"),
            category=_bounded_case_text(case, "category"),
            retrieval_fixture=_bounded_case_text(case, "retrieval_fixture"),
            expected_result=_bounded_case_text(case, "expected_result"),
            expected_failure_class=_optional_bounded_case_text(case, "expected_failure_class"),
        )
        for case in payload["cases"]
    )
    if not 1 <= len(cases) <= 1_000 or len({case.case_id for case in cases}) != len(cases):
        raise ValueError("Evaluation dataset cases are invalid")
    return EvaluationDatasetDefinition(
        dataset_id=_bounded_text(payload, "dataset_id", 64),
        task_key=_bounded_text(payload, "task_key", 64),
        task_version=_bounded_text(payload, "task_version", 32),
        dataset_version=_bounded_text(payload, "dataset_version", 64),
        purpose=_bounded_text(payload, "purpose", 128),
        checksum=sha256(canonical.encode()).hexdigest(),
        cases=cases,
    )


def case_checksum(case: EvaluationCase) -> str:
    return sha256(
        json.dumps(
            {
                "id": case.case_id,
                "category": case.category,
                "retrieval_fixture": case.retrieval_fixture,
                "expected_result": case.expected_result,
                "expected_failure_class": case.expected_failure_class,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def _bounded_text(payload: dict, key: str, maximum: int) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not 1 <= len(value) <= maximum:
        raise ValueError("Evaluation dataset metadata is invalid")
    return value


def _bounded_case_text(case: object, key: str) -> str:
    if not isinstance(case, dict):
        raise ValueError("Evaluation dataset case is invalid")
    return _bounded_text(case, key, 64)


def _optional_bounded_case_text(case: object, key: str) -> str | None:
    if not isinstance(case, dict):
        raise ValueError("Evaluation dataset case is invalid")
    value = case.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not 1 <= len(value) <= 64:
        raise ValueError("Evaluation dataset case is invalid")
    return value
