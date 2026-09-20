from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path


class ProductionReadinessHandoffError(ValueError):
    """Raised when a production-readiness handoff package is invalid."""


PRIVATE_MARKERS = (
    b"BEGIN PRIVATE KEY",
    b"BEGIN OPENSSH PRIVATE KEY",
    b"BEGIN RSA PRIVATE KEY",
    b"BEGIN EC PRIVATE KEY",
)
CREDENTIAL_MARKERS = (
    b"ghp_",
    b"github_pat_",
    b"AWS_SECRET_ACCESS_KEY",
)


@dataclass(frozen=True, slots=True)
class HandoffSource:
    path: str
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        candidate = Path(self.path)
        if (
            not self.path.strip()
            or candidate.is_absolute()
            or ".." in candidate.parts
            or str(candidate) == "."
        ):
            raise ProductionReadinessHandoffError(
                "handoff source path must be relative and traversal-free"
            )
        if len(self.sha256) != 64 or any(
            c not in "0123456789abcdef" for c in self.sha256.lower()
        ):
            raise ProductionReadinessHandoffError(
                "handoff source sha256 must be a SHA-256 hex digest"
            )
        if self.size_bytes < 0:
            raise ProductionReadinessHandoffError(
                "handoff source size_bytes cannot be negative"
            )


@dataclass(frozen=True, slots=True)
class ProductionReadinessHandoff:
    handoff_version: int
    repository: str
    release_id: str
    tag: str
    candidate_sha: str
    convergence_fingerprint: str
    sources: tuple[HandoffSource, ...]
    created_at: datetime

    def __post_init__(self) -> None:
        if self.handoff_version != 1:
            raise ProductionReadinessHandoffError(
                "unsupported handoff version"
            )
        if not self.repository.strip() or not self.release_id.strip():
            raise ProductionReadinessHandoffError(
                "repository and release_id are required"
            )
        if not self.tag.strip():
            raise ProductionReadinessHandoffError("tag is required")
        if len(self.candidate_sha) != 40 or any(
            c not in "0123456789abcdef" for c in self.candidate_sha.lower()
        ):
            raise ProductionReadinessHandoffError(
                "candidate_sha must be a Git commit SHA-1"
            )
        if len(self.convergence_fingerprint) != 64 or any(
            c not in "0123456789abcdef"
            for c in self.convergence_fingerprint.lower()
        ):
            raise ProductionReadinessHandoffError(
                "convergence_fingerprint must be SHA-256"
            )
        if not self.sources:
            raise ProductionReadinessHandoffError(
                "handoff must contain at least one source"
            )
        paths = tuple(source.path for source in self.sources)
        if len(paths) != len(set(paths)):
            raise ProductionReadinessHandoffError(
                "handoff source paths must be unique"
            )
        if self.created_at.tzinfo is None:
            raise ProductionReadinessHandoffError(
                "created_at must be timezone-aware"
            )

    @property
    def fingerprint(self) -> str:
        payload = {
            "handoff_version": self.handoff_version,
            "repository": self.repository,
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha.lower(),
            "convergence_fingerprint": self.convergence_fingerprint.lower(),
            "sources": [
                (source.path, source.sha256.lower(), source.size_bytes)
                for source in self.sources
            ],
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
            "handoff_version": self.handoff_version,
            "repository": self.repository,
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha,
            "convergence_fingerprint": self.convergence_fingerprint,
            "sources": [
                {
                    "path": source.path,
                    "sha256": source.sha256,
                    "size_bytes": source.size_bytes,
                }
                for source in self.sources
            ],
            "created_at": self.created_at.isoformat(),
            "fingerprint": self.fingerprint,
        }


def build_handoff(
    *,
    root: Path,
    source_paths: tuple[str, ...],
    repository: str,
    release_id: str,
    tag: str,
    candidate_sha: str,
    convergence_fingerprint: str,
    created_at: datetime,
) -> ProductionReadinessHandoff:
    if created_at.tzinfo is None:
        raise ProductionReadinessHandoffError(
            "created_at must be timezone-aware"
        )
    sources: list[HandoffSource] = []
    for relative in sorted(set(source_paths)):
        path = root / relative
        if path.is_symlink():
            raise ProductionReadinessHandoffError(
                f"handoff source cannot be a symlink: {relative}"
            )
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise ProductionReadinessHandoffError(
                f"handoff source is unreadable: {relative}"
            ) from exc
        if any(marker in data for marker in PRIVATE_MARKERS):
            raise ProductionReadinessHandoffError(
                f"private-key material found in handoff source: {relative}"
            )
        if any(marker in data for marker in CREDENTIAL_MARKERS):
            raise ProductionReadinessHandoffError(
                f"credential material found in handoff source: {relative}"
            )
        sources.append(
            HandoffSource(
                path=relative,
                sha256=sha256(data).hexdigest(),
                size_bytes=len(data),
            )
        )
    return ProductionReadinessHandoff(
        handoff_version=1,
        repository=repository,
        release_id=release_id,
        tag=tag,
        candidate_sha=candidate_sha,
        convergence_fingerprint=convergence_fingerprint,
        sources=tuple(sources),
        created_at=created_at,
    )


def verify_handoff_sources(
    *,
    handoff: ProductionReadinessHandoff,
    root: Path,
) -> None:
    expected_paths = {source.path for source in handoff.sources}
    if not root.is_dir():
        raise ProductionReadinessHandoffError(
            f"handoff source root does not exist: {root}"
        )
    discovered = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ProductionReadinessHandoffError(
                f"handoff source tree contains a symlink: {path.relative_to(root)}"
            )
        if path.is_file():
            discovered.add(str(path.relative_to(root)))
    if discovered != expected_paths:
        raise ProductionReadinessHandoffError(
            "handoff source set differs from recorded manifest"
        )
    for source in handoff.sources:
        path = root / source.path
        data = path.read_bytes()
        if sha256(data).hexdigest() != source.sha256.lower():
            raise ProductionReadinessHandoffError(
                f"handoff source sha256 mismatch: {source.path}"
            )
        if len(data) != source.size_bytes:
            raise ProductionReadinessHandoffError(
                f"handoff source size mismatch: {source.path}"
            )


def write_handoff(
    handoff: ProductionReadinessHandoff,
    path: Path,
) -> None:
    if path.exists():
        raise ProductionReadinessHandoffError(
            "production-readiness handoff is write-once"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            handoff.to_payload(),
            ensure_ascii=True,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def load_handoff(path: Path) -> ProductionReadinessHandoff:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        sources = tuple(
            HandoffSource(
                path=item["path"],
                sha256=item["sha256"],
                size_bytes=int(item["size_bytes"]),
            )
            for item in payload["sources"]
        )
        handoff = ProductionReadinessHandoff(
            handoff_version=int(payload["handoff_version"]),
            repository=payload["repository"],
            release_id=payload["release_id"],
            tag=payload["tag"],
            candidate_sha=payload["candidate_sha"],
            convergence_fingerprint=payload["convergence_fingerprint"],
            sources=sources,
            created_at=datetime.fromisoformat(payload["created_at"]),
        )
    except (
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        raise ProductionReadinessHandoffError(
            "production-readiness handoff structure is invalid"
        ) from exc
    if payload.get("fingerprint") != handoff.fingerprint:
        raise ProductionReadinessHandoffError(
            "production-readiness handoff fingerprint mismatch"
        )
    return handoff
