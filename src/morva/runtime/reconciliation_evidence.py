from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import re

from morva.runtime.authoritative_evidence_intake import (
    AuthoritativeEvidenceRegistry,
)


class ReconciliationEvidenceError(ValueError):
    """Raised when three-way reconciliation evidence is unsafe."""


_PERIOD_PATTERN = re.compile(r"^14\d{2}-(?:0[1-9]|1[0-2])$")


def _timestamp(name: str, value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ReconciliationEvidenceError(f"{name} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ReconciliationEvidenceError(f"{name} must include a timezone")
    return parsed


def _sha256(name: str, value: str) -> None:
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value.lower()):
        raise ReconciliationEvidenceError(f"{name} must be SHA-256")


@dataclass(frozen=True, slots=True)
class ThreeWayReconciliationEvidence:
    evidence_version: int
    reconciliation_id: str
    population_scope: str
    payroll_period: str
    authoritative_evidence_id: str
    morva_entitlement_sha256: str
    treasury_instruction_sha256: str
    bank_settlement_sha256: str
    comparison_fingerprint: str
    evidence_document_sha256: str
    reconciliation_status: str
    reviewer_id: str
    approver_id: str
    reviewed_at: str
    approved_at: str

    def __post_init__(self) -> None:
        if self.evidence_version != 1:
            raise ReconciliationEvidenceError(
                "unsupported reconciliation evidence version"
            )
        for name, value in (
            ("reconciliation_id", self.reconciliation_id),
            ("population_scope", self.population_scope),
            ("payroll_period", self.payroll_period),
            ("authoritative_evidence_id", self.authoritative_evidence_id),
            ("reviewer_id", self.reviewer_id),
            ("approver_id", self.approver_id),
        ):
            if not value.strip():
                raise ReconciliationEvidenceError(f"{name} is required")
        if not _PERIOD_PATTERN.fullmatch(self.payroll_period):
            raise ReconciliationEvidenceError(
                "payroll_period must use Jalali YYYY-MM format"
            )
        if self.reconciliation_status != "reconciled":
            raise ReconciliationEvidenceError(
                "reconciliation status must be reconciled"
            )
        artifact_hashes = (
            self.morva_entitlement_sha256.lower(),
            self.treasury_instruction_sha256.lower(),
            self.bank_settlement_sha256.lower(),
        )
        if len(set(artifact_hashes)) != 3:
            raise ReconciliationEvidenceError(
                "three-way artifact hashes must be independently identified"
            )
        for name, value in (
            ("morva_entitlement_sha256", self.morva_entitlement_sha256),
            ("treasury_instruction_sha256", self.treasury_instruction_sha256),
            ("bank_settlement_sha256", self.bank_settlement_sha256),
            ("comparison_fingerprint", self.comparison_fingerprint),
            ("evidence_document_sha256", self.evidence_document_sha256),
        ):
            _sha256(name, value)
        if self.reviewer_id.strip() == self.approver_id.strip():
            raise ReconciliationEvidenceError(
                "reviewer and approver must be distinct"
            )
        reviewed_at = _timestamp("reviewed_at", self.reviewed_at)
        approved_at = _timestamp("approved_at", self.approved_at)
        if approved_at < reviewed_at:
            raise ReconciliationEvidenceError(
                "approved_at cannot precede reviewed_at"
            )

    @property
    def fingerprint(self) -> str:
        payload = {
            "evidence_version": self.evidence_version,
            "reconciliation_id": self.reconciliation_id,
            "population_scope": self.population_scope,
            "payroll_period": self.payroll_period,
            "authoritative_evidence_id": self.authoritative_evidence_id,
            "morva_entitlement_sha256": self.morva_entitlement_sha256.lower(),
            "treasury_instruction_sha256": self.treasury_instruction_sha256.lower(),
            "bank_settlement_sha256": self.bank_settlement_sha256.lower(),
            "comparison_fingerprint": self.comparison_fingerprint.lower(),
            "evidence_document_sha256": self.evidence_document_sha256.lower(),
            "reconciliation_status": self.reconciliation_status,
            "reviewer_id": self.reviewer_id,
            "approver_id": self.approver_id,
            "reviewed_at": self.reviewed_at,
            "approved_at": self.approved_at,
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
class ThreeWayReconciliationBinding:
    binding_version: int
    reconciliation_id: str
    population_scope: str
    payroll_period: str
    authoritative_evidence_id: str
    morva_entitlement_sha256: str
    treasury_instruction_sha256: str
    bank_settlement_sha256: str
    comparison_fingerprint: str
    evidence_document_sha256: str
    bound_by: str
    bound_at: datetime

    @property
    def fingerprint(self) -> str:
        payload = {
            "binding_version": self.binding_version,
            "reconciliation_id": self.reconciliation_id,
            "population_scope": self.population_scope,
            "payroll_period": self.payroll_period,
            "authoritative_evidence_id": self.authoritative_evidence_id,
            "morva_entitlement_sha256": self.morva_entitlement_sha256.lower(),
            "treasury_instruction_sha256": self.treasury_instruction_sha256.lower(),
            "bank_settlement_sha256": self.bank_settlement_sha256.lower(),
            "comparison_fingerprint": self.comparison_fingerprint.lower(),
            "evidence_document_sha256": self.evidence_document_sha256.lower(),
            "bound_by": self.bound_by,
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


def build_three_way_reconciliation_binding(
    evidence: ThreeWayReconciliationEvidence,
    registry: AuthoritativeEvidenceRegistry,
    *,
    bound_by: str,
    bound_at: datetime,
) -> ThreeWayReconciliationBinding:
    if not bound_by.strip():
        raise ReconciliationEvidenceError("bound_by is required")
    if bound_at.tzinfo is None:
        raise ReconciliationEvidenceError("bound_at must be timezone-aware")

    authoritative = next(
        (
            item
            for item in registry.items
            if item.evidence_id == evidence.authoritative_evidence_id
        ),
        None,
    )
    if authoritative is None:
        raise ReconciliationEvidenceError(
            "authoritative reconciliation evidence is not present in registry"
        )
    if authoritative.source_type != "reconciliation":
        raise ReconciliationEvidenceError(
            "reconciliation requires reconciliation authoritative evidence"
        )
    if authoritative.status != "accepted":
        raise ReconciliationEvidenceError(
            "authoritative reconciliation evidence must be accepted"
        )
    if authoritative.source_sha256.lower() != evidence.evidence_document_sha256.lower():
        raise ReconciliationEvidenceError(
            "evidence document SHA-256 does not match authoritative evidence SHA-256"
        )
    if authoritative.population_scope.strip() != evidence.population_scope.strip():
        raise ReconciliationEvidenceError(
            "population scope does not match authoritative evidence"
        )

    bound_at_utc = bound_at.astimezone(timezone.utc)
    if authoritative.approved_at is None:
        raise ReconciliationEvidenceError(
            "authoritative reconciliation approval is required"
        )
    approved_at = _timestamp("approved_at", authoritative.approved_at)
    if approved_at > bound_at_utc:
        raise ReconciliationEvidenceError(
            "binding precedes authoritative reconciliation approval"
        )
    effective_from = _timestamp("effective_from", authoritative.effective_from)
    if effective_from > bound_at_utc:
        raise ReconciliationEvidenceError(
            "authoritative reconciliation evidence is not yet effective"
        )
    if authoritative.effective_to is not None:
        effective_to = _timestamp("effective_to", authoritative.effective_to)
        if effective_to <= bound_at_utc:
            raise ReconciliationEvidenceError(
                "authoritative reconciliation evidence is no longer effective"
            )
    if authoritative.expires_at is not None:
        expires_at = _timestamp("expires_at", authoritative.expires_at)
        if expires_at <= bound_at_utc:
            raise ReconciliationEvidenceError(
                "authoritative reconciliation evidence is expired"
            )

    return ThreeWayReconciliationBinding(
        binding_version=1,
        reconciliation_id=evidence.reconciliation_id.strip(),
        population_scope=evidence.population_scope.strip(),
        payroll_period=evidence.payroll_period,
        authoritative_evidence_id=evidence.authoritative_evidence_id.strip(),
        morva_entitlement_sha256=evidence.morva_entitlement_sha256.lower(),
        treasury_instruction_sha256=evidence.treasury_instruction_sha256.lower(),
        bank_settlement_sha256=evidence.bank_settlement_sha256.lower(),
        comparison_fingerprint=evidence.comparison_fingerprint.lower(),
        evidence_document_sha256=evidence.evidence_document_sha256.lower(),
        bound_by=bound_by.strip(),
        bound_at=bound_at_utc,
    )
