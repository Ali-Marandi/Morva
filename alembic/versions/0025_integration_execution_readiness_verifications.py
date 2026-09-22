"""Persist independently verified integration readiness receipts.

Revision ID: 0025_integration_execution_readiness_verifications
Revises: 0024_evidence_role_bindings
"""

from alembic import op
import sqlalchemy as sa

revision = "0025_integration_execution_readiness_verifications"
down_revision = "0024_evidence_role_bindings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "integration_execution_readiness_verifications",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("assessment_version", sa.Integer(), nullable=False),
        sa.Column("repository", sa.String(200), nullable=False),
        sa.Column("candidate_sha", sa.String(40), nullable=False),
        sa.Column("target_environment", sa.String(20), nullable=False),
        sa.Column(
            "assessment_checked_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "evidence_readiness_fingerprint",
            sa.String(64),
            nullable=False,
        ),
        sa.Column("binding_fingerprint", sa.String(64), nullable=False),
        sa.Column(
            "binding_verification_fingerprint",
            sa.String(64),
            nullable=False,
        ),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("blockers", sa.JSON(), nullable=False),
        sa.Column("assessment_fingerprint", sa.String(64), nullable=False),
        sa.Column("verification_fingerprint", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "verification_fingerprint",
            name="uq_integration_readiness_verification_fingerprint",
        ),
    )
    op.create_index(
        "ix_integration_readiness_verification_repository",
        "integration_execution_readiness_verifications",
        ["repository"],
    )
    op.create_index(
        "ix_integration_readiness_verification_candidate_sha",
        "integration_execution_readiness_verifications",
        ["candidate_sha"],
    )
    op.create_index(
        "ix_integration_readiness_verification_target_environment",
        "integration_execution_readiness_verifications",
        ["target_environment"],
    )
    op.create_index(
        "ix_integration_readiness_verification_assessment_checked_at",
        "integration_execution_readiness_verifications",
        ["assessment_checked_at"],
    )
    op.create_index(
        "ix_integration_readiness_verification_verified_at",
        "integration_execution_readiness_verifications",
        ["verified_at"],
    )
    op.create_index(
        "ix_integration_readiness_verification_evidence_fingerprint",
        "integration_execution_readiness_verifications",
        ["evidence_readiness_fingerprint"],
    )
    op.create_index(
        "ix_integration_readiness_verification_binding_fingerprint",
        "integration_execution_readiness_verifications",
        ["binding_fingerprint"],
    )
    op.create_index(
        "ix_integ_readiness_binding_verification_fp",
        "integration_execution_readiness_verifications",
        ["binding_verification_fingerprint"],
    )
    op.create_index(
        "ix_integration_readiness_verification_state",
        "integration_execution_readiness_verifications",
        ["state"],
    )
    op.create_index(
        "ix_integration_readiness_verification_assessment_fingerprint",
        "integration_execution_readiness_verifications",
        ["assessment_fingerprint"],
    )
    op.create_index(
        "ix_integration_readiness_verification_fingerprint",
        "integration_execution_readiness_verifications",
        ["verification_fingerprint"],
    )


def downgrade() -> None:
    op.drop_table("integration_execution_readiness_verifications")
