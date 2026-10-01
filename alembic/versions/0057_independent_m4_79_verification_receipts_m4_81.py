"""Persist M4.80 independent M4.79 verification results."""

from alembic import op
import sqlalchemy as sa


revision = "0057_independent_m4_79_verification_receipts_m4_81"
down_revision = "0056_independent_m4_77_verification_receipts_m4_79"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "independent_m4_79_verification_receipts_m4_81",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "verification_receipt_id",
            sa.Uuid(),
            sa.ForeignKey("independent_m4_77_verification_receipts_m4_79.id"),
            nullable=False,
        ),
        sa.Column("persisted_fingerprint", sa.String(64), nullable=False),
        sa.Column("reconstructed_fingerprint", sa.String(64), nullable=False),
        sa.Column("persisted_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("reconstructed_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("persisted_valid", sa.Boolean(), nullable=False),
        sa.Column("reconstructed_valid", sa.Boolean(), nullable=False),
        sa.Column("valid", sa.Boolean(), nullable=False),
        sa.Column("blockers_json", sa.Text(), nullable=False),
        sa.Column("verification_fingerprint", sa.String(64), nullable=False),
        sa.Column("recorded_by", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "verification_fingerprint",
            name="uq_m4_81_verification_fingerprint",
        ),
    )
    op.create_index(
        "ix_m4_81_verification_receipt_id",
        "independent_m4_79_verification_receipts_m4_81",
        ["verification_receipt_id"],
    )
    op.create_index(
        "ix_m4_81_verification_valid",
        "independent_m4_79_verification_receipts_m4_81",
        ["valid"],
    )
    op.create_index(
        "ix_m4_81_verification_created_at",
        "independent_m4_79_verification_receipts_m4_81",
        ["created_at"],
    )
    op.create_index(
        "ix_m4_81_verification_fingerprint",
        "independent_m4_79_verification_receipts_m4_81",
        ["verification_fingerprint"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("independent_m4_79_verification_receipts_m4_81")
