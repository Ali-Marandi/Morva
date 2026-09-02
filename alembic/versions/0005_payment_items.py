"""Per-beneficiary payment items.

Revision ID: 0005_payment_items
Revises: 0004_enterprise_artifacts
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_payment_items"
down_revision = "0004_enterprise_artifacts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_items",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("payment_batch_id", sa.Uuid(), nullable=False),
        sa.Column("employee_no", sa.String(50), nullable=False),
        sa.Column("artifact_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(24, 4), nullable=False),
        sa.Column("currency_code", sa.String(3), nullable=False),
        sa.Column("bank_account_ciphertext", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("external_payment_id", sa.String(150), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("payment_batch_id", "employee_no", name="uq_payment_item_batch_employee"),
    )
    op.create_index("ix_payment_items_batch", "payment_items", ["payment_batch_id"])
    op.create_index("ix_payment_items_employee", "payment_items", ["employee_no"])
    op.create_index("ix_payment_items_artifact", "payment_items", ["artifact_id"])
    op.create_index("ix_payment_items_external", "payment_items", ["external_payment_id"])


def downgrade() -> None:
    op.drop_table("payment_items")
