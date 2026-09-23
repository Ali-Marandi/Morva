"""Persist M4.41 historical snapshot-bound freshness receipt lineage.

Revision ID: 0033_historical_snapshot_freshness_receipt_lineage
Revises: 0032_historical_snapshot_bound_freshness_receipts
"""

from alembic import op
import sqlalchemy as sa


revision = "0033_historical_snapshot_freshness_receipt_lineage"
down_revision = "0032_historical_snapshot_bound_freshness_receipts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "historical_snapshot_freshness_receipt_lineages_m4_41",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "freshness_receipt_id",
            sa.Uuid(),
            sa.ForeignKey(
                "historical_snapshot_bound_policy_readiness_freshness_receipts.id"
            ),
            nullable=False,
        ),
        sa.Column(
            "historical_binding_id",
            sa.Uuid(),
            sa.ForeignKey(
                "historical_registry_bound_freshness_receipt_bindings.id"
            ),
            nullable=False,
        ),
        sa.Column(
            "snapshot_id",
            sa.Uuid(),
            sa.ForeignKey("readiness_freshness_policy_registry_snapshots.id"),
            nullable=False,
        ),
        sa.Column("freshness_receipt_fingerprint", sa.String(64), nullable=False),
        sa.Column("historical_binding_fingerprint", sa.String(64), nullable=False),
        sa.Column("snapshot_fingerprint", sa.String(64), nullable=False),
        sa.Column("registry_integrity_version", sa.Integer(), nullable=False),
        sa.Column("registry_policy_count", sa.Integer(), nullable=False),
        sa.Column("registry_fingerprint", sa.String(64), nullable=False),
        sa.Column("policy_id", sa.String(100), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("policy_fingerprint", sa.String(64), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("bound_by", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "freshness_receipt_id",
            name="uq_m4_41_lineage_freshness_receipt_id",
        ),
        sa.UniqueConstraint(
            "fingerprint",
            name="uq_m4_41_lineage_fingerprint",
        ),
    )
    op.create_index(
        "ix_m4_41_lineage_historical_binding_id",
        "historical_snapshot_freshness_receipt_lineages_m4_41",
        ["historical_binding_id"],
    )
    op.create_index(
        "ix_m4_41_lineage_snapshot_id",
        "historical_snapshot_freshness_receipt_lineages_m4_41",
        ["snapshot_id"],
    )
    op.create_index(
        "ix_m4_41_lineage_snapshot_fingerprint",
        "historical_snapshot_freshness_receipt_lineages_m4_41",
        ["snapshot_fingerprint"],
    )
    op.create_index(
        "ix_m4_41_lineage_policy_fingerprint",
        "historical_snapshot_freshness_receipt_lineages_m4_41",
        ["policy_fingerprint"],
    )


def downgrade() -> None:
    op.drop_table("historical_snapshot_freshness_receipt_lineages_m4_41")
