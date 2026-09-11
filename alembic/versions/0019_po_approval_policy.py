"""Persist organizational personnel-order approval policy provenance.

Revision ID: 0019_po_approval_policy
Revises: 0018_master_data_integrity_snap
"""
from alembic import op
import sqlalchemy as sa

revision = "0019_po_approval_policy"
down_revision = "0018_master_data_integrity_snap"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "personnel_order_approval_policies",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("policy_code", sa.String(100), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("order_types", sa.JSON(), nullable=False),
        sa.Column("required_submission_role", sa.String(100), nullable=False),
        sa.Column("required_decision_role", sa.String(100), nullable=False),
        sa.Column("source_reference", sa.Text(), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("approved_by", sa.String(100), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("policy_hash", sa.String(64), nullable=False),
        sa.UniqueConstraint("policy_code", "version", name="uq_personnel_order_approval_policy_version"),
    )
    op.create_index("ix_personnel_order_approval_policies_policy_code", "personnel_order_approval_policies", ["policy_code"])
    op.create_index("ix_personnel_order_approval_policies_version", "personnel_order_approval_policies", ["version"])
    op.create_index("ix_personnel_order_approval_policies_status", "personnel_order_approval_policies", ["status"])
    op.create_index("ix_personnel_order_approval_policies_policy_hash", "personnel_order_approval_policies", ["policy_hash"])

    op.add_column("personnel_order_submissions", sa.Column("submitted_role", sa.String(100), nullable=True))
    op.add_column("personnel_order_submissions", sa.Column("approval_policy_code", sa.String(100), nullable=True))
    op.add_column("personnel_order_submissions", sa.Column("approval_policy_hash", sa.String(64), nullable=True))
    op.create_index("ix_personnel_order_submissions_submitted_role", "personnel_order_submissions", ["submitted_role"])
    op.create_index("ix_personnel_order_submissions_approval_policy_code", "personnel_order_submissions", ["approval_policy_code"])
    op.create_index("ix_personnel_order_submissions_approval_policy_hash", "personnel_order_submissions", ["approval_policy_hash"])

    op.add_column("personnel_order_decisions", sa.Column("decided_role", sa.String(100), nullable=True))
    op.add_column("personnel_order_decisions", sa.Column("approval_policy_code", sa.String(100), nullable=True))
    op.add_column("personnel_order_decisions", sa.Column("approval_policy_hash", sa.String(64), nullable=True))
    op.create_index("ix_personnel_order_decisions_decided_role", "personnel_order_decisions", ["decided_role"])
    op.create_index("ix_personnel_order_decisions_approval_policy_code", "personnel_order_decisions", ["approval_policy_code"])
    op.create_index("ix_personnel_order_decisions_approval_policy_hash", "personnel_order_decisions", ["approval_policy_hash"])


def downgrade() -> None:
    op.drop_index("ix_personnel_order_decisions_approval_policy_hash", table_name="personnel_order_decisions")
    op.drop_index("ix_personnel_order_decisions_approval_policy_code", table_name="personnel_order_decisions")
    op.drop_index("ix_personnel_order_decisions_decided_role", table_name="personnel_order_decisions")
    op.drop_column("personnel_order_decisions", "approval_policy_hash")
    op.drop_column("personnel_order_decisions", "approval_policy_code")
    op.drop_column("personnel_order_decisions", "decided_role")

    op.drop_index("ix_personnel_order_submissions_approval_policy_hash", table_name="personnel_order_submissions")
    op.drop_index("ix_personnel_order_submissions_approval_policy_code", table_name="personnel_order_submissions")
    op.drop_index("ix_personnel_order_submissions_submitted_role", table_name="personnel_order_submissions")
    op.drop_column("personnel_order_submissions", "approval_policy_hash")
    op.drop_column("personnel_order_submissions", "approval_policy_code")
    op.drop_column("personnel_order_submissions", "submitted_role")

    op.drop_index("ix_personnel_order_approval_policies_policy_hash", table_name="personnel_order_approval_policies")
    op.drop_index("ix_personnel_order_approval_policies_status", table_name="personnel_order_approval_policies")
    op.drop_index("ix_personnel_order_approval_policies_version", table_name="personnel_order_approval_policies")
    op.drop_index("ix_personnel_order_approval_policies_policy_code", table_name="personnel_order_approval_policies")
    op.drop_table("personnel_order_approval_policies")
