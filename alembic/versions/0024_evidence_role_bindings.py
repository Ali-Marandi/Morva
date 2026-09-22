"""Persist certification-role evidence bindings.

Revision ID: 0024_evidence_role_bindings
Revises: 0023_evidence_lifecycle
"""

from alembic import op
import sqlalchemy as sa

revision = "0024_evidence_role_bindings"
down_revision = "0023_evidence_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "authoritative_evidence_role_bindings",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("certification_role", sa.String(60), nullable=False),
        sa.Column(
            "authoritative_evidence_id",
            sa.String(120),
            sa.ForeignKey(
                "authoritative_evidence_submissions.evidence_id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column("binding_kind", sa.String(100), nullable=False),
        sa.Column("binding_fingerprint", sa.String(64), nullable=False),
        sa.Column("registry_fingerprint", sa.String(64), nullable=False),
        sa.Column("population_scope", sa.String(300), nullable=False),
        sa.Column("submission_scope", sa.String(30), nullable=False),
        sa.Column("submission_scope_id", sa.String(100), nullable=False),
        sa.Column("bound_by", sa.String(100), nullable=False),
        sa.Column("bound_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "certification_role",
            "registry_fingerprint",
            "submission_scope",
            "submission_scope_id",
            name="uq_evidence_role_binding_registry_scope",
        ),
        sa.UniqueConstraint(
            "binding_fingerprint",
            name="uq_evidence_role_binding_fingerprint",
        ),
    )
    op.create_index(
        "ix_evidence_role_binding_role",
        "authoritative_evidence_role_bindings",
        ["certification_role"],
    )
    op.create_index(
        "ix_evidence_role_binding_evidence_id",
        "authoritative_evidence_role_bindings",
        ["authoritative_evidence_id"],
    )
    op.create_index(
        "ix_evidence_role_binding_binding_fingerprint",
        "authoritative_evidence_role_bindings",
        ["binding_fingerprint"],
    )
    op.create_index(
        "ix_evidence_role_binding_registry_fingerprint",
        "authoritative_evidence_role_bindings",
        ["registry_fingerprint"],
    )
    op.create_index(
        "ix_evidence_role_binding_submission_scope",
        "authoritative_evidence_role_bindings",
        ["submission_scope"],
    )
    op.create_index(
        "ix_evidence_role_binding_submission_scope_id",
        "authoritative_evidence_role_bindings",
        ["submission_scope_id"],
    )
    op.create_index(
        "ix_evidence_role_binding_bound_by",
        "authoritative_evidence_role_bindings",
        ["bound_by"],
    )
    op.create_index(
        "ix_evidence_role_binding_bound_at",
        "authoritative_evidence_role_bindings",
        ["bound_at"],
    )


def downgrade() -> None:
    op.drop_table("authoritative_evidence_role_bindings")
