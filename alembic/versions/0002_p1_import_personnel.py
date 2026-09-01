"""P1 import and personnel provenance

Revision ID: 0002_p1_import_personnel
Revises: 0001_baseline
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_p1_import_personnel"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("employees", sa.Column("source_employee_key", sa.String(length=100), nullable=True))
    op.create_index("ix_employees_source_employee_key", "employees", ["source_employee_key"], unique=True)

    op.add_column("payroll_runs", sa.Column("source_import_batch_id", sa.Uuid(), nullable=True))
    op.create_index("ix_payroll_runs_source_import_batch_id", "payroll_runs", ["source_import_batch_id"], unique=False)

    op.create_table(
        "import_records",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("import_batch_id", sa.Uuid(), nullable=False),
        sa.Column("source_name", sa.String(length=200), nullable=False),
        sa.Column("period", sa.String(length=7), nullable=False),
        sa.Column("source_employee_key", sa.String(length=100), nullable=False),
        sa.Column("record_hash", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("import_batch_id", "record_hash", name="uq_import_record_hash"),
    )
    op.create_index("ix_import_records_import_batch_id", "import_records", ["import_batch_id"], unique=False)
    op.create_index("ix_import_records_source_name", "import_records", ["source_name"], unique=False)
    op.create_index("ix_import_records_period", "import_records", ["period"], unique=False)
    op.create_index("ix_import_records_source_employee_key", "import_records", ["source_employee_key"], unique=False)
    op.create_index("ix_import_records_record_hash", "import_records", ["record_hash"], unique=False)

    op.create_table(
        "personnel_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("employee_no", sa.String(length=50), nullable=False),
        sa.Column("effective_period", sa.String(length=7), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("organization_unit_id", sa.String(length=50), nullable=False),
        sa.Column("position_id", sa.String(length=50), nullable=False),
        sa.Column("employment_type", sa.String(length=30), nullable=False),
        sa.Column("employment_status", sa.String(length=30), nullable=False),
        sa.Column("source_import_batch_id", sa.Uuid(), nullable=True),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("snapshot_hash", sa.String(length=64), nullable=False),
        sa.Column("order_numbers", sa.JSON(), nullable=False),
        sa.Column("components", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("employee_no", "effective_period", name="uq_personnel_snapshot_employee_period"),
    )
    op.create_index("ix_personnel_snapshots_employee_no", "personnel_snapshots", ["employee_no"], unique=False)
    op.create_index("ix_personnel_snapshots_effective_period", "personnel_snapshots", ["effective_period"], unique=False)
    op.create_index("ix_personnel_snapshots_organization_unit_id", "personnel_snapshots", ["organization_unit_id"], unique=False)
    op.create_index("ix_personnel_snapshots_source_import_batch_id", "personnel_snapshots", ["source_import_batch_id"], unique=False)
    op.create_index("ix_personnel_snapshots_snapshot_hash", "personnel_snapshots", ["snapshot_hash"], unique=False)


def downgrade() -> None:
    op.drop_table("personnel_snapshots")
    op.drop_table("import_records")
    op.drop_index("ix_payroll_runs_source_import_batch_id", table_name="payroll_runs")
    op.drop_column("payroll_runs", "source_import_batch_id")
    op.drop_index("ix_employees_source_employee_key", table_name="employees")
    op.drop_column("employees", "source_employee_key")
