from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json


class ReleaseAttestationError(ValueError):
    """Raised when release provenance or signing evidence is incomplete or invalid."""


@dataclass(frozen=True, slots=True)
class ArtifactAttestation:
    path: str
    sha256: str

    def __post_init__(self) -> None:
        if not self.path.strip():
            raise ReleaseAttestationError("artifact path is required")
        if len(self.sha256) != 64 or any(
            char not in "0123456789abcdef" for char in self.sha256.lower()
        ):
            raise ReleaseAttestationError("artifact sha256 must be a SHA-256 hex digest")


@dataclass(frozen=True, slots=True)
class ReleaseAttestation:
    release_id: str
    tag: str
    candidate_sha: str
    certification_fingerprint: str
    evidence_bundle_fingerprint: str
    artifacts: tuple[ArtifactAttestation, ...]
    signer: str | None = None
    signed_at: datetime | None = None
    signature_uri: str | None = None
    release_uri: str | None = None

    def __post_init__(self) -> None:
        if not self.release_id.strip():
            raise ReleaseAttestationError("release_id is required")
        if not self.tag.strip():
            raise ReleaseAttestationError("tag is required")
        if len(self.candidate_sha) != 40 or any(
            char not in "0123456789abcdef" for char in self.candidate_sha.lower()
        ):
            raise ReleaseAttestationError("candidate_sha must be a Git commit SHA-1")
        for name, value in (
            ("certification_fingerprint", self.certification_fingerprint),
            ("evidence_bundle_fingerprint", self.evidence_bundle_fingerprint),
        ):
            if len(value) != 64 or any(char not in "0123456789abcdef" for char in value.lower()):
                raise ReleaseAttestationError(f"{name} must be a SHA-256 hex digest")
        paths = [artifact.path for artifact in self.artifacts]
        if len(paths) != len(set(paths)):
            raise ReleaseAttestationError("artifact paths must be unique")
        if self.signed_at is not None and self.signed_at.tzinfo is None:
            raise ReleaseAttestationError("signed_at must be timezone-aware")

    @property
    def signing_complete(self) -> bool:
        return bool(self.signer and self.signed_at and self.signature_uri)

    @property
    def release_evidence_complete(self) -> bool:
        return bool(self.artifacts and self.release_uri)

    @property
    def release_ready(self) -> bool:
        return self.signing_complete and self.release_evidence_complete

    @property
    def fingerprint(self) -> str:
        payload = {
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha.lower(),
            "certification_fingerprint": self.certification_fingerprint.lower(),
            "evidence_bundle_fingerprint": self.evidence_bundle_fingerprint.lower(),
            "artifacts": tuple((item.path, item.sha256.lower()) for item in self.artifacts),
            "signer": self.signer,
            "signed_at": self.signed_at.isoformat() if self.signed_at else None,
            "signature_uri": self.signature_uri,
            "release_uri": self.release_uri,
        }
        canonical = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()

    def assert_release_ready(self) -> None:
        if self.release_ready:
            return
        blockers: list[str] = []
        if not self.artifacts:
            blockers.append("release artifacts are missing")
        if not self.release_uri:
            blockers.append("release URI is missing")
        if not self.signing_complete:
            blockers.append("release signing evidence is incomplete")
        raise ReleaseAttestationError("; ".join(blockers))
