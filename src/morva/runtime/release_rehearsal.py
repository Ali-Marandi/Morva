from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

from .release_gate import ReleaseGate, ReleaseGateError
from .release_manifest import ReleaseManifest


class ReleaseRehearsalError(ValueError):
    """Raised when a release rehearsal is internally inconsistent or not ready."""


@dataclass(frozen=True, slots=True)
class ReleaseRehearsal:
    candidate_sha: str
    tag: str
    manifest: ReleaseManifest
    gate: ReleaseGate

    def __post_init__(self) -> None:
        if len(self.candidate_sha) != 40 or any(
            char not in "0123456789abcdef" for char in self.candidate_sha.lower()
        ):
            raise ReleaseRehearsalError("candidate_sha must be a Git commit SHA-1")
        expected = self.candidate_sha.lower()
        if self.manifest.candidate_sha.lower() != expected:
            raise ReleaseRehearsalError("manifest candidate_sha does not match rehearsal SHA")
        if self.gate.candidate_sha.lower() != expected:
            raise ReleaseRehearsalError("release gate candidate_sha does not match rehearsal SHA")
        if self.manifest.tag != self.tag:
            raise ReleaseRehearsalError("manifest tag does not match rehearsal tag")
        if self.gate.attestation.tag != self.tag:
            raise ReleaseRehearsalError("attestation tag does not match rehearsal tag")
        if self.manifest.release_id != self.gate.certification.release_id:
            raise ReleaseRehearsalError(
                "manifest release_id does not match certification release_id"
            )
        if self.manifest.release_id != self.gate.attestation.release_id:
            raise ReleaseRehearsalError(
                "manifest release_id does not match attestation release_id"
            )
        manifest_artifacts = {
            (item.path, item.sha256.lower()) for item in self.manifest.artifacts
        }
        attestation_artifacts = {
            (item.path, item.sha256.lower()) for item in self.gate.attestation.artifacts
        }
        if manifest_artifacts != attestation_artifacts:
            raise ReleaseRehearsalError(
                "manifest artifacts do not exactly match attestation artifacts"
            )

    @property
    def release_ready(self) -> bool:
        return self.gate.release_ready

    @property
    def blockers(self) -> tuple[str, ...]:
        return self.gate.blockers

    @property
    def fingerprint(self) -> str:
        payload = {
            "candidate_sha": self.candidate_sha.lower(),
            "tag": self.tag,
            "release_id": self.manifest.release_id,
            "manifest": self.manifest.fingerprint,
            "gate": self.gate.fingerprint,
        }
        canonical = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()

    def assert_consistent(self, artifact_dir: Path | None = None) -> None:
        if artifact_dir is None:
            return
        try:
            self.manifest.verify_files(artifact_dir)
        except ValueError as exc:
            raise ReleaseRehearsalError(str(exc)) from exc

    def assert_release_ready(self, artifact_dir: Path | None = None) -> None:
        self.assert_consistent(artifact_dir)
        try:
            self.gate.assert_release_ready()
        except ReleaseGateError as exc:
            raise ReleaseRehearsalError(str(exc)) from exc
