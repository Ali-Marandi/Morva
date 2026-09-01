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


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
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
    Base.metadata.drop_all(bind=op.get_bind())
