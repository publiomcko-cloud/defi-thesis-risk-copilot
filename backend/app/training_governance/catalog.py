from __future__ import annotations

import hashlib
import json
from importlib.resources import files
from pathlib import Path
from typing import Final

from fastapi import HTTPException


DATASET_KEY: Final = "report_synthesis_training_synthetic_v1"
DATASET_SCHEMA_VERSION: Final = "training.dataset.v1"
SPLIT_POLICY_VERSION: Final = "training.split.sha256.v1"
ELIGIBILITY_POLICY_VERSION: Final = "training.eligibility.v1"
RECIPE_KEY: Final = "report_synthesis_local_fake"
RECIPE_VERSION: Final = "v1"
COMPUTE_PROFILE_ID: Final = "local_fake_v1"
COMPUTE_PROFILE_VERSION: Final = "v1"
EXPECTED_ARTIFACT_TYPES: Final = ("training_model_card", "training_execution_receipt")


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def checksum(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def checked_in_entries() -> list[dict[str, str]]:
    path = Path(__file__).with_name("data") / f"{DATASET_KEY}.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:  # Fail closed if checked-in authority is damaged.
        raise RuntimeError("The checked-in synthetic training fixture is unavailable.") from exc
    if not isinstance(value, list) or len(value) < 3:
        raise RuntimeError("The checked-in synthetic training fixture is invalid.")
    entries: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in value:
        if (
            not isinstance(item, dict)
            or set(item) != {"id", "input", "target"}
            or not all(isinstance(item[field], str) and item[field].strip() for field in ("id", "input", "target"))
            or len(item["id"]) > 128
            or len(item["input"]) > 4096
            or len(item["target"]) > 4096
            or item["id"] in seen
        ):
            raise RuntimeError("The checked-in synthetic training fixture is invalid.")
        seen.add(item["id"])
        entries.append({"id": item["id"], "input": item["input"], "target": item["target"]})
    return sorted(entries, key=lambda entry: entry["id"])


def deterministic_splits(entry_keys: list[str]) -> dict[str, str]:
    """Stable SHA-256 ranking with explicit non-empty held-out partitions."""

    if len(entry_keys) < 3 or len(set(entry_keys)) != len(entry_keys):
        raise RuntimeError("The checked-in synthetic training fixture cannot be split safely.")
    ranked = sorted(entry_keys, key=lambda value: hashlib.sha256(value.encode("utf-8")).hexdigest())
    held_out_count = max(1, len(ranked) // 5)
    validation_count = max(1, len(ranked) // 5)
    return {
        key: ("test" if index < held_out_count else "validation" if index < held_out_count + validation_count else "train")
        for index, key in enumerate(ranked)
    }


def dataset_entry_snapshot(entry: dict[str, str], split: str) -> dict[str, str]:
    source_reference = f"checked-in://training-governance/{DATASET_KEY}/{entry['id']}"
    normalized = {"input": entry["input"].strip(), "target": entry["target"].strip()}
    return {
        "entry_key": entry["id"],
        "split": split,
        "source_class": "checked_in_synthetic",
        "source_reference": source_reference,
        "input_text": normalized["input"],
        "target_text": normalized["target"],
        "content_checksum": checksum(entry),
        "input_checksum": checksum(normalized["input"]),
        "target_checksum": checksum(normalized["target"]),
        "normalized_content_checksum": checksum(normalized),
    }


def dataset_manifest_snapshot() -> dict[str, object]:
    entries = checked_in_entries()
    splits = deterministic_splits([entry["id"] for entry in entries])
    rows = [dataset_entry_snapshot(entry, splits[entry["id"]]) for entry in entries]
    _reject_training_evaluation_overlap(rows)
    counts = {split: sum(row["split"] == split for row in rows) for split in ("train", "validation", "test")}
    if not all(counts.values()):
        raise RuntimeError("The deterministic split does not produce all required partitions.")
    # Phase 21B candidate evaluation suites and Phase 21C feedback stay out of this
    # source path. This checksum preserves that exclusion as a reviewable policy fact.
    held_out = {
        "phase21b_evaluation_fingerprints": _current_evaluation_fingerprints(),
        "phase21c_feedback": "excluded_not_loaded",
        "private_user_data": "excluded_not_loaded",
        "organization_data": "excluded_not_loaded",
    }
    content = [{key: row[key] for key in ("entry_key", "input_text", "target_text")} for row in rows]
    manifest = {
        "purpose": "offline_training_preparation",
        "source_type": "checked_in_synthetic",
        "dataset_version": DATASET_KEY,
        "schema_version": DATASET_SCHEMA_VERSION,
        "content_checksum": checksum(content),
        "held_out_evaluation_checksum": checksum(held_out),
        "split_policy_version": SPLIT_POLICY_VERSION,
        "eligibility_policy_version": ELIGIBILITY_POLICY_VERSION,
        "eligibility_result": "approved_checked_in_synthetic",
        "lifecycle_state": "sealed",
        "entry_count": len(rows),
        "train_count": counts["train"],
        "validation_count": counts["validation"],
        "test_count": counts["test"],
        "entries": rows,
    }
    manifest["manifest_checksum"] = checksum({key: value for key, value in manifest.items() if key != "entries"})
    return manifest


def training_recipe() -> dict[str, object]:
    recipe = {
        "recipe_key": RECIPE_KEY,
        "recipe_version": RECIPE_VERSION,
        "intended_task": "report_synthesis_training_preparation",
        "algorithm": "deterministic_local_fake",
        "dataset_schema_version": DATASET_SCHEMA_VERSION,
        "trainable_splits": ["train", "validation"],
        "held_out_split": "test",
        "max_training_steps": 0,
        "max_sequence_length": 4096,
        "expected_artifact_types": list(EXPECTED_ARTIFACT_TYPES),
        "network_policy": "disabled",
        "shell_policy": "disabled",
        "credential_policy": "unavailable",
    }
    return {**recipe, "recipe_checksum": checksum(recipe)}


def compute_profile() -> dict[str, object]:
    profile = {
        "compute_profile_id": COMPUTE_PROFILE_ID,
        "compute_profile_version": COMPUTE_PROFILE_VERSION,
        "execution_mode": "local_fake",
        "provider": "none",
        "approved_runtime_identity": "in-process-local-fake@sha256:7a42d5b65f95b19f36de3de675adb88155e3a23fb8a9e92d49762305066d945a",
        "network_policy": "disabled",
        "gpu_class": "none_local_fake",
        "gpu_count": 0,
        "max_concurrency": 1,
        "max_runtime_seconds": 90,
        "max_disk_mib": 1024,
        "max_total_cost_microusd": 0,
        "max_hourly_cost_microusd": 0,
        "base_model_identity": "local-fake/report-synthesis-base@sha256:5c6a4f46335210d5d6a1ba75d4cd48a7815ebdaa563d2215d06fd359602c57e9",
    }
    return {**profile, "compute_profile_checksum": checksum(profile)}


def require_checked_in_dataset(dataset_key: str | None) -> None:
    if dataset_key not in {None, DATASET_KEY}:
        raise HTTPException(status_code=422, detail="Only the server-owned checked-in synthetic dataset is available.")


def _current_evaluation_fingerprints() -> dict[str, object]:
    """Bind the sealed dataset to the current held-out 21B/21C corpora without loading them into training."""

    fingerprints: list[dict[str, str]] = []
    for filename in ("report_synthesis_public_v2.json", "report_synthesis_adversarial_v1.json"):
        try:
            document = json.loads(files("app.llm").joinpath(f"evaluation_data/{filename}").read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise RuntimeError("The held-out evaluation corpus is unavailable.") from exc
        dataset_id = document.get("dataset_id") if isinstance(document, dict) else None
        cases = document.get("cases") if isinstance(document, dict) else None
        if not isinstance(dataset_id, str) or not isinstance(cases, list):
            raise RuntimeError("The held-out evaluation corpus is invalid.")
        for case in cases:
            if not isinstance(case, dict) or not isinstance(case.get("id"), str):
                raise RuntimeError("The held-out evaluation corpus is invalid.")
            fingerprints.append(
                {
                    "dataset_id": dataset_id,
                    "case_id": case["id"],
                    "case_checksum": checksum(case),
                }
            )
    return {"policy": "excluded_not_loaded", "cases": sorted(fingerprints, key=lambda item: (item["dataset_id"], item["case_id"]))}


def _reject_training_evaluation_overlap(rows: list[dict[str, str]]) -> None:
    """Fail before sealing if a synthetic record resembles an evaluator case or another split."""

    evaluation = _current_evaluation_fingerprints()
    cases = evaluation["cases"]
    evaluation_ids = {case["case_id"] for case in cases if isinstance(case, dict)}
    seen_normalized: dict[str, str] = {}
    for row in rows:
        entry_key = row["entry_key"]
        normalized = row["normalized_content_checksum"]
        if entry_key in evaluation_ids:
            raise RuntimeError("Training data overlaps a held-out evaluation case identifier.")
        existing_split = seen_normalized.get(normalized)
        if existing_split is not None:
            raise RuntimeError("Training data has a duplicate normalized content fingerprint across splits.")
        seen_normalized[normalized] = row["split"]
