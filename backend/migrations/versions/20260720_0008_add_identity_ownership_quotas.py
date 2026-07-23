"""add identity ownership quotas

Revision ID: 20260720_0008
Revises: 20260714_0007
Create Date: 2026-07-20
"""
from alembic import op
import sqlalchemy as sa


revision = "20260720_0008"
down_revision = "20260714_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("auth_provider", sa.String(length=32), nullable=False, server_default="legacy_local"))
        batch.add_column(sa.Column("auth_subject", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("platform_role", sa.String(length=32), nullable=False, server_default="user"))
        batch.add_column(sa.Column("account_status", sa.String(length=32), nullable=False, server_default="active"))
        batch.add_column(sa.Column("plan", sa.String(length=32), nullable=False, server_default="free"))
        batch.add_column(sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE users SET platform_role = 'admin' WHERE role = 'admin'")
    op.create_index(op.f("ix_users_auth_subject"), "users", ["auth_subject"], unique=True)

    for table in ("analysis_requests", "reports", "watchlist_items"):
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("owner_user_id", sa.String(length=64), nullable=True))
            batch.add_column(sa.Column("organization_id", sa.String(length=64), nullable=True))
            batch.add_column(sa.Column("visibility", sa.String(length=32), nullable=False, server_default="public_demo"))
            batch.add_column(sa.Column("anonymous_session_id", sa.String(length=128), nullable=True))
            batch.add_column(sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
            batch.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        op.create_index(op.f(f"ix_{table}_owner_user_id"), table, ["owner_user_id"])
        op.create_index(op.f(f"ix_{table}_organization_id"), table, ["organization_id"])
        op.create_index(op.f(f"ix_{table}_visibility"), table, ["visibility"])
        op.create_index(op.f(f"ix_{table}_anonymous_session_id"), table, ["anonymous_session_id"])

    op.create_table(
        "organizations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(op.f("ix_organizations_created_by_user_id"), "organizations", ["created_by_user_id"])
    op.create_index(op.f("ix_organizations_slug"), "organizations", ["slug"])
    op.create_index(op.f("ix_organizations_status"), "organizations", ["status"])

    op.create_table(
        "organization_memberships",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_organization_membership_user"),
    )
    op.create_index(op.f("ix_organization_memberships_organization_id"), "organization_memberships", ["organization_id"])
    op.create_index(op.f("ix_organization_memberships_status"), "organization_memberships", ["status"])
    op.create_index(op.f("ix_organization_memberships_user_id"), "organization_memberships", ["user_id"])

    op.create_table(
        "saved_theses",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("owner_user_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("strategy_text", sa.Text(), nullable=False),
        sa.Column("protocols", sa.JSON(), nullable=False),
        sa.Column("assumptions_json", sa.JSON(), nullable=False),
        sa.Column("visibility", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_saved_theses_owner_user_id"), "saved_theses", ["owner_user_id"])
    op.create_index(op.f("ix_saved_theses_organization_id"), "saved_theses", ["organization_id"])
    op.create_index(op.f("ix_saved_theses_visibility"), "saved_theses", ["visibility"])

    op.create_table(
        "usage_quotas",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False),
        sa.Column("subject_id", sa.String(length=128), nullable=False),
        sa.Column("plan", sa.String(length=32), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Integer(), nullable=False),
        sa.Column("limit", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("subject_type", "subject_id", "action", "period_start", "period_end", name="uq_usage_quota_period"),
    )
    op.create_index(op.f("ix_usage_quotas_subject_type"), "usage_quotas", ["subject_type"])
    op.create_index(op.f("ix_usage_quotas_subject_id"), "usage_quotas", ["subject_id"])
    op.create_index(op.f("ix_usage_quotas_action"), "usage_quotas", ["action"])

    op.create_table(
        "consent_records",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("document_type", sa.String(length=32), nullable=False),
        sa.Column("document_version", sa.String(length=32), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_consent_records_user_id"), "consent_records", ["user_id"])
    op.create_index(op.f("ix_consent_records_document_type"), "consent_records", ["document_type"])

    op.create_table(
        "anonymous_sessions",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_anonymous_sessions_status"), "anonymous_sessions", ["status"])
    op.create_index(op.f("ix_anonymous_sessions_expires_at"), "anonymous_sessions", ["expires_at"])


def downgrade() -> None:
    op.drop_index(op.f("ix_anonymous_sessions_expires_at"), table_name="anonymous_sessions")
    op.drop_index(op.f("ix_anonymous_sessions_status"), table_name="anonymous_sessions")
    op.drop_table("anonymous_sessions")
    op.drop_index(op.f("ix_consent_records_document_type"), table_name="consent_records")
    op.drop_index(op.f("ix_consent_records_user_id"), table_name="consent_records")
    op.drop_table("consent_records")
    op.drop_index(op.f("ix_usage_quotas_action"), table_name="usage_quotas")
    op.drop_index(op.f("ix_usage_quotas_subject_id"), table_name="usage_quotas")
    op.drop_index(op.f("ix_usage_quotas_subject_type"), table_name="usage_quotas")
    op.drop_table("usage_quotas")
    op.drop_index(op.f("ix_saved_theses_visibility"), table_name="saved_theses")
    op.drop_index(op.f("ix_saved_theses_organization_id"), table_name="saved_theses")
    op.drop_index(op.f("ix_saved_theses_owner_user_id"), table_name="saved_theses")
    op.drop_table("saved_theses")
    op.drop_index(op.f("ix_organization_memberships_user_id"), table_name="organization_memberships")
    op.drop_index(op.f("ix_organization_memberships_status"), table_name="organization_memberships")
    op.drop_index(op.f("ix_organization_memberships_organization_id"), table_name="organization_memberships")
    op.drop_table("organization_memberships")
    op.drop_index(op.f("ix_organizations_status"), table_name="organizations")
    op.drop_index(op.f("ix_organizations_slug"), table_name="organizations")
    op.drop_index(op.f("ix_organizations_created_by_user_id"), table_name="organizations")
    op.drop_table("organizations")

    for table in ("watchlist_items", "reports", "analysis_requests"):
        op.drop_index(op.f(f"ix_{table}_anonymous_session_id"), table_name=table)
        op.drop_index(op.f(f"ix_{table}_visibility"), table_name=table)
        op.drop_index(op.f(f"ix_{table}_organization_id"), table_name=table)
        op.drop_index(op.f(f"ix_{table}_owner_user_id"), table_name=table)
        with op.batch_alter_table(table) as batch:
            batch.drop_column("deleted_at")
            batch.drop_column("expires_at")
            batch.drop_column("anonymous_session_id")
            batch.drop_column("visibility")
            batch.drop_column("organization_id")
            batch.drop_column("owner_user_id")

    op.drop_index(op.f("ix_users_auth_subject"), table_name="users")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("deleted_at")
        batch.drop_column("last_login_at")
        batch.drop_column("plan")
        batch.drop_column("account_status")
        batch.drop_column("platform_role")
        batch.drop_column("email_verified_at")
        batch.drop_column("auth_subject")
        batch.drop_column("auth_provider")
