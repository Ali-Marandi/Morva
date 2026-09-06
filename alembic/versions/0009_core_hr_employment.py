"""Core HR historical employment records.

Revision ID: 0009_core_hr_employment
Revises: 0008_enterprise_domain_ledgers
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_core_hr_employment"
down_revision = "0008_enterprise_domain_ledgers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("employee_no", sa.String(50), nullable=False),
        sa.Column("employment_type", sa.String(30), nullable=False),
        sa.Column("organization_unit_id", sa.String(50), nullable=False),
        sa.Column("position_id", sa.String(50), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("source_record_id", sa.Uuid(), nullable=True),
        sa.Column("source_hash", sa.String(64), nullable=True),
    )
    op.create_index("ix_employments_employee_no", "employments", ["employee_no"])
    op.create_index("ix_employments_starts_on", "employments", ["starts_on"])
    op.create_index("ix_employments_organization", "employments", ["organization_unit_id"])
    op.create_index("ix_employments_position", "employments", ["position_id"])


def downgrade() -> None:
    op.drop_index("ix_employments_position", table_name="employments")
    op.drop_index("ix_employments_organization", table_name="employments")
    op.drop_index("ix_employments_starts_on", table_name="employments")
    op.drop_index("ix_employments_employee_no", table_name="employments")
    op.drop_table("employments")
