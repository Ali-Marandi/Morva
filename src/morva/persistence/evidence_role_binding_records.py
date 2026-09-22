from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from morva.persistence.evidence_submission_records import (
    AuthoritativeEvidenceSubmissionRecord,
)
from morva.persistence.models import Base
from morva.runtime.evidence_convergence import (
    CANONICAL_BINDING_KINDS,
    CLOSURE_ROLE_SOURCE_TYPES,
    IMPLEMENTED_SOURCE_TYPES,
    EvidenceBindingReceipt,
    EvidenceConvergenceError,
    build_convergence_assessment,
)
from morva.runtime.evidence_registry_bridge import build_registry_projection
from morva.runtime.evidence_submission import verify_submission_record


class EvidenceRoleBindingError(ValueError):
    """Raised when a certification-role binding cannot pass fail-closed validation."""


class EvidenceRoleBindingRecord(Base):
    """Append-only persisted certification-role binding receipt."""

    __tablename__ = "authoritative_evidence_role_bindings"
    __table_args__ = (
        UniqueConstraint(
            "certification_role",
            "registry_fingerprint",
            "submission_scope",
            "submission_scope_id",
            name="uq_evidence_role_binding_registry_scope",
        ),
        UniqueConstraint(
            "binding_fingerprint",
            name="uq_evidence_role_binding_fingerprint",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    certification_role: Mapped[str] = mapped_column(String(60), index=True)
    authoritative_evidence_id: Mapped[str] = mapped_column(
        String(120),
        ForeignKey(
            "authoritative_evidence_submissions.evidence_id",
            ondelete="RESTRICT",
        ),
        index=True,
    )
    binding_kind: Mapped[str] = mapped_column(String(100))
    binding_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    registry_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    population_scope: Mapped[str] = mapped_column(String(300))
    submission_scope: Mapped[str] = mapped_column(String(30), index=True)
    submission_scope_id: Mapped[str] = mapped_column(String(100), index=True)
    bound_by: Mapped[str] = mapped_column(String(100), index=True)
    bound_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str] = mapped_column(Text)

    def to_receipt(self) -> EvidenceBindingReceipt:
        return EvidenceBindingReceipt(
            receipt_version=1,
            certification_role=self.certification_role,
            binding_kind=self.binding_kind,
            authoritative_evidence_id=self.authoritative_evidence_id,
            binding_fingerprint=self.binding_fingerprint,
            registry_fingerprint=self.registry_fingerprint,
            population_scope=self.population_scope,
            bound_at=_ensure_timezone(self.bound_at, "bound_at"),
        )


class EvidenceRoleBindingRepository:
    """Transactional persistence boundary for M4.17 role binding receipts."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_binding(
        self,
        *,
        certification_role: str,
        authoritative_evidence_id: str,
        bound_by: str,
        bound_at: datetime,
        reason: str,
        principal_scope,
        principal_scope_id: str,
    ) -> EvidenceRoleBindingRecord:
        role = certification_role.strip()
        evidence_id = authoritative_evidence_id.strip()
        actor = bound_by.strip()
        cause = reason.strip()
        now = _ensure_timezone(bound_at, "bound_at")

        if role not in CLOSURE_ROLE_SOURCE_TYPES:
            raise EvidenceRoleBindingError("unsupported certification role")
        if not evidence_id or not actor or not cause:
            raise EvidenceRoleBindingError(
                "certification role, evidence id, actor and reason are required"
            )
        if principal_scope_id is None or not principal_scope_id.strip():
            raise EvidenceRoleBindingError("principal_scope_id is required")

        record = self._normalize_loaded_submission(
            self._scalar_locked(
                select(AuthoritativeEvidenceSubmissionRecord).where(
                    AuthoritativeEvidenceSubmissionRecord.evidence_id == evidence_id
                )
            )
        )
        if record is None:
            raise KeyError(f"evidence submission not found: {evidence_id}")

        try:
            verify_submission_record(record)
        except ValueError as exc:
            raise EvidenceRoleBindingError(
                f"evidence submission verification failed: {exc}"
            ) from exc
        if record.status != "accepted":
            raise EvidenceRoleBindingError(
                "role binding requires accepted evidence"
            )
        if record.source_type != IMPLEMENTED_SOURCE_TYPES[role]:
            raise EvidenceRoleBindingError(
                f"wrong source_type for certification role {role}"
            )
        if (
            record.submission_scope != principal_scope.value
            or record.submission_scope_id != principal_scope_id.strip()
        ):
            raise EvidenceRoleBindingError(
                "organization scope violation"
            )
        if actor in {record.submitted_by, record.decided_by}:
            raise EvidenceRoleBindingError(
                "separation of duties violation: binding actor must differ from submitter and approver"
            )
        if not _is_current(record, now):
            raise EvidenceRoleBindingError(
                "evidence must be current, accepted and non-expired at binding time"
            )

        accepted_records = self.session.scalars(
            select(AuthoritativeEvidenceSubmissionRecord)
            .where(
                AuthoritativeEvidenceSubmissionRecord.status == "accepted",
                AuthoritativeEvidenceSubmissionRecord.submission_scope
                == record.submission_scope,
                AuthoritativeEvidenceSubmissionRecord.submission_scope_id
                == record.submission_scope_id,
            )
            .order_by(AuthoritativeEvidenceSubmissionRecord.evidence_id.asc())
        ).all()
        accepted_records = [
            self._normalize_loaded_submission(record)
            for record in accepted_records
        ]
        registry, _ = build_registry_projection(
            accepted_records,
            projected_at=now,
        )
        existing = self.session.scalar(
            select(EvidenceRoleBindingRecord).where(
                EvidenceRoleBindingRecord.certification_role == role,
                EvidenceRoleBindingRecord.registry_fingerprint
                == registry.fingerprint,
                EvidenceRoleBindingRecord.submission_scope
                == record.submission_scope,
                EvidenceRoleBindingRecord.submission_scope_id
                == record.submission_scope_id,
            )
        )
        if existing is not None:
            raise EvidenceRoleBindingError(
                "certification role is already bound for current registry"
            )

        binding_kind = CANONICAL_BINDING_KINDS[role]
        binding_fingerprint = _binding_fingerprint(
            role=role,
            binding_kind=binding_kind,
            evidence_id=record.evidence_id,
            evidence_fingerprint=record.fingerprint,
            registry_fingerprint=registry.fingerprint,
            population_scope=record.population_scope,
            bound_by=actor,
            bound_at=now,
        )
        receipt = EvidenceBindingReceipt(
            receipt_version=1,
            certification_role=role,
            binding_kind=binding_kind,
            authoritative_evidence_id=record.evidence_id,
            binding_fingerprint=binding_fingerprint,
            registry_fingerprint=registry.fingerprint,
            population_scope=record.population_scope,
            bound_at=now,
        )
        if receipt.fingerprint == binding_fingerprint:
            raise EvidenceRoleBindingError(
                "binding fingerprint must remain distinct from receipt fingerprint"
            )

        new_record = EvidenceRoleBindingRecord(
            certification_role=receipt.certification_role,
            authoritative_evidence_id=receipt.authoritative_evidence_id,
            binding_kind=receipt.binding_kind,
            binding_fingerprint=receipt.binding_fingerprint,
            registry_fingerprint=receipt.registry_fingerprint,
            population_scope=receipt.population_scope,
            submission_scope=record.submission_scope,
            submission_scope_id=record.submission_scope_id,
            bound_by=actor,
            bound_at=now,
            reason=cause,
        )
        self.session.add(new_record)
        self.session.flush()
        return new_record

    def _scalar_locked(self, statement):
        bind = self.session.get_bind()
        if bind is not None and bind.dialect.name == "sqlite":
            return self.session.scalar(statement)
        return self.session.scalar(statement.with_for_update())

    def _normalize_loaded_submission(self, record):
        if record is None:
            return None
        bind = self.session.get_bind()
        if bind is not None and bind.dialect.name == "sqlite":
            for field_name in (
                "effective_from",
                "effective_to",
                "expires_at",
                "submitted_at",
                "decided_at",
            ):
                value = getattr(record, field_name)
                if value is not None and value.tzinfo is None:
                    setattr(record, field_name, value.replace(tzinfo=timezone.utc))
        return record

    def _normalize_loaded_binding(self, record):
        bind = self.session.get_bind()
        if bind is not None and bind.dialect.name == "sqlite":
            if record.bound_at.tzinfo is None:
                record.bound_at = record.bound_at.replace(tzinfo=timezone.utc)
        return record

    def list_current(
        self,
        *,
        principal_scope,
        principal_scope_id: str,
        checked_at: datetime,
    ) -> tuple[list[EvidenceRoleBindingRecord], object]:
        now = _ensure_timezone(checked_at, "checked_at")
        accepted_query = select(AuthoritativeEvidenceSubmissionRecord).where(
            AuthoritativeEvidenceSubmissionRecord.status == "accepted"
        )
        if principal_scope.value != "ministry":
            accepted_query = accepted_query.where(
                AuthoritativeEvidenceSubmissionRecord.submission_scope
                == principal_scope.value,
                AuthoritativeEvidenceSubmissionRecord.submission_scope_id
                == principal_scope_id,
            )
        accepted_records = self.session.scalars(
            accepted_query.order_by(
                AuthoritativeEvidenceSubmissionRecord.evidence_id.asc()
            )
        ).all()
        accepted_records = [
            self._normalize_loaded_submission(record)
            for record in accepted_records
        ]
        registry, _ = build_registry_projection(
            accepted_records,
            projected_at=now,
        )

        query = select(EvidenceRoleBindingRecord).where(
            EvidenceRoleBindingRecord.registry_fingerprint == registry.fingerprint
        )
        if principal_scope.value != "ministry":
            query = query.where(
                EvidenceRoleBindingRecord.submission_scope
                == principal_scope.value,
                EvidenceRoleBindingRecord.submission_scope_id
                == principal_scope_id,
            )
        records = [
            self._normalize_loaded_binding(record)
            for record in self.session.scalars(
                query.order_by(
                    EvidenceRoleBindingRecord.certification_role.asc()
                )
            ).all()
        ]
        submissions = {
            record.evidence_id: record
            for record in accepted_records
        }
        for binding in records:
            if (
                not binding.certification_role.strip()
                or not binding.population_scope.strip()
                or not binding.bound_by.strip()
                or not binding.reason.strip()
            ):
                raise EvidenceRoleBindingError(
                    "persisted role binding contains incomplete governance metadata"
                )
            evidence = submissions.get(binding.authoritative_evidence_id)
            if evidence is None:
                raise EvidenceRoleBindingError(
                    "role binding references evidence outside the current registry"
                )
            try:
                verify_submission_record(evidence)
            except ValueError as exc:
                raise EvidenceRoleBindingError(
                    f"bound evidence verification failed: {exc}"
                ) from exc
            if (
                binding.submission_scope != evidence.submission_scope
                or binding.submission_scope_id != evidence.submission_scope_id
            ):
                raise EvidenceRoleBindingError(
                    "persisted role binding organization scope does not match bound evidence"
                )
            if binding.binding_kind != CANONICAL_BINDING_KINDS.get(binding.certification_role):
                raise EvidenceRoleBindingError(
                    f"persisted role binding has non-canonical binding kind for role {binding.certification_role}"
                )
            if binding.certification_role not in IMPLEMENTED_SOURCE_TYPES:
                raise EvidenceRoleBindingError(
                    "persisted role binding references an unsupported certification role"
                )
            if evidence.source_type != IMPLEMENTED_SOURCE_TYPES[binding.certification_role]:
                raise EvidenceRoleBindingError(
                    f"persisted role binding has wrong source_type for role {binding.certification_role}"
                )
            expected_binding_fingerprint = _binding_fingerprint(
                role=binding.certification_role,
                binding_kind=binding.binding_kind,
                evidence_id=binding.authoritative_evidence_id,
                evidence_fingerprint=evidence.fingerprint,
                registry_fingerprint=binding.registry_fingerprint,
                population_scope=binding.population_scope,
                bound_by=binding.bound_by,
                bound_at=_ensure_timezone(binding.bound_at, "bound_at"),
            )
            if binding.binding_fingerprint != expected_binding_fingerprint:
                raise EvidenceRoleBindingError(
                    "persisted role binding fingerprint mismatch"
                )
        try:
            assessment = build_convergence_assessment(
                registry,
                repository="Ali-Marandi/Morva",
                checked_at=now,
                receipts=tuple(record.to_receipt() for record in records),
            )
        except EvidenceConvergenceError as exc:
            raise EvidenceRoleBindingError(
                f"persisted evidence role binding verification failed: {exc}"
            ) from exc
        return records, assessment


def _is_current(record: AuthoritativeEvidenceSubmissionRecord, now: datetime) -> bool:
    def parse(value: datetime | None) -> datetime | None:
        return _ensure_timezone(value, "evidence timestamp") if value else None

    effective_from = parse(record.effective_from)
    if effective_from and effective_from > now:
        return False
    effective_to = parse(record.effective_to)
    if effective_to and effective_to <= now:
        return False
    approved_at = parse(record.decided_at)
    if approved_at is None or approved_at > now:
        return False
    expires_at = parse(record.expires_at)
    if expires_at and expires_at <= now:
        return False
    return True


def _binding_fingerprint(
    *,
    role: str,
    binding_kind: str,
    evidence_id: str,
    evidence_fingerprint: str,
    registry_fingerprint: str,
    population_scope: str,
    bound_by: str,
    bound_at: datetime,
) -> str:
    payload = {
        "binding_version": 1,
        "certification_role": role,
        "binding_kind": binding_kind,
        "authoritative_evidence_id": evidence_id,
        "authoritative_evidence_fingerprint": evidence_fingerprint.lower(),
        "registry_fingerprint": registry_fingerprint.lower(),
        "population_scope": population_scope,
        "bound_by": bound_by,
        "bound_at": bound_at.astimezone(timezone.utc).isoformat(),
    }
    return sha256(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _ensure_timezone(value: datetime, name: str) -> datetime:
    if value is None or value.tzinfo is None:
        raise EvidenceRoleBindingError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)
