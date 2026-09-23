"""Persist registry-bound freshness evaluation receipts.

Revision ID: 0029_registry_bound_freshness_receipts
Revises: 0028_readiness_convergence_freshness_policies
"""

from alembic import op
import sqlalchemy as sa


revision = "0029_registry_bound_freshness_receipts"
down_revision = "0028_readiness_convergence_freshness_policies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "registry_bound_policy_readiness_freshness_receipts",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("repository", sa.String(200), nullable=False),
        sa.Column("candidate_sha", sa.String(40), nullable=False),
        sa.Column("target_environment", sa.String(20), nullable=False),
        sa.Column("organization_scope", sa.String(20), nullable=False),
        sa.Column("organization_scope_id", sa.String(100), nullable=False),
        sa.Column("policy_id", sa.String(100), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("policy_fingerprint", sa.String(64), nullable=False),
        sa.Column("registry_integrity_version", sa.Integer(), nullable=False),
        sa.Column("registry_policy_count", sa.Integer(), nullable=False),
        sa.Column("registry_fingerprint", sa.String(64), nullable=False),
        sa.Column("convergence_fingerprint", sa.String(64), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_age_seconds", sa.Integer(), nullable=False),
        sa.Column("age_seconds", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("blockers", sa.JSON(), nullable=False),
        sa.Column("freshness_fingerprint", sa.String(64), nullable=False),
        sa.Column("binding_fingerprint", sa.String(64), nullable=False),
        sa.Column("recorded_by", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "binding_fingerprint",
            name="uq_registry_bound_freshness_receipt_binding_fp",
        ),
    )
    op.create_index(
        "ix_registry_bound_freshness_receipt_candidate_sha",
        "registry_bound_policy_readiness_freshness_receipts",
        ["candidate_sha"],
    )
    op.create_index(
        "ix_registry_bound_freshness_receipt_scope_created_at",
        "registry_bound_policy_readiness_freshness_receipts",
        ["organization_scope", "organization_scope_id", "created_at"],
    )
    op.create_index(
        "ix_registry_bound_freshness_receipt_binding_fp",
        "registry_bound_policy_readiness_freshness_receipts",
        ["binding_fingerprint"],
    )
    op.create_index(
        "ix_registry_bound_freshness_receipt_registry_fp",
        "registry_bound_policy_readiness_freshness_receipts",
        ["registry_fingerprint"],
    )
    op.create_index(
        "ix_registry_bound_freshness_receipt_state",
        "registry_bound_policy_readiness_freshness_receipts",
        ["state"],
    )
    op.create_index(
        "ix_registry_bound_freshness_receipt_recorded_by",
        "registry_bound_policy_readiness_freshness_receipts",
        ["recorded_by"],
    )


def downgrade() -> None:
    op.drop_table("registry_bound_policy_readiness_freshness_receipts")
