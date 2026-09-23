from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from morva.runtime.readiness_convergence_freshness_policy_m4_29 import (
    ReadinessConvergenceFreshnessPolicy,
    ReadinessConvergenceFreshnessPolicyError,
    build_freshness_policy,
)

from .models import Base


class ReadinessConvergenceFreshnessPolicyPersistenceError(ValueError):
    """Raised when a freshness policy cannot be persisted safely."""


class ReadinessConvergenceFreshnessPolicyRecord(Base):
    """Append-only persisted identity for a versioned freshness policy."""

    __tablename__ = "readiness_convergence_freshness_policies"
    __table_args__ = (
        Index(
            "ix_readiness_freshness_policy_policy_id_version",
            "policy_id",
            "policy_version",
            unique=True,
        ),
        Index(
            "ix_readiness_freshness_policy_fingerprint",
            "fingerprint",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    policy_version: Mapped[int] = mapped_column(nullable=False)
    policy_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    max_age_seconds: Mapped[int] = mapped_column(nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    recorded_by: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_policy(self) -> ReadinessConvergenceFreshnessPolicy:
        try:
            return ReadinessConvergenceFreshnessPolicy(
                policy_version=self.policy_version,
                policy_id=self.policy_id,
                max_age_seconds=self.max_age_seconds,
                fingerprint=self.fingerprint,
            )
        except (TypeError, ValueError, ReadinessConvergenceFreshnessPolicyError) as exc:
            raise ReadinessConvergenceFreshnessPolicyPersistenceError(
                "persisted freshness policy is structurally invalid"
            ) from exc


class ReadinessConvergenceFreshnessPolicyRepository:
    """Append-only persistence boundary for M4.29 freshness policy identities."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self,
        policy: ReadinessConvergenceFreshnessPolicy,
        *,
        recorded_by: str,
    ) -> ReadinessConvergenceFreshnessPolicyRecord:
        actor = recorded_by.strip()
        if not actor:
            raise ReadinessConvergenceFreshnessPolicyPersistenceError(
                "recorded_by is required"
            )

        try:
            policy = build_freshness_policy(
                policy_id=policy.policy_id,
                max_age_seconds=policy.max_age_seconds,
                policy_version=policy.policy_version,
            )
            if policy.fingerprint.lower() != policy.fingerprint:
                raise ReadinessConvergenceFreshnessPolicyError(
                    "policy fingerprint is not normalized"
                )
        except ReadinessConvergenceFreshnessPolicyError as exc:
            raise ReadinessConvergenceFreshnessPolicyPersistenceError(
                str(exc)
            ) from exc

        existing = self.session.scalar(
            select(ReadinessConvergenceFreshnessPolicyRecord).where(
                ReadinessConvergenceFreshnessPolicyRecord.fingerprint
                == policy.fingerprint.lower()
            )
        )
        if existing is not None:
            _normalize_loaded_policy_record(self.session, existing)
            existing.to_policy()
            if existing.recorded_by != actor:
                raise ReadinessConvergenceFreshnessPolicyPersistenceError(
                    "policy fingerprint is already recorded by a different actor"
                )
            return existing

        existing_version = self.session.scalar(
            select(ReadinessConvergenceFreshnessPolicyRecord).where(
                ReadinessConvergenceFreshnessPolicyRecord.policy_id
                == policy.policy_id,
                ReadinessConvergenceFreshnessPolicyRecord.policy_version
                == policy.policy_version,
            )
        )
        if existing_version is not None:
            _normalize_loaded_policy_record(self.session, existing_version)
            existing_policy = existing_version.to_policy()
            if existing_policy.fingerprint != policy.fingerprint:
                raise ReadinessConvergenceFreshnessPolicyPersistenceError(
                    "policy id/version is already bound to a different fingerprint"
                )
            if existing_version.recorded_by != actor:
                raise ReadinessConvergenceFreshnessPolicyPersistenceError(
                    "policy id/version is already recorded by a different actor"
                )
            return existing_version

        record = ReadinessConvergenceFreshnessPolicyRecord(
            policy_version=policy.policy_version,
            policy_id=policy.policy_id,
            max_age_seconds=policy.max_age_seconds,
            fingerprint=policy.fingerprint.lower(),
            recorded_by=actor,
        )
        self.session.add(record)
        self.session.flush()
        record.to_policy()
        return record

    def list(
        self,
        *,
        before_created_at: datetime | None = None,
        before_id: UUID | None = None,
        limit: int = 50,
    ) -> tuple[list[ReadinessConvergenceFreshnessPolicyRecord], bool]:
        if limit < 1 or limit > 100:
            raise ReadinessConvergenceFreshnessPolicyPersistenceError(
                "limit must be between 1 and 100"
            )
        stmt = select(ReadinessConvergenceFreshnessPolicyRecord)
        if before_created_at is not None and before_created_at.tzinfo is None:
            raise ReadinessConvergenceFreshnessPolicyPersistenceError(
                "before_created_at must be timezone-aware"
            )
        if before_created_at is not None and before_id is None:
            stmt = stmt.where(
                ReadinessConvergenceFreshnessPolicyRecord.created_at
                < before_created_at
            )
        elif before_created_at is not None and before_id is not None:
            stmt = stmt.where(
                (
                    ReadinessConvergenceFreshnessPolicyRecord.created_at
                    < before_created_at
                )
                |
                (
                    (
                        ReadinessConvergenceFreshnessPolicyRecord.created_at
                        == before_created_at
                    )
                    & (
                        ReadinessConvergenceFreshnessPolicyRecord.id
                        < before_id
                    )
                )
            )
        stmt = stmt.order_by(
            ReadinessConvergenceFreshnessPolicyRecord.created_at.desc(),
            ReadinessConvergenceFreshnessPolicyRecord.id.desc(),
        ).limit(limit + 1)
        records = list(self.session.scalars(stmt).all())
        has_more = len(records) > limit
        records = records[:limit]
        for record in records:
            _normalize_loaded_policy_record(self.session, record)
            record.to_policy()
        return records, has_more

    def get(
        self,
        *,
        policy_id: str,
        policy_version: int = 1,
    ) -> ReadinessConvergenceFreshnessPolicyRecord | None:
        if policy_version < 1:
            raise ReadinessConvergenceFreshnessPolicyPersistenceError(
                "policy_version must be positive"
            )
        record = self.session.scalar(
            select(ReadinessConvergenceFreshnessPolicyRecord).where(
                ReadinessConvergenceFreshnessPolicyRecord.policy_id
                == policy_id.strip(),
                ReadinessConvergenceFreshnessPolicyRecord.policy_version
                == policy_version,
            )
        )
        if record is None:
            return None
        _normalize_loaded_policy_record(self.session, record)
        record.to_policy()
        return record


def _normalize_loaded_policy_record(
    session: Session,
    record: ReadinessConvergenceFreshnessPolicyRecord,
) -> None:
    bind = session.get_bind()
    if bind is not None and bind.dialect.name == "sqlite":
        for field_name in ("created_at",):
            value = getattr(record, field_name)
            if value.tzinfo is None:
                setattr(
                    record,
                    field_name,
                    value.replace(tzinfo=timezone.utc),
                )
