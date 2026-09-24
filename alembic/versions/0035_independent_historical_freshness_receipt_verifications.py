"""Persist M4.45 independent historical freshness receipt verifications.

Revision ID: 0035_independent_historical_freshness_receipt_verifications
Revises: 0034_historical_freshness_chain_verification_receipts
"""

from alembic import op
import sqlalchemy as sa


revision = "0035_independent_historical_freshness_receipt_verifications"
down_revision = "0034_historical_freshness_chain_verification_receipts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "independent_historical_freshness_receipt_verifications_m4_46",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "receipt_id",
            sa.Uuid(),
            sa.ForeignKey(
                "historical_freshness_chain_verification_receipts_m4_44.id"
            ),
            nullable=False,
        ),
        sa.Column("lineage_id", sa.Uuid(), nullable=False),
        sa.Column("persisted_fingerprint", sa.String(64), nullable=False),
        sa.Column("reconstructed_fingerprint", sa.String(64), nullable=False),
        sa.Column("chain_valid", sa.Boolean(), nullable=False),
        sa.Column("valid", sa.Boolean(), nullable=False),
        sa.Column("blockers_json", sa.Text(), nullable=False),
        sa.Column("verification_fingerprint", sa.String(64), nullable=False),
        sa.Column("recorded_by", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "verification_fingerprint",
            name="uq_m4_46_independent_verification_fingerprint",
        ),
    )
    op.create_index(
        "ix_m4_46_independent_receipt_id",
        "independent_historical_freshness_receipt_verifications_m4_46",
        ["receipt_id"],
    )
    op.create_index(
        "ix_m4_46_independent_lineage_id",
        "independent_historical_freshness_receipt_verifications_m4_46",
        ["lineage_id"],
    )
    op.create_index(
        "ix_m4_46_independent_valid",
        "independent_historical_freshness_receipt_verifications_m4_46",
        ["valid"],
    )
    op.create_index(
        "ix_m4_46_independent_created_at",
        "independent_historical_freshness_receipt_verifications_m4_46",
        ["created_at"],
    )
    op.create_index(
        "ix_m4_46_independent_verification_fingerprint",
        "independent_historical_freshness_receipt_verifications_m4_46",
        ["verification_fingerprint"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("independent_historical_freshness_receipt_verifications_m4_46")
