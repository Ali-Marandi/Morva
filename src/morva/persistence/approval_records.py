from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base


class PersonnelOrderApprovalPolicyRecord(Base):
    """Persisted organizational approval policy bound to personnel-order decisions."""

    __tablename__ = "personnel_order_approval_policies"
    __table_args__ = (UniqueConstraint("policy_code", "version", name="uq_personnel_order_approval_policy_version"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    policy_code: Mapped[str] = mapped_column(String(100), index=True)
    version: Mapped[str] = mapped_column(String(50), index=True)
    order_types: Mapped[list] = mapped_column(JSON, default=list)
    required_submission_role: Mapped[str] = mapped_column(String(100))
    required_decision_role: Mapped[str] = mapped_column(String(100))
    source_reference: Mapped[str] = mapped_column(Text)
    source_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30), default="review_required", index=True)
    approved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    policy_hash: Mapped[str] = mapped_column(String(64), index=True)


class PersonnelOrderSubmissionRecord(Base):
    """Immutable submission provenance for a personnel order."""

    __tablename__ = "personnel_order_submissions"
    __table_args__ = (UniqueConstraint("order_id", name="uq_personnel_order_submission_order"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(index=True)
    order_no: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    submitted_by: Mapped[str] = mapped_column(String(100), index=True)
    submitted_role: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    order_fingerprint: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    approval_policy_code: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    approval_policy_hash: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)


class PersonnelOrderDecisionRecord(Base):
    """Append-only final decision. At most one decision exists for an order."""

    __tablename__ = "personnel_order_decisions"
    __table_args__ = (UniqueConstraint("order_id", name="uq_personnel_order_decision_order"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(index=True)
    order_no: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    decision: Mapped[str] = mapped_column(String(20))
    decided_by: Mapped[str] = mapped_column(String(100), index=True)
    decided_role: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    order_fingerprint: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    approval_policy_code: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    approval_policy_hash: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
