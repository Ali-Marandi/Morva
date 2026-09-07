"""Persist master-data acceptance assessment.

Revision ID: 0014_master_data_acceptance
Revises: 0013_personnel_order_approval
"""
from alembic import op
import sqlalchemy as sa

revision = "0014_master_data_acceptance"
down_revision = "0013_personnel_order_approval"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "master_data_acceptance",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("dataset_name", sa.String(120), nullable=False),
        sa.Column("schema_version", sa.String(50), nullable=False),
        sa.Column("source_system", sa.String(120), nullable=False),
        sa.Column("source_uri", sa.String(500), nullable=False),
        sa.Column("authoritative_source_reference", sa.String(300), nullable=False),
        sa.Column("dataset_period", sa.String(7), nullable=False),
        sa.Column("dataset_sha256", sa.String(64), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("duplicate_key_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejected_row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("schema_valid", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(30), nullable=False, server_default="blocked"),
        sa.Column("integrity_blocking", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("blockers", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("submitted_by", sa.String(100), nullable=False),
        sa.Column("accepted_by", sa.String(100), nullable=True),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("authority_confirmation_reference", sa.String(300), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "dataset_name",
            "dataset_sha256",
            name="uq_master_data_acceptance_dataset_hash",
        ),
    )
    op.create_index(
        "ix_master_data_acceptance_dataset_name",
        "master_data_acceptance",
        ["dataset_name"],
    )
    op.create_index(
        "ix_master_data_acceptance_dataset_period",
        "master_data_acceptance",
        ["dataset_period"],
    )
    op.create_index(
        "ix_master_data_acceptance_dataset_sha256",
        "master_data_acceptance",
        ["dataset_sha256"],
    )
    op.create_index("ix_master_data_acceptance_status", "master_data_acceptance", ["status"])
    op.create_index(
        "ix_master_data_acceptance_submitted_by",
        "master_data_acceptance",
        ["submitted_by"],
    )


def downgrade() -> None:
    op.drop_index("ix_master_data_acceptance_submitted_by", table_name="master_data_acceptance")
    op.drop_index("ix_master_data_acceptance_status", table_name="master_data_acceptance")
    op.drop_index(
        "ix_master_data_acceptance_dataset_sha256",
        table_name="master_data_acceptance",
    )
    op.drop_index("ix_master_data_acceptance_dataset_period", table_name="master_data_acceptance")
    op.drop_index("ix_master_data_acceptance_dataset_name", table_name="master_data_acceptance")
    op.drop_table("master_data_acceptance")
