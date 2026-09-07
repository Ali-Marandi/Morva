"""Persist calculation matrix governance entries.

Revision ID: 0015_calculation_matrix
Revises: 0014_master_data_acceptance
"""
from alembic import op
import sqlalchemy as sa

revision = "0015_calculation_matrix"
down_revision = "0014_master_data_acceptance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "calculation_matrix",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("rule_pack_version", sa.String(80), nullable=False),
        sa.Column("component_code", sa.String(80), nullable=False),
        sa.Column("population_scope", sa.String(200), nullable=False),
        sa.Column("treatment", sa.String(20), nullable=False),
        sa.Column("expression", sa.JSON(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("legal_source_id", sa.Uuid(), nullable=False),
        sa.Column("legal_article", sa.String(100), nullable=False),
        sa.Column("legal_clause", sa.String(100), nullable=True),
        sa.Column("taxable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("pensionable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("insurable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("regression_suite_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="review_required"),
        sa.Column("reviewed_by", sa.String(100), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("approved_by", sa.String(100), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "rule_pack_version",
            "component_code",
            "population_scope",
            name="uq_calculation_matrix_pack_component_population",
        ),
    )
    for index_name, column in (
        ("ix_calculation_matrix_rule_pack_version", "rule_pack_version"),
        ("ix_calculation_matrix_component_code", "component_code"),
        ("ix_calculation_matrix_population_scope", "population_scope"),
        ("ix_calculation_matrix_effective_from", "effective_from"),
        ("ix_calculation_matrix_legal_source_id", "legal_source_id"),
        ("ix_calculation_matrix_status", "status"),
    ):
        op.create_index(index_name, "calculation_matrix", [column])


def downgrade() -> None:
    for index_name in (
        "ix_calculation_matrix_status",
        "ix_calculation_matrix_legal_source_id",
        "ix_calculation_matrix_effective_from",
        "ix_calculation_matrix_population_scope",
        "ix_calculation_matrix_component_code",
        "ix_calculation_matrix_rule_pack_version",
    ):
        op.drop_index(index_name, table_name="calculation_matrix")
    op.drop_table("calculation_matrix")
