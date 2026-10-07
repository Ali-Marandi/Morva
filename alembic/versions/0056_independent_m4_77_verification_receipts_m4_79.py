"""Persist M4.78 independent-verification results as M4.79 receipts."""

from alembic import op
import sqlalchemy as sa


revision = "0056_independent_m4_77_verification_receipts_m4_79"
down_revision = "0055_independent_m4_75_verification_receipts_m4_77"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "independent_m4_77_verification_receipts_m4_79",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "verification_receipt_id",
            sa.Uuid(),
            sa.ForeignKey(
                "independent_historical_m4_75_verification_receipts_m4_77.id"
            ),
            nullable=False,
        ),
        sa.Column(
            "persisted_snapshot_id",
            sa.Uuid(),
            sa.ForeignKey(
                "historical_m4_74_verification_receipt_history_integrity_m4_75.id"
            ),
            nullable=False,
        ),
        sa.Column("reconstructed_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column(
            "persisted_verification_fingerprint", sa.String(64), nullable=False
        ),
        sa.Column(
            "reconstructed_verification_fingerprint", sa.String(64), nullable=False
        ),
        sa.Column("persisted_valid", sa.Boolean(), nullable=False),
        sa.Column("reconstructed_valid", sa.Boolean(), nullable=False),
        sa.Column("persisted_blockers_json", sa.Text(), nullable=False),
        sa.Column("reconstructed_blockers_json", sa.Text(), nullable=False),
        sa.Column("valid", sa.Boolean(), nullable=False),
        sa.Column("blockers_json", sa.Text(), nullable=False),
        sa.Column("verification_fingerprint", sa.String(64), nullable=False),
        sa.Column("recorded_by", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "verification_fingerprint",
            name="uq_m4_79_verification_fingerprint",
        ),
    )
    op.create_index(
        "ix_m4_79_verification_receipt_id",
        "independent_m4_77_verification_receipts_m4_79",
        ["verification_receipt_id"],
    )
    op.create_index(
        "ix_m4_79_verification_snapshot_id",
        "independent_m4_77_verification_receipts_m4_79",
        ["persisted_snapshot_id"],
    )
    op.create_index(
        "ix_m4_79_verification_valid",
        "independent_m4_77_verification_receipts_m4_79",
        ["valid"],
    )
    op.create_index(
        "ix_m4_79_verification_created_at",
        "independent_m4_77_verification_receipts_m4_79",
        ["created_at"],
    )
    op.create_index(
        "ix_m4_79_verification_recorded_by",
        "independent_m4_77_verification_receipts_m4_79",
        ["recorded_by"],
    )
    op.create_index(
        "ix_m4_79_verification_fingerprint",
        "independent_m4_77_verification_receipts_m4_79",
        ["verification_fingerprint"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("independent_m4_77_verification_receipts_m4_79")
