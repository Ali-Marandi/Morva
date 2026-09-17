from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json


class ReleaseCertificationError(ValueError):
    """Raised when formal release certification evidence is incomplete or invalid."""


@dataclass(frozen=True, slots=True)
class CertificationSignoff:
    role: str
    signer: str
    signed_at: datetime
    evidence_uri: str

    def __post_init__(self) -> None:
        if self.role not in {"finance", "legal", "operations"}:
            raise ReleaseCertificationError("unsupported certification role")
        if not self.signer.strip():
            raise ReleaseCertificationError("signer is required")
        if self.signed_at.tzinfo is None:
            raise ReleaseCertificationError("signed_at must be timezone-aware")
        if not self.evidence_uri.strip():
            raise ReleaseCertificationError("evidence_uri is required")


@dataclass(frozen=True, slots=True)
class ReleaseCertification:
    release_id: str
    candidate_sha: str
    required_evidence: tuple[str, ...]
    verified_evidence: tuple[str, ...]
    security_signoff_complete: bool = False
    disaster_recovery_signoff_complete: bool = False
    load_signoff_complete: bool = False
    reconciliation_signoff_complete: bool = False
    signoffs: tuple[CertificationSignoff, ...] = ()

    def __post_init__(self) -> None:
        if not self.release_id.strip():
            raise ReleaseCertificationError("release_id is required")
        if len(self.candidate_sha) != 40 or any(
            char not in "0123456789abcdef" for char in self.candidate_sha.lower()
        ):
            raise ReleaseCertificationError("candidate_sha must be a Git commit SHA-1")
        required = tuple(item.strip() for item in self.required_evidence)
        verified = tuple(item.strip() for item in self.verified_evidence)
        if any(not item for item in required + verified):
            raise ReleaseCertificationError("evidence identifiers cannot be empty")
        if len(set(required)) != len(required) or len(set(verified)) != len(verified):
            raise ReleaseCertificationError("evidence identifiers must be unique")
        roles = [signoff.role for signoff in self.signoffs]
        if len(roles) != len(set(roles)):
            raise ReleaseCertificationError("each certification role may sign only once")

    @property
    def missing_evidence(self) -> tuple[str, ...]:
        verified = set(self.verified_evidence)
        return tuple(item for item in self.required_evidence if item not in verified)

    @property
    def missing_signoffs(self) -> tuple[str, ...]:
        signed = {signoff.role for signoff in self.signoffs}
        return tuple(role for role in ("finance", "legal", "operations") if role not in signed)

    @property
    def signoff_complete(self) -> bool:
        return not self.missing_signoffs

    @property
    def release_ready(self) -> bool:
        return (
            not self.missing_evidence
            and self.signoff_complete
            and self.security_signoff_complete
            and self.disaster_recovery_signoff_complete
            and self.load_signoff_complete
            and self.reconciliation_signoff_complete
        )

    @property
    def fingerprint(self) -> str:
        payload = {
            "release_id": self.release_id,
            "candidate_sha": self.candidate_sha.lower(),
            "required_evidence": self.required_evidence,
            "verified_evidence": self.verified_evidence,
            "security_signoff_complete": self.security_signoff_complete,
            "disaster_recovery_signoff_complete": self.disaster_recovery_signoff_complete,
            "load_signoff_complete": self.load_signoff_complete,
            "reconciliation_signoff_complete": self.reconciliation_signoff_complete,
            "signoffs": tuple(
                (item.role, item.signer, item.signed_at.isoformat(), item.evidence_uri)
                for item in self.signoffs
            ),
        }
        canonical = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()

    def assert_release_ready(self) -> None:
        if self.release_ready:
            return
        blockers: list[str] = []
        if self.missing_evidence:
            blockers.append(f"missing certification evidence: {', '.join(self.missing_evidence)}")
        if self.missing_signoffs:
            blockers.append(f"missing certification signoffs: {', '.join(self.missing_signoffs)}")
        for label, ready in (
            ("independent security", self.security_signoff_complete),
            ("disaster recovery", self.disaster_recovery_signoff_complete),
            ("load/performance", self.load_signoff_complete),
            ("three-way reconciliation", self.reconciliation_signoff_complete),
        ):
            if not ready:
                blockers.append(f"{label} signoff is incomplete")
        raise ReleaseCertificationError("; ".join(blockers))
