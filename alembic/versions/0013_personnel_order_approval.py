"""Personnel order approval tables.

Revision ID: 0013_personnel_order_approval
Revises: 0012_position_master_data
"""
from alembic import op
import sqlalchemy as sa

revision = "0013_personnel_order_approval"
down_revision = "0012_position_master_data"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "personnel_order_submissions",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("order_no", sa.String(80), nullable=False),
        sa.Column("submitted_by", sa.String(100), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("order_id", name="uq_personnel_order_submission_order"),
        sa.UniqueConstraint("order_no", name="uq_personnel_order_submission_order_no"),
    )
    op.create_index("ix_personnel_order_submissions_order_id", "personnel_order_submissions", ["order_id"])
    op.create_index("ix_personnel_order_submissions_submitted_by", "personnel_order_submissions", ["submitted_by"])

    op.create_table(
        "personnel_order_decisions",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("order_no", sa.String(80), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("decided_by", sa.String(100), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("order_id", name="uq_personnel_order_decision_order"),
        sa.UniqueConstraint("order_no", name="uq_personnel_order_decision_order_no"),
        sa.CheckConstraint("decision IN ('approved', 'rejected')", name="ck_personnel_order_decision_value"),
    )
    op.create_index("ix_personnel_order_decisions_order_id", "personnel_order_decisions", ["order_id"])
    op.create_index("ix_personnel_order_decisions_decided_by", "personnel_order_decisions", ["decided_by"])


def downgrade() -> None:
    op.drop_table("personnel_order_decisions")
    op.drop_table("personnel_order_submissions")
