"""Persist M4.47 historical verification history integrity snapshots.

Revision ID: 0036_historical_freshness_verification_history_integrity
Revises: 0035_independent_historical_freshness_receipt_verifications
"""

from alembic import op
import sqlalchemy as sa


revision = "0036_historical_freshness_verification_history_integrity"
down_revision = "0035_independent_historical_freshness_receipt_verifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "historical_freshness_verification_history_integrity_m4_47",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("integrity_version", sa.Integer(), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("valid_count", sa.Integer(), nullable=False),
        sa.Column("chain_valid_count", sa.Integer(), nullable=False),
        sa.Column("history_fingerprint", sa.String(64), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("captured_by", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "fingerprint",
            name="uq_m4_47_history_integrity_fingerprint",
        ),
    )
    op.create_index(
        "ix_m4_47_history_integrity_created_at",
        "historical_freshness_verification_history_integrity_m4_47",
        ["created_at"],
    )
    op.create_index(
        "ix_m4_47_history_integrity_fingerprint",
        "historical_freshness_verification_history_integrity_m4_47",
        ["fingerprint"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("historical_freshness_verification_history_integrity_m4_47")
