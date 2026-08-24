"""add organization invitations

Revision ID: 20260824_0028
Revises: 20260821_0026
"""
from alembic import op
import sqlalchemy as sa

revision = "20260824_0028"
down_revision = "20260821_0026"
branch_labels = None
depends_on = None

def upgrade() -> None:
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

def downgrade() -> None:
    op.drop_index("ix_organization_invitations_org_status", table_name="organization_invitations")
    op.drop_table("organization_invitations")
