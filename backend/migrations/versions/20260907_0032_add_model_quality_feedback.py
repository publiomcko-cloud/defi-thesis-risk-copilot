"""Add bounded model quality evidence and feedback governance.

Revision ID: 20260907_0032
Revises: 20260906_0031
"""

from alembic import op
import sqlalchemy as sa


revision = "20260907_0032"
down_revision = "20260906_0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("model_evaluation_runs") as batch:
        batch.add_column(sa.Column("adversarial_dataset_id", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("citation_consistency_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("unsupported_claim_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("uncertainty_preserved_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("source_instruction_flag_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("poisoning_detected_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("deterministic_integrity_count", sa.Integer(), nullable=False, server_default="0"))
        batch.create_check_constraint("ck_model_evaluation_runs_citation_count", "citation_consistency_count BETWEEN 0 AND case_count")
        batch.create_check_constraint("ck_model_evaluation_runs_unsupported_count", "unsupported_claim_count BETWEEN 0 AND 64000")
        batch.create_check_constraint("ck_model_evaluation_runs_uncertainty_count", "uncertainty_preserved_count BETWEEN 0 AND case_count")
        batch.create_check_constraint("ck_model_evaluation_runs_instruction_count", "source_instruction_flag_count BETWEEN 0 AND 64000")
        batch.create_check_constraint("ck_model_evaluation_runs_poisoning_count", "poisoning_detected_count BETWEEN 0 AND case_count")
        batch.create_check_constraint("ck_model_evaluation_runs_quality_deterministic_count", "deterministic_integrity_count BETWEEN 0 AND case_count")
        batch.create_foreign_key(
            "fk_model_evaluation_runs_adversarial_dataset",
            "model_evaluation_datasets",
            ["adversarial_dataset_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    with op.batch_alter_table("model_evaluation_case_results") as batch:
        batch.add_column(sa.Column("citation_consistency", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("unsupported_claim_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("uncertainty_preserved", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("source_instruction_flag_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("poisoning_detected", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("deterministic_integrity", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.create_check_constraint("ck_model_evaluation_case_results_unsupported_count", "unsupported_claim_count BETWEEN 0 AND 64")
        batch.create_check_constraint("ck_model_evaluation_case_results_instruction_count", "source_instruction_flag_count BETWEEN 0 AND 64")

    op.create_table(
        "model_run_quality_evidence",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("model_run_provenance_id", sa.String(length=64), nullable=False),
        sa.Column("quality_policy_version", sa.String(length=64), nullable=False),
        sa.Column("quality_policy_checksum", sa.String(length=64), nullable=False),
        sa.Column("citation_consistency", sa.Boolean(), nullable=False),
        sa.Column("unsupported_claim_count", sa.Integer(), nullable=False),
        sa.Column("missing_source_honesty", sa.Boolean(), nullable=False),
        sa.Column("uncertainty_preserved", sa.Boolean(), nullable=False),
        sa.Column("source_instruction_flag_count", sa.Integer(), nullable=False),
        sa.Column("poisoning_detected", sa.Boolean(), nullable=False),
        sa.Column("unsafe_language_violation", sa.Boolean(), nullable=False),
        sa.Column("deterministic_integrity", sa.Boolean(), nullable=False),
        sa.Column("overall_quality_pass", sa.Boolean(), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(quality_policy_version) BETWEEN 1 AND 64", name="ck_model_quality_evidence_policy_version"),
        sa.CheckConstraint("length(quality_policy_checksum) = 64", name="ck_model_quality_evidence_policy_checksum"),
        sa.CheckConstraint("unsupported_claim_count BETWEEN 0 AND 64", name="ck_model_quality_evidence_unsupported_count"),
        sa.CheckConstraint("source_instruction_flag_count BETWEEN 0 AND 64", name="ck_model_quality_evidence_instruction_count"),
        sa.CheckConstraint("reason_code IS NULL OR length(reason_code) BETWEEN 1 AND 64", name="ck_model_quality_evidence_reason"),
        sa.ForeignKeyConstraint(["model_run_provenance_id"], ["model_run_provenance.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_run_provenance_id", name="uq_model_run_quality_evidence_run"),
    )
    op.create_index("ix_model_quality_evidence_run", "model_run_quality_evidence", ["model_run_provenance_id"])

    op.create_table(
        "model_feedback",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("report_id", sa.String(length=64), nullable=False),
        sa.Column("model_run_provenance_id", sa.String(length=64), nullable=True),
        sa.Column("owner_user_id", sa.String(length=64), nullable=True),
        sa.Column("organization_id", sa.String(length=64), nullable=True),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("review_state", sa.String(length=32), nullable=False),
        sa.Column("dataset_review_reference", sa.String(length=64), nullable=True),
        sa.Column("reviewed_by_user_id", sa.String(length=64), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("category IN ('helpful', 'incorrect', 'missing_source', 'bad_citation', 'unclear', 'entity_error', 'unsafe')", name="ck_model_feedback_category"),
        sa.CheckConstraint("review_state IN ('submitted', 'reviewed', 'approved_for_dataset', 'rejected')", name="ck_model_feedback_review_state"),
        sa.CheckConstraint("comment IS NULL OR length(comment) BETWEEN 1 AND 1000", name="ck_model_feedback_comment"),
        sa.CheckConstraint("dataset_review_reference IS NULL OR length(dataset_review_reference) BETWEEN 1 AND 64", name="ck_model_feedback_dataset_reference"),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["model_run_provenance_id"], ["model_run_provenance.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_model_feedback_owner_created", "model_feedback", ["owner_user_id", "created_at"])
    op.create_index("ix_model_feedback_org_created", "model_feedback", ["organization_id", "created_at"])
    op.create_index("ix_model_feedback_review_state", "model_feedback", ["review_state", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_model_feedback_review_state", table_name="model_feedback")
    op.drop_index("ix_model_feedback_org_created", table_name="model_feedback")
    op.drop_index("ix_model_feedback_owner_created", table_name="model_feedback")
    op.drop_table("model_feedback")
    op.drop_index("ix_model_quality_evidence_run", table_name="model_run_quality_evidence")
    op.drop_table("model_run_quality_evidence")

    with op.batch_alter_table("model_evaluation_case_results") as batch:
        batch.drop_constraint("ck_model_evaluation_case_results_instruction_count", type_="check")
        batch.drop_constraint("ck_model_evaluation_case_results_unsupported_count", type_="check")
        batch.drop_column("deterministic_integrity")
        batch.drop_column("poisoning_detected")
        batch.drop_column("source_instruction_flag_count")
        batch.drop_column("uncertainty_preserved")
        batch.drop_column("unsupported_claim_count")
        batch.drop_column("citation_consistency")

    with op.batch_alter_table("model_evaluation_runs") as batch:
        batch.drop_constraint("ck_model_evaluation_runs_quality_deterministic_count", type_="check")
        batch.drop_constraint("ck_model_evaluation_runs_poisoning_count", type_="check")
        batch.drop_constraint("ck_model_evaluation_runs_instruction_count", type_="check")
        batch.drop_constraint("ck_model_evaluation_runs_uncertainty_count", type_="check")
        batch.drop_constraint("ck_model_evaluation_runs_unsupported_count", type_="check")
        batch.drop_constraint("ck_model_evaluation_runs_citation_count", type_="check")
        batch.drop_constraint("fk_model_evaluation_runs_adversarial_dataset", type_="foreignkey")
        batch.drop_column("deterministic_integrity_count")
        batch.drop_column("poisoning_detected_count")
        batch.drop_column("source_instruction_flag_count")
        batch.drop_column("uncertainty_preserved_count")
        batch.drop_column("unsupported_claim_count")
        batch.drop_column("citation_consistency_count")
        batch.drop_column("adversarial_dataset_id")
