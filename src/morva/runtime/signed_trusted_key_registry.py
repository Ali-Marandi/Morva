from __future__ import annotations

from base64 import b64decode, b64encode
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .trusted_key_registry import TrustedKeyRegistry


class SignedTrustedRegistryError(ValueError):
    """Raised when a signed trusted-key registry is invalid or unverifiable."""


@dataclass(frozen=True, slots=True)
class TrustedRegistrySignature:
    algorithm: str
    root_key_id: str
    signature_b64: str
    signed_at: datetime

    def __post_init__(self) -> None:
        if self.algorithm != "Ed25519":
            raise SignedTrustedRegistryError("unsupported registry signature algorithm")
        if not self.root_key_id.strip():
            raise SignedTrustedRegistryError("root_key_id is required")
        if not self.signature_b64.strip():
            raise SignedTrustedRegistryError("registry signature is required")
        if self.signed_at.tzinfo is None:
            raise SignedTrustedRegistryError("signed_at must be timezone-aware")
        try:
            raw = b64decode(self.signature_b64, validate=True)
        except Exception as exc:
            raise SignedTrustedRegistryError("registry signature is not valid base64") from exc
        if len(raw) != 64:
            raise SignedTrustedRegistryError("Ed25519 registry signature must be 64 bytes")


@dataclass(frozen=True, slots=True)
class SignedTrustedKeyRegistry:
    registry: TrustedKeyRegistry
    signature: TrustedRegistrySignature | None = None

    @property
    def fingerprint(self) -> str:
        payload = {
            "registry_fingerprint": self.registry.fingerprint,
            "signature": (
                {
                    "algorithm": self.signature.algorithm,
                    "root_key_id": self.signature.root_key_id,
                    "signed_at": self.signature.signed_at.isoformat(),
                }
                if self.signature
                else None
            ),
        }
        canonical = json.dumps(
            payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        )
        return sha256(canonical.encode("utf-8")).hexdigest()

    def signing_bytes(self, context: TrustedRegistrySignature) -> bytes:
        payload = {
            "registry_id": self.registry.registry_id,
            "version": self.registry.version,
            "registry_fingerprint": self.registry.fingerprint,
            "root_key_id": context.root_key_id,
            "signed_at": context.signed_at.isoformat(),
            "algorithm": context.algorithm,
        }
        canonical = json.dumps(
            payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        )
        return canonical.encode("utf-8")

    @staticmethod
    def root_key_id_for(public_key: Ed25519PublicKey) -> str:
        raw = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return sha256(raw).hexdigest()

    def sign(
        self, private_key: Ed25519PrivateKey, signed_at: datetime
    ) -> "SignedTrustedKeyRegistry":
        if signed_at.tzinfo is None:
            raise SignedTrustedRegistryError("signed_at must be timezone-aware")
        key_id = self.root_key_id_for(private_key.public_key())
        context = TrustedRegistrySignature(
            algorithm="Ed25519",
            root_key_id=key_id,
            signature_b64=b64encode(b"\x00" * 64).decode("ascii"),
            signed_at=signed_at,
        )
        signature = b64encode(private_key.sign(self.signing_bytes(context))).decode("ascii")
        return SignedTrustedKeyRegistry(
            registry=self.registry,
            signature=TrustedRegistrySignature(
                algorithm=context.algorithm,
                root_key_id=context.root_key_id,
                signature_b64=signature,
                signed_at=context.signed_at,
            ),
        )

    def verify_signature(self, public_key: Ed25519PublicKey) -> None:
        if self.signature is None:
            raise SignedTrustedRegistryError("trusted key registry is unsigned")
        expected_id = self.root_key_id_for(public_key)
        if self.signature.root_key_id != expected_id:
            raise SignedTrustedRegistryError("root public key does not match registry signature")
        try:
            public_key.verify(
                b64decode(self.signature.signature_b64, validate=True),
                self.signing_bytes(self.signature),
            )
        except Exception as exc:
            raise SignedTrustedRegistryError(
                "trusted key registry signature verification failed"
            ) from exc

    def assert_signed(self) -> None:
        if self.signature is None:
            raise SignedTrustedRegistryError("trusted key registry is unsigned")
