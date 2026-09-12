"""master data acceptance evidence package

Revision ID: 0020_master_data_evidence
Revises: 0019_po_approval_policy
"""

from alembic import op
import sqlalchemy as sa


revision = "0020_master_data_evidence"
down_revision = "0019_po_approval_policy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("master_data_acceptance")}
    additions = (
        ("evidence_reference", sa.String(length=300), True),
        ("evidence_sha256", sa.String(length=64), True),
        ("population_scope", sa.String(length=300), True),
        ("coverage_evidence", sa.JSON(), True),
        ("evidence_fingerprint", sa.String(length=64), True),
    )
    for name, column_type, nullable in additions:
        if name not in columns:
            op.add_column(
                "master_data_acceptance",
                sa.Column(name, column_type, nullable=nullable),
            )
    op.create_index(
        "ix_master_data_acceptance_evidence_sha256",
        "master_data_acceptance",
        ["evidence_sha256"],
        unique=False,
    )
    op.create_index(
        "ix_master_data_acceptance_evidence_fingerprint",
        "master_data_acceptance",
        ["evidence_fingerprint"],
        unique=False,
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    indexes = {index["name"] for index in inspector.get_indexes("master_data_acceptance")}
    if "ix_master_data_acceptance_evidence_fingerprint" in indexes:
        op.drop_index("ix_master_data_acceptance_evidence_fingerprint", table_name="master_data_acceptance")
    if "ix_master_data_acceptance_evidence_sha256" in indexes:
        op.drop_index("ix_master_data_acceptance_evidence_sha256", table_name="master_data_acceptance")
    columns = {column["name"] for column in inspector.get_columns("master_data_acceptance")}
    for name in ("evidence_fingerprint", "coverage_evidence", "population_scope", "evidence_sha256", "evidence_reference"):
        if name in columns:
            op.drop_column("master_data_acceptance", name)
