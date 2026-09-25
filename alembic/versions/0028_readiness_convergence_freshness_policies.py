"""Persist explicit readiness-convergence freshness policy identities.

Revision ID: 0028_readiness_convergence_freshness_policies
Revises: 0027_scope_bound_readiness_convergences
"""

from alembic import op
import sqlalchemy as sa


revision = "0028_readiness_convergence_freshness_policies"
down_revision = "0027_scope_bound_readiness_convergences"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "readiness_convergence_freshness_policies",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("policy_id", sa.String(100), nullable=False),
        sa.Column("max_age_seconds", sa.Integer(), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("recorded_by", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "policy_id",
            "policy_version",
            name="uq_readiness_freshness_policy_id_version",
        ),
        sa.UniqueConstraint(
            "fingerprint",
            name="uq_readiness_freshness_policy_fingerprint",
        ),
    )
    op.create_index(
        "ix_readiness_freshness_policy_id",
        "readiness_convergence_freshness_policies",
        ["policy_id"],
    )
    op.create_index(
        "ix_readiness_freshness_policy_fingerprint",
        "readiness_convergence_freshness_policies",
        ["fingerprint"],
    )
    op.create_index(
        "ix_readiness_freshness_policy_recorded_by",
        "readiness_convergence_freshness_policies",
        ["recorded_by"],
    )


def downgrade() -> None:
    op.drop_table("readiness_convergence_freshness_policies")
