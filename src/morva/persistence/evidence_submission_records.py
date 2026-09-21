from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base


class AuthoritativeEvidenceSubmissionRecord(Base):
    __tablename__ = "authoritative_evidence_submissions"
    __table_args__ = (
        UniqueConstraint(
            "evidence_id",
            name="uq_authoritative_evidence_submission_evidence_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    evidence_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    source_type: Mapped[str] = mapped_column(String(50), index=True)
    source_uri: Mapped[str] = mapped_column(String(500))
    source_sha256: Mapped[str] = mapped_column(String(64), index=True)
    issuer: Mapped[str] = mapped_column(String(200))
    population_scope: Mapped[str] = mapped_column(String(300), index=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    submitted_by: Mapped[str] = mapped_column(String(100), index=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
