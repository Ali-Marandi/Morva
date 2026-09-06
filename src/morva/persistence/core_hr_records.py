from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

from sqlalchemy import Date, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base


class EducationRecord(Base):
    __tablename__ = "employee_education"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    employee_no: Mapped[str] = mapped_column(String(50), index=True)
    level: Mapped[str] = mapped_column(String(30), index=True)
    field_of_study: Mapped[str] = mapped_column(String(200))
    institution: Mapped[str] = mapped_column(String(200))
    completed_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    certificate_reference: Mapped[str | None] = mapped_column(String(150), nullable=True)


class ExperienceRecord(Base):
    __tablename__ = "employee_experience"
    __table_args__ = (
        UniqueConstraint(
            "employee_no", "organization_name", "starts_on", name="uq_employee_experience_period"
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    employee_no: Mapped[str] = mapped_column(String(50), index=True)
    experience_type: Mapped[str] = mapped_column(String(30), index=True)
    organization_name: Mapped[str] = mapped_column(String(200))
    starts_on: Mapped[date] = mapped_column(Date, index=True)
    ends_on: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    reference: Mapped[str | None] = mapped_column(String(150), nullable=True)


class DependentRecord(Base):
    __tablename__ = "employee_dependents"
    __table_args__ = (
        UniqueConstraint("employee_no", "name", "relationship", name="uq_employee_dependent_identity"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    employee_no: Mapped[str] = mapped_column(String(50), index=True)
    relationship: Mapped[str] = mapped_column(String(30), index=True)
    name: Mapped[str] = mapped_column(String(200))
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
