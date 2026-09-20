from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path


class ExternalCertificationEvidenceError(ValueError):
    """Raised when required external certification evidence is invalid."""


REQUIRED_ROLES = (
    "legal_approval",
    "finance_approval",
    "security_assessment",
    "operations_approval",
    "authoritative_master_data",
    "official_adapters",
    "reconciliation_evidence",
    "dr_exercise",
    "load_validation",
    "release_certification",
    "publication_evidence",
    "deployment_validation",
)


@dataclass(frozen=True, slots=True)
class ExternalCertificationEvidence:
    evidence_version: int
    role: str
    evidence_id: str
    repository: str
    candidate_sha: str
    issuer: str
    status: str
    digest_sha256: str
    verified_at: str
    expires_at: str | None = None

    def __post_init__(self) -> None:
        if self.evidence_version != 1:
            raise ExternalCertificationEvidenceError(
                "unsupported external evidence version"
            )
        if self.role not in REQUIRED_ROLES:
            raise ExternalCertificationEvidenceError(
                "unsupported external evidence role"
            )
        if not self.evidence_id.strip() or not self.issuer.strip():
            raise ExternalCertificationEvidenceError(
                "evidence_id and issuer are required"
            )
        if not self.repository.strip():
            raise ExternalCertificationEvidenceError(
                "repository is required"
            )
        if len(self.candidate_sha) != 40 or any(
            c not in "0123456789abcdef"
            for c in self.candidate_sha.lower()
        ):
            raise ExternalCertificationEvidenceError(
                "candidate_sha must be a Git commit SHA-1"
            )
        if self.status != "verified":
            raise ExternalCertificationEvidenceError(
                "external evidence status must be verified"
            )
        if len(self.digest_sha256) != 64 or any(
            c not in "0123456789abcdef"
            for c in self.digest_sha256.lower()
        ):
            raise ExternalCertificationEvidenceError(
                "digest_sha256 must be SHA-256"
            )
        for name, value in (
            ("verified_at", self.verified_at),
            ("expires_at", self.expires_at),
        ):
            if value is None:
                continue
            try:
                timestamp = datetime.fromisoformat(value)
            except ValueError as exc:
                raise ExternalCertificationEvidenceError(
                    f"{name} must be ISO-8601"
                ) from exc
            if timestamp.tzinfo is None:
                raise ExternalCertificationEvidenceError(
                    f"{name} must include a timezone"
                )

    def to_payload(self) -> dict[str, object]:
        return {
            "evidence_version": self.evidence_version,
            "role": self.role,
            "evidence_id": self.evidence_id,
            "repository": self.repository,
            "candidate_sha": self.candidate_sha,
            "issuer": self.issuer,
            "status": self.status,
            "digest_sha256": self.digest_sha256,
            "verified_at": self.verified_at,
            "expires_at": self.expires_at,
        }


def load_evidence(path: Path) -> ExternalCertificationEvidence:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExternalCertificationEvidenceError(
            f"external evidence file is invalid: {path}"
        ) from exc
    try:
        return ExternalCertificationEvidence(
            evidence_version=int(payload["evidence_version"]),
            role=payload["role"],
            evidence_id=payload["evidence_id"],
            repository=payload["repository"],
            candidate_sha=payload["candidate_sha"],
            issuer=payload["issuer"],
            status=payload["status"],
            digest_sha256=payload["digest_sha256"],
            verified_at=payload["verified_at"],
            expires_at=payload.get("expires_at"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ExternalCertificationEvidenceError(
            "external evidence structure is invalid"
        ) from exc


def build_evidence_registry(
    paths: tuple[Path, ...],
    *,
    repository: str,
    candidate_sha: str,
    checked_at: datetime,
) -> tuple[ExternalCertificationEvidence, ...]:
    if not paths:
        raise ExternalCertificationEvidenceError(
            "evidence registry cannot be empty"
        )
    if checked_at.tzinfo is None:
        raise ExternalCertificationEvidenceError(
            "checked_at must be timezone-aware"
        )
    items = tuple(load_evidence(path) for path in paths)
    roles = [item.role for item in items]
    if len(roles) != len(set(roles)):
        raise ExternalCertificationEvidenceError(
            "duplicate external evidence role"
        )
    if set(roles) != set(REQUIRED_ROLES):
        missing = sorted(set(REQUIRED_ROLES) - set(roles))
        unexpected = sorted(set(roles) - set(REQUIRED_ROLES))
        detail = []
        if missing:
            detail.append(f"missing={','.join(missing)}")
        if unexpected:
            detail.append(f"unexpected={','.join(unexpected)}")
        raise ExternalCertificationEvidenceError(
            "external evidence role set mismatch: " + "; ".join(detail)
        )
    now = checked_at.astimezone(timezone.utc)
    for item in items:
        if item.repository != repository:
            raise ExternalCertificationEvidenceError(
                f"repository mismatch for role {item.role}"
            )
        if item.candidate_sha.lower() != candidate_sha.lower():
            raise ExternalCertificationEvidenceError(
                f"candidate SHA mismatch for role {item.role}"
            )
        verified_at = datetime.fromisoformat(item.verified_at)
        if verified_at > now:
            raise ExternalCertificationEvidenceError(
                f"verification timestamp is in the future for role {item.role}"
            )
        if item.expires_at is not None:
            if datetime.fromisoformat(item.expires_at) <= now:
                raise ExternalCertificationEvidenceError(
                    f"external evidence is expired for role {item.role}"
                )
    role_order = {role: index for index, role in enumerate(REQUIRED_ROLES)}
    return tuple(sorted(items, key=lambda item: role_order[item.role]))


@dataclass(frozen=True, slots=True)
class ExternalCertificationEvidenceRegistry:
    registry_version: int
    repository: str
    candidate_sha: str
    items: tuple[ExternalCertificationEvidence, ...]
    registered_at: datetime

    def __post_init__(self) -> None:
        if self.registry_version != 1:
            raise ExternalCertificationEvidenceError(
                "unsupported evidence registry version"
            )
        if self.repository.strip() == "":
            raise ExternalCertificationEvidenceError(
                "repository is required"
            )
        if len(self.items) != len(REQUIRED_ROLES):
            raise ExternalCertificationEvidenceError(
                "complete external evidence registry is required"
            )
        if self.registered_at.tzinfo is None:
            raise ExternalCertificationEvidenceError(
                "registered_at must be timezone-aware"
            )

    @property
    def fingerprint(self) -> str:
        payload = {
            "registry_version": self.registry_version,
            "repository": self.repository,
            "candidate_sha": self.candidate_sha.lower(),
            "items": [item.to_payload() for item in self.items],
        }
        canonical = json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(canonical.encode("utf-8")).hexdigest()

    def to_payload(self) -> dict[str, object]:
        return {
            "registry_version": self.registry_version,
            "repository": self.repository,
            "candidate_sha": self.candidate_sha,
            "items": [item.to_payload() for item in self.items],
            "registered_at": self.registered_at.isoformat(),
            "fingerprint": self.fingerprint,
        }


def write_registry(
    registry: ExternalCertificationEvidenceRegistry,
    path: Path,
) -> None:
    if path.exists():
        raise ExternalCertificationEvidenceError(
            "external certification evidence registry is write-once"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            registry.to_payload(),
            ensure_ascii=True,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
