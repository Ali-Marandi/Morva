from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base


class PositionRecord(Base):
    __tablename__ = "positions"
    __table_args__ = (
        UniqueConstraint("code", name="uq_position_code"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(50), index=True)
    title: Mapped[str] = mapped_column(String(200))
    occupational_group: Mapped[str] = mapped_column(String(100), index=True)
    grade: Mapped[int | None] = mapped_column(nullable=True)
    job_points: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"))
    full_time_educational: Mapped[bool] = mapped_column(Boolean, default=False)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
