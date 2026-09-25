"""Persist M4.53 point-in-time M4.52 receipt-history integrity snapshots.

Revision ID: 0040_historical_m4_52_verification_receipt_history_integrity
Revises: 0039_independent_receipt_history_verification_m4_52
"""

from alembic import op
import sqlalchemy as sa


revision = "0040_historical_m4_52_verification_receipt_history_integrity"
down_revision = "0039_independent_receipt_history_verification_m4_52"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "historical_m4_52_receipt_history_integrity_m4_53",
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
            name="uq_m4_53_history_integrity_fingerprint",
        ),
    )
    op.create_index(
        "ix_m4_53_history_integrity_created_at",
        "historical_m4_52_receipt_history_integrity_m4_53",
        ["created_at"],
    )
    op.create_index(
        "ix_m4_53_history_integrity_fingerprint",
        "historical_m4_52_receipt_history_integrity_m4_53",
        ["fingerprint"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("historical_m4_52_receipt_history_integrity_m4_53")
