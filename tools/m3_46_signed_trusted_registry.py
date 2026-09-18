from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from morva.runtime.signed_trusted_key_registry import (
    SignedTrustedKeyRegistry,
    SignedTrustedRegistryError,
    TrustedRegistrySignature,
)
from tools.m3_45_trusted_key_registry import load_registry


def load_signed_registry(path: Path) -> SignedTrustedKeyRegistry:
    payload = json.loads(path.read_text(encoding="utf-8"))
    signature_payload = payload.get("signature")
    signature = (
        TrustedRegistrySignature(
            algorithm=signature_payload["algorithm"],
            root_key_id=signature_payload["root_key_id"],
            signature_b64=signature_payload["signature_b64"],
            signed_at=datetime.fromisoformat(
                signature_payload["signed_at"].replace("Z", "+00:00")
            ),
        )
        if signature_payload
        else None
    )
    registry_payload = payload["registry"]
    registry_path = path.with_name(f".{path.name}.registry.json")
    registry_path.write_text(
        json.dumps(registry_payload, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    try:
        registry = load_registry(registry_path)
    finally:
        registry_path.unlink(missing_ok=True)
    envelope = SignedTrustedKeyRegistry(registry=registry, signature=signature)
    if payload.get("fingerprint") != envelope.fingerprint:
        raise SignedTrustedRegistryError(
            "signed trusted-key registry fingerprint does not match its contents"
        )
    return envelope


def write_signed_registry(envelope: SignedTrustedKeyRegistry, path: Path) -> None:
    registry = envelope.registry
    signature = envelope.signature
    payload = {
        "registry": {
            "registry_id": registry.registry_id,
            "version": registry.version,
            "keys": [
                {
                    "key_id": item.key_id,
                    "public_key_sha256": item.public_key_sha256,
                    "status": item.status,
                    "valid_from": item.valid_from.isoformat(),
                    "valid_until": (
                        item.valid_until.isoformat() if item.valid_until else None
                    ),
                    "replacement_key_id": item.replacement_key_id,
                }
                for item in registry.keys
            ],
            "fingerprint": registry.fingerprint,
        },
        "signature": (
            {
                "algorithm": signature.algorithm,
                "root_key_id": signature.root_key_id,
                "signature_b64": signature.signature_b64,
                "signed_at": signature.signed_at.isoformat(),
            }
            if signature
            else None
        ),
        "fingerprint": envelope.fingerprint,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def load_public_key(path: Path) -> Ed25519PublicKey:
    key = serialization.load_pem_public_key(path.read_bytes())
    if not isinstance(key, Ed25519PublicKey):
        raise TypeError("public key must be Ed25519")
    return key


def load_private_key(path: Path) -> Ed25519PrivateKey:
    key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise TypeError("private key must be Ed25519")
    return key
