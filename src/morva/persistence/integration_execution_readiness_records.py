from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, JSON, String, UniqueConstraint, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from morva.runtime.independent_integration_execution_readiness_verifier_m4_21 import (
    IndependentIntegrationExecutionReadinessVerification,
)
from morva.runtime.integration_execution_readiness_assessment import (
    IntegrationExecutionReadinessAssessment,
)

from .models import Base


class IntegrationExecutionReadinessPersistenceError(ValueError):
    """Raised when an M4.22 readiness verification cannot be persisted safely."""


class IntegrationExecutionReadinessVerificationRecord(Base):
    """Append-only persisted receipt for an independently verified M4.20 assessment."""

    __tablename__ = "integration_execution_readiness_verifications"
    __table_args__ = (
        UniqueConstraint(
            "verification_fingerprint",
            name="uq_integration_readiness_verification_fingerprint",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    assessment_version: Mapped[int] = mapped_column()
    repository: Mapped[str] = mapped_column(String(200), index=True)
    candidate_sha: Mapped[str] = mapped_column(String(40), index=True)
    target_environment: Mapped[str] = mapped_column(String(20), index=True)
    assessment_checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    evidence_readiness_fingerprint: Mapped[str] = mapped_column(
        String(64), index=True
    )
    binding_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    binding_verification_fingerprint: Mapped[str] = mapped_column(
        String(64), index=True
    )
    state: Mapped[str] = mapped_column(String(20), index=True)
    blockers: Mapped[list] = mapped_column(JSON, default=list)
    assessment_fingerprint: Mapped[str] = mapped_column(
        String(64), index=True
    )
    verification_fingerprint: Mapped[str] = mapped_column(
        String(64), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def to_verification(self) -> IndependentIntegrationExecutionReadinessVerification:
        assessment = IntegrationExecutionReadinessAssessment(
            assessment_version=self.assessment_version,
            repository=self.repository,
            candidate_sha=self.candidate_sha,
            target_environment=self.target_environment,
            checked_at=_ensure_timezone(self.assessment_checked_at, "assessment_checked_at"),
            evidence_readiness_fingerprint=self.evidence_readiness_fingerprint,
            binding_fingerprint=self.binding_fingerprint,
            binding_verification_fingerprint=self.binding_verification_fingerprint,
            state=self.state,
            blockers=tuple(self.blockers),
            fingerprint=self.assessment_fingerprint,
        )
        verification = IndependentIntegrationExecutionReadinessVerification(
            assessment=assessment,
            verified_at=_ensure_timezone(self.verified_at, "verified_at"),
        )
        if verification.fingerprint.lower() != self.verification_fingerprint.lower():
            raise IntegrationExecutionReadinessPersistenceError(
                "persisted integration readiness verification fingerprint mismatch"
            )
        return verification


class IntegrationExecutionReadinessVerificationRepository:
    """Append-only persistence boundary for M4.21 verification receipts."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self,
        verification: IndependentIntegrationExecutionReadinessVerification,
    ) -> IntegrationExecutionReadinessVerificationRecord:
        if verification.assessment.repository != "Ali-Marandi/Morva":
            raise IntegrationExecutionReadinessPersistenceError(
                "integration readiness persistence requires the canonical repository"
            )

        verification_fingerprint = verification.fingerprint.lower()
        existing = self.session.scalar(
            select(IntegrationExecutionReadinessVerificationRecord).where(
                IntegrationExecutionReadinessVerificationRecord.verification_fingerprint
                == verification_fingerprint
            )
        )
        if existing is not None:
            return existing

        assessment = verification.assessment
        record = IntegrationExecutionReadinessVerificationRecord(
            assessment_version=assessment.assessment_version,
            repository=assessment.repository,
            candidate_sha=assessment.candidate_sha.lower(),
            target_environment=assessment.target_environment,
            assessment_checked_at=_ensure_timezone(
                assessment.checked_at, "assessment_checked_at"
            ),
            verified_at=_ensure_timezone(verification.verified_at, "verified_at"),
            evidence_readiness_fingerprint=assessment.evidence_readiness_fingerprint.lower(),
            binding_fingerprint=assessment.binding_fingerprint.lower(),
            binding_verification_fingerprint=assessment.binding_verification_fingerprint.lower(),
            state=assessment.state,
            blockers=list(assessment.blockers),
            assessment_fingerprint=assessment.fingerprint.lower(),
            verification_fingerprint=verification_fingerprint,
        )
        self.session.add(record)
        self.session.flush()
        return record

    def latest(
        self,
        *,
        repository: str = "Ali-Marandi/Morva",
        candidate_sha: str | None = None,
        target_environment: str | None = None,
    ) -> IntegrationExecutionReadinessVerificationRecord | None:
        query = select(IntegrationExecutionReadinessVerificationRecord).where(
            IntegrationExecutionReadinessVerificationRecord.repository == repository
        )
        if candidate_sha is not None:
            query = query.where(
                IntegrationExecutionReadinessVerificationRecord.candidate_sha
                == candidate_sha.lower()
            )
        if target_environment is not None:
            query = query.where(
                IntegrationExecutionReadinessVerificationRecord.target_environment
                == target_environment
            )
        record = self.session.scalar(
            query.order_by(
                IntegrationExecutionReadinessVerificationRecord.verified_at.desc(),
                IntegrationExecutionReadinessVerificationRecord.id.desc(),
            ).limit(1)
        )
        if record is not None:
            record.assessment_checked_at = _ensure_timezone(
                record.assessment_checked_at, "assessment_checked_at"
            )
            record.verified_at = _ensure_timezone(record.verified_at, "verified_at")
            record.created_at = _ensure_timezone(record.created_at, "created_at")
            record.to_verification()
        return record


def _ensure_timezone(value: datetime, name: str) -> datetime:
    if value.tzinfo is None:
        raise IntegrationExecutionReadinessPersistenceError(
            f"{name} must be timezone-aware"
        )
    return value.astimezone(timezone.utc)
