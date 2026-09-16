"""Persist payment exception lifecycle and immutable resolution events.

Revision ID: 0021_payment_exception_persistence
Revises: 0020_master_data_evidence
"""
from alembic import op
import sqlalchemy as sa

revision = "0021_payment_exception_persistence"
down_revision = "0020_master_data_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_exceptions",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("exception_id", sa.String(100), nullable=False),
        sa.Column("payment_item_id", sa.String(100), nullable=False),
        sa.Column("exception_type", sa.String(40), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="open"),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_actor", sa.String(100), nullable=True),
        sa.Column("resolution_reason", sa.Text(), nullable=True),
        sa.Column("evidence_ref", sa.Text(), nullable=True),
        sa.Column("resolution_fingerprint", sa.String(64), nullable=True),
        sa.UniqueConstraint("exception_id", name="uq_payment_exception_exception_id"),
        sa.UniqueConstraint(
            "payment_item_id",
            "exception_type",
            "status",
            name="uq_payment_exception_item_type_status",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'resolved', 'blocked')",
            name="ck_payment_exception_status",
        ),
        sa.CheckConstraint(
            "exception_type IN ('return', 'reject', 'partial_settlement', 'reversal', 'unresolved_mismatch')",
            name="ck_payment_exception_type",
        ),
    )
    op.create_index("ix_payment_exceptions_exception_id", "payment_exceptions", ["exception_id"], unique=True)
    op.create_index("ix_payment_exceptions_payment_item_id", "payment_exceptions", ["payment_item_id"])
    op.create_index("ix_payment_exceptions_exception_type", "payment_exceptions", ["exception_type"])
    op.create_index("ix_payment_exceptions_status", "payment_exceptions", ["status"])
    op.create_index("ix_payment_exceptions_resolution_fingerprint", "payment_exceptions", ["resolution_fingerprint"])

    op.create_table(
        "payment_exception_events",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("exception_id", sa.String(100), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("actor", sa.String(100), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("evidence_ref", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(150), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.UniqueConstraint(
            "exception_id",
            "idempotency_key",
            name="uq_payment_exception_event_idempotency",
        ),
        sa.CheckConstraint(
            "status = 'resolved'",
            name="ck_payment_exception_event_status",
        ),
    )
    op.create_index("ix_payment_exception_events_exception_id", "payment_exception_events", ["exception_id"])
    op.create_index("ix_payment_exception_events_actor", "payment_exception_events", ["actor"])
    op.create_index("ix_payment_exception_events_idempotency_key", "payment_exception_events", ["idempotency_key"])
    op.create_index("ix_payment_exception_events_fingerprint", "payment_exception_events", ["fingerprint"])


def downgrade() -> None:
    op.drop_table("payment_exception_events")
    op.drop_table("payment_exceptions")
