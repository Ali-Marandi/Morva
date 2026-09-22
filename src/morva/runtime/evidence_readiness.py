from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json

from morva.runtime.authoritative_evidence_intake import AuthoritativeEvidenceRegistry
from morva.runtime.evidence_closure_matrix import CLOSURE_ROLE_SOURCE_TYPES
from morva.runtime.evidence_convergence import (
    EvidenceBindingReceipt,
    EvidenceConvergenceAssessment,
)
from morva.runtime.evidence_lifecycle import EvidenceLifecycleAssessment


class EvidenceReadinessError(ValueError):
    """Raised when evidence readiness cannot be evaluated safely."""


@dataclass(frozen=True, slots=True)
class EvidenceRemediationItem:
    role: str
    state: str
    reason_code: str
    detail: str
    evidence_id: str | None = None

    def __post_init__(self) -> None:
        if self.role not in CLOSURE_ROLE_SOURCE_TYPES:
            raise EvidenceReadinessError(
                f"unsupported certification role: {self.role}"
            )
        if self.state not in {"ready", "blocked"}:
            raise EvidenceReadinessError(
                f"unsupported remediation state: {self.state}"
            )
        if not self.reason_code.strip() or not self.detail.strip():
            raise EvidenceReadinessError(
                "reason_code and detail are required"
            )

    def to_payload(self) -> dict[str, object]:
        return {
            "role": self.role,
            "state": self.state,
            "reason_code": self.reason_code,
            "detail": self.detail,
            "evidence_id": self.evidence_id,
        }


@dataclass(frozen=True, slots=True)
class EvidenceReadinessAssessment:
    assessment_version: int
    repository: str
    checked_at: datetime
    registry_fingerprint: str
    convergence_fingerprint: str
    lifecycle_fingerprint: str | None
    ready_roles: tuple[str, ...]
    blocked_roles: tuple[str, ...]
    remediation: tuple[EvidenceRemediationItem, ...]
    fingerprint: str

    def __post_init__(self) -> None:
        if self.assessment_version != 1:
            raise EvidenceReadinessError(
                "unsupported evidence readiness assessment version"
            )
        if not self.repository.strip():
            raise EvidenceReadinessError("repository is required")
        if self.checked_at.tzinfo is None:
            raise EvidenceReadinessError(
                "checked_at must be timezone-aware"
            )
        _sha256("registry_fingerprint", self.registry_fingerprint)
        _sha256("convergence_fingerprint", self.convergence_fingerprint)
        if self.lifecycle_fingerprint is not None:
            _sha256("lifecycle_fingerprint", self.lifecycle_fingerprint)
        if set(self.ready_roles) & set(self.blocked_roles):
            raise EvidenceReadinessError(
                "role cannot be both ready and blocked"
            )
        if len(self.remediation) != len(self.blocked_roles):
            raise EvidenceReadinessError(
                "each blocked role must have exactly one remediation item"
            )
        _sha256("fingerprint", self.fingerprint)
        expected_fingerprint = _readiness_fingerprint(
            repository=self.repository,
            checked_at=self.checked_at,
            registry_fingerprint=self.registry_fingerprint,
            convergence_fingerprint=self.convergence_fingerprint,
            lifecycle_fingerprint=self.lifecycle_fingerprint,
            ready_roles=self.ready_roles,
            blocked_roles=self.blocked_roles,
            remediation=self.remediation,
        )
        if self.fingerprint.lower() != expected_fingerprint:
            raise EvidenceReadinessError(
                "evidence readiness assessment fingerprint mismatch"
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
            "convergence_fingerprint": self.convergence_fingerprint,
            "lifecycle_fingerprint": self.lifecycle_fingerprint,
            "ready_roles": list(self.ready_roles),
            "blocked_roles": list(self.blocked_roles),
            "remediation": [
                item.to_payload() for item in self.remediation
            ],
            "complete": self.complete,
            "fingerprint": self.fingerprint,
        }


def build_readiness_assessment(
    registry: AuthoritativeEvidenceRegistry,
    convergence: EvidenceConvergenceAssessment,
    *,
    repository: str,
    checked_at: datetime,
    receipts: tuple[EvidenceBindingReceipt, ...],
    lifecycle: EvidenceLifecycleAssessment | None = None,
) -> EvidenceReadinessAssessment:
    if checked_at.tzinfo is None:
        raise EvidenceReadinessError(
            "checked_at must be timezone-aware"
        )
    if convergence.registry_fingerprint.lower() != registry.fingerprint.lower():
        raise EvidenceReadinessError(
            "convergence assessment does not match current registry"
        )
    if lifecycle is not None and lifecycle.registry_fingerprint.lower() != registry.fingerprint.lower():
        raise EvidenceReadinessError(
            "lifecycle assessment does not match current registry"
        )

    receipt_by_role = {
        receipt.certification_role: receipt for receipt in receipts
    }
    registry_by_id = {
        item.evidence_id: item for item in registry.items
    }
    superseded = (
        set(lifecycle.superseded_evidence_ids)
        if lifecycle is not None
        else set()
    )

    ready_roles: list[str] = []
    blocked_roles: list[str] = []
    remediation: list[EvidenceRemediationItem] = []

    for role in CLOSURE_ROLE_SOURCE_TYPES:
        receipt = receipt_by_role.get(role)
        if receipt is None:
            blocked_roles.append(role)
            remediation.append(
                EvidenceRemediationItem(
                    role=role,
                    state="blocked",
                    reason_code="MISSING_BINDING",
                    detail=(
                        "Create a current role binding against the active "
                        "evidence registry."
                    ),
                )
            )
            continue

        evidence = registry_by_id.get(receipt.authoritative_evidence_id)
        if evidence is None:
            blocked_roles.append(role)
            remediation.append(
                EvidenceRemediationItem(
                    role=role,
                    state="blocked",
                    reason_code="EVIDENCE_NOT_FOUND",
                    detail=(
                        "The bound authoritative evidence is no longer "
                        "present in the current registry."
                    ),
                    evidence_id=receipt.authoritative_evidence_id,
                )
            )
            continue

        if receipt.authoritative_evidence_id in superseded:
            blocked_roles.append(role)
            remediation.append(
                EvidenceRemediationItem(
                    role=role,
                    state="blocked",
                    reason_code="EVIDENCE_SUPERSEDED",
                    detail=(
                        "Rebind this certification role to the current "
                        "lineage head."
                    ),
                    evidence_id=receipt.authoritative_evidence_id,
                )
            )
            continue

        if receipt.population_scope.strip() != evidence.population_scope.strip():
            blocked_roles.append(role)
            remediation.append(
                EvidenceRemediationItem(
                    role=role,
                    state="blocked",
                    reason_code="POPULATION_SCOPE_MISMATCH",
                    detail=(
                        "Rebind using evidence with the exact certified "
                        "population scope."
                    ),
                    evidence_id=receipt.authoritative_evidence_id,
                )
            )
            continue

        ready_roles.append(role)

    ready_roles_tuple = tuple(ready_roles)
    blocked_roles_tuple = tuple(blocked_roles)
    remediation_tuple = tuple(remediation)
    lifecycle_fingerprint = (
        lifecycle.fingerprint if lifecycle is not None else None
    )
    fingerprint = _readiness_fingerprint(
        repository=repository,
        checked_at=checked_at,
        registry_fingerprint=registry.fingerprint,
        convergence_fingerprint=convergence.fingerprint,
        lifecycle_fingerprint=lifecycle_fingerprint,
        ready_roles=ready_roles_tuple,
        blocked_roles=blocked_roles_tuple,
        remediation=remediation_tuple,
    )
    return EvidenceReadinessAssessment(
        assessment_version=1,
        repository=repository,
        checked_at=checked_at,
        registry_fingerprint=registry.fingerprint,
        convergence_fingerprint=convergence.fingerprint,
        lifecycle_fingerprint=lifecycle_fingerprint,
        ready_roles=ready_roles_tuple,
        blocked_roles=blocked_roles_tuple,
        remediation=remediation_tuple,
        fingerprint=fingerprint,
    )


def _readiness_fingerprint(
    *,
    repository: str,
    checked_at: datetime,
    registry_fingerprint: str,
    convergence_fingerprint: str,
    lifecycle_fingerprint: str | None,
    ready_roles: tuple[str, ...],
    blocked_roles: tuple[str, ...],
    remediation: tuple[EvidenceRemediationItem, ...],
) -> str:
    payload = {
        "assessment_version": 1,
        "repository": repository,
        "checked_at": checked_at.astimezone(timezone.utc).isoformat(),
        "registry_fingerprint": registry_fingerprint.lower(),
        "convergence_fingerprint": convergence_fingerprint.lower(),
        "lifecycle_fingerprint": (
            lifecycle_fingerprint.lower()
            if lifecycle_fingerprint
            else None
        ),
        "ready_roles": list(ready_roles),
        "blocked_roles": list(blocked_roles),
        "remediation": [
            item.to_payload() for item in remediation
        ],
    }
    return sha256(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _sha256(name: str, value: str) -> None:
    if len(value) != 64 or any(
        char not in "0123456789abcdef" for char in value.lower()
    ):
        raise EvidenceReadinessError(f"{name} must be SHA-256")
