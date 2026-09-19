from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .release_evidence import ReleaseEvidenceBundle
from .root_trust_rotation import RootRotationCeremony
from .signed_trusted_key_registry import SignedTrustedKeyRegistry
from .trust_rotation import TrustRegistryRotationCeremony


class TrustChainVerificationError(ValueError):
    """Raised when the complete release trust chain is invalid."""


@dataclass(frozen=True, slots=True)
class TrustChainVerification:
    release_id: str
    tag: str
    candidate_sha: str
    previous_registry_fingerprint: str
    intermediate_registry_fingerprint: str
    current_registry_fingerprint: str
    signing_key_rotation_fingerprint: str
    root_rotation_fingerprint: str
    bundle_fingerprint: str

    @property
    def fingerprint(self) -> str:
        payload = {
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha.lower(),
            "previous_registry_fingerprint": self.previous_registry_fingerprint.lower(),
            "intermediate_registry_fingerprint": (
                self.intermediate_registry_fingerprint.lower()
            ),
            "current_registry_fingerprint": self.current_registry_fingerprint.lower(),
            "signing_key_rotation_fingerprint": (
                self.signing_key_rotation_fingerprint.lower()
            ),
            "root_rotation_fingerprint": self.root_rotation_fingerprint.lower(),
            "bundle_fingerprint": self.bundle_fingerprint.lower(),
        }
        canonical = json.dumps(
            payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        )
        return sha256(canonical.encode("utf-8")).hexdigest()


def verify_trust_chain(
    *,
    previous: SignedTrustedKeyRegistry,
    intermediate: SignedTrustedKeyRegistry,
    current: SignedTrustedKeyRegistry,
    signing_key_rotation: TrustRegistryRotationCeremony,
    root_rotation: RootRotationCeremony,
    release_bundle: ReleaseEvidenceBundle,
    release_signing_public_key: Ed25519PublicKey,
    old_root_public_key: Ed25519PublicKey,
    new_root_public_key: Ed25519PublicKey,
    verified_at: datetime,
) -> TrustChainVerification:
    if verified_at.tzinfo is None:
        raise TrustChainVerificationError("verified_at must be timezone-aware")
    if previous.signature is None or intermediate.signature is None or current.signature is None:
        raise TrustChainVerificationError("all registry versions must be signed")
    if not release_bundle.release_id.strip() or not release_bundle.tag.strip():
        raise TrustChainVerificationError("release bundle identity is required")
    if release_bundle.registry_id != current.registry.registry_id:
        raise TrustChainVerificationError("release bundle is not bound to current registry ID")
    if release_bundle.registry_version != current.registry.version:
        raise TrustChainVerificationError("release bundle is not bound to current registry version")
    if release_bundle.registry_fingerprint != current.registry.fingerprint:
        raise TrustChainVerificationError(
            "release bundle is not bound to current registry fingerprint"
        )

    signing_key_rotation.assert_signed_registries(previous, intermediate)
    root_rotation.assert_source_bindings(
        intermediate,
        current,
        old_root_public_key,
        new_root_public_key,
    )

    if signing_key_rotation.root_key_id != root_rotation.old_root_key_id:
        raise TrustChainVerificationError(
            "signing-key rotation root does not match root-rotation source root"
        )
    if intermediate.signature.root_key_id != root_rotation.old_root_key_id:
        raise TrustChainVerificationError(
            "intermediate registry root does not match root-rotation source root"
        )
    if current.signature.root_key_id != root_rotation.new_root_key_id:
        raise TrustChainVerificationError(
            "current registry root does not match root-rotation target root"
        )

    if release_bundle.signature is None:
        raise TrustChainVerificationError("release bundle must be signed")
    expected_signing_key_id = current.registry.key_id_for(release_signing_public_key)
    if release_bundle.signature.key_id != expected_signing_key_id:
        raise TrustChainVerificationError(
            "release bundle signer is not the declared release-signing key"
        )
    try:
        current.registry.assert_trusted(
            expected_signing_key_id,
            release_signing_public_key,
            verified_at,
        )
    except Exception as exc:
        raise TrustChainVerificationError(
            "current registry does not trust release-signing key"
        ) from exc

    release_bundle.verify_signature(release_signing_public_key)

    return TrustChainVerification(
        release_id=release_bundle.release_id,
        tag=release_bundle.tag,
        candidate_sha=release_bundle.candidate_sha.lower(),
        previous_registry_fingerprint=previous.registry.fingerprint,
        intermediate_registry_fingerprint=intermediate.registry.fingerprint,
        current_registry_fingerprint=current.registry.fingerprint,
        signing_key_rotation_fingerprint=signing_key_rotation.fingerprint,
        root_rotation_fingerprint=root_rotation.fingerprint,
        bundle_fingerprint=release_bundle.fingerprint,
    )
