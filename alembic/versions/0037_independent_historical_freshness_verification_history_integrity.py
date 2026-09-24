"""Persist M4.48 independent verification of M4.47 history integrity snapshots.

Revision ID: 0037_independent_historical_freshness_verification_history_integrity
Revises: 0036_historical_freshness_verification_history_integrity
"""

from alembic import op
import sqlalchemy as sa


revision = "0037_independent_historical_freshness_verification_history_integrity"
down_revision = "0036_historical_freshness_verification_history_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "independent_historical_freshness_verification_history_integrity_m4_48",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("persisted_history_fingerprint", sa.String(64), nullable=False),
        sa.Column("reconstructed_history_fingerprint", sa.String(64), nullable=False),
        sa.Column("persisted_fingerprint", sa.String(64), nullable=False),
        sa.Column("reconstructed_fingerprint", sa.String(64), nullable=False),
        sa.Column("persisted_record_count", sa.Integer(), nullable=False),
        sa.Column("reconstructed_record_count", sa.Integer(), nullable=False),
        sa.Column("persisted_valid_count", sa.Integer(), nullable=False),
        sa.Column("reconstructed_valid_count", sa.Integer(), nullable=False),
        sa.Column("persisted_chain_valid_count", sa.Integer(), nullable=False),
        sa.Column("reconstructed_chain_valid_count", sa.Integer(), nullable=False),
        sa.Column("valid", sa.Boolean(), nullable=False),
        sa.Column("blockers_json", sa.Text(), nullable=False),
        sa.Column("verification_fingerprint", sa.String(64), nullable=False),
        sa.Column("verified_by", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["historical_freshness_verification_history_integrity_m4_47.id"],
        ),
        sa.UniqueConstraint(
            "verification_fingerprint",
            name="uq_m4_48_history_integrity_verification_fingerprint",
        ),
    )
    op.create_index(
        "ix_m4_48_history_integrity_snapshot_id",
        "independent_historical_freshness_verification_history_integrity_m4_48",
        ["snapshot_id"],
    )
    op.create_index(
        "ix_m4_48_history_integrity_valid",
        "independent_historical_freshness_verification_history_integrity_m4_48",
        ["valid"],
    )
    op.create_index(
        "ix_m4_48_history_integrity_created_at",
        "independent_historical_freshness_verification_history_integrity_m4_48",
        ["created_at"],
    )
    op.create_index(
        "ix_m4_48_history_integrity_verification_fingerprint",
        "independent_historical_freshness_verification_history_integrity_m4_48",
        ["verification_fingerprint"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("independent_historical_freshness_verification_history_integrity_m4_48")
