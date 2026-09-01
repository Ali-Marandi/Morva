from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class EmployeeRecord(Base):
    __tablename__ = "employees"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    employee_no: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    national_id: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    employment_type: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), default="active")
    organization_unit_id: Mapped[str] = mapped_column(String(50), index=True)
    position_id: Mapped[str] = mapped_column(String(50), index=True)
    hire_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class SalaryRuleRecord(Base):
    __tablename__ = "salary_rules"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(200))
    version: Mapped[str] = mapped_column(String(50), index=True)
    effective_from: Mapped[date] = mapped_column(Date, index=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    formula: Mapped[str] = mapped_column(Text)
    taxable: Mapped[bool] = mapped_column(Boolean, default=False)
    pensionable: Mapped[bool] = mapped_column(Boolean, default=False)
    insurable: Mapped[bool] = mapped_column(Boolean, default=False)
    legal_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_status: Mapped[str] = mapped_column(String(30), default="review_required", index=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class RulePackRecord(Base):
    __tablename__ = "rule_packs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    version: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    legal_source_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rules_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class PayrollRunRecord(Base):
    __tablename__ = "payroll_runs"
    __table_args__ = (UniqueConstraint("period", "organization_unit_id", name="uq_payroll_run_period_org"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    period: Mapped[str] = mapped_column(String(7), index=True)
    organization_unit_id: Mapped[str] = mapped_column(String(50), index=True)
    ruleset_version: Mapped[str] = mapped_column(String(50))
    ruleset_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    currency_code: Mapped[str] = mapped_column(String(3), default="IRR")
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    input_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    output_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reviewed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    exported_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    submitted_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    payment_confirmed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payment_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reconciled_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class PayrollLineRecord(Base):
    __tablename__ = "payroll_lines"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    payroll_run_id: Mapped[UUID] = mapped_column(index=True)
    employee_no: Mapped[str] = mapped_column(String(50), index=True)
    code: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(200))
    amount: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    currency_code: Mapped[str] = mapped_column(String(3), default="IRR")
    kind: Mapped[str] = mapped_column(String(20))
    taxable: Mapped[bool] = mapped_column(Boolean, default=False)
    pensionable: Mapped[bool] = mapped_column(Boolean, default=False)
    insurable: Mapped[bool] = mapped_column(Boolean, default=False)
    rule_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)


class ImportBatchRecord(Base):
    __tablename__ = "import_batches"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_name: Mapped[str] = mapped_column(String(200))
    template_version: Mapped[str] = mapped_column(String(50))
    period: Mapped[str] = mapped_column(String(7), index=True)
    owner: Mapped[str] = mapped_column(String(100))
    file_sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30), default="received", index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)


class ImportIssueRecord(Base):
    __tablename__ = "import_issues"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    import_batch_id: Mapped[UUID] = mapped_column(index=True)
    issue_code: Mapped[str] = mapped_column(String(100), index=True)
    severity: Mapped[str] = mapped_column(String(20))
    record_key: Mapped[str] = mapped_column(String(100), index=True)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="quarantined")
    assigned_to: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class PersonnelOrderRecord(Base):
    __tablename__ = "personnel_orders"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_no: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    employee_no: Mapped[str] = mapped_column(String(50), index=True)
    order_type: Mapped[str] = mapped_column(String(50), index=True)
    issue_date: Mapped[date] = mapped_column(Date)
    effective_date: Mapped[date] = mapped_column(Date, index=True)
    legal_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[date] = mapped_column(Date, default=date.today)


class RetroCaseRecord(Base):
    __tablename__ = "retro_cases"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    employee_no: Mapped[str] = mapped_column(String(50), index=True)
    from_period: Mapped[str] = mapped_column(String(7))
    to_period: Mapped[str] = mapped_column(String(7))
    original_total: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    recalculated_total: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    difference: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[date] = mapped_column(Date, default=date.today)


class AuditChainHeadRecord(Base):
    __tablename__ = "audit_chain_head"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    sequence_no: Mapped[int] = mapped_column(default=0)
    digest: Mapped[str | None] = mapped_column(String(64), nullable=True)


class AuditEventRecord(Base):
    __tablename__ = "audit_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    sequence_no: Mapped[int] = mapped_column(index=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    actor_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(100), index=True)
    entity_id: Mapped[str] = mapped_column(String(100), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    digest: Mapped[str] = mapped_column(String(64))
