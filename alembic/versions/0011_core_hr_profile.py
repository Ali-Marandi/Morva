"""Persist employee education, experience and dependents.

Revision ID: 0011_core_hr_profile
Revises: 0010_core_hr_assignments
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_core_hr_profile"
down_revision = "0010_core_hr_assignments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employee_education",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("employee_no", sa.String(50), nullable=False),
        sa.Column("level", sa.String(30), nullable=False),
        sa.Column("field_of_study", sa.String(200), nullable=False),
        sa.Column("institution", sa.String(200), nullable=False),
        sa.Column("completed_on", sa.Date(), nullable=True),
        sa.Column("certificate_reference", sa.String(150), nullable=True),
    )
    op.create_index("ix_employee_education_employee_no", "employee_education", ["employee_no"])
    op.create_index("ix_employee_education_level", "employee_education", ["level"])

    op.create_table(
        "employee_experience",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("employee_no", sa.String(50), nullable=False),
        sa.Column("experience_type", sa.String(30), nullable=False),
        sa.Column("organization_name", sa.String(200), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("reference", sa.String(150), nullable=True),
        sa.UniqueConstraint("employee_no", "organization_name", "starts_on", name="uq_employee_experience_period"),
        sa.CheckConstraint("ends_on IS NULL OR ends_on >= starts_on", name="ck_employee_experience_valid_range"),
    )
    op.create_index("ix_employee_experience_employee_no", "employee_experience", ["employee_no"])
    op.create_index("ix_employee_experience_type", "employee_experience", ["experience_type"])
    op.create_index("ix_employee_experience_starts_on", "employee_experience", ["starts_on"])
    op.create_index("ix_employee_experience_ends_on", "employee_experience", ["ends_on"])

    op.create_table(
        "employee_dependents",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("employee_no", sa.String(50), nullable=False),
        sa.Column("relationship", sa.String(30), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.UniqueConstraint("employee_no", "name", "relationship", name="uq_employee_dependent_identity"),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name="ck_employee_dependent_valid_range",
        ),
    )
    op.create_index("ix_employee_dependents_employee_no", "employee_dependents", ["employee_no"])
    op.create_index("ix_employee_dependents_relationship", "employee_dependents", ["relationship"])
    op.create_index("ix_employee_dependents_valid_from", "employee_dependents", ["valid_from"])
    op.create_index("ix_employee_dependents_valid_to", "employee_dependents", ["valid_to"])


def downgrade() -> None:
    op.drop_table("employee_dependents")
    op.drop_table("employee_experience")
    op.drop_table("employee_education")
