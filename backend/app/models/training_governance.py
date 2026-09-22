from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base


_CHECKSUM = "length({column}) = 64"


class TrainingDatasetManifestModel(Base):
    """Immutable, server-sealed dataset evidence for local training preparation."""

    __tablename__ = "training_dataset_manifests"
    __table_args__ = (
        UniqueConstraint("purpose", "dataset_version", name="uq_training_dataset_manifest_identity"),
        UniqueConstraint("manifest_checksum", name="uq_training_dataset_manifest_checksum"),
        CheckConstraint("purpose = 'offline_training_preparation'", name="ck_training_dataset_manifest_purpose"),
        CheckConstraint("source_type = 'checked_in_synthetic'", name="ck_training_dataset_manifest_source"),
        CheckConstraint("schema_version = 'training.dataset.v1'", name="ck_training_dataset_manifest_schema"),
        CheckConstraint("split_policy_version = 'training.split.sha256.v1'", name="ck_training_dataset_manifest_split_policy"),
        CheckConstraint("eligibility_policy_version = 'training.eligibility.v1'", name="ck_training_dataset_manifest_eligibility"),
        CheckConstraint("eligibility_result = 'approved_checked_in_synthetic'", name="ck_training_dataset_manifest_eligibility_result"),
        CheckConstraint("lifecycle_state = 'sealed'", name="ck_training_dataset_manifest_lifecycle"),
        CheckConstraint(_CHECKSUM.format(column="content_checksum"), name="ck_training_dataset_manifest_content_checksum"),
        CheckConstraint(_CHECKSUM.format(column="manifest_checksum"), name="ck_training_dataset_manifest_checksum"),
        CheckConstraint(_CHECKSUM.format(column="held_out_evaluation_checksum"), name="ck_training_dataset_manifest_heldout_checksum"),
        CheckConstraint("entry_count > 0", name="ck_training_dataset_manifest_entry_count"),
        CheckConstraint("train_count > 0 AND validation_count > 0 AND test_count > 0", name="ck_training_dataset_manifest_split_counts"),
        Index("ix_training_dataset_manifests_created", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    purpose: Mapped[str] = mapped_column(String(64), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(128), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    content_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    manifest_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    held_out_evaluation_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    split_policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    eligibility_policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    eligibility_result: Mapped[str] = mapped_column(String(64), nullable=False)
    lifecycle_state: Mapped[str] = mapped_column(String(32), nullable=False, default="sealed")
    entry_count: Mapped[int] = mapped_column(Integer, nullable=False)
    train_count: Mapped[int] = mapped_column(Integer, nullable=False)
    validation_count: Mapped[int] = mapped_column(Integer, nullable=False)
    test_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class TrainingDatasetEntryModel(Base):
    """Immutable normalized entries; only checked-in synthetic material is admissible."""

    __tablename__ = "training_dataset_entries"
    __table_args__ = (
        UniqueConstraint("manifest_id", "entry_key", name="uq_training_dataset_entry_key"),
        UniqueConstraint("manifest_id", "normalized_content_checksum", name="uq_training_dataset_entry_normalized"),
        CheckConstraint("split IN ('train', 'validation', 'test')", name="ck_training_dataset_entry_split"),
        CheckConstraint("source_class = 'checked_in_synthetic'", name="ck_training_dataset_entry_source"),
        CheckConstraint(_CHECKSUM.format(column="content_checksum"), name="ck_training_dataset_entry_content_checksum"),
        CheckConstraint(_CHECKSUM.format(column="input_checksum"), name="ck_training_dataset_entry_input_checksum"),
        CheckConstraint(_CHECKSUM.format(column="target_checksum"), name="ck_training_dataset_entry_target_checksum"),
        CheckConstraint(_CHECKSUM.format(column="normalized_content_checksum"), name="ck_training_dataset_entry_normalized_checksum"),
        Index("ix_training_dataset_entries_manifest_split", "manifest_id", "split"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    manifest_id: Mapped[str] = mapped_column(ForeignKey("training_dataset_manifests.id", ondelete="CASCADE"), nullable=False)
    entry_key: Mapped[str] = mapped_column(String(128), nullable=False)
    split: Mapped[str] = mapped_column(String(16), nullable=False)
    source_class: Mapped[str] = mapped_column(String(64), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    target_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    input_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    target_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    normalized_content_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class TrainingRunModel(Base):
    """Immutable execution snapshot; it is not a registry candidate or route authority."""

    __tablename__ = "training_runs"
    __table_args__ = (
        UniqueConstraint("job_id", name="uq_training_runs_job"),
        CheckConstraint("execution_mode IN ('dry_run', 'local_fake')", name="ck_training_runs_execution_mode"),
        CheckConstraint("status IN ('queued', 'running', 'completed', 'failed', 'cancelled')", name="ck_training_runs_status"),
        CheckConstraint("cleanup_state IN ('not_required', 'completed')", name="ck_training_runs_cleanup"),
        CheckConstraint("candidate_class = 'not_registry_eligible'", name="ck_training_runs_candidate_class"),
        CheckConstraint("real_training_occurred = false", name="ck_training_runs_real_training"),
        CheckConstraint(_CHECKSUM.format(column="manifest_checksum"), name="ck_training_runs_manifest_checksum"),
        CheckConstraint(_CHECKSUM.format(column="recipe_checksum"), name="ck_training_runs_recipe_checksum"),
        CheckConstraint(_CHECKSUM.format(column="compute_profile_checksum"), name="ck_training_runs_profile_checksum"),
        CheckConstraint("estimated_cost_microusd = 0 AND actual_cost_microusd = 0", name="ck_training_runs_zero_cost"),
        Index("ix_training_runs_status_created", "status", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="RESTRICT"), nullable=False)
    manifest_id: Mapped[str] = mapped_column(ForeignKey("training_dataset_manifests.id", ondelete="RESTRICT"), nullable=False)
    manifest_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    recipe_key: Mapped[str] = mapped_column(String(128), nullable=False)
    recipe_version: Mapped[str] = mapped_column(String(64), nullable=False)
    recipe_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    base_model_identity: Mapped[str] = mapped_column(String(255), nullable=False)
    compute_profile_id: Mapped[str] = mapped_column(String(128), nullable=False)
    compute_profile_version: Mapped[str] = mapped_column(String(64), nullable=False)
    compute_profile_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    execution_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    execution_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    cleanup_state: Mapped[str] = mapped_column(String(32), nullable=False, default="not_required")
    candidate_class: Mapped[str] = mapped_column(String(64), nullable=False, default="not_registry_eligible")
    real_training_occurred: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    result_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    estimated_cost_microusd: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    actual_cost_microusd: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
