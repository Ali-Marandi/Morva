"""baseline schema

Revision ID: 0001_baseline
Revises:
"""
from alembic import op
import sqlalchemy as sa

from morva.persistence.models import Base

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None

_BASELINE_TABLES = (
    "employees",
    "salary_rules",
    "rule_packs",
    "payroll_runs",
    "payroll_lines",
    "import_batches",
    "retro_cases",
    "audit_chain_head",
    "audit_events",
)


def upgrade() -> None:
    bind = op.get_bind()
    baseline_tables = [Base.metadata.tables[name] for name in _BASELINE_TABLES]
    Base.metadata.create_all(bind=bind, tables=baseline_tables)
    if bind.dialect.name != "sqlite":
        bind.execute(
            sa.text(
                "INSERT INTO audit_chain_head (id, sequence_no, digest) VALUES (1, 0, NULL) "
                "ON CONFLICT (id) DO NOTHING"
            )
        )
    else:
        bind.execute(
            sa.text(
                "INSERT INTO audit_chain_head (id, sequence_no, digest) "
                "SELECT 1, 0, NULL WHERE NOT EXISTS "
                "(SELECT 1 FROM audit_chain_head WHERE id = 1)"
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    for table_name in reversed(_BASELINE_TABLES):
        table = Base.metadata.tables.get(table_name)
        if table is not None:
            table.drop(bind=bind, checkfirst=True)
