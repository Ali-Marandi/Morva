"""Persist M4.55 independent M4.54 receipt-history verification results.

Revision ID: 0041_independent_m4_53_verification_receipts_m4_55
Revises: 0040_historical_m4_52_verification_receipt_history_integrity
"""

from alembic import op
import sqlalchemy as sa


revision = "0041_independent_m4_53_verification_receipts_m4_55"
down_revision = "0040_historical_m4_52_verification_receipt_history_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "independent_m4_53_verification_receipts_m4_55",
        sa.Column(
            "id",
            sa.Uuid(),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "snapshot_id",
            sa.Uuid(),
            sa.ForeignKey(
                "historical_m4_52_receipt_history_integrity_m4_53.id"
            ),
            nullable=False,
        ),
        sa.Column("persisted_fingerprint", sa.String(64), nullable=False),
        sa.Column("reconstructed_fingerprint", sa.String(64), nullable=False),
        sa.Column("persisted_history_fingerprint", sa.String(64), nullable=False),
        sa.Column("reconstructed_history_fingerprint", sa.String(64), nullable=False),
        sa.Column("persisted_record_count", sa.Integer(), nullable=False),
        sa.Column("reconstructed_record_count", sa.Integer(), nullable=False),
        sa.Column("persisted_valid_count", sa.Integer(), nullable=False),
        sa.Column("reconstructed_valid_count", sa.Integer(), nullable=False),
        sa.Column("valid", sa.Boolean(), nullable=False),
        sa.Column("blockers_json", sa.Text(), nullable=False),
        sa.Column("verification_fingerprint", sa.String(64), nullable=False),
        sa.Column("recorded_by", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_m4_55_snapshot_id",
        "independent_m4_53_verification_receipts_m4_55",
        ["snapshot_id"],
    )
    op.create_index(
        "ix_m4_55_valid",
        "independent_m4_53_verification_receipts_m4_55",
        ["valid"],
    )
    op.create_index(
        "ix_m4_55_created_at",
        "independent_m4_53_verification_receipts_m4_55",
        ["created_at"],
    )
    op.create_index(
        "ix_m4_55_verification_fingerprint",
        "independent_m4_53_verification_receipts_m4_55",
        ["verification_fingerprint"],
        unique=True,
    )
    op.create_index(
        "ix_m4_55_recorded_by",
        "independent_m4_53_verification_receipts_m4_55",
        ["recorded_by"],
    )


def downgrade() -> None:
    op.drop_table("independent_m4_53_verification_receipts_m4_55")
