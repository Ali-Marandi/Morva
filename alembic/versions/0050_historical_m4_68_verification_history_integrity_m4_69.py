"""Persist M4.69 point-in-time M4.68 verification-history integrity snapshots."""

from alembic import op
import sqlalchemy as sa


revision = "0050_historical_m4_68_verification_history_integrity_m4_69"
down_revision = "0049_independent_m4_66_receipt_verification_persistence_m4_68"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "historical_m4_68_verification_history_integrity_m4_69",
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
            name="uq_m4_69_history_integrity_fingerprint",
        ),
    )
    op.create_index(
        "ix_m4_69_history_integrity_created_at",
        "historical_m4_68_verification_history_integrity_m4_69",
        ["created_at"],
    )
    op.create_index(
        "ix_m4_69_history_integrity_fingerprint",
        "historical_m4_68_verification_history_integrity_m4_69",
        ["fingerprint"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("historical_m4_68_verification_history_integrity_m4_69")
