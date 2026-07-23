"""add durable job foundation

Revision ID: 20260723_0011
Revises: 20260721_0010
Create Date: 2026-07-23
"""

from alembic import op
import sqlalchemy as sa


revision = "20260723_0011"
down_revision = "20260721_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workers",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("protocol_version", sa.String(length=32), nullable=False),
        sa.Column("software_version", sa.String(length=64), nullable=True),
        sa.Column("capabilities_json", sa.JSON(), nullable=False),
        sa.Column("allowed_job_types", sa.JSON(), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=True),
        sa.Column("max_concurrency", sa.Integer(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('active', 'disabled', 'stale', 'revoked')",
            name="ck_workers_status",
        ),
        sa.CheckConstraint("max_concurrency > 0", name="ck_workers_max_concurrency"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_workers_name"),
    )
    op.create_index("ix_workers_status", "workers", ["status"])
    op.create_index("ix_workers_organization_id", "workers", ["organization_id"])
    op.create_index("ix_workers_status_last_seen", "workers", ["status", "last_seen_at"])
    op.create_index("ix_workers_org_status", "workers", ["organization_id", "status"])

    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("priority_class", sa.String(length=32), nullable=False),
        sa.Column("owner_user_id", sa.String(length=64), nullable=True),
        sa.Column("organization_id", sa.String(length=64), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=64), nullable=False),
        sa.Column("visibility", sa.String(length=32), nullable=False),
        sa.Column("input_schema_version", sa.String(length=32), nullable=False),
        sa.Column("input_json", sa.JSON(), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("result_schema_version", sa.String(length=32), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("result_resource_type", sa.String(length=64), nullable=True),
        sa.Column("result_resource_id", sa.String(length=64), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("queue_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("leased_by_worker_id", sa.String(length=64), nullable=True),
        sa.Column("lease_generation", sa.Integer(), nullable=False),
        sa.Column("lease_token_hash", sa.String(length=128), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("progress_percent", sa.Integer(), nullable=False),
        sa.Column("progress_message", sa.String(length=512), nullable=True),
        sa.Column("idempotency_subject_type", sa.String(length=32), nullable=False),
        sa.Column("idempotency_subject_id", sa.String(length=128), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("estimated_cost_microusd", sa.BigInteger(), nullable=False),
        sa.Column("reserved_cost_microusd", sa.BigInteger(), nullable=False),
        sa.Column("actual_cost_microusd", sa.BigInteger(), nullable=False),
        sa.Column("replay_of_job_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('queued', 'leased', 'running', 'retry_wait', 'completed', 'failed', "
            "'cancel_requested', 'cancelled', 'dead_letter')",
            name="ck_jobs_status",
        ),
        sa.CheckConstraint(
            "priority_class IN ('standard', 'elevated', 'admin')",
            name="ck_jobs_priority_class",
        ),
        sa.CheckConstraint("visibility IN ('private', 'organization')", name="ck_jobs_visibility"),
        sa.CheckConstraint("attempt_count >= 0", name="ck_jobs_attempt_count"),
        sa.CheckConstraint("max_attempts > 0", name="ck_jobs_max_attempts"),
        sa.CheckConstraint("lease_generation >= 0", name="ck_jobs_lease_generation"),
        sa.CheckConstraint(
            "progress_percent >= 0 AND progress_percent <= 100",
            name="ck_jobs_progress_percent",
        ),
        sa.CheckConstraint("estimated_cost_microusd >= 0", name="ck_jobs_estimated_cost"),
        sa.CheckConstraint("reserved_cost_microusd >= 0", name="ck_jobs_reserved_cost"),
        sa.CheckConstraint("actual_cost_microusd >= 0", name="ck_jobs_actual_cost"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["leased_by_worker_id"], ["workers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["replay_of_job_id"], ["jobs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "idempotency_subject_type",
            "idempotency_subject_id",
            "job_type",
            "idempotency_key",
            name="uq_jobs_idempotency_scope",
        ),
    )
    for column in (
        "job_type",
        "status",
        "owner_user_id",
        "organization_id",
        "created_by_user_id",
        "visibility",
        "available_at",
        "leased_by_worker_id",
        "replay_of_job_id",
    ):
        op.create_index(f"ix_jobs_{column}", "jobs", [column])
    op.create_index("ix_jobs_claim", "jobs", ["status", "priority_class", "available_at", "created_at"])
    op.create_index("ix_jobs_owner_status", "jobs", ["owner_user_id", "status", "available_at"])
    op.create_index("ix_jobs_org_status", "jobs", ["organization_id", "status", "available_at"])
    op.create_index("ix_jobs_retention", "jobs", ["deleted_at", "status", "updated_at"])

    op.create_table(
        "job_attempts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("worker_id", sa.String(length=64), nullable=True),
        sa.Column("lease_generation", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.String(length=32), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("runtime_ms", sa.BigInteger(), nullable=False),
        sa.Column("estimated_cost_microusd", sa.BigInteger(), nullable=False),
        sa.Column("actual_cost_microusd", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("attempt_number > 0", name="ck_job_attempts_number"),
        sa.CheckConstraint("lease_generation > 0", name="ck_job_attempts_generation"),
        sa.CheckConstraint("runtime_ms >= 0", name="ck_job_attempts_runtime"),
        sa.CheckConstraint("estimated_cost_microusd >= 0", name="ck_job_attempts_estimated_cost"),
        sa.CheckConstraint("actual_cost_microusd >= 0", name="ck_job_attempts_actual_cost"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worker_id"], ["workers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "attempt_number", name="uq_job_attempts_number"),
        sa.UniqueConstraint("job_id", "lease_generation", name="uq_job_attempts_generation"),
    )
    op.create_index("ix_job_attempts_job_id", "job_attempts", ["job_id"])
    op.create_index("ix_job_attempts_worker_id", "job_attempts", ["worker_id"])
    op.create_index("ix_job_attempts_outcome", "job_attempts", ["outcome"])
    op.create_index("ix_job_attempts_worker_outcome", "job_attempts", ["worker_id", "outcome", "created_at"])

    op.create_table(
        "job_events",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("message", sa.String(length=512), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("actor_user_id", sa.String(length=64), nullable=True),
        sa.Column("worker_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["worker_id"], ["workers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "sequence_number", name="uq_job_events_sequence"),
    )
    for column in ("job_id", "event_type", "actor_user_id", "worker_id"):
        op.create_index(f"ix_job_events_{column}", "job_events", [column])
    op.create_index("ix_job_events_job_created", "job_events", ["job_id", "created_at"])

    op.create_table(
        "worker_credentials",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("worker_id", sa.String(length=64), nullable=False),
        sa.Column("token_prefix", sa.String(length=24), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("allowed_job_types", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rotated_from_id", sa.String(length=64), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('active', 'revoked', 'expired')",
            name="ck_worker_credentials_status",
        ),
        sa.ForeignKeyConstraint(["worker_id"], ["workers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rotated_from_id"], ["worker_credentials.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_prefix", name="uq_worker_credentials_prefix"),
        sa.UniqueConstraint("token_hash", name="uq_worker_credentials_hash"),
    )
    for column in ("worker_id", "status", "rotated_from_id", "created_by_user_id"):
        op.create_index(f"ix_worker_credentials_{column}", "worker_credentials", [column])
    op.create_index(
        "ix_worker_credentials_worker_status",
        "worker_credentials",
        ["worker_id", "status", "expires_at"],
    )

    op.create_table(
        "artifacts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("owner_user_id", sa.String(length=64), nullable=True),
        sa.Column("organization_id", sa.String(length=64), nullable=True),
        sa.Column("visibility", sa.String(length=32), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=True),
        sa.Column("resource_id", sa.String(length=64), nullable=True),
        sa.Column("storage_backend", sa.String(length=64), nullable=True),
        sa.Column("storage_key", sa.String(length=1024), nullable=True),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending_storage', 'incomplete', 'available', 'deleted')",
            name="ck_artifacts_status",
        ),
        sa.CheckConstraint("visibility IN ('private', 'organization')", name="ck_artifacts_visibility"),
        sa.CheckConstraint("size_bytes IS NULL OR size_bytes >= 0", name="ck_artifacts_size"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("job_id", "artifact_type", "status", "owner_user_id", "organization_id", "visibility"):
        op.create_index(f"ix_artifacts_{column}", "artifacts", [column])
    op.create_index("ix_artifacts_job_status", "artifacts", ["job_id", "status"])
    op.create_index("ix_artifacts_owner_deleted", "artifacts", ["owner_user_id", "deleted_at"])
    op.create_index(
        "ix_artifacts_org_visibility_deleted",
        "artifacts",
        ["organization_id", "visibility", "deleted_at"],
    )
    op.create_index("ix_artifacts_retention", "artifacts", ["retention_until", "status"])


def downgrade() -> None:
    for index in (
        "ix_artifacts_retention",
        "ix_artifacts_org_visibility_deleted",
        "ix_artifacts_owner_deleted",
        "ix_artifacts_job_status",
        "ix_artifacts_visibility",
        "ix_artifacts_organization_id",
        "ix_artifacts_owner_user_id",
        "ix_artifacts_status",
        "ix_artifacts_artifact_type",
        "ix_artifacts_job_id",
    ):
        op.drop_index(index, table_name="artifacts")
    op.drop_table("artifacts")

    for index in (
        "ix_worker_credentials_worker_status",
        "ix_worker_credentials_created_by_user_id",
        "ix_worker_credentials_rotated_from_id",
        "ix_worker_credentials_status",
        "ix_worker_credentials_worker_id",
    ):
        op.drop_index(index, table_name="worker_credentials")
    op.drop_table("worker_credentials")

    for index in (
        "ix_job_events_job_created",
        "ix_job_events_worker_id",
        "ix_job_events_actor_user_id",
        "ix_job_events_event_type",
        "ix_job_events_job_id",
    ):
        op.drop_index(index, table_name="job_events")
    op.drop_table("job_events")

    for index in (
        "ix_job_attempts_worker_outcome",
        "ix_job_attempts_outcome",
        "ix_job_attempts_worker_id",
        "ix_job_attempts_job_id",
    ):
        op.drop_index(index, table_name="job_attempts")
    op.drop_table("job_attempts")

    for index in (
        "ix_jobs_retention",
        "ix_jobs_org_status",
        "ix_jobs_owner_status",
        "ix_jobs_claim",
        "ix_jobs_replay_of_job_id",
        "ix_jobs_leased_by_worker_id",
        "ix_jobs_available_at",
        "ix_jobs_visibility",
        "ix_jobs_created_by_user_id",
        "ix_jobs_organization_id",
        "ix_jobs_owner_user_id",
        "ix_jobs_status",
        "ix_jobs_job_type",
    ):
        op.drop_index(index, table_name="jobs")
    op.drop_table("jobs")

    for index in (
        "ix_workers_org_status",
        "ix_workers_status_last_seen",
        "ix_workers_organization_id",
        "ix_workers_status",
    ):
        op.drop_index(index, table_name="workers")
    op.drop_table("workers")
