"""add organization invitations

Revision ID: 20260824_0028
Revises: 20260821_0026
"""
from alembic import op
import sqlalchemy as sa
from datetime import UTC, datetime

revision = "20260824_0028"
down_revision = "20260821_0026"
branch_labels = None
depends_on = None

def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.drop_constraint("ck_entitlement_assignments_user_only", "entitlement_assignments", type_="check")
        op.drop_constraint("entitlement_assignments_subject_id_fkey", "entitlement_assignments", type_="foreignkey")
        op.create_check_constraint("ck_entitlement_assignments_subject_type", "entitlement_assignments", "subject_type IN ('user', 'organization')")
    op.create_table("organization_invitations",
        sa.Column("id", sa.String(64), primary_key=True), sa.Column("organization_id", sa.String(64), nullable=False),
        sa.Column("destination_email", sa.String(255), nullable=False), sa.Column("role", sa.String(16), nullable=False),
        sa.Column("invited_by_user_id", sa.String(64), nullable=False), sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("status", sa.String(16), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True)), sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("supersedes_id", sa.String(64)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('admin', 'member', 'viewer')", name="ck_organization_invitations_role"),
        sa.CheckConstraint("status IN ('pending', 'accepted', 'revoked', 'expired', 'superseded')", name="ck_organization_invitations_status"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"]), sa.ForeignKeyConstraint(["supersedes_id"], ["organization_invitations.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("token_hash", name="uq_organization_invitations_token_hash"))
    op.create_index("ix_organization_invitations_org_status", "organization_invitations", ["organization_id", "status", "expires_at"])
    timestamp = datetime(2026, 8, 24, tzinfo=UTC)
    op.bulk_insert(sa.table("plan_versions", sa.column("id", sa.String), sa.column("plan_key", sa.String), sa.column("version", sa.Integer), sa.column("status", sa.String), sa.column("effective_from", sa.DateTime(timezone=True)), sa.column("created_at", sa.DateTime(timezone=True))), [{"id": "plan_portfolio_org_v1", "plan_key": "portfolio-org-v1", "version": 1, "status": "active", "effective_from": timestamp, "created_at": timestamp}])
    op.bulk_insert(sa.table("plan_entitlements", sa.column("id", sa.String), sa.column("plan_version_id", sa.String), sa.column("entitlement_key", sa.String), sa.column("hard_limit", sa.Integer), sa.column("created_at", sa.DateTime(timezone=True))), [{"id": "ent_portfolio_org_seats", "plan_version_id": "plan_portfolio_org_v1", "entitlement_key": "limit.organization.seats.count", "hard_limit": 5, "created_at": timestamp}])

def downgrade() -> None:
    op.execute("DELETE FROM entitlement_assignments WHERE subject_type = 'organization'")
    op.execute("DELETE FROM plan_entitlements WHERE plan_version_id = 'plan_portfolio_org_v1'")
    op.execute("DELETE FROM plan_versions WHERE id = 'plan_portfolio_org_v1'")
    op.drop_index("ix_organization_invitations_org_status", table_name="organization_invitations")
    op.drop_table("organization_invitations")
    if op.get_bind().dialect.name == "postgresql":
        op.drop_constraint("ck_entitlement_assignments_subject_type", "entitlement_assignments", type_="check")
        op.create_foreign_key("entitlement_assignments_subject_id_fkey", "entitlement_assignments", "users", ["subject_id"], ["id"], ondelete="CASCADE")
        op.create_check_constraint("ck_entitlement_assignments_user_only", "entitlement_assignments", "subject_type = 'user'")
