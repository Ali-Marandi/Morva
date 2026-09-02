"""Enterprise payroll domain ledger tables

Revision ID: 0008_enterprise_domain_ledgers
Revises: 0007_payslip_line_sequence
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_enterprise_domain_ledgers"
down_revision = "0007_payslip_line_sequence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "teacher_rank_cases",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("employee_no", sa.String(length=50), nullable=False),
        sa.Column("current_rank", sa.String(length=50), nullable=True),
        sa.Column("proposed_rank", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"),
        sa.Column("effect_period", sa.String(length=7), nullable=False),
        sa.Column("assessment_payload", sa.JSON(), nullable=False),
        sa.Column("committee_payload", sa.JSON(), nullable=False),
        sa.Column("appeal_payload", sa.JSON(), nullable=False),
        sa.Column("decision_reference", sa.String(length=150), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_teacher_rank_cases_employee_no", "teacher_rank_cases", ["employee_no"])
    op.create_index("ix_teacher_rank_cases_effect_period", "teacher_rank_cases", ["effect_period"])

    op.create_table(
        "attendance_facts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("employee_no", sa.String(length=50), nullable=False),
        sa.Column("period", sa.String(length=7), nullable=False),
        sa.Column("source_record_key", sa.String(length=150), nullable=False),
        sa.Column("worked_units", sa.Numeric(20, 4), nullable=False),
        sa.Column("leave_units", sa.Numeric(20, 4), nullable=False),
        sa.Column("absence_units", sa.Numeric(20, 4), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="received"),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.UniqueConstraint("employee_no", "period", "source_record_key", name="uq_attendance_employee_period_source"),
    )
    op.create_index("ix_attendance_facts_employee_no", "attendance_facts", ["employee_no"])
    op.create_index("ix_attendance_facts_period", "attendance_facts", ["period"])

    op.create_table(
        "variable_earnings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("employee_no", sa.String(length=50), nullable=False),
        sa.Column("period", sa.String(length=7), nullable=False),
        sa.Column("component_code", sa.String(length=80), nullable=False),
        sa.Column("amount", sa.Numeric(24, 4), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("source_record_id", sa.Uuid(), nullable=True),
        sa.Column("approval_status", sa.String(length=30), nullable=False, server_default="review_required"),
        sa.Column("evidence", sa.JSON(), nullable=False),
    )
    op.create_index("ix_variable_earnings_employee_no", "variable_earnings", ["employee_no"])
    op.create_index("ix_variable_earnings_period", "variable_earnings", ["period"])
    op.create_index("ix_variable_earnings_component_code", "variable_earnings", ["component_code"])

    op.create_table(
        "deduction_ledgers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("employee_no", sa.String(length=50), nullable=False),
        sa.Column("period", sa.String(length=7), nullable=False),
        sa.Column("deduction_code", sa.String(length=80), nullable=False),
        sa.Column("amount", sa.Numeric(24, 4), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("authority_reference", sa.String(length=150), nullable=True),
        sa.Column("source_record_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="review_required"),
        sa.Column("evidence", sa.JSON(), nullable=False),
    )
    op.create_index("ix_deduction_ledgers_employee_no", "deduction_ledgers", ["employee_no"])
    op.create_index("ix_deduction_ledgers_period", "deduction_ledgers", ["period"])
    op.create_index("ix_deduction_ledgers_deduction_code", "deduction_ledgers", ["deduction_code"])

    op.create_table(
        "loans",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("employee_no", sa.String(length=50), nullable=False),
        sa.Column("lender_code", sa.String(length=80), nullable=False),
        sa.Column("loan_reference", sa.String(length=150), nullable=False, unique=True),
        sa.Column("opening_balance", sa.Numeric(24, 4), nullable=False),
        sa.Column("remaining_balance", sa.Numeric(24, 4), nullable=False),
        sa.Column("installment_amount", sa.Numeric(24, 4), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_loans_employee_no", "loans", ["employee_no"])
    op.create_index("ix_loans_lender_code", "loans", ["lender_code"])

    op.create_table(
        "insurance_ledgers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("employee_no", sa.String(length=50), nullable=False),
        sa.Column("period", sa.String(length=7), nullable=False),
        sa.Column("scheme_code", sa.String(length=80), nullable=False),
        sa.Column("employee_amount", sa.Numeric(24, 4), nullable=False),
        sa.Column("employer_amount", sa.Numeric(24, 4), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="review_required"),
        sa.Column("evidence", sa.JSON(), nullable=False),
    )
    op.create_index("ix_insurance_ledgers_employee_no", "insurance_ledgers", ["employee_no"])
    op.create_index("ix_insurance_ledgers_period", "insurance_ledgers", ["period"])
    op.create_index("ix_insurance_ledgers_scheme_code", "insurance_ledgers", ["scheme_code"])

    op.create_table(
        "pension_ledgers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("employee_no", sa.String(length=50), nullable=False),
        sa.Column("period", sa.String(length=7), nullable=False),
        sa.Column("fund_code", sa.String(length=80), nullable=False),
        sa.Column("pensionable_base", sa.Numeric(24, 4), nullable=False),
        sa.Column("employee_amount", sa.Numeric(24, 4), nullable=False),
        sa.Column("employer_amount", sa.Numeric(24, 4), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="review_required"),
        sa.Column("evidence", sa.JSON(), nullable=False),
    )
    op.create_index("ix_pension_ledgers_employee_no", "pension_ledgers", ["employee_no"])
    op.create_index("ix_pension_ledgers_period", "pension_ledgers", ["period"])
    op.create_index("ix_pension_ledgers_fund_code", "pension_ledgers", ["fund_code"])

    op.create_table(
        "tax_ledgers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("employee_no", sa.String(length=50), nullable=False),
        sa.Column("period", sa.String(length=7), nullable=False),
        sa.Column("taxable_base", sa.Numeric(24, 4), nullable=False),
        sa.Column("tax_amount", sa.Numeric(24, 4), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("rule_pack_version", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="review_required"),
        sa.Column("evidence", sa.JSON(), nullable=False),
    )
    op.create_index("ix_tax_ledgers_employee_no", "tax_ledgers", ["employee_no"])
    op.create_index("ix_tax_ledgers_period", "tax_ledgers", ["period"])

    op.create_table(
        "accounting_batches",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("payroll_run_id", sa.Uuid(), nullable=False),
        sa.Column("document_reference", sa.String(length=150), nullable=False, unique=True),
        sa.Column("amount", sa.Numeric(24, 4), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("external_id", sa.String(length=150), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=False),
    )
    op.create_index("ix_accounting_batches_payroll_run_id", "accounting_batches", ["payroll_run_id"])

    op.create_table(
        "treasury_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("payroll_run_id", sa.Uuid(), nullable=False),
        sa.Column("request_reference", sa.String(length=150), nullable=False, unique=True),
        sa.Column("amount", sa.Numeric(24, 4), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("external_id", sa.String(length=150), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=False),
    )
    op.create_index("ix_treasury_requests_payroll_run_id", "treasury_requests", ["payroll_run_id"])

    op.create_table(
        "bank_settlements",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("payment_batch_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(length=150), nullable=False, unique=True),
        sa.Column("expected_amount", sa.Numeric(24, 4), nullable=False),
        sa.Column("settled_amount", sa.Numeric(24, 4), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="received"),
        sa.Column("return_reason", sa.Text(), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=False),
    )
    op.create_index("ix_bank_settlements_payment_batch_id", "bank_settlements", ["payment_batch_id"])
    op.create_index("ix_bank_settlements_external_id", "bank_settlements", ["external_id"])

    op.create_table(
        "employee_cases",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("employee_no", sa.String(length=50), nullable=False),
        sa.Column("case_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="open"),
        sa.Column("rule_reference", sa.String(length=150), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_employee_cases_employee_no", "employee_cases", ["employee_no"])
    op.create_index("ix_employee_cases_case_type", "employee_cases", ["case_type"])
    op.create_index("ix_employee_cases_status", "employee_cases", ["status"])


def downgrade() -> None:
    op.drop_index("ix_employee_cases_status", table_name="employee_cases")
    op.drop_index("ix_employee_cases_case_type", table_name="employee_cases")
    op.drop_index("ix_employee_cases_employee_no", table_name="employee_cases")
    op.drop_table("employee_cases")

    op.drop_index("ix_bank_settlements_external_id", table_name="bank_settlements")
    op.drop_index("ix_bank_settlements_payment_batch_id", table_name="bank_settlements")
    op.drop_table("bank_settlements")

    op.drop_index("ix_treasury_requests_payroll_run_id", table_name="treasury_requests")
    op.drop_table("treasury_requests")

    op.drop_index("ix_accounting_batches_payroll_run_id", table_name="accounting_batches")
    op.drop_table("accounting_batches")

    op.drop_index("ix_tax_ledgers_period", table_name="tax_ledgers")
    op.drop_index("ix_tax_ledgers_employee_no", table_name="tax_ledgers")
    op.drop_table("tax_ledgers")

    op.drop_index("ix_pension_ledgers_fund_code", table_name="pension_ledgers")
    op.drop_index("ix_pension_ledgers_period", table_name="pension_ledgers")
    op.drop_index("ix_pension_ledgers_employee_no", table_name="pension_ledgers")
    op.drop_table("pension_ledgers")

    op.drop_index("ix_insurance_ledgers_scheme_code", table_name="insurance_ledgers")
    op.drop_index("ix_insurance_ledgers_period", table_name="insurance_ledgers")
    op.drop_index("ix_insurance_ledgers_employee_no", table_name="insurance_ledgers")
    op.drop_table("insurance_ledgers")

    op.drop_index("ix_loans_lender_code", table_name="loans")
    op.drop_index("ix_loans_employee_no", table_name="loans")
    op.drop_table("loans")

    op.drop_index("ix_deduction_ledgers_deduction_code", table_name="deduction_ledgers")
    op.drop_index("ix_deduction_ledgers_period", table_name="deduction_ledgers")
    op.drop_index("ix_deduction_ledgers_employee_no", table_name="deduction_ledgers")
    op.drop_table("deduction_ledgers")

    op.drop_index("ix_variable_earnings_component_code", table_name="variable_earnings")
    op.drop_index("ix_variable_earnings_period", table_name="variable_earnings")
    op.drop_index("ix_variable_earnings_employee_no", table_name="variable_earnings")
    op.drop_table("variable_earnings")

    op.drop_index("ix_attendance_facts_period", table_name="attendance_facts")
    op.drop_index("ix_attendance_facts_employee_no", table_name="attendance_facts")
    op.drop_table("attendance_facts")

    op.drop_index("ix_teacher_rank_cases_effect_period", table_name="teacher_rank_cases")
    op.drop_index("ix_teacher_rank_cases_employee_no", table_name="teacher_rank_cases")
    op.drop_table("teacher_rank_cases")
