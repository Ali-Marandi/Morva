"""Bind personnel-order approval evidence to immutable order fingerprints.

Revision ID: 0017_personnel_order_integrity
Revises: 0016_employee_self_service_cases
"""
from alembic import op
import sqlalchemy as sa

revision = "0017_personnel_order_integrity"
down_revision = "0016_employee_self_service_cases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("personnel_orders", sa.Column("content_hash", sa.String(64), nullable=True))
    op.create_index("ix_personnel_orders_content_hash", "personnel_orders", ["content_hash"])
    op.add_column("personnel_order_submissions", sa.Column("order_fingerprint", sa.String(64), nullable=True))
    op.create_index("ix_personnel_order_submissions_order_fingerprint", "personnel_order_submissions", ["order_fingerprint"])
    op.add_column("personnel_order_decisions", sa.Column("order_fingerprint", sa.String(64), nullable=True))
    op.create_index("ix_personnel_order_decisions_order_fingerprint", "personnel_order_decisions", ["order_fingerprint"])


def downgrade() -> None:
    op.drop_index("ix_personnel_order_decisions_order_fingerprint", table_name="personnel_order_decisions")
    op.drop_column("personnel_order_decisions", "order_fingerprint")
    op.drop_index("ix_personnel_order_submissions_order_fingerprint", table_name="personnel_order_submissions")
    op.drop_column("personnel_order_submissions", "order_fingerprint")
    op.drop_index("ix_personnel_orders_content_hash", table_name="personnel_orders")
    op.drop_column("personnel_orders", "content_hash")
