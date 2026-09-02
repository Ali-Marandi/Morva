"""Rule-pack legal evidence by payroll component.

Revision ID: 0006_rule_pack_evidence
Revises: 0005_payment_items
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_rule_pack_evidence"
down_revision = "0005_payment_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rule_evidence",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("rule_pack_version", sa.String(80), nullable=False),
        sa.Column("component_code", sa.String(80), nullable=False),
        sa.Column("legal_source_id", sa.Uuid(), nullable=False),
        sa.Column("issuer", sa.String(200), nullable=False),
        sa.Column("article", sa.String(100), nullable=False),
        sa.Column("clause", sa.String(100), nullable=True),
        sa.Column("population_scope", sa.String(200), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("regression_suite_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="review_required"),
        sa.Column("reviewed_by", sa.String(100), nullable=True),
        sa.Column("approved_by", sa.String(100), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("rule_pack_version", "component_code", name="uq_rule_evidence_pack_component"),
    )
    op.create_index("ix_rule_evidence_pack", "rule_evidence", ["rule_pack_version"])
    op.create_index("ix_rule_evidence_component", "rule_evidence", ["component_code"])
    op.create_index("ix_rule_evidence_status", "rule_evidence", ["status"])


def downgrade() -> None:
    op.drop_table("rule_evidence")
