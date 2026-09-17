from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from hashlib import sha256


class SecurityAssessmentError(ValueError):
    """Raised when an independent security assessment record is invalid or blocked."""


@dataclass(frozen=True, slots=True)
class SecurityFinding:
    finding_id: str
    severity: str
    status: str

    def __post_init__(self) -> None:
        if not self.finding_id.strip():
            raise SecurityAssessmentError("finding_id is required")
        if self.severity not in {"critical", "high", "medium", "low"}:
            raise SecurityAssessmentError("unsupported finding severity")
        if self.status not in {"open", "remediated", "false_positive"}:
            raise SecurityAssessmentError("unsupported finding status")


@dataclass(frozen=True, slots=True)
class SecurityAssessment:
    assessment_id: str
    assessed_at: datetime
    scope_hash: str
    required_controls: tuple[str, ...]
    verified_controls: tuple[str, ...]
    findings: tuple[SecurityFinding, ...] = ()
    independent_assessor: str | None = None
    independent_report_uri: str | None = None
    independent_signed_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.assessment_id.strip():
            raise SecurityAssessmentError("assessment_id is required")
        if self.assessed_at.tzinfo is None:
            raise SecurityAssessmentError("assessed_at must be timezone-aware")
        if len(self.scope_hash) != 64 or any(
            char not in "0123456789abcdef" for char in self.scope_hash.lower()
        ):
            raise SecurityAssessmentError("scope_hash must be a SHA-256 hex digest")
        required = tuple(control.strip() for control in self.required_controls)
        verified = tuple(control.strip() for control in self.verified_controls)
        if any(not control for control in required + verified):
            raise SecurityAssessmentError("security control identifiers cannot be empty")
        if len(set(required)) != len(required) or len(set(verified)) != len(verified):
            raise SecurityAssessmentError("security control identifiers must be unique")
        if self.independent_signed_at is not None and self.independent_signed_at.tzinfo is None:
            raise SecurityAssessmentError("independent_signed_at must be timezone-aware")

    @property
    def open_critical_or_high(self) -> tuple[SecurityFinding, ...]:
        return tuple(
            finding
            for finding in self.findings
            if finding.severity in {"critical", "high"} and finding.status == "open"
        )

    @property
    def missing_controls(self) -> tuple[str, ...]:
        verified = set(self.verified_controls)
        return tuple(control for control in self.required_controls if control not in verified)

    @property
    def independent_signoff_complete(self) -> bool:
        return bool(
            self.independent_assessor
            and self.independent_report_uri
            and self.independent_signed_at
        )

    @property
    def release_ready(self) -> bool:
        return (
            self.independent_signoff_complete
            and not self.open_critical_or_high
            and not self.missing_controls
        )

    @property
    def fingerprint(self) -> str:
        payload = {
            "assessment_id": self.assessment_id,
            "assessed_at": self.assessed_at.isoformat(),
            "scope_hash": self.scope_hash.lower(),
            "required_controls": self.required_controls,
            "verified_controls": self.verified_controls,
            "findings": tuple(
                (finding.finding_id, finding.severity, finding.status)
                for finding in self.findings
            ),
            "independent_assessor": self.independent_assessor,
            "independent_report_uri": self.independent_report_uri,
            "independent_signed_at": (
                self.independent_signed_at.isoformat() if self.independent_signed_at else None
            ),
        }
        canonical = json.dumps(
            payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        )
        return sha256(canonical.encode("utf-8")).hexdigest()

    def assert_release_ready(self) -> None:
        if self.release_ready:
            return
        blockers: list[str] = []
        if not self.independent_signoff_complete:
            blockers.append("independent security signoff is incomplete")
        if self.open_critical_or_high:
            blockers.append("open critical/high security findings remain")
        if self.missing_controls:
            blockers.append(
                f"unverified security controls: {', '.join(self.missing_controls)}"
            )
        raise SecurityAssessmentError("; ".join(blockers))
