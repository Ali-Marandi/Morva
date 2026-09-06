from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base


class EmploymentRecord(Base):
    __tablename__ = "employments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    employee_no: Mapped[str] = mapped_column(String(50), index=True)
    employment_type: Mapped[str] = mapped_column(String(30))
    organization_unit_id: Mapped[str] = mapped_column(String(50), index=True)
    position_id: Mapped[str] = mapped_column(String(50), index=True)
    starts_on: Mapped[date] = mapped_column(Date, index=True)
    ends_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active")
    source_record_id: Mapped[UUID | None] = mapped_column(nullable=True)
    source_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
