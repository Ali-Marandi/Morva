from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json

from morva.runtime.authoritative_evidence_intake import (
    AuthoritativeEvidenceRegistry,
)
from morva.runtime.security_assessment import SecurityAssessment


class SecurityEvidenceBridgeError(ValueError):
    """Raised when independent security evidence cannot bind safely."""


@dataclass(frozen=True, slots=True)
class SecurityEvidenceBinding:
    binding_version: int
    assessment_id: str
    authoritative_evidence_id: str
    scope_hash: str
    report_uri: str
    assessment_fingerprint: str
    assessor: str
    signed_at: datetime
    bound_by: str
    bound_at: datetime

    def __post_init__(self) -> None:
        if self.binding_version != 1:
            raise SecurityEvidenceBridgeError(
                "unsupported security evidence binding version"
            )
        for name, value in (
            ("assessment_id", self.assessment_id),
            ("authoritative_evidence_id", self.authoritative_evidence_id),
            ("scope_hash", self.scope_hash),
            ("report_uri", self.report_uri),
            ("assessment_fingerprint", self.assessment_fingerprint),
            ("assessor", self.assessor),
            ("bound_by", self.bound_by),
        ):
            if not value.strip():
                raise SecurityEvidenceBridgeError(f"{name} is required")
        for name, value in (
            ("scope_hash", self.scope_hash),
            ("assessment_fingerprint", self.assessment_fingerprint),
        ):
            if len(value) != 64 or any(
                char not in "0123456789abcdef"
                for char in value.lower()
            ):
                raise SecurityEvidenceBridgeError(
                    f"{name} must be SHA-256"
                )
        if self.signed_at.tzinfo is None:
            raise SecurityEvidenceBridgeError(
                "signed_at must be timezone-aware"
            )
        if self.bound_at.tzinfo is None:
            raise SecurityEvidenceBridgeError(
                "bound_at must be timezone-aware"
            )

    @property
    def fingerprint(self) -> str:
        payload = {
            "binding_version": self.binding_version,
            "assessment_id": self.assessment_id,
            "authoritative_evidence_id": self.authoritative_evidence_id,
            "scope_hash": self.scope_hash.lower(),
            "report_uri": self.report_uri,
            "assessment_fingerprint": self.assessment_fingerprint.lower(),
            "assessor": self.assessor,
            "signed_at": self.signed_at.astimezone(timezone.utc).isoformat(),
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


def build_security_evidence_binding(
    assessment: SecurityAssessment,
    registry: AuthoritativeEvidenceRegistry,
    *,
    authoritative_evidence_id: str,
    bound_by: str,
    bound_at: datetime,
) -> SecurityEvidenceBinding:
    if not isinstance(assessment, SecurityAssessment):
        raise SecurityEvidenceBridgeError(
            "SecurityAssessment instance is required"
        )
    if not authoritative_evidence_id.strip():
        raise SecurityEvidenceBridgeError(
            "authoritative_evidence_id is required"
        )
    if not bound_by.strip():
        raise SecurityEvidenceBridgeError("bound_by is required")
    if bound_at.tzinfo is None:
        raise SecurityEvidenceBridgeError(
            "bound_at must be timezone-aware"
        )
    if not assessment.release_ready:
        raise SecurityEvidenceBridgeError(
            "security assessment is not release-ready"
        )
    if not assessment.independent_assessor:
        raise SecurityEvidenceBridgeError(
            "independent assessor is required"
        )
    if not assessment.independent_report_uri:
        raise SecurityEvidenceBridgeError(
            "independent security report URI is required"
        )
    if not assessment.independent_signed_at:
        raise SecurityEvidenceBridgeError(
            "independent security signature time is required"
        )

    authoritative = next(
        (
            item
            for item in registry.items
            if item.evidence_id == authoritative_evidence_id
        ),
        None,
    )
    if authoritative is None:
        raise SecurityEvidenceBridgeError(
            "authoritative security evidence is not present in registry"
        )
    if authoritative.source_type != "security_assessment":
        raise SecurityEvidenceBridgeError(
            "security evidence requires security_assessment authority"
        )
    if authoritative.status != "accepted":
        raise SecurityEvidenceBridgeError(
            "authoritative security evidence must be accepted"
        )
    if authoritative.source_uri.strip() != assessment.independent_report_uri.strip():
        raise SecurityEvidenceBridgeError(
            "security report URI does not match authoritative evidence"
        )
    if authoritative.source_sha256.lower() != assessment.fingerprint.lower():
        raise SecurityEvidenceBridgeError(
            "security assessment fingerprint does not match authoritative evidence SHA-256"
        )

    bound_at_utc = bound_at.astimezone(timezone.utc)
    if assessment.assessed_at > bound_at_utc:
        raise SecurityEvidenceBridgeError(
            "security assessment is future-dated"
        )
    if assessment.independent_signed_at > bound_at_utc:
        raise SecurityEvidenceBridgeError(
            "security report signature is future-dated"
        )
    approved_at = (
        datetime.fromisoformat(authoritative.approved_at)
        if authoritative.approved_at
        else None
    )
    if approved_at is None or approved_at > bound_at_utc:
        raise SecurityEvidenceBridgeError(
            "binding precedes authoritative security evidence approval"
        )
    effective_from = datetime.fromisoformat(authoritative.effective_from)
    if effective_from > bound_at_utc:
        raise SecurityEvidenceBridgeError(
            "authoritative security evidence is not yet effective"
        )
    if authoritative.effective_to is not None:
        effective_to = datetime.fromisoformat(authoritative.effective_to)
        if effective_to <= bound_at_utc:
            raise SecurityEvidenceBridgeError(
                "authoritative security evidence is no longer effective"
            )
    if authoritative.expires_at is not None:
        expires_at = datetime.fromisoformat(authoritative.expires_at)
        if expires_at <= bound_at_utc:
            raise SecurityEvidenceBridgeError(
                "authoritative security evidence is expired"
            )
    if bound_by.strip() == assessment.independent_assessor.strip():
        raise SecurityEvidenceBridgeError(
            "binding actor must differ from independent assessor"
        )

    return SecurityEvidenceBinding(
        binding_version=1,
        assessment_id=assessment.assessment_id.strip(),
        authoritative_evidence_id=authoritative_evidence_id.strip(),
        scope_hash=assessment.scope_hash.lower(),
        report_uri=assessment.independent_report_uri.strip(),
        assessment_fingerprint=assessment.fingerprint.lower(),
        assessor=assessment.independent_assessor.strip(),
        signed_at=assessment.independent_signed_at.astimezone(timezone.utc),
        bound_by=bound_by.strip(),
        bound_at=bound_at_utc,
    )
