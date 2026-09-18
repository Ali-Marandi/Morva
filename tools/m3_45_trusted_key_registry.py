from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from morva.runtime.trusted_key_registry import TrustedKeyRegistry, TrustedKeyRegistryError, TrustedSigningKey


def load_registry(path: Path) -> TrustedKeyRegistry:
    payload = json.loads(path.read_text(encoding="utf-8"))
    keys = tuple(
        TrustedSigningKey(
            key_id=item["key_id"],
            public_key_sha256=item["public_key_sha256"],
            status=item["status"],
            valid_from=datetime.fromisoformat(item["valid_from"].replace("Z", "+00:00")),
            valid_until=(
                datetime.fromisoformat(item["valid_until"].replace("Z", "+00:00"))
                if item.get("valid_until")
                else None
            ),
            replacement_key_id=item.get("replacement_key_id"),
        )
        for item in payload["keys"]
    )
    registry = TrustedKeyRegistry(
        registry_id=payload["registry_id"],
        version=int(payload["version"]),
        keys=keys,
    )
    if payload.get("fingerprint") != registry.fingerprint:
        raise TrustedKeyRegistryError(
            "trusted key registry fingerprint does not match its contents"
        )
    return registry


def load_public_key(path: Path) -> Ed25519PublicKey:
    key = serialization.load_pem_public_key(path.read_bytes())
    if not isinstance(key, Ed25519PublicKey):
        raise TypeError("public key must be Ed25519")
    return key
