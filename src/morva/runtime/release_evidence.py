from __future__ import annotations

from base64 import b64decode, b64encode
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .release_rehearsal import ReleaseRehearsal


class ReleaseEvidenceError(ValueError):
    """Raised when a release evidence bundle is invalid or cannot be verified."""


@dataclass(frozen=True, slots=True)
class EvidenceFile:
    path: str
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        if (
            not self.path.strip()
            or self.path.startswith("/")
            or ".." in Path(self.path).parts
        ):
            raise ReleaseEvidenceError("evidence file path must be relative and traversal-free")
        if len(self.sha256) != 64 or any(
            char not in "0123456789abcdef" for char in self.sha256.lower()
        ):
            raise ReleaseEvidenceError("evidence file sha256 must be a SHA-256 hex digest")
        if self.size_bytes < 0:
            raise ReleaseEvidenceError("evidence file size_bytes cannot be negative")


@dataclass(frozen=True, slots=True)
class EvidenceBundleSignature:
    algorithm: str
    key_id: str
    signature_b64: str
    signed_at: datetime

    def __post_init__(self) -> None:
        if self.algorithm != "Ed25519":
            raise ReleaseEvidenceError("unsupported evidence signature algorithm")
        if not self.key_id.strip():
            raise ReleaseEvidenceError("signature key_id is required")
        if not self.signature_b64.strip():
            raise ReleaseEvidenceError("signature value is required")
        if self.signed_at.tzinfo is None:
            raise ReleaseEvidenceError("signed_at must be timezone-aware")
        try:
            raw = b64decode(self.signature_b64, validate=True)
        except Exception as exc:
            raise ReleaseEvidenceError("signature_b64 is not valid base64") from exc
        if len(raw) != 64:
            raise ReleaseEvidenceError("Ed25519 signature must be 64 bytes")


@dataclass(frozen=True, slots=True)
class ReleaseEvidenceBundle:
    release_id: str
    tag: str
    candidate_sha: str
    manifest_fingerprint: str
    gate_fingerprint: str
    rehearsal_fingerprint: str
    registry_id: str
    registry_version: int
    registry_fingerprint: str
    evidence_files: tuple[EvidenceFile, ...]
    signature: EvidenceBundleSignature | None = None

    def __post_init__(self) -> None:
        if not self.release_id.strip() or not self.tag.strip():
            raise ReleaseEvidenceError("release_id and tag are required")
        if len(self.candidate_sha) != 40 or any(
            char not in "0123456789abcdef" for char in self.candidate_sha.lower()
        ):
            raise ReleaseEvidenceError("candidate_sha must be a Git commit SHA-1")
        if not self.registry_id.strip():
            raise ReleaseEvidenceError("registry_id is required")
        if self.registry_version < 1:
            raise ReleaseEvidenceError("registry_version must be positive")
        for name, value in (
            ("manifest_fingerprint", self.manifest_fingerprint),
            ("gate_fingerprint", self.gate_fingerprint),
            ("rehearsal_fingerprint", self.rehearsal_fingerprint),
            ("registry_fingerprint", self.registry_fingerprint),
        ):
            if len(value) != 64 or any(
                char not in "0123456789abcdef" for char in value.lower()
            ):
                raise ReleaseEvidenceError(f"{name} must be a SHA-256 hex digest")
        paths = tuple(item.path for item in self.evidence_files)
        if not paths:
            raise ReleaseEvidenceError("at least one evidence file is required")
        if len(paths) != len(set(paths)):
            raise ReleaseEvidenceError("evidence file paths must be unique")

    @property
    def fingerprint(self) -> str:
        payload = self._payload()
        signature = self.signature
        if signature is not None:
            payload["signature_context"] = {
                "algorithm": signature.algorithm,
                "key_id": signature.key_id,
                "signed_at": signature.signed_at.isoformat(),
            }
        canonical = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()

    def _payload(self) -> dict[str, object]:
        return {
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha.lower(),
            "manifest_fingerprint": self.manifest_fingerprint.lower(),
            "gate_fingerprint": self.gate_fingerprint.lower(),
            "rehearsal_fingerprint": self.rehearsal_fingerprint.lower(),
            "registry_id": self.registry_id,
            "registry_version": self.registry_version,
            "registry_fingerprint": self.registry_fingerprint.lower(),
            "evidence_files": tuple(
                (item.path, item.sha256.lower(), item.size_bytes)
                for item in self.evidence_files
            ),
        }

    def signing_bytes(self, signature_context: EvidenceBundleSignature | None = None) -> bytes:
        payload = self._payload()
        context = signature_context or self.signature
        if context is None:
            raise ReleaseEvidenceError("signature context is required for signing")
        payload["signature_context"] = {
            "algorithm": context.algorithm,
            "key_id": context.key_id,
            "signed_at": context.signed_at.isoformat(),
        }
        canonical = json.dumps(
            payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        )
        return canonical.encode("utf-8")

    def assert_matches_rehearsal(self, rehearsal: ReleaseRehearsal) -> None:
        if self.release_id != rehearsal.manifest.release_id:
            raise ReleaseEvidenceError("bundle release_id does not match rehearsal")
        if self.tag != rehearsal.tag:
            raise ReleaseEvidenceError("bundle tag does not match rehearsal")
        if self.candidate_sha.lower() != rehearsal.candidate_sha.lower():
            raise ReleaseEvidenceError("bundle candidate_sha does not match rehearsal")
        if self.manifest_fingerprint != rehearsal.manifest.fingerprint:
            raise ReleaseEvidenceError("bundle manifest fingerprint does not match rehearsal")
        if self.gate_fingerprint != rehearsal.gate.fingerprint:
            raise ReleaseEvidenceError("bundle gate fingerprint does not match rehearsal")
        if self.rehearsal_fingerprint != rehearsal.fingerprint:
            raise ReleaseEvidenceError("bundle rehearsal fingerprint does not match rehearsal")

    def verify_files(self, root: Path) -> None:
        base = root.resolve()
        if not base.is_dir():
            raise ReleaseEvidenceError(f"evidence root does not exist: {base}")
        for item in self.evidence_files:
            path = base / item.path
            if not path.is_file():
                raise ReleaseEvidenceError(f"missing evidence file: {item.path}")
            digest = sha256(path.read_bytes()).hexdigest()
            if digest != item.sha256.lower():
                raise ReleaseEvidenceError(f"evidence file sha256 mismatch: {item.path}")
            if path.stat().st_size != item.size_bytes:
                raise ReleaseEvidenceError(f"evidence file size mismatch: {item.path}")

    def sign(self, private_key: Ed25519PrivateKey, signed_at: datetime) -> "ReleaseEvidenceBundle":
        if signed_at.tzinfo is None:
            raise ReleaseEvidenceError("signed_at must be timezone-aware")
        public_bytes = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        key_id = sha256(public_bytes).hexdigest()
        context = EvidenceBundleSignature(
            algorithm="Ed25519",
            key_id=key_id,
            signature_b64=b64encode(b"\\x00" * 64).decode("ascii"),
            signed_at=signed_at,
        )
        signature = b64encode(private_key.sign(self.signing_bytes(context))).decode("ascii")
        return ReleaseEvidenceBundle(
            release_id=self.release_id,
            tag=self.tag,
            candidate_sha=self.candidate_sha,
            manifest_fingerprint=self.manifest_fingerprint,
            gate_fingerprint=self.gate_fingerprint,
            rehearsal_fingerprint=self.rehearsal_fingerprint,
            registry_id=self.registry_id,
            registry_version=self.registry_version,
            registry_fingerprint=self.registry_fingerprint,
            evidence_files=self.evidence_files,
            signature=EvidenceBundleSignature(
                algorithm=context.algorithm,
                key_id=context.key_id,
                signature_b64=signature,
                signed_at=context.signed_at,
            ),
        )

    def verify_signature(self, public_key: Ed25519PublicKey) -> None:
        if self.signature is None:
            raise ReleaseEvidenceError("evidence bundle is unsigned")
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        expected_key_id = sha256(public_bytes).hexdigest()
        if self.signature.key_id != expected_key_id:
            raise ReleaseEvidenceError("signature key_id does not match public key")
        try:
            public_key.verify(
                b64decode(self.signature.signature_b64, validate=True),
                self.signing_bytes(self.signature),
            )
        except Exception as exc:
            raise ReleaseEvidenceError("evidence bundle signature verification failed") from exc

    def assert_signed(self) -> None:
        if self.signature is None:
            raise ReleaseEvidenceError("evidence bundle is unsigned")

    @property
    def production_ready(self) -> bool:
        return False


def load_evidence_bundle(path: Path) -> ReleaseEvidenceBundle:
    payload = json.loads(path.read_text(encoding="utf-8"))
    signature_payload = payload.get("signature")
    signature = (
        EvidenceBundleSignature(
            algorithm=signature_payload["algorithm"],
            key_id=signature_payload["key_id"],
            signature_b64=signature_payload["signature_b64"],
            signed_at=datetime.fromisoformat(
                signature_payload["signed_at"].replace("Z", "+00:00")
            ),
        )
        if signature_payload
        else None
    )
    bundle = ReleaseEvidenceBundle(
        release_id=payload["release_id"],
        tag=payload["tag"],
        candidate_sha=payload["candidate_sha"],
        manifest_fingerprint=payload["manifest_fingerprint"],
        gate_fingerprint=payload["gate_fingerprint"],
        rehearsal_fingerprint=payload["rehearsal_fingerprint"],
        registry_id=payload["registry_id"],
        registry_version=int(payload["registry_version"]),
        registry_fingerprint=payload["registry_fingerprint"],
        evidence_files=tuple(
            EvidenceFile(**item) for item in payload["evidence_files"]
        ),
        signature=signature,
    )
    if payload.get("fingerprint") != bundle.fingerprint:
        raise ReleaseEvidenceError(
            "release evidence bundle fingerprint does not match its contents"
        )
    return bundle
