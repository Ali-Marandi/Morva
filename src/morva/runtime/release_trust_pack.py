from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import re


class ReleaseTrustPackError(ValueError):
    """Raised when a release trust evidence pack is invalid."""


@dataclass(frozen=True, slots=True)
class TrustPackSource:
    role: str
    path: str
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        if not self.role.strip():
            raise ReleaseTrustPackError("source role is required")
        candidate = Path(self.path)
        if (
            not self.path.strip()
            or candidate.is_absolute()
            or ".." in candidate.parts
        ):
            raise ReleaseTrustPackError("source path must be relative and traversal-free")
        if len(self.sha256) != 64 or any(
            char not in "0123456789abcdef" for char in self.sha256.lower()
        ):
            raise ReleaseTrustPackError("source sha256 must be a SHA-256 hex digest")
        if self.size_bytes < 0:
            raise ReleaseTrustPackError("source size_bytes cannot be negative")


@dataclass(frozen=True, slots=True)
class ReleaseTrustEvidencePack:
    pack_id: str
    release_id: str
    tag: str
    candidate_sha: str
    verified_at: datetime
    bundle_fingerprint: str
    signing_key_rotation_fingerprint: str
    root_rotation_fingerprint: str
    chain_fingerprint: str
    previous_registry_fingerprint: str
    intermediate_registry_fingerprint: str
    current_registry_fingerprint: str
    sources: tuple[TrustPackSource, ...]

    REQUIRED_ROLES = (
        "release_bundle",
        "manifest",
        "gate",
        "rehearsal",
        "release_signing_public_key",
        "previous_registry",
        "intermediate_registry",
        "current_registry",
        "signing_key_rotation",
        "root_rotation",
        "old_root_public_key",
        "new_root_public_key",
        "chain_verification_receipt",
    )

    def __post_init__(self) -> None:
        if not self.pack_id.strip() or not self.release_id.strip() or not self.tag.strip():
            raise ReleaseTrustPackError("pack_id, release_id and tag are required")
        if len(self.candidate_sha) != 40 or any(
            char not in "0123456789abcdef" for char in self.candidate_sha.lower()
        ):
            raise ReleaseTrustPackError("candidate_sha must be a Git commit SHA-1")
        if self.verified_at.tzinfo is None:
            raise ReleaseTrustPackError("verified_at must be timezone-aware")
        for name, value in (
            ("bundle_fingerprint", self.bundle_fingerprint),
            ("signing_key_rotation_fingerprint", self.signing_key_rotation_fingerprint),
            ("root_rotation_fingerprint", self.root_rotation_fingerprint),
            ("chain_fingerprint", self.chain_fingerprint),
            ("previous_registry_fingerprint", self.previous_registry_fingerprint),
            ("intermediate_registry_fingerprint", self.intermediate_registry_fingerprint),
            ("current_registry_fingerprint", self.current_registry_fingerprint),
        ):
            if len(value) != 64 or any(
                char not in "0123456789abcdef" for char in value.lower()
            ):
                raise ReleaseTrustPackError(f"{name} must be a SHA-256 hex digest")
        roles = tuple(item.role for item in self.sources)
        paths = tuple(item.path for item in self.sources)
        if set(roles) != set(self.REQUIRED_ROLES) or len(roles) != len(self.REQUIRED_ROLES):
            raise ReleaseTrustPackError(
                "trust pack must contain exactly one source for each required role"
            )
        if len(paths) != len(set(paths)):
            raise ReleaseTrustPackError("trust pack source paths must be unique")

    @property
    def fingerprint(self) -> str:
        payload = {
            "pack_id": self.pack_id,
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha.lower(),
            "verified_at": self.verified_at.isoformat(),
            "bundle_fingerprint": self.bundle_fingerprint.lower(),
            "signing_key_rotation_fingerprint": (
                self.signing_key_rotation_fingerprint.lower()
            ),
            "root_rotation_fingerprint": self.root_rotation_fingerprint.lower(),
            "chain_fingerprint": self.chain_fingerprint.lower(),
            "previous_registry_fingerprint": self.previous_registry_fingerprint.lower(),
            "intermediate_registry_fingerprint": (
                self.intermediate_registry_fingerprint.lower()
            ),
            "current_registry_fingerprint": self.current_registry_fingerprint.lower(),
            "sources": tuple(
                (item.role, item.path, item.sha256.lower(), item.size_bytes)
                for item in sorted(self.sources, key=lambda entry: entry.role)
            ),
        }
        canonical = json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(canonical.encode("utf-8")).hexdigest()

    def source_for(self, role: str) -> TrustPackSource:
        for source in self.sources:
            if source.role == role:
                return source
        raise ReleaseTrustPackError(f"missing trust-pack role: {role}")

    def verify_files(self, root: Path) -> None:
        base = root.resolve()
        if not base.is_dir():
            raise ReleaseTrustPackError(f"trust pack root does not exist: {base}")
        expected = {source.path for source in self.sources}
        actual = {
            path.relative_to(base).as_posix()
            for path in base.rglob("*")
            if path.is_file() and path.relative_to(base).as_posix() != "pack.json"
        }
        if actual != expected:
            missing = sorted(expected - actual)
            unexpected = sorted(actual - expected)
            raise ReleaseTrustPackError(
                f"trust pack file set mismatch; missing={missing}, unexpected={unexpected}"
            )
        for source in self.sources:
            path = base / source.path
            digest = sha256(path.read_bytes()).hexdigest()
            if digest != source.sha256.lower():
                raise ReleaseTrustPackError(
                    f"trust pack source sha256 mismatch: {source.role}"
                )
            if path.stat().st_size != source.size_bytes:
                raise ReleaseTrustPackError(
                    f"trust pack source size mismatch: {source.role}"
                )
            if source.role.endswith("public_key") and b"PRIVATE KEY" in path.read_bytes():
                raise ReleaseTrustPackError(
                    f"private key material is forbidden in trust pack: {source.role}"
                )

    @property
    def source_map(self) -> dict[str, TrustPackSource]:
        return {source.role: source for source in self.sources}


def _is_private_key_bytes(data: bytes) -> bool:
    return re.search(rb"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----", data) is not None


def reject_private_key_material(root: Path) -> None:
    base = root.resolve()
    if not base.is_dir():
        raise ReleaseTrustPackError(f"trust pack root does not exist: {base}")
    for path in base.rglob("*"):
        if not path.is_file():
            continue
        if path.name == "pack.json":
            continue
        data = path.read_bytes()
        if _is_private_key_bytes(data):
            raise ReleaseTrustPackError(
                f"private key material is forbidden in trust pack: {path.name}"
            )
