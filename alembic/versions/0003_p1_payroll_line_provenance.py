"""P1 payroll line provenance

Revision ID: 0003_p1_payroll_line_provenance
Revises: 0002_p1_import_personnel
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_p1_payroll_line_provenance"
down_revision = "0002_p1_import_personnel"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {c["name"] for c in inspector.get_columns("payroll_lines")}
    if "source_record_id" not in columns:
        op.add_column("payroll_lines", sa.Column("source_record_id", sa.Uuid(), nullable=True))
    if "mapping_status" not in columns:
        op.add_column("payroll_lines", sa.Column("mapping_status", sa.String(length=30), nullable=False, server_default="review_required"))
    indexes = {i["name"] for i in inspector.get_indexes("payroll_lines")}
    if "ix_payroll_lines_source_record_id" not in indexes:
        op.create_index("ix_payroll_lines_source_record_id", "payroll_lines", ["source_record_id"], unique=False)
    if "ix_payroll_lines_mapping_status" not in indexes:
        op.create_index("ix_payroll_lines_mapping_status", "payroll_lines", ["mapping_status"], unique=False)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    indexes = {i["name"] for i in inspector.get_indexes("payroll_lines")}
    if "ix_payroll_lines_mapping_status" in indexes:
        op.drop_index("ix_payroll_lines_mapping_status", table_name="payroll_lines")
    if "ix_payroll_lines_source_record_id" in indexes:
        op.drop_index("ix_payroll_lines_source_record_id", table_name="payroll_lines")
    columns = {c["name"] for c in inspector.get_columns("payroll_lines")}
    if "mapping_status" in columns:
        op.drop_column("payroll_lines", "mapping_status")
    if "source_record_id" in columns:
        op.drop_column("payroll_lines", "source_record_id")
