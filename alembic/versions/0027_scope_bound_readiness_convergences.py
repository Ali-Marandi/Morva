"""Persist scope-bound readiness convergence observations.

Revision ID: 0027_scope_bound_readiness_convergences
Revises: 0026_integration_readiness_scope_bindings
"""

from alembic import op
import sqlalchemy as sa


revision = "0027_scope_bound_readiness_convergences"
down_revision = "0026_integration_readiness_scope_bindings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scope_bound_readiness_convergences",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("repository", sa.String(200), nullable=False),
        sa.Column("candidate_sha", sa.String(40), nullable=False),
        sa.Column("target_environment", sa.String(20), nullable=False),
        sa.Column("organization_scope", sa.String(20), nullable=False),
        sa.Column("organization_scope_id", sa.String(100), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "persisted_verification_fingerprint",
            sa.String(64),
            nullable=False,
        ),
        sa.Column(
            "persisted_evidence_readiness_fingerprint",
            sa.String(64),
            nullable=False,
        ),
        sa.Column(
            "current_evidence_readiness_fingerprint",
            sa.String(64),
            nullable=False,
        ),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("blockers", sa.JSON(), nullable=False),
        sa.Column(
            "convergence_fingerprint",
            sa.String(64),
            nullable=False,
        ),
        sa.Column("recorded_by", sa.String(100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "convergence_fingerprint",
            name="uq_scope_bound_readiness_convergence_fingerprint",
        ),
    )
    for name, columns in (
        (
            "ix_scope_bound_readiness_convergence_repository",
            ["repository"],
        ),
        (
            "ix_scope_bound_readiness_convergence_candidate_sha",
            ["candidate_sha"],
        ),
        (
            "ix_scope_bound_readiness_convergence_target_environment",
            ["target_environment"],
        ),
        (
            "ix_scope_bound_readiness_convergence_scope",
            ["organization_scope", "organization_scope_id"],
        ),
        (
            "ix_scope_bound_readiness_convergence_checked_at",
            ["checked_at"],
        ),
        (
            "ix_scope_bound_readiness_convergence_state",
            ["state"],
        ),
        (
            "ix_scope_bound_readiness_convergence_verification_fp",
            ["persisted_verification_fingerprint"],
        ),
    ):
        op.create_index(
            name,
            "scope_bound_readiness_convergences",
            columns,
        )


def downgrade() -> None:
    op.drop_table("scope_bound_readiness_convergences")
