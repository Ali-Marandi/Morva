from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json

from morva.runtime.authoritative_evidence_intake import (
    AuthoritativeEvidenceRegistry,
)
from morva.runtime.evidence_closure_matrix import CLOSURE_ROLE_SOURCE_TYPES


class EvidenceConvergenceError(ValueError):
    """Raised when cross-milestone evidence convergence is unsafe."""


CANONICAL_BINDING_KINDS = {
    "legal_approval": "external_approval",
    "finance_approval": "external_approval",
    "security_assessment": "security_evidence_bridge",
    "operations_approval": "external_approval",
    "authoritative_master_data": "masterdata_evidence_bridge",
    "official_adapters": "adapter_contract_evidence_bridge",
    "reconciliation_evidence": "reconciliation_evidence_bridge",
    "dr_exercise": "dr_evidence_bridge",
    "load_validation": "load_validation_evidence_bridge",
    "release_certification": "external_approval",
    "publication_evidence": "external_approval",
    "deployment_validation": "external_approval",
}

IMPLEMENTED_SOURCE_TYPES = {
    "legal_approval": "legal_rule",
    "finance_approval": "finance_approval",
    "security_assessment": "security_assessment",
    "operations_approval": "operations_approval",
    "authoritative_master_data": "master_data",
    "official_adapters": "adapter_contract",
    "reconciliation_evidence": "reconciliation",
    "dr_exercise": "dr_report",
    "load_validation": "load_validation",
    "release_certification": "release_certification",
    "publication_evidence": "publication",
    "deployment_validation": "deployment_validation",
}


def _sha256(name: str, value: str) -> None:
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value.lower()):
        raise EvidenceConvergenceError(f"{name} must be SHA-256")


def _current_accepted(item, checked_at: datetime) -> bool:
    if item.status != "accepted" or not item.approved_at:
        return False
    now = checked_at.astimezone(timezone.utc)
    approved_at = datetime.fromisoformat(item.approved_at)
    if approved_at > now:
        return False
    effective_from = datetime.fromisoformat(item.effective_from)
    if effective_from > now:
        return False
    if item.effective_to is not None:
        effective_to = datetime.fromisoformat(item.effective_to)
        if effective_to <= now:
            return False
    if item.expires_at is not None:
        expires_at = datetime.fromisoformat(item.expires_at)
        if expires_at <= now:
            return False
    return True


@dataclass(frozen=True, slots=True)
class EvidenceBindingReceipt:
    receipt_version: int
    certification_role: str
    binding_kind: str
    authoritative_evidence_id: str
    binding_fingerprint: str
    registry_fingerprint: str
    population_scope: str
    bound_at: datetime

    def __post_init__(self) -> None:
        if self.receipt_version != 1:
            raise EvidenceConvergenceError(
                "unsupported evidence convergence receipt version"
            )
        if self.certification_role not in CLOSURE_ROLE_SOURCE_TYPES:
            raise EvidenceConvergenceError(
                "unsupported certification role"
            )
        expected_kind = CANONICAL_BINDING_KINDS[self.certification_role]
        if self.binding_kind != expected_kind:
            raise EvidenceConvergenceError(
                f"non-canonical binding kind for role {self.certification_role}"
            )
        for name, value in (
            ("authoritative_evidence_id", self.authoritative_evidence_id),
            ("population_scope", self.population_scope),
        ):
            if not value.strip():
                raise EvidenceConvergenceError(f"{name} is required")
        _sha256("binding_fingerprint", self.binding_fingerprint)
        _sha256("registry_fingerprint", self.registry_fingerprint)
        if self.bound_at.tzinfo is None:
            raise EvidenceConvergenceError(
                "bound_at must be timezone-aware"
            )

    @property
    def fingerprint(self) -> str:
        payload = {
            "receipt_version": self.receipt_version,
            "certification_role": self.certification_role,
            "binding_kind": self.binding_kind,
            "authoritative_evidence_id": self.authoritative_evidence_id,
            "binding_fingerprint": self.binding_fingerprint.lower(),
            "registry_fingerprint": self.registry_fingerprint.lower(),
            "population_scope": self.population_scope,
            "bound_at": self.bound_at.astimezone(timezone.utc).isoformat(),
        }
        return sha256(
            json.dumps(
                payload,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class EvidenceConvergenceAssessment:
    assessment_version: int
    repository: str
    checked_at: datetime
    registry_fingerprint: str
    satisfied_roles: tuple[str, ...]
    blocked_roles: tuple[str, ...]
    receipt_fingerprints: tuple[str, ...]
    supporting_evidence_ids: tuple[str, ...]
    fingerprint: str

    def __post_init__(self) -> None:
        if self.assessment_version != 1:
            raise EvidenceConvergenceError(
                "unsupported evidence convergence assessment version"
            )
        if not self.repository.strip():
            raise EvidenceConvergenceError("repository is required")
        if self.checked_at.tzinfo is None:
            raise EvidenceConvergenceError(
                "checked_at must be timezone-aware"
            )
        _sha256("registry_fingerprint", self.registry_fingerprint)
        _sha256("fingerprint", self.fingerprint)

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
            "receipt_fingerprints": list(self.receipt_fingerprints),
            "supporting_evidence_ids": list(self.supporting_evidence_ids),
            "complete": self.complete,
            "fingerprint": self.fingerprint,
        }


def _assessment_fingerprint(
    *,
    repository: str,
    checked_at: datetime,
    registry_fingerprint: str,
    satisfied_roles: tuple[str, ...],
    blocked_roles: tuple[str, ...],
    receipt_fingerprints: tuple[str, ...],
    supporting_evidence_ids: tuple[str, ...],
) -> str:
    payload = {
        "assessment_version": 1,
        "repository": repository,
        "checked_at": checked_at.isoformat(),
        "registry_fingerprint": registry_fingerprint.lower(),
        "satisfied_roles": list(satisfied_roles),
        "blocked_roles": list(blocked_roles),
        "receipt_fingerprints": list(receipt_fingerprints),
        "supporting_evidence_ids": list(supporting_evidence_ids),
    }
    return sha256(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def build_convergence_assessment(
    registry: AuthoritativeEvidenceRegistry,
    *,
    repository: str,
    checked_at: datetime,
    receipts: tuple[EvidenceBindingReceipt, ...],
    supporting_evidence_ids: tuple[str, ...] = (),
) -> EvidenceConvergenceAssessment:
    if checked_at.tzinfo is None:
        raise EvidenceConvergenceError(
            "checked_at must be timezone-aware"
        )
    if not repository.strip():
        raise EvidenceConvergenceError("repository is required")

    now = checked_at.astimezone(timezone.utc)
    by_id = {item.evidence_id: item for item in registry.items}

    role_receipts = {}
    receipt_fingerprints = []
    for receipt in receipts:
        if receipt.certification_role in role_receipts:
            raise EvidenceConvergenceError(
                "duplicate certification-role receipt"
            )
        if receipt.registry_fingerprint.lower() != registry.fingerprint.lower():
            raise EvidenceConvergenceError(
                "receipt registry fingerprint does not match current registry"
            )
        authority = by_id.get(receipt.authoritative_evidence_id)
        if authority is None:
            raise EvidenceConvergenceError(
                f"authoritative evidence {receipt.authoritative_evidence_id} is missing"
            )
        expected_source_type = IMPLEMENTED_SOURCE_TYPES[receipt.certification_role]
        if authority.source_type != expected_source_type:
            raise EvidenceConvergenceError(
                f"wrong authority source type for role {receipt.certification_role}"
            )
        if not _current_accepted(authority, now):
            raise EvidenceConvergenceError(
                f"authority evidence is not current and accepted for role {receipt.certification_role}"
            )
        if receipt.bound_at > now:
            raise EvidenceConvergenceError(
                f"receipt is future-dated for role {receipt.certification_role}"
            )
        if receipt.population_scope.strip() != authority.population_scope.strip():
            raise EvidenceConvergenceError(
                f"receipt population scope mismatch for role {receipt.certification_role}"
            )
        role_receipts[receipt.certification_role] = receipt
        receipt_fingerprints.append(receipt.fingerprint)

    supporting_ids = tuple(sorted(set(supporting_evidence_ids)))
    for evidence_id in supporting_ids:
        item = by_id.get(evidence_id)
        if item is None:
            raise EvidenceConvergenceError(
                f"supporting evidence {evidence_id} is missing"
            )
        if not _current_accepted(item, now):
            raise EvidenceConvergenceError(
                f"supporting evidence {evidence_id} is not current and accepted"
            )

    satisfied = []
    blocked = []
    for role in CLOSURE_ROLE_SOURCE_TYPES:
        receipt = role_receipts.get(role)
        if receipt is None:
            blocked.append(role)
        else:
            satisfied.append(role)

    satisfied_roles = tuple(satisfied)
    blocked_roles = tuple(blocked)
    receipt_fingerprints_tuple = tuple(sorted(receipt_fingerprints))
    registry_fingerprint = registry.fingerprint
    fingerprint = _assessment_fingerprint(
        repository=repository,
        checked_at=checked_at,
        registry_fingerprint=registry_fingerprint,
        satisfied_roles=satisfied_roles,
        blocked_roles=blocked_roles,
        receipt_fingerprints=receipt_fingerprints_tuple,
        supporting_evidence_ids=supporting_ids,
    )
    return EvidenceConvergenceAssessment(
        assessment_version=1,
        repository=repository,
        checked_at=checked_at,
        registry_fingerprint=registry_fingerprint,
        satisfied_roles=satisfied_roles,
        blocked_roles=blocked_roles,
        receipt_fingerprints=receipt_fingerprints_tuple,
        supporting_evidence_ids=supporting_ids,
        fingerprint=fingerprint,
    )
