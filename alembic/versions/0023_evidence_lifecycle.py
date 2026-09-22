"""Persist evidence lifecycle supersession links.

Revision ID: 0023_evidence_lifecycle
Revises: 0022_authoritative_evidence_submissions
"""

from alembic import op
import sqlalchemy as sa

revision = "0023_evidence_lifecycle"
down_revision = "0022_authoritative_evidence_submissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "authoritative_evidence_lifecycle_events",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "predecessor_evidence_id",
            sa.String(120),
            sa.ForeignKey(
                "authoritative_evidence_submissions.evidence_id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column(
            "successor_evidence_id",
            sa.String(120),
            sa.ForeignKey(
                "authoritative_evidence_submissions.evidence_id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column("linked_by", sa.String(100), nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.UniqueConstraint(
            "predecessor_evidence_id",
            name="uq_evidence_lifecycle_predecessor",
        ),
        sa.UniqueConstraint(
            "successor_evidence_id",
            name="uq_evidence_lifecycle_successor",
        ),
        sa.UniqueConstraint(
            "fingerprint",
            name="uq_evidence_lifecycle_fingerprint",
        ),
    )
    op.create_index(
        "ix_evidence_lifecycle_predecessor",
        "authoritative_evidence_lifecycle_events",
        ["predecessor_evidence_id"],
    )
    op.create_index(
        "ix_evidence_lifecycle_successor",
        "authoritative_evidence_lifecycle_events",
        ["successor_evidence_id"],
    )
    op.create_index(
        "ix_evidence_lifecycle_linked_by",
        "authoritative_evidence_lifecycle_events",
        ["linked_by"],
    )
    op.create_index(
        "ix_evidence_lifecycle_linked_at",
        "authoritative_evidence_lifecycle_events",
        ["linked_at"],
    )
    op.create_index(
        "ix_evidence_lifecycle_fingerprint",
        "authoritative_evidence_lifecycle_events",
        ["fingerprint"],
    )


def downgrade() -> None:
    op.drop_table("authoritative_evidence_lifecycle_events")
