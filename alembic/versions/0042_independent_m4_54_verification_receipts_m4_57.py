"""Persist M4.57 independent verification results."""

from alembic import op
import sqlalchemy as sa


revision = "0042_independent_m4_54_verification_receipts_m4_57"
down_revision = "0041_independent_m4_53_verification_receipts_m4_55"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "independent_m4_54_verification_receipts_m4_57",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "receipt_id",
            sa.Uuid(),
            sa.ForeignKey("independent_m4_53_verification_receipts_m4_55.id"),
            nullable=False,
        ),
        sa.Column("persisted_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("reconstructed_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("persisted_verification_fingerprint", sa.String(64), nullable=False),
        sa.Column("reconstructed_verification_fingerprint", sa.String(64), nullable=False),
        sa.Column("valid", sa.Boolean(), nullable=False),
        sa.Column("blockers_json", sa.Text(), nullable=False),
        sa.Column("verification_fingerprint", sa.String(64), nullable=False),
        sa.Column("recorded_by", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_m4_57_receipt_id",
        "independent_m4_54_verification_receipts_m4_57",
        ["receipt_id"],
    )
    op.create_index(
        "ix_m4_57_valid",
        "independent_m4_54_verification_receipts_m4_57",
        ["valid"],
    )
    op.create_index(
        "ix_m4_57_created_at",
        "independent_m4_54_verification_receipts_m4_57",
        ["created_at"],
    )
    op.create_index(
        "ix_m4_57_verification_fingerprint",
        "independent_m4_54_verification_receipts_m4_57",
        ["verification_fingerprint"],
        unique=True,
    )
    op.create_index(
        "ix_m4_57_recorded_by",
        "independent_m4_54_verification_receipts_m4_57",
        ["recorded_by"],
    )


def downgrade() -> None:
    op.drop_table("independent_m4_54_verification_receipts_m4_57")
