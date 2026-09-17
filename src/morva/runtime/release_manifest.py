from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path


class ReleaseManifestError(ValueError):
    """Raised when a release artifact manifest is incomplete or invalid."""


@dataclass(frozen=True, slots=True)
class ReleaseArtifact:
    path: str
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        if not self.path.strip():
            raise ReleaseManifestError("artifact path is required")
        if self.path.startswith("/") or ".." in Path(self.path).parts:
            raise ReleaseManifestError("artifact path must be relative and traversal-free")
        if not self.sha256 or len(self.sha256) != 64 or any(
            char not in "0123456789abcdef" for char in self.sha256.lower()
        ):
            raise ReleaseManifestError("artifact sha256 must be a SHA-256 hex digest")
        if self.size_bytes < 0:
            raise ReleaseManifestError("artifact size_bytes cannot be negative")


@dataclass(frozen=True, slots=True)
class ReleaseManifest:
    release_id: str
    tag: str
    candidate_sha: str
    artifacts: tuple[ReleaseArtifact, ...]

    def __post_init__(self) -> None:
        if not self.release_id.strip():
            raise ReleaseManifestError("release_id is required")
        if not self.tag.strip():
            raise ReleaseManifestError("tag is required")
        if len(self.candidate_sha) != 40 or any(
            char not in "0123456789abcdef" for char in self.candidate_sha.lower()
        ):
            raise ReleaseManifestError("candidate_sha must be a Git commit SHA-1")
        paths = tuple(item.path for item in self.artifacts)
        if len(paths) != len(set(paths)):
            raise ReleaseManifestError("artifact paths must be unique")
        if not self.artifacts:
            raise ReleaseManifestError("at least one release artifact is required")

    @property
    def fingerprint(self) -> str:
        payload = {
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha.lower(),
            "artifacts": tuple(
                (item.path, item.sha256.lower(), item.size_bytes) for item in self.artifacts
            ),
        }
        canonical = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()

    def assert_matches(self, expected_sha: str) -> None:
        if expected_sha.lower() != self.candidate_sha.lower():
            raise ReleaseManifestError("candidate_sha does not match expected release commit")

    def verify_files(self, artifact_dir: Path) -> None:
        root = artifact_dir.resolve()
        if not root.is_dir():
            raise ReleaseManifestError(f"artifact directory does not exist: {root}")
        expected = {item.path: item for item in self.artifacts}
        actual_paths = {
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_file() and not path.name.startswith(".")
        }
        missing = sorted(set(expected) - actual_paths)
        unexpected = sorted(actual_paths - set(expected))
        if missing or unexpected:
            details = []
            if missing:
                details.append(f"missing artifacts: {', '.join(missing)}")
            if unexpected:
                details.append(f"unexpected artifacts: {', '.join(unexpected)}")
            raise ReleaseManifestError("; ".join(details))

        for relative_path, expected_artifact in expected.items():
            path = root / relative_path
            digest = sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            actual_sha = digest.hexdigest()
            actual_size = path.stat().st_size
            if actual_sha != expected_artifact.sha256.lower():
                raise ReleaseManifestError(f"artifact sha256 mismatch: {relative_path}")
            if actual_size != expected_artifact.size_bytes:
                raise ReleaseManifestError(f"artifact size mismatch: {relative_path}")
