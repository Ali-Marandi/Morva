"""Bind personnel-order approval evidence to immutable order fingerprints.

Revision ID: 0017_personnel_order_integrity
Revises: 0016_employee_self_service_cases
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0017_personnel_order_integrity"
down_revision = "0016_employee_self_service_cases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if "personnel_orders" not in inspector.get_table_names():
        op.create_table(
            "personnel_orders",
            sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
            sa.Column("order_no", sa.String(80), nullable=False),
            sa.Column("employee_no", sa.String(50), nullable=False),
            sa.Column("order_type", sa.String(50), nullable=False),
            sa.Column("issue_date", sa.Date(), nullable=False),
            sa.Column("effective_date", sa.Date(), nullable=False),
            sa.Column("legal_reference", sa.Text(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("content_hash", sa.String(64), nullable=True),
            sa.Column("created_at", sa.Date(), nullable=False),
            sa.UniqueConstraint("order_no", name="uq_personnel_orders_order_no"),
        )
        op.create_index("ix_personnel_orders_order_no", "personnel_orders", ["order_no"])
        op.create_index("ix_personnel_orders_employee_no", "personnel_orders", ["employee_no"])
        op.create_index("ix_personnel_orders_order_type", "personnel_orders", ["order_type"])
        op.create_index("ix_personnel_orders_effective_date", "personnel_orders", ["effective_date"])
        op.create_index("ix_personnel_orders_content_hash", "personnel_orders", ["content_hash"])
    elif "content_hash" not in {column["name"] for column in inspector.get_columns("personnel_orders")}:
        op.add_column("personnel_orders", sa.Column("content_hash", sa.String(64), nullable=True))
        op.create_index("ix_personnel_orders_content_hash", "personnel_orders", ["content_hash"])

    submission_columns = {column["name"] for column in inspector.get_columns("personnel_order_submissions")}
    if "order_fingerprint" not in submission_columns:
        op.add_column("personnel_order_submissions", sa.Column("order_fingerprint", sa.String(64), nullable=True))
        op.create_index(
            "ix_personnel_order_submissions_order_fingerprint",
            "personnel_order_submissions",
            ["order_fingerprint"],
        )

    decision_columns = {column["name"] for column in inspector.get_columns("personnel_order_decisions")}
    if "order_fingerprint" not in decision_columns:
        op.add_column("personnel_order_decisions", sa.Column("order_fingerprint", sa.String(64), nullable=True))
        op.create_index(
            "ix_personnel_order_decisions_order_fingerprint",
            "personnel_order_decisions",
            ["order_fingerprint"],
        )


def downgrade() -> None:
    inspector = inspect(op.get_bind())

    if "ix_personnel_order_decisions_order_fingerprint" in {
        index["name"] for index in inspector.get_indexes("personnel_order_decisions")
    }:
        op.drop_index("ix_personnel_order_decisions_order_fingerprint", table_name="personnel_order_decisions")
    if "order_fingerprint" in {column["name"] for column in inspector.get_columns("personnel_order_decisions")}:
        op.drop_column("personnel_order_decisions", "order_fingerprint")

    if "ix_personnel_order_submissions_order_fingerprint" in {
        index["name"] for index in inspector.get_indexes("personnel_order_submissions")
    }:
        op.drop_index("ix_personnel_order_submissions_order_fingerprint", table_name="personnel_order_submissions")
    if "order_fingerprint" in {column["name"] for column in inspector.get_columns("personnel_order_submissions")}:
        op.drop_column("personnel_order_submissions", "order_fingerprint")

    if "personnel_orders" in inspector.get_table_names():
        if "ix_personnel_orders_content_hash" in {
            index["name"] for index in inspector.get_indexes("personnel_orders")
        }:
            op.drop_index("ix_personnel_orders_content_hash", table_name="personnel_orders")
        if "content_hash" in {column["name"] for column in inspector.get_columns("personnel_orders")}:
            op.drop_column("personnel_orders", "content_hash")
