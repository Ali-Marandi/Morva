"""Persist M4.64 point-in-time M4.63 receipt-history integrity snapshots.

Revision ID: 0047_historical_m4_63_receipt_history_integrity
Revises: 0046_independent_m4_61_verification_receipts_m4_63
"""

from alembic import op
import sqlalchemy as sa


revision = "0047_historical_m4_63_receipt_history_integrity"
down_revision = "0046_independent_m4_61_verification_receipts_m4_63"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "historical_m4_63_receipt_history_integrity_m4_64",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("integrity_version", sa.Integer(), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("valid_count", sa.Integer(), nullable=False),
        sa.Column("history_fingerprint", sa.String(64), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("captured_by", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "fingerprint",
            name="uq_m4_64_history_integrity_fingerprint",
        ),
    )
    op.create_index(
        "ix_m4_64_history_created_at",
        "historical_m4_63_receipt_history_integrity_m4_64",
        ["created_at"],
    )
    op.create_index(
        "ix_m4_64_history_fingerprint",
        "historical_m4_63_receipt_history_integrity_m4_64",
        ["fingerprint"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("historical_m4_63_receipt_history_integrity_m4_64")
