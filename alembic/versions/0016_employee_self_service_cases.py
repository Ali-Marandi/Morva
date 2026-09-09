"""Persist employee self-service objection/case records.

Revision ID: 0016_employee_self_service_cases
Revises: 0015_calculation_matrix
"""
from alembic import op
import sqlalchemy as sa

revision = "0016_employee_self_service_cases"
down_revision = "0015_calculation_matrix"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employee_cases",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("employee_no", sa.String(50), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False, server_default="normal"),
        sa.Column("status", sa.String(30), nullable=False, server_default="open"),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("submitted_by", sa.String(100), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_by", sa.String(100), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
    )
    for index_name, column in (
        ("ix_employee_cases_employee_no", "employee_no"),
        ("ix_employee_cases_category", "category"),
        ("ix_employee_cases_priority", "priority"),
        ("ix_employee_cases_status", "status"),
        ("ix_employee_cases_submitted_by", "submitted_by"),
    ):
        op.create_index(index_name, "employee_cases", [column])


def downgrade() -> None:
    for index_name in (
        "ix_employee_cases_submitted_by",
        "ix_employee_cases_status",
        "ix_employee_cases_priority",
        "ix_employee_cases_category",
        "ix_employee_cases_employee_no",
    ):
        op.drop_index(index_name, table_name="employee_cases")
    op.drop_table("employee_cases")
