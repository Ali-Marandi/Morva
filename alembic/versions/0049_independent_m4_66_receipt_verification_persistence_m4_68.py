"""Persist M4.67 independent M4.66 receipt-verification results."""

from alembic import op
import sqlalchemy as sa


revision = "0049_independent_m4_66_receipt_verification_persistence_m4_68"
down_revision = "0048_independent_m4_64_verification_receipts_m4_66"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "independent_m4_66_verification_results_m4_68",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "verification_receipt_id",
            sa.Uuid(),
            sa.ForeignKey("independent_m4_64_verification_receipts_m4_66.id"),
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
        sa.UniqueConstraint(
            "verification_fingerprint",
            name="uq_m4_68_verification_fingerprint",
        ),
    )
    op.create_index(
        "ix_m4_68_receipt_id",
        "independent_m4_66_verification_results_m4_68",
        ["verification_receipt_id"],
    )
    op.create_index(
        "ix_m4_68_valid",
        "independent_m4_66_verification_results_m4_68",
        ["valid"],
    )
    op.create_index(
        "ix_m4_68_created_at",
        "independent_m4_66_verification_results_m4_68",
        ["created_at"],
    )
    op.create_index(
        "ix_m4_68_verification_fingerprint",
        "independent_m4_66_verification_results_m4_68",
        ["verification_fingerprint"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("independent_m4_66_verification_results_m4_68")
