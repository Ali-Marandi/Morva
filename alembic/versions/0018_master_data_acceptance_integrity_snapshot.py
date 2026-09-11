"""Bind master-data acceptance to a deterministic persisted integrity snapshot.

Revision ID: 0018_master_data_integrity_snap
Revises: 0017_personnel_order_integrity
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0018_master_data_integrity_snap"
down_revision = "0017_personnel_order_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("master_data_acceptance")}
    if "integrity_snapshot_hash" not in columns:
        op.add_column(
            "master_data_acceptance",
            sa.Column("integrity_snapshot_hash", sa.String(64), nullable=True),
        )
        op.create_index(
            "ix_master_data_acceptance_integrity_snapshot_hash",
            "master_data_acceptance",
            ["integrity_snapshot_hash"],
        )


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if "ix_master_data_acceptance_integrity_snapshot_hash" in {
        index["name"] for index in inspector.get_indexes("master_data_acceptance")
    }:
        op.drop_index(
            "ix_master_data_acceptance_integrity_snapshot_hash",
            table_name="master_data_acceptance",
        )
    if "integrity_snapshot_hash" in {
        column["name"] for column in inspector.get_columns("master_data_acceptance")
    }:
        op.drop_column("master_data_acceptance", "integrity_snapshot_hash")
