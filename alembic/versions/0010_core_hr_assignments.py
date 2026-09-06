"""Persist effective-dated employee assignments.

Revision ID: 0010_core_hr_assignments
Revises: 0009_core_hr_employment
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_core_hr_assignments"
down_revision = "0009_core_hr_employment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employee_assignments",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("employee_no", sa.String(50), nullable=False),
        sa.Column("organization_code", sa.String(50), nullable=False),
        sa.Column("position_code", sa.String(50), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("acting", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("source_reference", sa.String(150), nullable=True),
        sa.Column("source_hash", sa.String(64), nullable=True),
        sa.UniqueConstraint(
            "employee_no",
            "starts_on",
            "position_code",
            name="uq_assignment_start_position",
        ),
        sa.CheckConstraint(
            "ends_on IS NULL OR ends_on >= starts_on",
            name="ck_assignment_valid_range",
        ),
    )
    op.create_index("ix_employee_assignments_employee_no", "employee_assignments", ["employee_no"])
    op.create_index("ix_employee_assignments_organization", "employee_assignments", ["organization_code"])
    op.create_index("ix_employee_assignments_position", "employee_assignments", ["position_code"])
    op.create_index("ix_employee_assignments_starts_on", "employee_assignments", ["starts_on"])


def downgrade() -> None:
    op.drop_table("employee_assignments")
