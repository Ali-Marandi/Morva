from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from morva.runtime.evidence_lifecycle import (
    EvidenceLifecycleError,
    EvidenceLifecycleLink,
    build_lifecycle_assessment,
    build_lifecycle_link,
)
from morva.runtime.evidence_registry_bridge import build_registry_projection
from morva.runtime.evidence_submission import verify_submission_record
from morva.security.policy import Scope

from .evidence_submission_records import AuthoritativeEvidenceSubmissionRecord
from .models import Base


class AuthoritativeEvidenceLifecycleEventRecord(Base):
    """Append-only persisted evidence supersession/renewal relationship."""

    __tablename__ = "authoritative_evidence_lifecycle_events"
    __table_args__ = (
        UniqueConstraint(
            "predecessor_evidence_id",
            name="uq_evidence_lifecycle_predecessor",
        ),
        UniqueConstraint(
            "successor_evidence_id",
            name="uq_evidence_lifecycle_successor",
        ),
        UniqueConstraint(
            "fingerprint",
            name="uq_evidence_lifecycle_fingerprint",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    predecessor_evidence_id: Mapped[str] = mapped_column(
        String(120),
        ForeignKey(
            "authoritative_evidence_submissions.evidence_id",
            ondelete="RESTRICT",
        ),
        index=True,
    )
    successor_evidence_id: Mapped[str] = mapped_column(
        String(120),
        ForeignKey(
            "authoritative_evidence_submissions.evidence_id",
            ondelete="RESTRICT",
        ),
        index=True,
    )
    linked_by: Mapped[str] = mapped_column(String(100), index=True)
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)

    def to_link(self) -> EvidenceLifecycleLink:
        return EvidenceLifecycleLink(
            link_version=1,
            predecessor_evidence_id=self.predecessor_evidence_id,
            successor_evidence_id=self.successor_evidence_id,
            linked_by=self.linked_by,
            linked_at=_ensure_timezone(self.linked_at, "linked_at"),
            reason=self.reason,
            fingerprint=self.fingerprint,
        )


class EvidenceLifecycleRepository:
    """Transactional persistence boundary for M4.15 evidence lineage."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_link(
        self,
        *,
        predecessor_evidence_id: str,
        successor_evidence_id: str,
        linked_by: str,
        linked_at: datetime,
        reason: str,
        principal_scope: Scope | None = None,
        principal_scope_id: str | None = None,
    ) -> AuthoritativeEvidenceLifecycleEventRecord:
        predecessor_id = predecessor_evidence_id.strip()
        successor_id = successor_evidence_id.strip()
        actor = linked_by.strip()
        cause = reason.strip()
        linked_at_utc = _ensure_timezone(linked_at, "linked_at")

        if not predecessor_id or not successor_id or not actor or not cause:
            raise EvidenceLifecycleError(
                "predecessor, successor, actor and reason are required"
            )
        if predecessor_id == successor_id:
            raise EvidenceLifecycleError("evidence cannot supersede itself")

        predecessor = self.session.scalar(
            select(AuthoritativeEvidenceSubmissionRecord)
            .where(
                AuthoritativeEvidenceSubmissionRecord.evidence_id == predecessor_id
            )
            .with_for_update()
        )
        successor = self.session.scalar(
            select(AuthoritativeEvidenceSubmissionRecord)
            .where(
                AuthoritativeEvidenceSubmissionRecord.evidence_id == successor_id
            )
            .with_for_update()
        )
        if predecessor is None:
            raise KeyError(f"predecessor evidence not found: {predecessor_id}")
        if successor is None:
            raise KeyError(f"successor evidence not found: {successor_id}")

        verify_submission_record(predecessor)
        verify_submission_record(successor)
        if predecessor.status != "accepted" or successor.status != "accepted":
            raise EvidenceLifecycleError(
                "lifecycle links require accepted predecessor and successor evidence"
            )
        if (
            predecessor.submission_scope != successor.submission_scope
            or predecessor.submission_scope_id != successor.submission_scope_id
        ):
            raise EvidenceLifecycleError(
                "lifecycle links require matching organization scope"
            )
        if principal_scope is not None and principal_scope is not Scope.MINISTRY:
            if predecessor.submission_scope != principal_scope.value:
                raise EvidenceLifecycleError(
                    "principal scope level does not match predecessor"
                )
            if principal_scope_id != predecessor.submission_scope_id:
                raise EvidenceLifecycleError(
                    "principal scope does not match predecessor"
                )
        if actor in {predecessor.submitted_by, successor.submitted_by}:
            raise EvidenceLifecycleError(
                "separation of duties violation: lifecycle actor must differ from submitters"
            )
        if _ensure_timezone(predecessor.submitted_at, "predecessor submitted_at") > linked_at_utc:
            raise EvidenceLifecycleError(
                "lifecycle link cannot precede predecessor submission"
            )
        if _ensure_timezone(successor.submitted_at, "successor submitted_at") > linked_at_utc:
            raise EvidenceLifecycleError(
                "lifecycle link cannot precede successor submission"
            )

        accepted_records = self.session.scalars(
            select(AuthoritativeEvidenceSubmissionRecord)
            .where(AuthoritativeEvidenceSubmissionRecord.status == "accepted")
            .order_by(AuthoritativeEvidenceSubmissionRecord.evidence_id.asc())
        ).all()
        registry, _ = build_registry_projection(
            accepted_records,
            projected_at=linked_at_utc,
        )
        existing_events = self.session.scalars(
            select(AuthoritativeEvidenceLifecycleEventRecord).order_by(
                AuthoritativeEvidenceLifecycleEventRecord.linked_at.asc()
            )
        ).all()
        existing_links = tuple(event.to_link() for event in existing_events)
        candidate = build_lifecycle_link(
            predecessor_evidence_id=predecessor_id,
            successor_evidence_id=successor_id,
            linked_by=actor,
            linked_at=linked_at_utc,
            reason=cause,
        )
        build_lifecycle_assessment(
            registry,
            repository="Ali-Marandi/Morva",
            checked_at=linked_at_utc,
            links=existing_links + (candidate,),
        )

        record = AuthoritativeEvidenceLifecycleEventRecord(
            predecessor_evidence_id=predecessor_id,
            successor_evidence_id=successor_id,
            linked_by=actor,
            linked_at=linked_at_utc,
            reason=cause,
            fingerprint=candidate.fingerprint,
        )
        self.session.add(record)
        self.session.flush()
        return record

    def list_for_scope(
        self,
        *,
        scope: Scope,
        scope_id: str,
    ) -> list[AuthoritativeEvidenceLifecycleEventRecord]:
        query = (
            select(AuthoritativeEvidenceLifecycleEventRecord)
            .join(
                AuthoritativeEvidenceSubmissionRecord,
                AuthoritativeEvidenceSubmissionRecord.evidence_id
                == AuthoritativeEvidenceLifecycleEventRecord.predecessor_evidence_id,
            )
            .where(
                AuthoritativeEvidenceSubmissionRecord.submission_scope == scope.value,
                AuthoritativeEvidenceSubmissionRecord.submission_scope_id == scope_id,
            )
            .order_by(
                AuthoritativeEvidenceLifecycleEventRecord.linked_at.asc(),
                AuthoritativeEvidenceLifecycleEventRecord.predecessor_evidence_id.asc(),
            )
        )
        return list(self.session.scalars(query).all())


def _ensure_timezone(value: datetime, name: str) -> datetime:
    if value.tzinfo is None:
        raise EvidenceLifecycleError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)
