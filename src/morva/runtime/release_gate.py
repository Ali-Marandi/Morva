from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json

from .release_attestation import ReleaseAttestation
from .release_certification import ReleaseCertification
from .security_assessment import SecurityAssessment


class ReleaseGateError(ValueError):
    """Raised when a release candidate fails the aggregate release gate."""


@dataclass(frozen=True, slots=True)
class ReleaseGate:
    candidate_sha: str
    security_assessment: SecurityAssessment
    certification: ReleaseCertification
    attestation: ReleaseAttestation

    def __post_init__(self) -> None:
        if len(self.candidate_sha) != 40 or any(
            char not in "0123456789abcdef" for char in self.candidate_sha.lower()
        ):
            raise ReleaseGateError("candidate_sha must be a Git commit SHA-1")
        expected = self.candidate_sha.lower()
        for name, value in (
            ("certification", self.certification.candidate_sha),
            ("attestation", self.attestation.candidate_sha),
        ):
            if value.lower() != expected:
                raise ReleaseGateError(f"{name} candidate_sha does not match release gate SHA")

    @property
    def release_ready(self) -> bool:
        return (
            self.security_assessment.release_ready
            and self.certification.release_ready
            and self.attestation.release_ready
        )

    @property
    def blockers(self) -> tuple[str, ...]:
        blockers: list[str] = []
        if not self.security_assessment.release_ready:
            if not self.security_assessment.independent_signoff_complete:
                blockers.append("independent security signoff is incomplete")
            if self.security_assessment.open_critical_or_high:
                blockers.append("open critical/high security findings remain")
            if self.security_assessment.missing_controls:
                blockers.append(
                    f"unverified security controls: {', '.join(self.security_assessment.missing_controls)}"
                )
        if not self.certification.release_ready:
            blockers.append("formal release certification is incomplete")
        if not self.attestation.release_ready:
            blockers.append("release provenance/signing attestation is incomplete")
        return tuple(blockers)

    @property
    def fingerprint(self) -> str:
        payload = {
            "candidate_sha": self.candidate_sha.lower(),
            "security_assessment": self.security_assessment.fingerprint,
            "certification": self.certification.fingerprint,
            "attestation": self.attestation.fingerprint,
        }
        canonical = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()

    def assert_release_ready(self) -> None:
        if self.release_ready:
            return
        raise ReleaseGateError("; ".join(self.blockers) or "release gate is not ready")
