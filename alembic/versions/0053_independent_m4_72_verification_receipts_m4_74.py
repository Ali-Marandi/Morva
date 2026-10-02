"""Persist M4.73 independent M4.72 verification receipts."""

from alembic import op
import sqlalchemy as sa


revision = "0053_independent_m4_72_verification_receipts_m4_74"
down_revision = "0052_historical_m4_71_verification_history_integrity_m4_72"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "independent_historical_m4_72_verification_receipts_m4_74",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "snapshot_id",
            sa.Uuid(),
            sa.ForeignKey(
                "historical_m4_71_verification_history_integrity_m4_72.id"
            ),
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
            name="uq_m4_74_verification_fingerprint",
        ),
    )
    op.create_index(
        "ix_m4_74_verification_snapshot_id",
        "independent_historical_m4_72_verification_receipts_m4_74",
        ["snapshot_id"],
    )
    op.create_index(
        "ix_m4_74_verification_valid",
        "independent_historical_m4_72_verification_receipts_m4_74",
        ["valid"],
    )
    op.create_index(
        "ix_m4_74_verification_created_at",
        "independent_historical_m4_72_verification_receipts_m4_74",
        ["created_at"],
    )
    op.create_index(
        "ix_m4_74_verification_recorded_by",
        "independent_historical_m4_72_verification_receipts_m4_74",
        ["recorded_by"],
    )
    op.create_index(
        "ix_m4_74_verification_fingerprint",
        "independent_historical_m4_72_verification_receipts_m4_74",
        ["verification_fingerprint"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("independent_historical_m4_72_verification_receipts_m4_74")
