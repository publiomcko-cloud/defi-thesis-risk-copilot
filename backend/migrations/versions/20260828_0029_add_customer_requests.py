"""add bounded customer requests

Revision ID: 20260828_0029
Revises: 20260824_0028
Create Date: 2026-08-28
"""

from alembic import op
import sqlalchemy as sa


revision = "20260828_0029"
down_revision = "20260824_0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customer_requests",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("owner_user_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=True),
        sa.Column("request_type", sa.String(length=32), nullable=False),
        sa.Column("subject", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=4000), nullable=False),
        sa.Column("workflow_state", sa.String(length=16), nullable=False),
        sa.Column("verification_state", sa.String(length=16), nullable=False),
        sa.Column("resolution_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "request_type IN ('support', 'feedback', 'abuse_report', 'privacy_access_export', 'privacy_deletion')",
            name="ck_customer_requests_request_type",
        ),
        sa.CheckConstraint(
            "workflow_state IN ('open', 'in_progress', 'resolved', 'closed')",
            name="ck_customer_requests_workflow_state",
        ),
        sa.CheckConstraint(
            "verification_state IN ('not_required', 'authenticated')",
            name="ck_customer_requests_verification_state",
        ),
        sa.CheckConstraint("length(subject) >= 1 AND length(subject) <= 120", name="ck_customer_requests_subject_length"),
        sa.CheckConstraint(
            "length(description) >= 1 AND length(description) <= 4000",
            name="ck_customer_requests_description_length",
        ),
        sa.CheckConstraint(
            "resolution_code IS NULL OR (length(resolution_code) >= 1 AND length(resolution_code) <= 64)",
            name="ck_customer_requests_resolution_code_length",
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customer_requests_owner_user_id", "customer_requests", ["owner_user_id"])
    op.create_index("ix_customer_requests_organization_id", "customer_requests", ["organization_id"])
    op.create_index("ix_customer_requests_request_type", "customer_requests", ["request_type"])
    op.create_index("ix_customer_requests_owner_created", "customer_requests", ["owner_user_id", "created_at"])
    op.create_index("ix_customer_requests_organization", "customer_requests", ["organization_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_customer_requests_organization", table_name="customer_requests")
    op.drop_index("ix_customer_requests_owner_created", table_name="customer_requests")
    op.drop_index("ix_customer_requests_request_type", table_name="customer_requests")
    op.drop_index("ix_customer_requests_organization_id", table_name="customer_requests")
    op.drop_index("ix_customer_requests_owner_user_id", table_name="customer_requests")
    op.drop_table("customer_requests")
