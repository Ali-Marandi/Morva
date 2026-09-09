"""Extend the canonical employee case table for self-service lifecycle fields.

Revision ID: 0016_employee_self_service_cases
Revises: 0015_calculation_matrix
"""
from alembic import op
import sqlalchemy as sa

revision = "0016_employee_self_service_cases"
down_revision = "0015_calculation_matrix"
branch_labels = None
depends_on = None


_NEW_COLUMNS = (
    ("title", sa.String(200)),
    ("description", sa.Text()),
    ("priority", sa.String(20)),
    ("submitted_by", sa.String(100)),
    ("submitted_at", sa.DateTime()),
    ("updated_at", sa.DateTime()),
    ("resolved_by", sa.String(100)),
)


def upgrade() -> None:
    for name, type_ in _NEW_COLUMNS:
        op.add_column("employee_cases", sa.Column(name, type_, nullable=True))
    op.create_index("ix_employee_cases_priority", "employee_cases", ["priority"])
    op.create_index("ix_employee_cases_submitted_by", "employee_cases", ["submitted_by"])


def downgrade() -> None:
    op.drop_index("ix_employee_cases_submitted_by", table_name="employee_cases")
    op.drop_index("ix_employee_cases_priority", table_name="employee_cases")
    for name, _type in reversed(_NEW_COLUMNS):
        op.drop_column("employee_cases", name)
