from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json

from morva.runtime.authoritative_evidence_intake import (
    ALLOWED_SOURCE_TYPES,
    AuthoritativeEvidenceIntakeError,
    AuthoritativeEvidenceRegistry,
)


class EvidenceClosureMatrixError(ValueError):
    """Raised when closure requirements cannot be evaluated safely."""


CLOSURE_ROLE_SOURCE_TYPES: dict[str, tuple[str, ...]] = {
    "legal_approval": ("legal_rule",),
    "finance_approval": ("finance_approval",),
    "security_assessment": ("security_assessment",),
    "operations_approval": ("operations_approval",),
    "authoritative_master_data": ("master_data",),
    "official_adapters": ("adapter_contract",),
    "reconciliation_evidence": ("reconciliation",),
    "dr_exercise": ("dr_report",),
    "load_validation": ("load_validation",),
    "release_certification": ("release_certification",),
    "publication_evidence": ("publication",),
    "deployment_validation": ("deployment_validation",),
}

for _source_types in CLOSURE_ROLE_SOURCE_TYPES.values():
    for _source_type in _source_types:
        if _source_type not in ALLOWED_SOURCE_TYPES:
            raise RuntimeError(
                f"closure matrix references unsupported source type: {_source_type}"
            )


@dataclass(frozen=True, slots=True)
class EvidenceClosureRequirement:
    role: str
    allowed_source_types: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.role not in CLOSURE_ROLE_SOURCE_TYPES:
            raise EvidenceClosureMatrixError(
                f"unsupported closure role: {self.role}"
            )
        if not self.allowed_source_types:
            raise EvidenceClosureMatrixError(
                "allowed_source_types cannot be empty"
            )
        expected = CLOSURE_ROLE_SOURCE_TYPES[self.role]
        if tuple(self.allowed_source_types) != expected:
            raise EvidenceClosureMatrixError(
                f"non-canonical source mapping for role {self.role}"
            )


CANONICAL_REQUIREMENTS = tuple(
    EvidenceClosureRequirement(
        role=role,
        allowed_source_types=source_types,
    )
    for role, source_types in CLOSURE_ROLE_SOURCE_TYPES.items()
)


@dataclass(frozen=True, slots=True)
class EvidenceClosureAssessment:
    assessment_version: int
    repository: str
    checked_at: datetime
    registry_fingerprint: str
    satisfied_roles: tuple[str, ...]
    blocked_roles: tuple[str, ...]
    fingerprint: str

    def __post_init__(self) -> None:
        if self.assessment_version != 1:
            raise EvidenceClosureMatrixError(
                "unsupported evidence closure assessment version"
            )
        if not self.repository.strip():
            raise EvidenceClosureMatrixError("repository is required")
        if self.checked_at.tzinfo is None:
            raise EvidenceClosureMatrixError(
                "checked_at must be timezone-aware"
            )
        for name, value in (
            ("registry_fingerprint", self.registry_fingerprint),
            ("fingerprint", self.fingerprint),
        ):
            if len(value) != 64 or any(
                char not in "0123456789abcdef"
                for char in value.lower()
            ):
                raise EvidenceClosureMatrixError(
                    f"{name} must be SHA-256"
                )

    @property
    def complete(self) -> bool:
        return not self.blocked_roles

    def to_payload(self) -> dict[str, object]:
        return {
            "assessment_version": self.assessment_version,
            "repository": self.repository,
            "checked_at": self.checked_at.isoformat(),
            "registry_fingerprint": self.registry_fingerprint,
            "satisfied_roles": list(self.satisfied_roles),
            "blocked_roles": list(self.blocked_roles),
            "complete": self.complete,
            "fingerprint": self.fingerprint,
        }


def _assessment_fingerprint(
    *,
    assessment_version: int,
    repository: str,
    checked_at: datetime,
    registry_fingerprint: str,
    satisfied_roles: tuple[str, ...],
    blocked_roles: tuple[str, ...],
) -> str:
    payload = {
        "assessment_version": assessment_version,
        "repository": repository,
        "checked_at": checked_at.isoformat(),
        "registry_fingerprint": registry_fingerprint.lower(),
        "satisfied_roles": list(satisfied_roles),
        "blocked_roles": list(blocked_roles),
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


def evaluate_closure(
    registry: AuthoritativeEvidenceRegistry,
    *,
    repository: str,
    checked_at: datetime,
) -> EvidenceClosureAssessment:
    if checked_at.tzinfo is None:
        raise EvidenceClosureMatrixError(
            "checked_at must be timezone-aware"
        )
    if not repository.strip():
        raise EvidenceClosureMatrixError("repository is required")
    if any(
        item.repository != repository
        for item in registry.items
    ):
        raise EvidenceClosureMatrixError(
            "registry contains evidence from another repository"
        )

    now = checked_at.astimezone(timezone.utc)
    by_type = {
        source_type: []
        for source_type in ALLOWED_SOURCE_TYPES
    }
    for item in registry.items:
        by_type[item.source_type].append(item)

    satisfied: list[str] = []
    blocked: list[str] = []

    for requirement in CANONICAL_REQUIREMENTS:
        candidates = [
            item
            for source_type in requirement.allowed_source_types
            for item in by_type[source_type]
        ]
        eligible = []
        for item in candidates:
            if item.status != "accepted":
                continue
            effective_from = datetime.fromisoformat(item.effective_from)
            if effective_from > now:
                continue
            if item.effective_to is not None:
                effective_to = datetime.fromisoformat(item.effective_to)
                if effective_to <= now:
                    continue
            if item.approved_at is None:
                continue
            approved_at = datetime.fromisoformat(item.approved_at)
            if approved_at > now:
                continue
            if item.expires_at is not None:
                expires_at = datetime.fromisoformat(item.expires_at)
                if expires_at <= now:
                    continue
            eligible.append(item)

        if eligible:
            satisfied.append(requirement.role)
        else:
            blocked.append(requirement.role)

    satisfied_roles = tuple(satisfied)
    blocked_roles = tuple(blocked)
    registry_fingerprint = registry.fingerprint
    fingerprint = _assessment_fingerprint(
        assessment_version=1,
        repository=repository,
        checked_at=checked_at,
        registry_fingerprint=registry_fingerprint,
        satisfied_roles=satisfied_roles,
        blocked_roles=blocked_roles,
    )
    return EvidenceClosureAssessment(
        assessment_version=1,
        repository=repository,
        checked_at=checked_at,
        registry_fingerprint=registry_fingerprint,
        satisfied_roles=satisfied_roles,
        blocked_roles=blocked_roles,
        fingerprint=fingerprint,
    )
