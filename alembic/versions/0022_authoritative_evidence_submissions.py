"""Persist authoritative evidence submissions for controlled approval workflow.

Revision ID: 0022_authoritative_evidence_submissions
Revises: 0021_payment_exception_persistence
"""
from alembic import op
import sqlalchemy as sa

revision = "0022_authoritative_evidence_submissions"
down_revision = "0021_payment_exception_persistence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "authoritative_evidence_submissions",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("evidence_id", sa.String(120), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_uri", sa.String(500), nullable=False),
        sa.Column("source_sha256", sa.String(64), nullable=False),
        sa.Column("issuer", sa.String(200), nullable=False),
        sa.Column("population_scope", sa.String(300), nullable=False),
        sa.Column("submission_scope", sa.String(30), nullable=False),
        sa.Column("submission_scope_id", sa.String(100), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("submitted_by", sa.String(100), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_by", sa.String(100), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.UniqueConstraint(
            "evidence_id",
            name="uq_authoritative_evidence_submission_evidence_id",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected')",
            name="ck_authoritative_evidence_submission_status",
        ),
    )
    op.create_index(
        "ix_authoritative_evidence_submissions_evidence_id",
        "authoritative_evidence_submissions",
        ["evidence_id"],
        unique=True,
    )
    op.create_index(
        "ix_authoritative_evidence_submissions_source_type",
        "authoritative_evidence_submissions",
        ["source_type"],
    )
    op.create_index(
        "ix_authoritative_evidence_submissions_source_sha256",
        "authoritative_evidence_submissions",
        ["source_sha256"],
    )
    op.create_index(
        "ix_authoritative_evidence_submissions_population_scope",
        "authoritative_evidence_submissions",
        ["population_scope"],
    )
    op.create_index(
        "ix_authoritative_evidence_submissions_submission_scope",
        "authoritative_evidence_submissions",
        ["submission_scope"],
    )
    op.create_index(
        "ix_authoritative_evidence_submissions_submission_scope_id",
        "authoritative_evidence_submissions",
        ["submission_scope_id"],
    )
    op.create_index(
        "ix_authoritative_evidence_submissions_effective_from",
        "authoritative_evidence_submissions",
        ["effective_from"],
    )
    op.create_index(
        "ix_authoritative_evidence_submissions_status",
        "authoritative_evidence_submissions",
        ["status"],
    )
    op.create_index(
        "ix_authoritative_evidence_submissions_submitted_by",
        "authoritative_evidence_submissions",
        ["submitted_by"],
    )
    op.create_index(
        "ix_authoritative_evidence_submissions_fingerprint",
        "authoritative_evidence_submissions",
        ["fingerprint"],
    )


def downgrade() -> None:
    op.drop_table("authoritative_evidence_submissions")
