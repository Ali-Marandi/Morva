"""Persist canonical payslip line order.

Revision ID: 0007_payslip_line_sequence
Revises: 0006_rule_pack_evidence
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_payslip_line_sequence"
down_revision = "0006_rule_pack_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("payslip_lines", sa.Column("line_sequence", sa.Integer(), nullable=True))
    # Existing rows are historical test/fixture rows; deterministic ordering is only
    # authoritative after the new artifact path populates line_sequence.
    op.execute(
        "UPDATE payslip_lines SET line_sequence = 1 WHERE line_sequence IS NULL"
    )
    op.alter_column("payslip_lines", "line_sequence", nullable=False)
    op.create_index("ix_payslip_lines_artifact_sequence", "payslip_lines", ["artifact_id", "line_sequence"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_payslip_lines_artifact_sequence", table_name="payslip_lines")
    op.drop_column("payslip_lines", "line_sequence")
