"""Enterprise payroll artifacts, hierarchy and integration ledgers.

Revision ID: 0004_enterprise_artifacts
Revises: 0003_p1_payroll_line_provenance
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_enterprise_artifacts"
down_revision = "0003_p1_payroll_line_provenance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organization_units",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("code", name="uq_organization_unit_code"),
    )
    op.create_index("ix_organization_units_code", "organization_units", ["code"], unique=True)
    op.create_index("ix_organization_units_kind", "organization_units", ["kind"])
    op.create_index("ix_organization_units_parent_id", "organization_units", ["parent_id"])

    op.create_table(
        "legal_sources",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("citation", sa.String(300), nullable=False),
        sa.Column("issuer", sa.String(200), nullable=False),
        sa.Column("adoption_date", sa.String(10), nullable=False),
        sa.Column("effective_from", sa.String(10), nullable=False),
        sa.Column("effective_to", sa.String(10), nullable=True),
        sa.Column("document_hash", sa.String(64), nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="review_required"),
    )
    op.create_index("ix_legal_sources_citation", "legal_sources", ["citation"])
    op.create_index("ix_legal_sources_status", "legal_sources", ["status"])

    op.create_table(
        "payroll_artifacts",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("payroll_run_id", sa.Uuid(), nullable=False),
        sa.Column("employee_no", sa.String(50), nullable=False),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("currency_code", sa.String(3), nullable=False),
        sa.Column("personnel_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("personnel_snapshot_hash", sa.String(64), nullable=False),
        sa.Column("rule_pack_version", sa.String(80), nullable=False),
        sa.Column("rule_pack_hash", sa.String(64), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("output_hash", sa.String(64), nullable=False),
        sa.Column("gross", sa.Numeric(24, 4), nullable=False),
        sa.Column("deductions", sa.Numeric(24, 4), nullable=False),
        sa.Column("net", sa.Numeric(24, 4), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="calculated"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("payroll_run_id", "employee_no", name="uq_payroll_artifact_run_employee"),
    )
    op.create_index("ix_payroll_artifacts_payroll_run_id", "payroll_artifacts", ["payroll_run_id"])
    op.create_index("ix_payroll_artifacts_employee_no", "payroll_artifacts", ["employee_no"])
    op.create_index("ix_payroll_artifacts_period", "payroll_artifacts", ["period"])
    op.create_index("ix_payroll_artifacts_output_hash", "payroll_artifacts", ["output_hash"])

    op.create_table(
        "payslip_lines",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("artifact_id", sa.Uuid(), nullable=False),
        sa.Column("employee_no", sa.String(50), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("amount", sa.Numeric(24, 4), nullable=False),
        sa.Column("currency_code", sa.String(3), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("taxable", sa.Boolean(), nullable=False),
        sa.Column("pensionable", sa.Boolean(), nullable=False),
        sa.Column("insurable", sa.Boolean(), nullable=False),
        sa.Column("rule_code", sa.String(80), nullable=True),
        sa.Column("legal_source_id", sa.Uuid(), nullable=True),
        sa.Column("source_record_id", sa.Uuid(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
    )
    op.create_index("ix_payslip_lines_artifact_id", "payslip_lines", ["artifact_id"])
    op.create_index("ix_payslip_lines_employee_no", "payslip_lines", ["employee_no"])
    op.create_index("ix_payslip_lines_code", "payslip_lines", ["code"])
    op.create_index("ix_payslip_lines_legal_source_id", "payslip_lines", ["legal_source_id"])

    op.create_table(
        "payroll_lifecycle_events",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("payroll_run_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("previous_status", sa.String(30), nullable=False),
        sa.Column("new_status", sa.String(30), nullable=False),
        sa.Column("actor_id", sa.String(100), nullable=False),
        sa.Column("organization_unit_id", sa.String(50), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("correlation_id", sa.String(100), nullable=False),
        sa.Column("idempotency_key", sa.String(150), nullable=False),
        sa.Column("evidence_hash", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("payroll_run_id", "sequence_no", name="uq_payroll_lifecycle_sequence"),
        sa.UniqueConstraint("payroll_run_id", "idempotency_key", name="uq_payroll_lifecycle_idempotency"),
    )
    op.create_index("ix_payroll_lifecycle_run", "payroll_lifecycle_events", ["payroll_run_id"])
    op.create_index("ix_payroll_lifecycle_actor", "payroll_lifecycle_events", ["actor_id"])
    op.create_index("ix_payroll_lifecycle_correlation", "payroll_lifecycle_events", ["correlation_id"])

    op.create_table(
        "sensitive_identities",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("national_id_ciphertext", sa.Text(), nullable=False),
        sa.Column("national_id_lookup_hmac", sa.String(128), nullable=False),
        sa.Column("bank_account_ciphertext", sa.Text(), nullable=True),
        sa.Column("bank_account_lookup_hmac", sa.String(128), nullable=True),
        sa.Column("key_version", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("employee_id", name="uq_sensitive_identity_employee"),
    )
    op.create_index("ix_sensitive_identities_lookup", "sensitive_identities", ["national_id_lookup_hmac"])

    op.create_table(
        "outbox_messages",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("operation", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("correlation_id", sa.String(100), nullable=False),
        sa.Column("idempotency_key", sa.String(150), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("idempotency_key", name="uq_outbox_idempotency"),
    )
    op.create_index("ix_outbox_status", "outbox_messages", ["status"])
    op.create_index("ix_outbox_provider", "outbox_messages", ["provider"])

    op.create_table(
        "inbox_messages",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("external_id", sa.String(150), nullable=False),
        sa.Column("correlation_id", sa.String(100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="received"),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("provider", "external_id", name="uq_inbox_provider_external"),
    )
    op.create_index("ix_inbox_correlation", "inbox_messages", ["correlation_id"])

    op.create_table(
        "integration_receipts",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("operation", sa.String(100), nullable=False),
        sa.Column("correlation_id", sa.String(100), nullable=False),
        sa.Column("idempotency_key", sa.String(150), nullable=False),
        sa.Column("external_id", sa.String(150), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_integration_receipts_correlation", "integration_receipts", ["correlation_id"])
    op.create_index("ix_integration_receipts_idempotency", "integration_receipts", ["idempotency_key"])

    op.create_table(
        "payment_batches",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("payroll_run_id", sa.Uuid(), nullable=False),
        sa.Column("batch_reference", sa.String(100), nullable=False),
        sa.Column("currency_code", sa.String(3), nullable=False),
        sa.Column("amount", sa.Numeric(24, 4), nullable=False),
        sa.Column("beneficiary_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("payroll_run_id", name="uq_payment_batch_run"),
        sa.UniqueConstraint("batch_reference", name="uq_payment_batch_reference"),
    )
    op.create_index("ix_payment_batches_run", "payment_batches", ["payroll_run_id"])
    op.create_index("ix_payment_batches_reference", "payment_batches", ["batch_reference"])

    op.create_table(
        "bank_reconciliations",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("payment_batch_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(150), nullable=False),
        sa.Column("expected_amount", sa.Numeric(24, 4), nullable=False),
        sa.Column("settled_amount", sa.Numeric(24, 4), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="unreconciled"),
        sa.Column("difference", sa.Numeric(24, 4), nullable=False, server_default="0"),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("reconciled_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_bank_reconciliations_payment_batch", "bank_reconciliations", ["payment_batch_id"])
    op.create_index("ix_bank_reconciliations_status", "bank_reconciliations", ["status"])


def downgrade() -> None:
    for table in [
        "bank_reconciliations", "payment_batches", "integration_receipts", "inbox_messages",
        "outbox_messages", "sensitive_identities", "payroll_lifecycle_events", "payslip_lines",
        "payroll_artifacts", "legal_sources", "organization_units",
    ]:
        op.drop_table(table)
