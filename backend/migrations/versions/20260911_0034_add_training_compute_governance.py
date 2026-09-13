"""Add immutable local training-compute governance.

Revision ID: 20260911_0034
Revises: 20260910_0033
"""

from alembic import op
import sqlalchemy as sa


revision = "20260911_0034"
down_revision = "20260910_0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "training_dataset_manifests",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("purpose", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("dataset_version", sa.String(length=128), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("content_checksum", sa.String(length=64), nullable=False),
        sa.Column("manifest_checksum", sa.String(length=64), nullable=False),
        sa.Column("held_out_evaluation_checksum", sa.String(length=64), nullable=False),
        sa.Column("split_policy_version", sa.String(length=64), nullable=False),
        sa.Column("eligibility_policy_version", sa.String(length=64), nullable=False),
        sa.Column("eligibility_result", sa.String(length=64), nullable=False),
        sa.Column("lifecycle_state", sa.String(length=32), nullable=False),
        sa.Column("entry_count", sa.Integer(), nullable=False),
        sa.Column("train_count", sa.Integer(), nullable=False),
        sa.Column("validation_count", sa.Integer(), nullable=False),
        sa.Column("test_count", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("purpose = 'offline_training_preparation'", name="ck_training_dataset_manifest_purpose"),
        sa.CheckConstraint("source_type = 'checked_in_synthetic'", name="ck_training_dataset_manifest_source"),
        sa.CheckConstraint("schema_version = 'training.dataset.v1'", name="ck_training_dataset_manifest_schema"),
        sa.CheckConstraint("split_policy_version = 'training.split.sha256.v1'", name="ck_training_dataset_manifest_split_policy"),
        sa.CheckConstraint("eligibility_policy_version = 'training.eligibility.v1'", name="ck_training_dataset_manifest_eligibility"),
        sa.CheckConstraint("eligibility_result = 'approved_checked_in_synthetic'", name="ck_training_dataset_manifest_eligibility_result"),
        sa.CheckConstraint("lifecycle_state = 'sealed'", name="ck_training_dataset_manifest_lifecycle"),
        sa.CheckConstraint("length(content_checksum) = 64", name="ck_training_dataset_manifest_content_checksum"),
        sa.CheckConstraint("length(manifest_checksum) = 64", name="ck_training_dataset_manifest_checksum"),
        sa.CheckConstraint("length(held_out_evaluation_checksum) = 64", name="ck_training_dataset_manifest_heldout_checksum"),
        sa.CheckConstraint("entry_count > 0", name="ck_training_dataset_manifest_entry_count"),
        sa.CheckConstraint("train_count > 0 AND validation_count > 0 AND test_count > 0", name="ck_training_dataset_manifest_split_counts"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("purpose", "dataset_version", name="uq_training_dataset_manifest_identity"),
        sa.UniqueConstraint("manifest_checksum", name="uq_training_dataset_manifest_checksum"),
    )
    op.create_index("ix_training_dataset_manifests_created", "training_dataset_manifests", ["created_at"])

    op.create_table(
        "training_dataset_entries",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("manifest_id", sa.String(length=64), nullable=False),
        sa.Column("entry_key", sa.String(length=128), nullable=False),
        sa.Column("split", sa.String(length=16), nullable=False),
        sa.Column("source_class", sa.String(length=64), nullable=False),
        sa.Column("source_reference", sa.String(length=255), nullable=False),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("target_text", sa.Text(), nullable=False),
        sa.Column("content_checksum", sa.String(length=64), nullable=False),
        sa.Column("input_checksum", sa.String(length=64), nullable=False),
        sa.Column("target_checksum", sa.String(length=64), nullable=False),
        sa.Column("normalized_content_checksum", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("split IN ('train', 'validation', 'test')", name="ck_training_dataset_entry_split"),
        sa.CheckConstraint("source_class = 'checked_in_synthetic'", name="ck_training_dataset_entry_source"),
        sa.CheckConstraint("length(content_checksum) = 64", name="ck_training_dataset_entry_content_checksum"),
        sa.CheckConstraint("length(input_checksum) = 64", name="ck_training_dataset_entry_input_checksum"),
        sa.CheckConstraint("length(target_checksum) = 64", name="ck_training_dataset_entry_target_checksum"),
        sa.CheckConstraint("length(normalized_content_checksum) = 64", name="ck_training_dataset_entry_normalized_checksum"),
        sa.ForeignKeyConstraint(["manifest_id"], ["training_dataset_manifests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("manifest_id", "entry_key", name="uq_training_dataset_entry_key"),
        sa.UniqueConstraint("manifest_id", "normalized_content_checksum", name="uq_training_dataset_entry_normalized"),
    )
    op.create_index("ix_training_dataset_entries_manifest_split", "training_dataset_entries", ["manifest_id", "split"])

    op.create_table(
        "training_runs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("manifest_id", sa.String(length=64), nullable=False),
        sa.Column("manifest_checksum", sa.String(length=64), nullable=False),
        sa.Column("recipe_key", sa.String(length=128), nullable=False),
        sa.Column("recipe_version", sa.String(length=64), nullable=False),
        sa.Column("recipe_checksum", sa.String(length=64), nullable=False),
        sa.Column("base_model_identity", sa.String(length=255), nullable=False),
        sa.Column("compute_profile_id", sa.String(length=128), nullable=False),
        sa.Column("compute_profile_version", sa.String(length=64), nullable=False),
        sa.Column("compute_profile_checksum", sa.String(length=64), nullable=False),
        sa.Column("execution_mode", sa.String(length=32), nullable=False),
        sa.Column("execution_snapshot", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("cleanup_state", sa.String(length=32), nullable=False),
        sa.Column("candidate_class", sa.String(length=64), nullable=False),
        sa.Column("real_training_occurred", sa.Boolean(), nullable=False),
        sa.Column("result_code", sa.String(length=64), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("estimated_cost_microusd", sa.Integer(), nullable=False),
        sa.Column("actual_cost_microusd", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=64), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("execution_mode IN ('dry_run', 'local_fake')", name="ck_training_runs_execution_mode"),
        sa.CheckConstraint("status IN ('queued', 'running', 'completed', 'failed', 'cancelled')", name="ck_training_runs_status"),
        sa.CheckConstraint("cleanup_state IN ('not_required', 'completed')", name="ck_training_runs_cleanup"),
        sa.CheckConstraint("candidate_class = 'not_registry_eligible'", name="ck_training_runs_candidate_class"),
        sa.CheckConstraint("real_training_occurred = false", name="ck_training_runs_real_training"),
        sa.CheckConstraint("length(manifest_checksum) = 64", name="ck_training_runs_manifest_checksum"),
        sa.CheckConstraint("length(recipe_checksum) = 64", name="ck_training_runs_recipe_checksum"),
        sa.CheckConstraint("length(compute_profile_checksum) = 64", name="ck_training_runs_profile_checksum"),
        sa.CheckConstraint("estimated_cost_microusd = 0 AND actual_cost_microusd = 0", name="ck_training_runs_zero_cost"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["manifest_id"], ["training_dataset_manifests.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", name="uq_training_runs_job"),
    )
    op.create_index("ix_training_runs_status_created", "training_runs", ["status", "created_at"])
    _create_immutability_guards()


def downgrade() -> None:
    _drop_immutability_guards()
    op.drop_index("ix_training_runs_status_created", table_name="training_runs")
    op.drop_table("training_runs")
    op.drop_index("ix_training_dataset_entries_manifest_split", table_name="training_dataset_entries")
    op.drop_table("training_dataset_entries")
    op.drop_index("ix_training_dataset_manifests_created", table_name="training_dataset_manifests")
    op.drop_table("training_dataset_manifests")


def _create_immutability_guards() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            CREATE FUNCTION phase21e_reject_manifest_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
              IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'sealed training manifest is immutable';
              END IF;
              IF ROW(NEW.id, NEW.purpose, NEW.source_type, NEW.dataset_version, NEW.schema_version,
                     NEW.content_checksum, NEW.manifest_checksum, NEW.held_out_evaluation_checksum,
                     NEW.split_policy_version, NEW.eligibility_policy_version, NEW.eligibility_result,
                     NEW.lifecycle_state, NEW.entry_count, NEW.train_count, NEW.validation_count,
                     NEW.test_count, NEW.created_at)
                 IS DISTINCT FROM
                 ROW(OLD.id, OLD.purpose, OLD.source_type, OLD.dataset_version, OLD.schema_version,
                     OLD.content_checksum, OLD.manifest_checksum, OLD.held_out_evaluation_checksum,
                     OLD.split_policy_version, OLD.eligibility_policy_version, OLD.eligibility_result,
                     OLD.lifecycle_state, OLD.entry_count, OLD.train_count, OLD.validation_count,
                     OLD.test_count, OLD.created_at) THEN
                RAISE EXCEPTION 'sealed training manifest is immutable';
              END IF;
              RETURN NEW;
            END $$;
            CREATE TRIGGER trg_phase21e_manifest_immutable BEFORE UPDATE OR DELETE ON training_dataset_manifests
              FOR EACH ROW EXECUTE FUNCTION phase21e_reject_manifest_mutation();
            CREATE FUNCTION phase21e_reject_entry_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'sealed training entry is immutable'; END $$;
            CREATE TRIGGER trg_phase21e_entry_immutable BEFORE UPDATE OR DELETE ON training_dataset_entries
              FOR EACH ROW EXECUTE FUNCTION phase21e_reject_entry_mutation();
            CREATE FUNCTION phase21e_reject_run_snapshot_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
              IF ROW(NEW.id, NEW.job_id, NEW.manifest_id, NEW.manifest_checksum, NEW.recipe_key,
                     NEW.recipe_version, NEW.recipe_checksum, NEW.base_model_identity, NEW.compute_profile_id,
                     NEW.compute_profile_version, NEW.compute_profile_checksum, NEW.execution_mode,
                     NEW.candidate_class, NEW.real_training_occurred,
                     NEW.estimated_cost_microusd, NEW.created_at)
                 IS DISTINCT FROM
                 ROW(OLD.id, OLD.job_id, OLD.manifest_id, OLD.manifest_checksum, OLD.recipe_key,
                     OLD.recipe_version, OLD.recipe_checksum, OLD.base_model_identity, OLD.compute_profile_id,
                     OLD.compute_profile_version, OLD.compute_profile_checksum, OLD.execution_mode,
                     OLD.candidate_class, OLD.real_training_occurred,
                     OLD.estimated_cost_microusd, OLD.created_at)
                 OR NEW.execution_snapshot::text IS DISTINCT FROM OLD.execution_snapshot::text THEN
                RAISE EXCEPTION 'training execution snapshot is immutable';
              END IF;
              RETURN NEW;
            END $$;
            CREATE TRIGGER trg_phase21e_run_snapshot_immutable BEFORE UPDATE ON training_runs
              FOR EACH ROW EXECUTE FUNCTION phase21e_reject_run_snapshot_mutation();
            """
        )
        return
    if bind.dialect.name == "sqlite":
        for statement in (
            """
            CREATE TRIGGER trg_phase21e_manifest_immutable BEFORE UPDATE ON training_dataset_manifests
            WHEN NEW.id IS NOT OLD.id OR NEW.purpose IS NOT OLD.purpose OR NEW.source_type IS NOT OLD.source_type
              OR NEW.dataset_version IS NOT OLD.dataset_version OR NEW.schema_version IS NOT OLD.schema_version
              OR NEW.content_checksum IS NOT OLD.content_checksum OR NEW.manifest_checksum IS NOT OLD.manifest_checksum
              OR NEW.held_out_evaluation_checksum IS NOT OLD.held_out_evaluation_checksum
              OR NEW.split_policy_version IS NOT OLD.split_policy_version
              OR NEW.eligibility_policy_version IS NOT OLD.eligibility_policy_version
              OR NEW.eligibility_result IS NOT OLD.eligibility_result OR NEW.lifecycle_state IS NOT OLD.lifecycle_state
              OR NEW.entry_count IS NOT OLD.entry_count OR NEW.train_count IS NOT OLD.train_count
              OR NEW.validation_count IS NOT OLD.validation_count OR NEW.test_count IS NOT OLD.test_count
              OR NEW.created_at IS NOT OLD.created_at
            BEGIN SELECT RAISE(ABORT, 'sealed training manifest is immutable'); END;
            """,
            """
            CREATE TRIGGER trg_phase21e_manifest_no_delete BEFORE DELETE ON training_dataset_manifests
            BEGIN SELECT RAISE(ABORT, 'sealed training manifest is immutable'); END;
            """,
            """
            CREATE TRIGGER trg_phase21e_entry_immutable BEFORE UPDATE ON training_dataset_entries
            BEGIN SELECT RAISE(ABORT, 'sealed training entry is immutable'); END;
            """,
            """
            CREATE TRIGGER trg_phase21e_entry_no_delete BEFORE DELETE ON training_dataset_entries
            BEGIN SELECT RAISE(ABORT, 'sealed training entry is immutable'); END;
            """,
            """
            CREATE TRIGGER trg_phase21e_run_snapshot_immutable BEFORE UPDATE ON training_runs
            WHEN NEW.id IS NOT OLD.id OR NEW.job_id IS NOT OLD.job_id OR NEW.manifest_id IS NOT OLD.manifest_id
              OR NEW.manifest_checksum IS NOT OLD.manifest_checksum OR NEW.recipe_key IS NOT OLD.recipe_key
              OR NEW.recipe_version IS NOT OLD.recipe_version OR NEW.recipe_checksum IS NOT OLD.recipe_checksum
              OR NEW.base_model_identity IS NOT OLD.base_model_identity OR NEW.compute_profile_id IS NOT OLD.compute_profile_id
              OR NEW.compute_profile_version IS NOT OLD.compute_profile_version
              OR NEW.compute_profile_checksum IS NOT OLD.compute_profile_checksum
              OR NEW.execution_mode IS NOT OLD.execution_mode OR NEW.execution_snapshot IS NOT OLD.execution_snapshot
              OR NEW.candidate_class IS NOT OLD.candidate_class OR NEW.real_training_occurred IS NOT OLD.real_training_occurred
              OR NEW.estimated_cost_microusd IS NOT OLD.estimated_cost_microusd OR NEW.created_at IS NOT OLD.created_at
            BEGIN SELECT RAISE(ABORT, 'training execution snapshot is immutable'); END;
            """,
        ):
            op.execute(statement)


def _drop_immutability_guards() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            DROP TRIGGER IF EXISTS trg_phase21e_run_snapshot_immutable ON training_runs;
            DROP TRIGGER IF EXISTS trg_phase21e_entry_immutable ON training_dataset_entries;
            DROP TRIGGER IF EXISTS trg_phase21e_manifest_immutable ON training_dataset_manifests;
            DROP FUNCTION IF EXISTS phase21e_reject_run_snapshot_mutation();
            DROP FUNCTION IF EXISTS phase21e_reject_entry_mutation();
            DROP FUNCTION IF EXISTS phase21e_reject_manifest_mutation();
            """
        )
        return
    if bind.dialect.name == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS trg_phase21e_run_snapshot_immutable")
        op.execute("DROP TRIGGER IF EXISTS trg_phase21e_entry_no_delete")
        op.execute("DROP TRIGGER IF EXISTS trg_phase21e_entry_immutable")
        op.execute("DROP TRIGGER IF EXISTS trg_phase21e_manifest_no_delete")
        op.execute("DROP TRIGGER IF EXISTS trg_phase21e_manifest_immutable")
