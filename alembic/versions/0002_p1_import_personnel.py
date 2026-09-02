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


def _inspector():
    return sa.inspect(op.get_bind())


def upgrade() -> None:
    inspector = _inspector()
    employees_columns = {column["name"] for column in inspector.get_columns("employees")}
    if "source_employee_key" not in employees_columns:
        op.add_column("employees", sa.Column("source_employee_key", sa.String(length=100), nullable=True))
    if "ix_employees_source_employee_key" not in {index["name"] for index in inspector.get_indexes("employees")}:
        op.create_index("ix_employees_source_employee_key", "employees", ["source_employee_key"], unique=True)

    payroll_columns = {column["name"] for column in inspector.get_columns("payroll_runs")}
    if "source_import_batch_id" not in payroll_columns:
        op.add_column("payroll_runs", sa.Column("source_import_batch_id", sa.Uuid(), nullable=True))
    if "ix_payroll_runs_source_import_batch_id" not in {index["name"] for index in inspector.get_indexes("payroll_runs")}:
        op.create_index("ix_payroll_runs_source_import_batch_id", "payroll_runs", ["source_import_batch_id"], unique=False)

    if "import_records" not in set(inspector.get_table_names()):
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
    inspector = _inspector()
    existing_import_indexes = {index["name"] for index in inspector.get_indexes("import_records")}
    for name, column in (("ix_import_records_import_batch_id", "import_batch_id"), ("ix_import_records_source_name", "source_name"), ("ix_import_records_period", "period"), ("ix_import_records_source_employee_key", "source_employee_key"), ("ix_import_records_record_hash", "record_hash")):
        if name not in existing_import_indexes:
            op.create_index(name, "import_records", [column], unique=False)

    if "personnel_snapshots" not in set(inspector.get_table_names()):
        op.create_table(
            "personnel_snapshots",
            sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
            sa.Column("employee_no", sa.String(length=50), nullable=False),
            sa.Column("effective_period", sa.String(length=7), nullable=False),
            sa.Column("effective_date", sa.Date(), nullable=True),
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
    inspector = _inspector()
    existing_snapshot_indexes = {index["name"] for index in inspector.get_indexes("personnel_snapshots")}
    for name, column in (("ix_personnel_snapshots_employee_no", "employee_no"), ("ix_personnel_snapshots_effective_period", "effective_period"), ("ix_personnel_snapshots_organization_unit_id", "organization_unit_id"), ("ix_personnel_snapshots_source_import_batch_id", "source_import_batch_id"), ("ix_personnel_snapshots_snapshot_hash", "snapshot_hash")):
        if name not in existing_snapshot_indexes:
            op.create_index(name, "personnel_snapshots", [column], unique=False)


def downgrade() -> None:
    inspector = _inspector()
    if "personnel_snapshots" in set(inspector.get_table_names()):
        op.drop_table("personnel_snapshots")
    if "import_records" in set(inspector.get_table_names()):
        op.drop_table("import_records")
    if "payroll_runs" in set(inspector.get_table_names()):
        if "ix_payroll_runs_source_import_batch_id" in {index["name"] for index in inspector.get_indexes("payroll_runs")}:
            op.drop_index("ix_payroll_runs_source_import_batch_id", table_name="payroll_runs")
        if "source_import_batch_id" in {column["name"] for column in inspector.get_columns("payroll_runs")}:
            op.drop_column("payroll_runs", "source_import_batch_id")
    if "employees" in set(inspector.get_table_names()):
        if "ix_employees_source_employee_key" in {index["name"] for index in inspector.get_indexes("employees")}:
            op.drop_index("ix_employees_source_employee_key", table_name="employees")
        if "source_employee_key" in {column["name"] for column in inspector.get_columns("employees")}:
            op.drop_column("employees", "source_employee_key")
