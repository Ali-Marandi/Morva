from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, Numeric, String, Text
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
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


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
