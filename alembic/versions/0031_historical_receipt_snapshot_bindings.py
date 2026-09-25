"""Bind registry-bound freshness receipts to historical registry snapshots.

Revision ID: 0031_historical_receipt_snapshot_bindings
Revises: 0030_readiness_freshness_policy_registry_snapshots
"""

from alembic import op
import sqlalchemy as sa


revision = "0031_historical_receipt_snapshot_bindings"
down_revision = "0030_readiness_freshness_policy_registry_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "historical_registry_bound_freshness_receipt_bindings",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "receipt_id",
            sa.Uuid(),
            sa.ForeignKey(
                "registry_bound_policy_readiness_freshness_receipts.id"
            ),
            nullable=False,
        ),
        sa.Column(
            "snapshot_id",
            sa.Uuid(),
            sa.ForeignKey(
                "readiness_freshness_policy_registry_snapshots.id"
            ),
            nullable=False,
        ),
        sa.Column("receipt_binding_fingerprint", sa.String(64), nullable=False),
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
            "receipt_id",
            name="uq_historical_receipt_snapshot_binding_receipt_id",
        ),
        sa.UniqueConstraint(
            "fingerprint",
            name="uq_historical_receipt_snapshot_binding_fingerprint",
        ),
    )
    op.create_index(
        "ix_historical_receipt_binding_snapshot_id",
        "historical_registry_bound_freshness_receipt_bindings",
        ["snapshot_id"],
    )
    op.create_index(
        "ix_historical_receipt_binding_registry_fingerprint",
        "historical_registry_bound_freshness_receipt_bindings",
        ["registry_fingerprint"],
    )
    op.create_index(
        "ix_historical_receipt_binding_policy_fingerprint",
        "historical_registry_bound_freshness_receipt_bindings",
        ["policy_fingerprint"],
    )


def downgrade() -> None:
    op.drop_table("historical_registry_bound_freshness_receipt_bindings")
