from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SealTrainingDatasetRequest(BaseModel):
    dataset_key: str | None = Field(default=None, max_length=128)

    model_config = ConfigDict(extra="forbid")


class SubmitTrainingRunRequest(BaseModel):
    dataset_key: str | None = Field(default=None, max_length=128)
    execution_mode: Literal["dry_run", "local_fake"] = "dry_run"

    model_config = ConfigDict(extra="forbid")


class TrainingManifestResponse(BaseModel):
    id: str
    dataset_version: str
    manifest_checksum: str
    content_checksum: str
    held_out_evaluation_checksum: str
    eligibility_result: str
    entry_count: int
    train_count: int
    validation_count: int
    test_count: int
    created_at: datetime


class TrainingArtifactResponse(BaseModel):
    id: str
    artifact_type: str
    status: str
    checksum: str | None
    size_bytes: int | None
    content_type: str | None
    storage_backend: str | None


class TrainingRunResponse(BaseModel):
    id: str
    job_id: str
    manifest_id: str
    manifest_checksum: str
    recipe_key: str
    recipe_version: str
    base_model_identity: str
    compute_profile_id: str
    compute_profile_version: str
    execution_mode: str
    status: str
    candidate_class: str
    real_training_occurred: bool
    result_code: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    artifacts: list[TrainingArtifactResponse] = Field(default_factory=list)


class TrainingGovernanceResponse(BaseModel):
    manifests: list[TrainingManifestResponse]
    runs: list[TrainingRunResponse]
    compute_profile: dict[str, object]
    recipe: dict[str, object]
