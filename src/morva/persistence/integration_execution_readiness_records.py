from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Index,
    JSON,
    String,
    UniqueConstraint,
    select,
)
from sqlalchemy.orm import Mapped, Session, mapped_column

from morva.runtime.independent_integration_execution_readiness_verifier_m4_21 import (
    IndependentIntegrationExecutionReadinessVerification,
)
from morva.runtime.integration_execution_readiness_assessment import (
    IntegrationExecutionReadinessAssessment,
)
from morva.runtime.readiness_scope_binding_m4_25 import (
    ReadinessScopeBindingError,
    normalize_readiness_scope,
    readiness_scope_binding_fingerprint,
    verify_readiness_scope_binding,
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
        Index(
            "ix_integ_readiness_binding_verification_fp",
            "binding_verification_fingerprint",
        ),
        UniqueConstraint(
            "scope_binding_fingerprint",
            name="uq_integration_readiness_scope_binding_fingerprint",
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
        String(64), index=False
    )
    state: Mapped[str] = mapped_column(String(20), index=True)
    blockers: Mapped[list] = mapped_column(JSON, default=list)
    assessment_fingerprint: Mapped[str] = mapped_column(
        String(64), index=True
    )
    verification_fingerprint: Mapped[str] = mapped_column(
        String(64), index=True
    )
    organization_scope: Mapped[str] = mapped_column(
        String(20), index=True
    )
    organization_scope_id: Mapped[str] = mapped_column(
        String(100), index=True
    )
    scope_binding_fingerprint: Mapped[str] = mapped_column(
        String(64), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def verify_scope_binding(self) -> None:
        try:
            scope, scope_id = normalize_readiness_scope(
                self.organization_scope,
                self.organization_scope_id,
            )
            if scope != self.organization_scope or scope_id != self.organization_scope_id:
                raise ReadinessScopeBindingError(
                    "persisted readiness organization scope is not normalized"
                )
            verify_readiness_scope_binding(
                verification_fingerprint=self.verification_fingerprint,
                organization_scope=scope,
                organization_scope_id=scope_id,
                scope_binding_fingerprint=self.scope_binding_fingerprint,
            )
        except ReadinessScopeBindingError as exc:
            raise IntegrationExecutionReadinessPersistenceError(str(exc)) from exc

    def to_verification(self) -> IndependentIntegrationExecutionReadinessVerification:
        try:
            assessment = IntegrationExecutionReadinessAssessment(
                assessment_version=self.assessment_version,
                repository=self.repository,
                candidate_sha=self.candidate_sha,
                target_environment=self.target_environment,
                checked_at=_ensure_timezone(
                    self.assessment_checked_at, "assessment_checked_at"
                ),
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
            self.verify_scope_binding()
            if verification.assessment.checked_at > verification.verified_at:
                raise IntegrationExecutionReadinessPersistenceError(
                    "persisted verification timestamp precedes assessment check time"
                )
            return verification
        except IntegrationExecutionReadinessPersistenceError:
            raise
        except (TypeError, ValueError) as exc:
            raise IntegrationExecutionReadinessPersistenceError(
                "persisted integration readiness verification is structurally invalid"
            ) from exc


class IntegrationExecutionReadinessVerificationRepository:
    """Append-only persistence boundary for M4.21 verification receipts."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self,
        verification: IndependentIntegrationExecutionReadinessVerification,
        *,
        organization_scope: str,
        organization_scope_id: str,
    ) -> IntegrationExecutionReadinessVerificationRecord:
        if verification.assessment.repository != "Ali-Marandi/Morva":
            raise IntegrationExecutionReadinessPersistenceError(
                "integration readiness persistence requires the canonical repository"
            )

        assessment = verification.assessment
        try:
            organization_scope, organization_scope_id = normalize_readiness_scope(
                organization_scope,
                organization_scope_id,
            )
        except ReadinessScopeBindingError as exc:
            raise IntegrationExecutionReadinessPersistenceError(str(exc)) from exc
        assessment_checked_at = _ensure_timezone(
            assessment.checked_at, "assessment_checked_at"
        )
        verified_at = _ensure_timezone(verification.verified_at, "verified_at")
        if assessment_checked_at > verified_at:
            raise IntegrationExecutionReadinessPersistenceError(
                "verification timestamp precedes assessment check time"
            )

        verification_fingerprint = verification.fingerprint.lower()
        existing = self.session.scalar(
            select(IntegrationExecutionReadinessVerificationRecord).where(
                IntegrationExecutionReadinessVerificationRecord.verification_fingerprint
                == verification_fingerprint
            )
        )
        scope_binding_fingerprint = readiness_scope_binding_fingerprint(
            verification_fingerprint=verification_fingerprint,
            organization_scope=organization_scope,
            organization_scope_id=organization_scope_id,
        )
        if existing is not None:
            try:
                existing.to_verification()
                if (
                    existing.organization_scope != organization_scope
                    or existing.organization_scope_id != organization_scope_id
                ):
                    raise IntegrationExecutionReadinessPersistenceError(
                        "verification is already bound to a different organization scope"
                    )
                if existing.scope_binding_fingerprint != scope_binding_fingerprint:
                    raise IntegrationExecutionReadinessPersistenceError(
                        "existing readiness scope binding fingerprint mismatch"
                    )
            except IntegrationExecutionReadinessPersistenceError:
                raise
            return existing

        record = IntegrationExecutionReadinessVerificationRecord(
            assessment_version=assessment.assessment_version,
            repository=assessment.repository,
            candidate_sha=assessment.candidate_sha.lower(),
            target_environment=assessment.target_environment,
            assessment_checked_at=assessment_checked_at,
            verified_at=verified_at,
            evidence_readiness_fingerprint=assessment.evidence_readiness_fingerprint.lower(),
            binding_fingerprint=assessment.binding_fingerprint.lower(),
            binding_verification_fingerprint=assessment.binding_verification_fingerprint.lower(),
            state=assessment.state,
            blockers=list(assessment.blockers),
            assessment_fingerprint=assessment.fingerprint.lower(),
            verification_fingerprint=verification_fingerprint,
            organization_scope=organization_scope,
            organization_scope_id=organization_scope_id,
            scope_binding_fingerprint=scope_binding_fingerprint,
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
        organization_scope: str | None = None,
        organization_scope_id: str | None = None,
    ) -> IntegrationExecutionReadinessVerificationRecord | None:
        records = self.list_verified(
            repository=repository,
            candidate_sha=candidate_sha,
            target_environment=target_environment,
            organization_scope=organization_scope,
            organization_scope_id=organization_scope_id,
            limit=1,
        )
        return records[0] if records else None

    def list_verified(
        self,
        *,
        repository: str = "Ali-Marandi/Morva",
        candidate_sha: str | None = None,
        target_environment: str | None = None,
        organization_scope: str | None = None,
        organization_scope_id: str | None = None,
        verified_before: datetime | None = None,
        before_id: UUID | None = None,
        limit: int = 100,
    ) -> list[IntegrationExecutionReadinessVerificationRecord]:
        if limit < 1 or limit > 101:
            raise IntegrationExecutionReadinessPersistenceError(
                "readiness history query limit must be between 1 and 101"
            )
        if (organization_scope is None) != (organization_scope_id is None):
            raise IntegrationExecutionReadinessPersistenceError(
                "organization_scope and organization_scope_id must be supplied together"
            )
        if organization_scope is not None and organization_scope_id is not None:
            try:
                organization_scope, organization_scope_id = normalize_readiness_scope(
                    organization_scope,
                    organization_scope_id,
                )
            except ReadinessScopeBindingError as exc:
                raise IntegrationExecutionReadinessPersistenceError(str(exc)) from exc

        if (verified_before is None) != (before_id is None):
            raise IntegrationExecutionReadinessPersistenceError(
                "verified_before and before_id must be supplied together"
            )
        if verified_before is not None:
            verified_before = _ensure_timezone(verified_before, "verified_before")

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
        if organization_scope is not None and organization_scope_id is not None:
            query = query.where(
                IntegrationExecutionReadinessVerificationRecord.organization_scope
                == organization_scope,
                IntegrationExecutionReadinessVerificationRecord.organization_scope_id
                == organization_scope_id,
            )
        if verified_before is not None and before_id is not None:
            query = query.where(
                (
                    IntegrationExecutionReadinessVerificationRecord.verified_at
                    < verified_before
                )
                | (
                    (
                        IntegrationExecutionReadinessVerificationRecord.verified_at
                        == verified_before
                    )
                    & (
                        IntegrationExecutionReadinessVerificationRecord.id
                        < before_id
                    )
                )
            )

        records = self.session.scalars(
            query.order_by(
                IntegrationExecutionReadinessVerificationRecord.verified_at.desc(),
                IntegrationExecutionReadinessVerificationRecord.id.desc(),
            ).limit(limit)
        ).all()

        bind = self.session.get_bind()
        for record in records:
            if bind is not None and bind.dialect.name == "sqlite":
                for field_name in (
                    "assessment_checked_at",
                    "verified_at",
                    "created_at",
                ):
                    value = getattr(record, field_name)
                    if value is not None and value.tzinfo is None:
                        setattr(record, field_name, value.replace(tzinfo=timezone.utc))
            record.assessment_checked_at = _ensure_timezone(
                record.assessment_checked_at, "assessment_checked_at"
            )
            record.verified_at = _ensure_timezone(record.verified_at, "verified_at")
            record.created_at = _ensure_timezone(record.created_at, "created_at")
            record.to_verification()
            record.verify_scope_binding()

        return records


def _ensure_timezone(value: datetime, name: str) -> datetime:
    if value.tzinfo is None:
        raise IntegrationExecutionReadinessPersistenceError(
            f"{name} must be timezone-aware"
        )
    return value.astimezone(timezone.utc)
