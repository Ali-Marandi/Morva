"""Persist M4.44 historical freshness chain verification receipts.

Revision ID: 0034_historical_freshness_chain_verification_receipts
Revises: 0033_historical_snapshot_freshness_receipt_lineage
"""

from alembic import op
import sqlalchemy as sa


revision = "0034_historical_freshness_chain_verification_receipts"
down_revision = "0033_historical_snapshot_freshness_receipt_lineage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "historical_freshness_chain_verification_receipts_m4_44",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "lineage_id",
            sa.Uuid(),
            sa.ForeignKey("historical_snapshot_freshness_receipt_lineages_m4_41.id"),
            nullable=False,
        ),
        sa.Column("freshness_receipt_id", sa.Uuid(), nullable=False),
        sa.Column("historical_binding_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("lineage_fingerprint", sa.String(64), nullable=False),
        sa.Column("freshness_receipt_fingerprint", sa.String(64), nullable=False),
        sa.Column("historical_binding_fingerprint", sa.String(64), nullable=False),
        sa.Column("snapshot_fingerprint", sa.String(64), nullable=False),
        sa.Column("policy_id", sa.String(100), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("policy_fingerprint", sa.String(64), nullable=False),
        sa.Column("registry_integrity_version", sa.Integer(), nullable=False),
        sa.Column("registry_policy_count", sa.Integer(), nullable=False),
        sa.Column("registry_fingerprint", sa.String(64), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("blockers_json", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("recorded_by", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("fingerprint", name="uq_m4_44_verification_fingerprint"),
    )
    op.create_index(
        "ix_m4_44_verification_lineage_id",
        "historical_freshness_chain_verification_receipts_m4_44",
        ["lineage_id"],
    )
    op.create_index(
        "ix_m4_44_verification_state",
        "historical_freshness_chain_verification_receipts_m4_44",
        ["state"],
    )
    op.create_index(
        "ix_m4_44_verification_created_at",
        "historical_freshness_chain_verification_receipts_m4_44",
        ["created_at"],
    )
    op.create_index(
        "ix_m4_44_verification_fingerprint",
        "historical_freshness_chain_verification_receipts_m4_44",
        ["fingerprint"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("historical_freshness_chain_verification_receipts_m4_44")
