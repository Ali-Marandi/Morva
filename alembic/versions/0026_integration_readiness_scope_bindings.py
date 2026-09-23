"""Bind persisted integration readiness receipts to organization scope.

Revision ID: 0026_integration_readiness_scope_bindings
Revises: 0025_integration_execution_readiness_verifications
"""

from hashlib import sha256

from alembic import op
import sqlalchemy as sa

revision = "0026_integration_readiness_scope_bindings"
down_revision = "0025_integration_execution_readiness_verifications"
branch_labels = None
depends_on = None


def _scope_binding_fingerprint(
    verification_fingerprint: str,
    organization_scope: str,
    organization_scope_id: str,
) -> str:
    canonical = (
        "readiness-scope-binding:v1:"
        f"{verification_fingerprint.lower()}:{organization_scope}:{organization_scope_id}"
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


def upgrade() -> None:
    op.add_column(
        "integration_execution_readiness_verifications",
        sa.Column("organization_scope", sa.String(20), nullable=True),
    )
    op.add_column(
        "integration_execution_readiness_verifications",
        sa.Column("organization_scope_id", sa.String(100), nullable=True),
    )
    op.add_column(
        "integration_execution_readiness_verifications",
        sa.Column("scope_binding_fingerprint", sa.String(64), nullable=True),
    )

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT id, verification_fingerprint
            FROM integration_execution_readiness_verifications
            """
        )
    ).mappings().all()

    for row in rows:
        scope = "ministry"
        scope_id = "ministry"
        fingerprint = _scope_binding_fingerprint(
            row["verification_fingerprint"],
            scope,
            scope_id,
        )
        bind.execute(
            sa.text(
                """
                UPDATE integration_execution_readiness_verifications
                SET organization_scope = :scope,
                    organization_scope_id = :scope_id,
                    scope_binding_fingerprint = :fingerprint
                WHERE id = :id
                """
            ),
            {
                "scope": scope,
                "scope_id": scope_id,
                "fingerprint": fingerprint,
                "id": row["id"],
            },
        )

    op.alter_column(
        "integration_execution_readiness_verifications",
        "organization_scope",
        existing_type=sa.String(20),
        nullable=False,
    )
    op.alter_column(
        "integration_execution_readiness_verifications",
        "organization_scope_id",
        existing_type=sa.String(100),
        nullable=False,
    )
    op.alter_column(
        "integration_execution_readiness_verifications",
        "scope_binding_fingerprint",
        existing_type=sa.String(64),
        nullable=False,
    )

    op.create_index(
        "ix_integration_readiness_verification_organization_scope",
        "integration_execution_readiness_verifications",
        ["organization_scope"],
    )
    op.create_index(
        "ix_integration_readiness_verification_organization_scope_id",
        "integration_execution_readiness_verifications",
        ["organization_scope_id"],
    )
    op.create_index(
        "ix_integration_readiness_verification_scope_binding_fingerprint",
        "integration_execution_readiness_verifications",
        ["scope_binding_fingerprint"],
    )
    op.create_unique_constraint(
        "uq_integration_readiness_scope_binding_fingerprint",
        "integration_execution_readiness_verifications",
        ["scope_binding_fingerprint"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_integration_readiness_scope_binding_fingerprint",
        "integration_execution_readiness_verifications",
        type_="unique",
    )
    op.drop_index(
        "ix_integration_readiness_verification_scope_binding_fingerprint",
        table_name="integration_execution_readiness_verifications",
    )
    op.drop_index(
        "ix_integration_readiness_verification_organization_scope_id",
        table_name="integration_execution_readiness_verifications",
    )
    op.drop_index(
        "ix_integration_readiness_verification_organization_scope",
        table_name="integration_execution_readiness_verifications",
    )
    op.drop_column(
        "integration_execution_readiness_verifications",
        "scope_binding_fingerprint",
    )
    op.drop_column(
        "integration_execution_readiness_verifications",
        "organization_scope_id",
    )
    op.drop_column(
        "integration_execution_readiness_verifications",
        "organization_scope",
    )
