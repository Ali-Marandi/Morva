"""Persist historical freshness-policy registry snapshot anchors.

Revision ID: 0030_readiness_freshness_policy_registry_snapshots
Revises: 0029_registry_bound_freshness_receipts
"""

from alembic import op
import sqlalchemy as sa


revision = "0030_readiness_freshness_policy_registry_snapshots"
down_revision = "0029_registry_bound_freshness_receipts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "readiness_freshness_policy_registry_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("snapshot_version", sa.Integer(), nullable=False),
        sa.Column("integrity_version", sa.Integer(), nullable=False),
        sa.Column("policy_count", sa.Integer(), nullable=False),
        sa.Column("registry_fingerprint", sa.String(64), nullable=False),
        sa.Column("member_record_ids", sa.JSON(), nullable=False),
        sa.Column("membership_fingerprint", sa.String(64), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("captured_by", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "fingerprint",
            name="uq_readiness_freshness_registry_snapshot_fingerprint",
        ),
    )
    op.create_index(
        "ix_readiness_freshness_registry_snapshot_registry_fingerprint",
        "readiness_freshness_policy_registry_snapshots",
        ["registry_fingerprint"],
    )
    op.create_index(
        "ix_readiness_freshness_registry_snapshot_captured_by",
        "readiness_freshness_policy_registry_snapshots",
        ["captured_by"],
    )


def downgrade() -> None:
    op.drop_table("readiness_freshness_policy_registry_snapshots")
