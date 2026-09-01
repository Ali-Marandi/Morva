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


class PayrollRunRecord(Base):
    __tablename__ = "payroll_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    period: Mapped[str] = mapped_column(String(7), index=True)
    ruleset_version: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    organization_scope: Mapped[str] = mapped_column(String(80), default="global", index=True)
    source_manifest_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payroll_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    exported_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PayrollRunEventRecord(Base):
    __tablename__ = "payroll_run_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    payroll_run_id: Mapped[UUID] = mapped_column(index=True)
    from_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_status: Mapped[str] = mapped_column(String(40), index=True)
    actor_id: Mapped[str] = mapped_column(String(100), index=True)
    actor_role: Mapped[str] = mapped_column(String(80))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class PayrollLineRecord(Base):
    __tablename__ = "payroll_lines"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    payroll_run_id: Mapped[UUID] = mapped_column(index=True)
    employee_no: Mapped[str] = mapped_column(String(50), index=True)
    code: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(200))
    amount: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    kind: Mapped[str] = mapped_column(String(20))
    rule_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)


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
    __tablename__ = "audit_chain_heads"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    last_sequence_no: Mapped[int] = mapped_column(default=0)
    last_hash: Mapped[str] = mapped_column(String(64), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditEventRecord(Base):
    __tablename__ = "audit_events"
    __table_args__ = (UniqueConstraint("sequence_no", name="uq_audit_event_sequence"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    sequence_no: Mapped[int] = mapped_column(index=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    actor_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(100), index=True)
    entity_id: Mapped[str] = mapped_column(String(100), index=True)
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    current_hash: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
