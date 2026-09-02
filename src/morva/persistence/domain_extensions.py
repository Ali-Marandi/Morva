from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base


class TeacherRankCaseRecord(Base):
    __tablename__ = "teacher_rank_cases"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    employee_no: Mapped[str] = mapped_column(String(50), index=True)
    current_rank: Mapped[str | None] = mapped_column(String(50), nullable=True)
    proposed_rank: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    effect_period: Mapped[str] = mapped_column(String(7), index=True)
    assessment_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    committee_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    appeal_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    decision_reference: Mapped[str | None] = mapped_column(String(150), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AttendanceFactRecord(Base):
    __tablename__ = "attendance_facts"
    __table_args__ = (UniqueConstraint("employee_no", "period", "source_record_key", name="uq_attendance_employee_period_source"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    employee_no: Mapped[str] = mapped_column(String(50), index=True)
    period: Mapped[str] = mapped_column(String(7), index=True)
    source_record_key: Mapped[str] = mapped_column(String(150))
    worked_units: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"))
    leave_units: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"))
    absence_units: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(30), default="received", index=True)
    source_hash: Mapped[str] = mapped_column(String(64))
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)


class VariableEarningRecord(Base):
    __tablename__ = "variable_earnings"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    employee_no: Mapped[str] = mapped_column(String(50), index=True)
    period: Mapped[str] = mapped_column(String(7), index=True)
    component_code: Mapped[str] = mapped_column(String(80), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    currency_code: Mapped[str] = mapped_column(String(3), default="IRR")
    source_record_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    approval_status: Mapped[str] = mapped_column(String(30), default="review_required", index=True)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)


class DeductionLedgerRecord(Base):
    __tablename__ = "deduction_ledgers"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    employee_no: Mapped[str] = mapped_column(String(50), index=True)
    period: Mapped[str] = mapped_column(String(7), index=True)
    deduction_code: Mapped[str] = mapped_column(String(80), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    currency_code: Mapped[str] = mapped_column(String(3), default="IRR")
    authority_reference: Mapped[str | None] = mapped_column(String(150), nullable=True)
    source_record_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="review_required", index=True)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)


class LoanRecord(Base):
    __tablename__ = "loans"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    employee_no: Mapped[str] = mapped_column(String(50), index=True)
    lender_code: Mapped[str] = mapped_column(String(80), index=True)
    loan_reference: Mapped[str] = mapped_column(String(150), unique=True)
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    remaining_balance: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    installment_amount: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    currency_code: Mapped[str] = mapped_column(String(3), default="IRR")
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    source_hash: Mapped[str] = mapped_column(String(64))


class InsuranceLedgerRecord(Base):
    __tablename__ = "insurance_ledgers"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    employee_no: Mapped[str] = mapped_column(String(50), index=True)
    period: Mapped[str] = mapped_column(String(7), index=True)
    scheme_code: Mapped[str] = mapped_column(String(80), index=True)
    employee_amount: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    employer_amount: Mapped[Decimal] = mapped_column(Numeric(24, 4), default=Decimal("0"))
    currency_code: Mapped[str] = mapped_column(String(3), default="IRR")
    status: Mapped[str] = mapped_column(String(30), default="review_required", index=True)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)


class PensionLedgerRecord(Base):
    __tablename__ = "pension_ledgers"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    employee_no: Mapped[str] = mapped_column(String(50), index=True)
    period: Mapped[str] = mapped_column(String(7), index=True)
    fund_code: Mapped[str] = mapped_column(String(80), index=True)
    pensionable_base: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    employee_amount: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    employer_amount: Mapped[Decimal] = mapped_column(Numeric(24, 4), default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(30), default="review_required", index=True)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)


class TaxLedgerRecord(Base):
    __tablename__ = "tax_ledgers"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    employee_no: Mapped[str] = mapped_column(String(50), index=True)
    period: Mapped[str] = mapped_column(String(7), index=True)
    taxable_base: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    currency_code: Mapped[str] = mapped_column(String(3), default="IRR")
    rule_pack_version: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(30), default="review_required", index=True)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)


class AccountingBatchRecord(Base):
    __tablename__ = "accounting_batches"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    payroll_run_id: Mapped[UUID] = mapped_column(index=True)
    document_reference: Mapped[str] = mapped_column(String(150), unique=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    currency_code: Mapped[str] = mapped_column(String(3), default="IRR")
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    external_id: Mapped[str | None] = mapped_column(String(150), nullable=True)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)


class TreasuryRequestRecord(Base):
    __tablename__ = "treasury_requests"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    payroll_run_id: Mapped[UUID] = mapped_column(index=True)
    request_reference: Mapped[str] = mapped_column(String(150), unique=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    currency_code: Mapped[str] = mapped_column(String(3), default="IRR")
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    external_id: Mapped[str | None] = mapped_column(String(150), nullable=True)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)


class BankSettlementRecord(Base):
    __tablename__ = "bank_settlements"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    payment_batch_id: Mapped[UUID] = mapped_column(index=True)
    external_id: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    expected_amount: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    settled_amount: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    status: Mapped[str] = mapped_column(String(30), default="received", index=True)
    return_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)


class EmployeeCaseRecord(Base):
    __tablename__ = "employee_cases"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    employee_no: Mapped[str] = mapped_column(String(50), index=True)
    case_type: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)
    rule_reference: Mapped[str | None] = mapped_column(String(150), nullable=True)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
