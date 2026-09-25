"""Persist M4.66 independent M4.65 verification results."""

from alembic import op
import sqlalchemy as sa


revision = "0048_independent_m4_64_verification_receipts_m4_66"
down_revision = "0047_historical_m4_63_receipt_history_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "independent_m4_64_verification_receipts_m4_66",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "snapshot_id",
            sa.Uuid(),
            sa.ForeignKey("historical_m4_63_receipt_history_integrity_m4_64.id"),
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
        sa.UniqueConstraint(
            "verification_fingerprint",
            name="uq_m4_66_verification_fingerprint",
        ),
    )
    op.create_index(
        "ix_m4_66_snapshot_id",
        "independent_m4_64_verification_receipts_m4_66",
        ["snapshot_id"],
    )
    op.create_index(
        "ix_m4_66_valid",
        "independent_m4_64_verification_receipts_m4_66",
        ["valid"],
    )
    op.create_index(
        "ix_m4_66_created_at",
        "independent_m4_64_verification_receipts_m4_66",
        ["created_at"],
    )
    op.create_index(
        "ix_m4_66_verification_fingerprint",
        "independent_m4_64_verification_receipts_m4_66",
        ["verification_fingerprint"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("independent_m4_64_verification_receipts_m4_66")
