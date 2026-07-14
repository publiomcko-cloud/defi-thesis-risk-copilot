"""add access control tables

Revision ID: 20260714_0006
Revises: 20260714_0005
Create Date: 2026-07-14
"""
from alembic import op
import sqlalchemy as sa


revision = "20260714_0006"
down_revision = "20260714_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("access_token_hash", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_access_token_hash"), "users", ["access_token_hash"])
    op.create_index(op.f("ix_users_email"), "users", ["email"])

    op.create_table(
        "api_credentials",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("secret_encrypted", sa.Text(), nullable=False),
        sa.Column("secret_last4", sa.String(length=8), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_api_credentials_provider"), "api_credentials", ["provider"])

    op.create_table(
        "access_audit_events",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("actor_user_id", sa.String(length=64), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=128), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_access_audit_events_action"), "access_audit_events", ["action"])
    op.create_index(
        op.f("ix_access_audit_events_actor_user_id"),
        "access_audit_events",
        ["actor_user_id"],
    )
    op.create_index(
        op.f("ix_access_audit_events_resource_type"),
        "access_audit_events",
        ["resource_type"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_access_audit_events_resource_type"), table_name="access_audit_events")
    op.drop_index(op.f("ix_access_audit_events_actor_user_id"), table_name="access_audit_events")
    op.drop_index(op.f("ix_access_audit_events_action"), table_name="access_audit_events")
    op.drop_table("access_audit_events")
    op.drop_index(op.f("ix_api_credentials_provider"), table_name="api_credentials")
    op.drop_table("api_credentials")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_access_token_hash"), table_name="users")
    op.drop_table("users")
