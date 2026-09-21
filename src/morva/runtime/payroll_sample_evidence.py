from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import re

from morva.runtime.authoritative_evidence_intake import (
    AuthoritativeEvidenceRegistry,
)


class PayrollSampleEvidenceError(ValueError):
    """Raised when authoritative payroll-sample evidence is unsafe."""


PERIOD_PATTERN = re.compile(r"^14\d{2}-(?:0[1-9]|1[0-2])$")


def _timestamp(name: str, value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise PayrollSampleEvidenceError(f"{name} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise PayrollSampleEvidenceError(f"{name} must include a timezone")
    return parsed


def _sha256(name: str, value: str) -> None:
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value.lower()):
        raise PayrollSampleEvidenceError(f"{name} must be SHA-256")


@dataclass(frozen=True, slots=True)
class PayrollSampleEvidence:
    evidence_version: int
    sample_id: str
    population_scope: str
    payroll_period: str
    authoritative_evidence_id: str
    input_manifest_sha256: str
    expected_output_sha256: str
    comparison_fingerprint: str
    source_uri: str
    issuer: str
    reviewer_id: str
    approver_id: str
    reviewed_at: str
    approved_at: str
    status: str = "approved"

    def __post_init__(self) -> None:
        if self.evidence_version != 1:
            raise PayrollSampleEvidenceError(
                "unsupported payroll-sample evidence version"
            )
        for name, value in (
            ("sample_id", self.sample_id),
            ("population_scope", self.population_scope),
            ("payroll_period", self.payroll_period),
            ("authoritative_evidence_id", self.authoritative_evidence_id),
            ("source_uri", self.source_uri),
            ("issuer", self.issuer),
            ("reviewer_id", self.reviewer_id),
            ("approver_id", self.approver_id),
        ):
            if not value.strip():
                raise PayrollSampleEvidenceError(f"{name} is required")
        if not PERIOD_PATTERN.fullmatch(self.payroll_period):
            raise PayrollSampleEvidenceError(
                "payroll_period must use Jalali YYYY-MM format"
            )
        _sha256("input_manifest_sha256", self.input_manifest_sha256)
        _sha256("expected_output_sha256", self.expected_output_sha256)
        _sha256("comparison_fingerprint", self.comparison_fingerprint)
        if self.status != "approved":
            raise PayrollSampleEvidenceError(
                "payroll-sample evidence must be explicitly approved"
            )
        if self.reviewer_id.strip() == self.approver_id.strip():
            raise PayrollSampleEvidenceError(
                "reviewer and approver must be distinct"
            )
        reviewed_at = _timestamp("reviewed_at", self.reviewed_at)
        approved_at = _timestamp("approved_at", self.approved_at)
        if approved_at < reviewed_at:
            raise PayrollSampleEvidenceError(
                "approved_at cannot precede reviewed_at"
            )

    @property
    def fingerprint(self) -> str:
        payload = {
            "evidence_version": self.evidence_version,
            "sample_id": self.sample_id,
            "population_scope": self.population_scope,
            "payroll_period": self.payroll_period,
            "authoritative_evidence_id": self.authoritative_evidence_id,
            "input_manifest_sha256": self.input_manifest_sha256.lower(),
            "expected_output_sha256": self.expected_output_sha256.lower(),
            "comparison_fingerprint": self.comparison_fingerprint.lower(),
            "source_uri": self.source_uri,
            "issuer": self.issuer,
            "reviewer_id": self.reviewer_id,
            "approver_id": self.approver_id,
            "reviewed_at": self.reviewed_at,
            "approved_at": self.approved_at,
            "status": self.status,
        }
        return sha256(
            json.dumps(
                payload,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

    def to_payload(self) -> dict[str, object]:
        return {
            "evidence_version": self.evidence_version,
            "sample_id": self.sample_id,
            "population_scope": self.population_scope,
            "payroll_period": self.payroll_period,
            "authoritative_evidence_id": self.authoritative_evidence_id,
            "input_manifest_sha256": self.input_manifest_sha256,
            "expected_output_sha256": self.expected_output_sha256,
            "comparison_fingerprint": self.comparison_fingerprint,
            "source_uri": self.source_uri,
            "issuer": self.issuer,
            "reviewer_id": self.reviewer_id,
            "approver_id": self.approver_id,
            "reviewed_at": self.reviewed_at,
            "approved_at": self.approved_at,
            "status": self.status,
            "fingerprint": self.fingerprint,
        }


@dataclass(frozen=True, slots=True)
class PayrollSampleEvidenceBinding:
    binding_version: int
    sample_id: str
    population_scope: str
    payroll_period: str
    authoritative_evidence_id: str
    source_uri: str
    input_manifest_sha256: str
    expected_output_sha256: str
    comparison_fingerprint: str
    bound_by: str
    bound_at: datetime

    @property
    def fingerprint(self) -> str:
        payload = {
            "binding_version": self.binding_version,
            "sample_id": self.sample_id,
            "population_scope": self.population_scope,
            "payroll_period": self.payroll_period,
            "authoritative_evidence_id": self.authoritative_evidence_id,
            "source_uri": self.source_uri,
            "input_manifest_sha256": self.input_manifest_sha256.lower(),
            "expected_output_sha256": self.expected_output_sha256.lower(),
            "comparison_fingerprint": self.comparison_fingerprint.lower(),
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

    def to_payload(self) -> dict[str, object]:
        return {
            "binding_version": self.binding_version,
            "sample_id": self.sample_id,
            "population_scope": self.population_scope,
            "payroll_period": self.payroll_period,
            "authoritative_evidence_id": self.authoritative_evidence_id,
            "source_uri": self.source_uri,
            "input_manifest_sha256": self.input_manifest_sha256,
            "expected_output_sha256": self.expected_output_sha256,
            "comparison_fingerprint": self.comparison_fingerprint,
            "bound_by": self.bound_by,
            "bound_at": self.bound_at.astimezone(timezone.utc).isoformat(),
            "fingerprint": self.fingerprint,
        }


def build_payroll_sample_evidence_binding(
    evidence: PayrollSampleEvidence,
    registry: AuthoritativeEvidenceRegistry,
    *,
    bound_by: str,
    bound_at: datetime,
) -> PayrollSampleEvidenceBinding:
    if not bound_by.strip():
        raise PayrollSampleEvidenceError("bound_by is required")
    if bound_at.tzinfo is None:
        raise PayrollSampleEvidenceError("bound_at must be timezone-aware")

    authoritative = next(
        (
            item
            for item in registry.items
            if item.evidence_id == evidence.authoritative_evidence_id
        ),
        None,
    )
    if authoritative is None:
        raise PayrollSampleEvidenceError(
            "authoritative payroll-sample evidence is not present in registry"
        )
    if authoritative.source_type != "payroll_sample":
        raise PayrollSampleEvidenceError(
            "payroll sample requires payroll_sample authoritative evidence"
        )
    if authoritative.status != "accepted":
        raise PayrollSampleEvidenceError(
            "authoritative payroll-sample evidence must be accepted"
        )
    if evidence.authoritative_evidence_id.strip() != authoritative.evidence_id.strip():
        raise PayrollSampleEvidenceError("authoritative evidence ID mismatch")
    if evidence.source_uri.strip() != authoritative.source_uri.strip():
        raise PayrollSampleEvidenceError("sample source URI does not match authority")
    if evidence.issuer.strip() != authoritative.issuer.strip():
        raise PayrollSampleEvidenceError("sample issuer does not match authority")
    if evidence.input_manifest_sha256.lower() != authoritative.source_sha256.lower():
        raise PayrollSampleEvidenceError(
            "input manifest SHA-256 does not match authoritative evidence"
        )
    if evidence.population_scope.strip() != authoritative.population_scope.strip():
        raise PayrollSampleEvidenceError(
            "population scope does not match authoritative evidence"
        )

    bound_at_utc = bound_at.astimezone(timezone.utc)
    if authoritative.approved_at is None:
        raise PayrollSampleEvidenceError("authoritative sample approval is required")
    approved_at = _timestamp("approved_at", authoritative.approved_at)
    if approved_at > bound_at_utc:
        raise PayrollSampleEvidenceError(
            "binding precedes authoritative sample approval"
        )
    effective_from = _timestamp("effective_from", authoritative.effective_from)
    if effective_from > bound_at_utc:
        raise PayrollSampleEvidenceError(
            "authoritative sample evidence is not yet effective"
        )
    if authoritative.effective_to is not None:
        effective_to = _timestamp("effective_to", authoritative.effective_to)
        if effective_to <= bound_at_utc:
            raise PayrollSampleEvidenceError(
                "authoritative sample evidence is no longer effective"
            )
    if authoritative.expires_at is not None:
        expires_at = _timestamp("expires_at", authoritative.expires_at)
        if expires_at <= bound_at_utc:
            raise PayrollSampleEvidenceError(
                "authoritative sample evidence is expired"
            )

    return PayrollSampleEvidenceBinding(
        binding_version=1,
        sample_id=evidence.sample_id.strip(),
        population_scope=evidence.population_scope.strip(),
        payroll_period=evidence.payroll_period,
        authoritative_evidence_id=evidence.authoritative_evidence_id.strip(),
        source_uri=evidence.source_uri.strip(),
        input_manifest_sha256=evidence.input_manifest_sha256.lower(),
        expected_output_sha256=evidence.expected_output_sha256.lower(),
        comparison_fingerprint=evidence.comparison_fingerprint.lower(),
        bound_by=bound_by.strip(),
        bound_at=bound_at_utc,
    )
