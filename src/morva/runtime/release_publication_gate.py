from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json


class ReleasePublicationGateError(ValueError):
    """Raised when release publication inputs do not match exactly."""


@dataclass(frozen=True, slots=True)
class ReleasePublicationGate:
    gate_version: int
    repository: str
    release_id: str
    tag: str
    candidate_sha: str
    artifact_id: str
    artifact_fingerprint: str
    archive_sha256: str
    archive_size_bytes: int
    verified_at: datetime
    publication_target: str = "github_release"

    def __post_init__(self) -> None:
        if self.gate_version != 1:
            raise ReleasePublicationGateError("unsupported publication gate version")
        if not self.repository.strip():
            raise ReleasePublicationGateError("repository is required")
        if not self.release_id.strip() or not self.tag.strip():
            raise ReleasePublicationGateError("release_id and tag are required")
        if len(self.candidate_sha) != 40 or any(
            char not in "0123456789abcdef" for char in self.candidate_sha.lower()
        ):
            raise ReleasePublicationGateError("candidate_sha must be a Git commit SHA-1")
        for name, value in (
            ("artifact_fingerprint", self.artifact_fingerprint),
            ("archive_sha256", self.archive_sha256),
        ):
            if len(value) != 64 or any(
                char not in "0123456789abcdef" for char in value.lower()
            ):
                raise ReleasePublicationGateError(
                    f"{name} must be a SHA-256 hex digest"
                )
        if not self.artifact_id.strip().startswith("morva-trust-evidence-v1-"):
            raise ReleasePublicationGateError(
                "artifact_id must use the M3.52 trust-artifact identifier"
            )
        if self.archive_size_bytes <= 0:
            raise ReleasePublicationGateError("archive_size_bytes must be positive")
        if self.verified_at.tzinfo is None:
            raise ReleasePublicationGateError("verified_at must be timezone-aware")
        if self.publication_target != "github_release":
            raise ReleasePublicationGateError(
                "unsupported publication target"
            )

    @property
    def fingerprint(self) -> str:
        payload = {
            "gate_version": self.gate_version,
            "repository": self.repository,
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha.lower(),
            "artifact_id": self.artifact_id,
            "artifact_fingerprint": self.artifact_fingerprint.lower(),
            "archive_sha256": self.archive_sha256.lower(),
            "archive_size_bytes": self.archive_size_bytes,
            "verified_at": self.verified_at.isoformat(),
            "publication_target": self.publication_target,
        }
        canonical = json.dumps(
            payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        )
        return sha256(canonical.encode("utf-8")).hexdigest()

    def assert_matches_artifact(self, artifact: object) -> None:
        expected = {
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha.lower(),
            "artifact_id": self.artifact_id,
            "artifact_fingerprint": self.artifact_fingerprint.lower(),
            "archive_sha256": self.archive_sha256.lower(),
            "archive_size_bytes": self.archive_size_bytes,
        }
        actual = {
            "release_id": artifact.release_id,
            "tag": artifact.tag,
            "candidate_sha": artifact.candidate_sha.lower(),
            "artifact_id": artifact.artifact_id,
            "artifact_fingerprint": artifact.fingerprint.lower(),
            "archive_sha256": artifact.archive_sha256.lower(),
            "archive_size_bytes": artifact.archive_size_bytes,
        }
        if expected != actual:
            raise ReleasePublicationGateError("publication gate does not match trust artifact")

    @property
    def release_ref(self) -> str:
        return f"refs/tags/{self.tag}"

    def to_payload(self) -> dict[str, object]:
        return {
            "gate_version": self.gate_version,
            "repository": self.repository,
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha,
            "artifact_id": self.artifact_id,
            "artifact_fingerprint": self.artifact_fingerprint,
            "archive_sha256": self.archive_sha256,
            "archive_size_bytes": self.archive_size_bytes,
            "verified_at": self.verified_at.isoformat(),
            "publication_target": self.publication_target,
            "release_ref": self.release_ref,
            "fingerprint": self.fingerprint,
        }