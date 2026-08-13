"""add consent-aware first-party product analytics

Revision ID: 20260731_0023
Revises: 20260728_0022
Create Date: 2026-07-31
"""

from alembic import op
import sqlalchemy as sa


revision = "20260731_0023"
down_revision = "20260728_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "privacy_preference_decisions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("purpose", sa.String(length=64), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("policy_version", sa.String(length=32), nullable=False),
        sa.Column("previous_decision_id", sa.String(length=64), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "decision IN ('grant', 'deny', 'withdraw')",
            name="ck_privacy_preference_decisions_decision",
        ),
        sa.CheckConstraint(
            "purpose = 'product_improvement'",
            name="ck_privacy_preference_decisions_purpose",
        ),
        sa.CheckConstraint(
            "source IN ('account_ui')",
            name="ck_privacy_preference_decisions_source",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["previous_decision_id"],
            ["privacy_preference_decisions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "purpose",
            "idempotency_key",
            name="uq_privacy_preference_decisions_idempotency",
        ),
    )
    op.create_index(
        "ix_privacy_preference_decisions_user_id",
        "privacy_preference_decisions",
        ["user_id"],
    )
    op.create_index(
        "ix_privacy_preference_decisions_purpose",
        "privacy_preference_decisions",
        ["purpose"],
    )
    op.create_index(
        "ix_privacy_preference_decisions_user_purpose_occurred",
        "privacy_preference_decisions",
        ["user_id", "purpose", "occurred_at"],
    )

    op.create_table(
        "privacy_preferences",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("purpose", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("policy_version", sa.String(length=32), nullable=False),
        sa.Column("latest_decision_id", sa.String(length=64), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "purpose = 'product_improvement'",
            name="ck_privacy_preferences_purpose",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["latest_decision_id"],
            ["privacy_preference_decisions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "purpose", name="uq_privacy_preferences_user_purpose"),
    )
    op.create_index("ix_privacy_preferences_user_id", "privacy_preferences", ["user_id"])
    op.create_index("ix_privacy_preferences_purpose", "privacy_preferences", ["purpose"])
    op.create_index(
        "ix_privacy_preferences_user_enabled",
        "privacy_preferences",
        ["user_id", "enabled"],
    )

    op.create_table(
        "product_analytics_events",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("event_name", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("purpose", sa.String(length=64), nullable=False),
        sa.Column("owner_user_id", sa.String(length=64), nullable=False),
        sa.Column("actor_class", sa.String(length=32), nullable=False),
        sa.Column("dimensions_json", sa.JSON(), nullable=False),
        sa.Column("event_key", sa.String(length=128), nullable=False),
        sa.Column("policy_version", sa.String(length=32), nullable=False),
        sa.Column("decision_id", sa.String(length=64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "event_name IN ('analysis_completed', 'analysis_failed', 'thesis_saved', 'watchlist_created')",
            name="ck_product_analytics_events_name",
        ),
        sa.CheckConstraint(
            "purpose = 'product_improvement'",
            name="ck_product_analytics_events_purpose",
        ),
        sa.CheckConstraint(
            "actor_class IN ('authenticated', 'organization_context')",
            name="ck_product_analytics_events_actor_class",
        ),
        sa.CheckConstraint("schema_version > 0", name="ck_product_analytics_events_schema_version"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["decision_id"],
            ["privacy_preference_decisions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_key", name="uq_product_analytics_events_event_key"),
    )
    op.create_index("ix_product_analytics_events_event_name", "product_analytics_events", ["event_name"])
    op.create_index("ix_product_analytics_events_purpose", "product_analytics_events", ["purpose"])
    op.create_index("ix_product_analytics_events_owner_user_id", "product_analytics_events", ["owner_user_id"])
    op.create_index(
        "ix_product_analytics_events_name_occurred",
        "product_analytics_events",
        ["event_name", "occurred_at"],
    )
    op.create_index(
        "ix_product_analytics_events_owner_occurred",
        "product_analytics_events",
        ["owner_user_id", "occurred_at"],
    )
    op.create_index(
        "ix_product_analytics_events_expiry",
        "product_analytics_events",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_product_analytics_events_expiry", table_name="product_analytics_events")
    op.drop_index("ix_product_analytics_events_owner_occurred", table_name="product_analytics_events")
    op.drop_index("ix_product_analytics_events_name_occurred", table_name="product_analytics_events")
    op.drop_index("ix_product_analytics_events_owner_user_id", table_name="product_analytics_events")
    op.drop_index("ix_product_analytics_events_purpose", table_name="product_analytics_events")
    op.drop_index("ix_product_analytics_events_event_name", table_name="product_analytics_events")
    op.drop_table("product_analytics_events")

    op.drop_index("ix_privacy_preferences_user_enabled", table_name="privacy_preferences")
    op.drop_index("ix_privacy_preferences_purpose", table_name="privacy_preferences")
    op.drop_index("ix_privacy_preferences_user_id", table_name="privacy_preferences")
    op.drop_table("privacy_preferences")

    op.drop_index(
        "ix_privacy_preference_decisions_user_purpose_occurred",
        table_name="privacy_preference_decisions",
    )
    op.drop_index("ix_privacy_preference_decisions_purpose", table_name="privacy_preference_decisions")
    op.drop_index("ix_privacy_preference_decisions_user_id", table_name="privacy_preference_decisions")
    op.drop_table("privacy_preference_decisions")
