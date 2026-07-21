"""harden identity ownership schema

Revision ID: 20260721_0010
Revises: 20260721_0009
Create Date: 2026-07-21
"""

from alembic import op
import sqlalchemy as sa


revision = "20260721_0010"
down_revision = "20260721_0009"
branch_labels = None
depends_on = None


RESOURCE_TABLES = ("analysis_requests", "reports", "watchlist_items")


def _detach_invalid_nullable_links() -> None:
    """Preserve legacy resources while making nullable links referentially valid."""
    for table in RESOURCE_TABLES:
        op.execute(
            sa.text(
                f"UPDATE {table} SET owner_user_id = NULL "
                "WHERE owner_user_id IS NOT NULL "
                "AND NOT EXISTS (SELECT 1 FROM users WHERE users.id = "
                f"{table}.owner_user_id)"
            )
        )
        op.execute(
            sa.text(
                f"UPDATE {table} SET organization_id = NULL "
                "WHERE organization_id IS NOT NULL "
                "AND NOT EXISTS (SELECT 1 FROM organizations WHERE organizations.id = "
                f"{table}.organization_id)"
            )
        )
        op.execute(
            sa.text(
                f"UPDATE {table} SET anonymous_session_id = NULL "
                "WHERE anonymous_session_id IS NOT NULL "
                "AND NOT EXISTS (SELECT 1 FROM anonymous_sessions WHERE anonymous_sessions.id = "
                f"{table}.anonymous_session_id)"
            )
        )

    op.execute(
        sa.text(
            "UPDATE saved_theses SET organization_id = NULL "
            "WHERE organization_id IS NOT NULL "
            "AND NOT EXISTS (SELECT 1 FROM organizations "
            "WHERE organizations.id = saved_theses.organization_id)"
        )
    )


def _assert_required_links_are_valid() -> None:
    checks = (
        ("saved_theses", "owner_user_id", "users"),
        ("consent_records", "user_id", "users"),
    )
    bind = op.get_bind()
    for table, column, target in checks:
        invalid_count = bind.execute(
            sa.text(
                f"SELECT COUNT(*) FROM {table} "
                f"WHERE NOT EXISTS (SELECT 1 FROM {target} "
                f"WHERE {target}.id = {table}.{column})"
            )
        ).scalar_one()
        if invalid_count:
            raise RuntimeError(
                f"Cannot add {table}.{column} foreign key: {invalid_count} invalid legacy reference(s)."
            )


def upgrade() -> None:
    _detach_invalid_nullable_links()
    _assert_required_links_are_valid()

    for table in RESOURCE_TABLES:
        with op.batch_alter_table(table) as batch:
            batch.create_foreign_key(
                f"fk_{table}_owner_user_id_users",
                "users",
                ["owner_user_id"],
                ["id"],
                ondelete="SET NULL",
            )
            batch.create_foreign_key(
                f"fk_{table}_organization_id_organizations",
                "organizations",
                ["organization_id"],
                ["id"],
                ondelete="SET NULL",
            )
            batch.create_foreign_key(
                f"fk_{table}_anonymous_session_id_anonymous_sessions",
                "anonymous_sessions",
                ["anonymous_session_id"],
                ["id"],
                ondelete="SET NULL",
            )
        op.create_index(f"ix_{table}_owner_deleted", table, ["owner_user_id", "deleted_at"])
        op.create_index(
            f"ix_{table}_org_visibility_deleted",
            table,
            ["organization_id", "visibility", "deleted_at"],
        )
        op.create_index(
            f"ix_{table}_anonymous_expires", table, ["anonymous_session_id", "expires_at"]
        )

    with op.batch_alter_table("saved_theses") as batch:
        batch.create_foreign_key(
            "fk_saved_theses_owner_user_id_users",
            "users",
            ["owner_user_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_foreign_key(
            "fk_saved_theses_organization_id_organizations",
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index("ix_saved_theses_owner_deleted", "saved_theses", ["owner_user_id", "deleted_at"])
    op.create_index(
        "ix_saved_theses_org_visibility_deleted",
        "saved_theses",
        ["organization_id", "visibility", "deleted_at"],
    )

    with op.batch_alter_table("consent_records") as batch:
        batch.create_foreign_key(
            "fk_consent_records_user_id_users",
            "users",
            ["user_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    op.create_index(
        "ix_organization_memberships_user_org_status",
        "organization_memberships",
        ["user_id", "organization_id", "status"],
    )
    op.create_index(
        "ix_usage_quotas_subject_action_period_end",
        "usage_quotas",
        ["subject_type", "subject_id", "action", "period_end"],
    )


def downgrade() -> None:
    op.drop_index("ix_usage_quotas_subject_action_period_end", table_name="usage_quotas")
    op.drop_index(
        "ix_organization_memberships_user_org_status", table_name="organization_memberships"
    )

    with op.batch_alter_table("consent_records") as batch:
        batch.drop_constraint("fk_consent_records_user_id_users", type_="foreignkey")

    op.drop_index("ix_saved_theses_org_visibility_deleted", table_name="saved_theses")
    op.drop_index("ix_saved_theses_owner_deleted", table_name="saved_theses")
    with op.batch_alter_table("saved_theses") as batch:
        batch.drop_constraint("fk_saved_theses_organization_id_organizations", type_="foreignkey")
        batch.drop_constraint("fk_saved_theses_owner_user_id_users", type_="foreignkey")

    for table in RESOURCE_TABLES:
        op.drop_index(f"ix_{table}_anonymous_expires", table_name=table)
        op.drop_index(f"ix_{table}_org_visibility_deleted", table_name=table)
        op.drop_index(f"ix_{table}_owner_deleted", table_name=table)
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(
                f"fk_{table}_anonymous_session_id_anonymous_sessions", type_="foreignkey"
            )
            batch.drop_constraint(
                f"fk_{table}_organization_id_organizations", type_="foreignkey"
            )
            batch.drop_constraint(f"fk_{table}_owner_user_id_users", type_="foreignkey")
