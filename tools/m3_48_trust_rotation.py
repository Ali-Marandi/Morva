from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path

from morva.runtime.trust_rotation import (
    TrustRegistryRotationCeremony,
    TrustRotationError,
)
from tools.m3_46_signed_trusted_registry import load_public_key, load_signed_registry


def _load_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise TrustRotationError("rotation timestamps must be timezone-aware")
    return parsed


def _load_ceremony(path: Path) -> TrustRegistryRotationCeremony:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return TrustRegistryRotationCeremony(
        ceremony_id=payload["ceremony_id"],
        registry_id=payload["registry_id"],
        from_version=int(payload["from_version"]),
        to_version=int(payload["to_version"]),
        old_key_id=payload["old_key_id"],
        new_key_id=payload["new_key_id"],
        effective_at=_load_datetime(payload["effective_at"]),
        previous_registry_fingerprint=payload["previous_registry_fingerprint"],
        new_registry_fingerprint=payload["new_registry_fingerprint"],
        root_key_id=payload["root_key_id"],
    )


def write_ceremony(
    ceremony: TrustRegistryRotationCeremony,
    path: Path,
) -> None:
    payload = {
        "ceremony_id": ceremony.ceremony_id,
        "registry_id": ceremony.registry_id,
        "from_version": ceremony.from_version,
        "to_version": ceremony.to_version,
        "old_key_id": ceremony.old_key_id,
        "new_key_id": ceremony.new_key_id,
        "effective_at": ceremony.effective_at.isoformat(),
        "previous_registry_fingerprint": ceremony.previous_registry_fingerprint,
        "new_registry_fingerprint": ceremony.new_registry_fingerprint,
        "root_key_id": ceremony.root_key_id,
        "fingerprint": ceremony.fingerprint,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def build_ceremony(
    previous_file: Path,
    current_file: Path,
    root_public_key_file: Path,
    ceremony_id: str,
    old_key_id: str,
    new_key_id: str,
    effective_at: datetime,
) -> TrustRegistryRotationCeremony:
    previous = load_signed_registry(previous_file)
    current = load_signed_registry(current_file)
    root_public_key = load_public_key(root_public_key_file)
    previous.verify_signature(root_public_key)
    current.verify_signature(root_public_key)

    if previous.signature is None or current.signature is None:
        raise TrustRotationError("both source registries must be signed")
    if previous.signature.root_key_id != current.signature.root_key_id:
        raise TrustRotationError("source registries must use the same root key")

    ceremony = TrustRegistryRotationCeremony(
        ceremony_id=ceremony_id,
        registry_id=previous.registry.registry_id,
        from_version=previous.registry.version,
        to_version=current.registry.version,
        old_key_id=old_key_id,
        new_key_id=new_key_id,
        effective_at=effective_at,
        previous_registry_fingerprint=previous.registry.fingerprint,
        new_registry_fingerprint=current.registry.fingerprint,
        root_key_id=previous.signature.root_key_id,
    )
    ceremony.assert_signed_registries(previous, current)
    return ceremony


def verify_ceremony(
    ceremony_file: Path,
    previous_file: Path,
    current_file: Path,
    root_public_key_file: Path,
) -> TrustRegistryRotationCeremony:
    ceremony = _load_ceremony(ceremony_file)
    previous = load_signed_registry(previous_file)
    current = load_signed_registry(current_file)
    root_public_key = load_public_key(root_public_key_file)

    previous.verify_signature(root_public_key)
    current.verify_signature(root_public_key)
    ceremony.assert_signed_registries(previous, current)

    payload = json.loads(ceremony_file.read_text(encoding="utf-8"))
    if payload.get("fingerprint") != ceremony.fingerprint:
        raise TrustRotationError(
            "rotation ceremony fingerprint does not match contents"
        )
    return ceremony


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create or verify a Morva trusted-key rotation ceremony"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build")
    build.add_argument("previous_registry", type=Path)
    build.add_argument("new_registry", type=Path)
    build.add_argument("--registry-root-public-key", type=Path, required=True)
    build.add_argument("--ceremony-id", required=True)
    build.add_argument("--old-key-id", required=True)
    build.add_argument("--new-key-id", required=True)
    build.add_argument("--effective-at", required=True)
    build.add_argument("--output", type=Path, required=True)

    verify = subparsers.add_parser("verify")
    verify.add_argument("ceremony", type=Path)
    verify.add_argument("previous_registry", type=Path)
    verify.add_argument("new_registry", type=Path)
    verify.add_argument("--registry-root-public-key", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "build":
        ceremony = build_ceremony(
            args.previous_registry,
            args.new_registry,
            args.registry_root_public_key,
            args.ceremony_id,
            args.old_key_id,
            args.new_key_id,
            _load_datetime(args.effective_at),
        )
        write_ceremony(ceremony, args.output)
        print("M3.48 trusted-key rotation ceremony built")
        print(f"ceremony_id={ceremony.ceremony_id}")
        print(f"from_version={ceremony.from_version}")
        print(f"to_version={ceremony.to_version}")
        print(f"effective_at={ceremony.effective_at.isoformat()}")
        print(f"fingerprint={ceremony.fingerprint}")
        return 0

    ceremony = verify_ceremony(
        args.ceremony,
        args.previous_registry,
        args.new_registry,
        args.registry_root_public_key,
    )
    print("M3.48 trusted-key rotation ceremony verified")
    print(f"ceremony_id={ceremony.ceremony_id}")
    print(f"fingerprint={ceremony.fingerprint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
