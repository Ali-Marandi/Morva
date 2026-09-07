"""Persist the position master-data registry.

Revision ID: 0012_position_master_data
Revises: 0011_core_hr_profile
"""
from alembic import op
import sqlalchemy as sa

revision = "0012_position_master_data"
down_revision = "0011_core_hr_profile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "positions",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("occupational_group", sa.String(100), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=True),
        sa.Column("job_points", sa.Numeric(20, 4), nullable=False),
        sa.Column("full_time_educational", sa.Boolean(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("code", name="uq_position_code"),
        sa.CheckConstraint("effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from", name="ck_position_valid_range"),
        sa.CheckConstraint("job_points >= 0", name="ck_position_job_points_nonnegative"),
    )
    op.create_index("ix_positions_code", "positions", ["code"])
    op.create_index("ix_positions_occupational_group", "positions", ["occupational_group"])
    op.create_index("ix_positions_effective_from", "positions", ["effective_from"])
    op.create_index("ix_positions_effective_to", "positions", ["effective_to"])
    op.create_index("ix_positions_active", "positions", ["active"])


def downgrade() -> None:
    op.drop_table("positions")
