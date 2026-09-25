"""Persist M4.50 historical M4.49 receipt-history integrity snapshots.

Revision ID: 0038_historical_independent_verification_receipt_history_integrity
Revises: 0037_independent_historical_freshness_verification_history_integrity_receipts
"""

from alembic import op
import sqlalchemy as sa


revision = "0038_historical_independent_verification_receipt_history_integrity"
down_revision = "0037_independent_historical_freshness_verification_history_integrity_receipts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "historical_independent_verification_receipt_history_m4_50",
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
            name="uq_m4_50_history_integrity_fingerprint",
        ),
    )
    op.create_index(
        "ix_m4_50_history_integrity_created_at",
        "historical_independent_verification_receipt_history_m4_50",
        ["created_at"],
    )
    op.create_index(
        "ix_m4_50_history_integrity_fingerprint",
        "historical_independent_verification_receipt_history_m4_50",
        ["fingerprint"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("historical_independent_verification_receipt_history_m4_50")
