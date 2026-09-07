from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base


class PersonnelOrderSubmissionRecord(Base):
    """Immutable submission provenance for a personnel order."""

    __tablename__ = "personnel_order_submissions"
    __table_args__ = (UniqueConstraint("order_id", name="uq_personnel_order_submission_order"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(index=True)
    order_no: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    submitted_by: Mapped[str] = mapped_column(String(100), index=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PersonnelOrderDecisionRecord(Base):
    """Append-only final decision. At most one decision exists for an order."""

    __tablename__ = "personnel_order_decisions"
    __table_args__ = (UniqueConstraint("order_id", name="uq_personnel_order_decision_order"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(index=True)
    order_no: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    decision: Mapped[str] = mapped_column(String(20))
    decided_by: Mapped[str] = mapped_column(String(100), index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
