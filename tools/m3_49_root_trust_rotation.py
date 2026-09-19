from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path

from morva.runtime.root_trust_rotation import RootRotationCeremony, RootRotationError
from tools.m3_46_signed_trusted_registry import (
    load_private_key,
    load_public_key,
    load_signed_registry,
)


def _load_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise RootRotationError("rotation timestamps must be timezone-aware")
    return parsed


def _load_ceremony(path: Path) -> RootRotationCeremony:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return RootRotationCeremony(
        ceremony_id=payload["ceremony_id"],
        registry_id=payload["registry_id"],
        from_version=int(payload["from_version"]),
        to_version=int(payload["to_version"]),
        old_root_key_id=payload["old_root_key_id"],
        new_root_key_id=payload["new_root_key_id"],
        effective_at=_load_datetime(payload["effective_at"]),
        transition_kind=payload["transition_kind"],
        old_root_action=payload["old_root_action"],
        previous_registry_fingerprint=payload["previous_registry_fingerprint"],
        new_registry_fingerprint=payload["new_registry_fingerprint"],
        old_root_signature_b64=payload.get("old_root_signature_b64"),
        new_root_signature_b64=payload["new_root_signature_b64"],
        recovery_anchor_key_id=payload.get("recovery_anchor_key_id"),
        recovery_signature_b64=payload.get("recovery_signature_b64"),
    )


def write_ceremony(ceremony: RootRotationCeremony, path: Path) -> None:
    payload = {
        **ceremony._payload(),
        "old_root_signature_b64": ceremony.old_root_signature_b64,
        "new_root_signature_b64": ceremony.new_root_signature_b64,
        "recovery_signature_b64": ceremony.recovery_signature_b64,
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
    new_root_private_key_file: Path,
    ceremony_id: str,
    effective_at: datetime,
    transition_kind: str,
    old_root_action: str,
    old_root_private_key_file: Path | None = None,
    recovery_anchor_private_key_file: Path | None = None,
) -> RootRotationCeremony:
    previous = load_signed_registry(previous_file)
    current = load_signed_registry(current_file)
    new_root = load_private_key(new_root_private_key_file)
    old_root = (
        load_private_key(old_root_private_key_file)
        if old_root_private_key_file is not None
        else None
    )
    recovery_anchor = (
        load_private_key(recovery_anchor_private_key_file)
        if recovery_anchor_private_key_file is not None
        else None
    )
    return RootRotationCeremony.create(
        ceremony_id=ceremony_id,
        registry_id=previous.registry.registry_id,
        previous=previous,
        current=current,
        old_root_private_key=old_root,
        new_root_private_key=new_root,
        recovery_anchor_private_key=recovery_anchor,
        effective_at=effective_at,
        transition_kind=transition_kind,
        old_root_action=old_root_action,
    )


def verify_ceremony(
    ceremony_file: Path,
    previous_file: Path,
    current_file: Path,
    old_root_public_key_file: Path,
    new_root_public_key_file: Path,
    recovery_anchor_public_key_file: Path | None = None,
) -> RootRotationCeremony:
    ceremony = _load_ceremony(ceremony_file)
    previous = load_signed_registry(previous_file)
    current = load_signed_registry(current_file)
    old_root = load_public_key(old_root_public_key_file)
    new_root = load_public_key(new_root_public_key_file)
    recovery_anchor = (
        load_public_key(recovery_anchor_public_key_file)
        if recovery_anchor_public_key_file is not None
        else None
    )
    previous.verify_signature(old_root)
    current.verify_signature(new_root)
    ceremony.assert_source_bindings(
        previous,
        current,
        old_root,
        new_root,
        recovery_anchor,
    )

    payload = json.loads(ceremony_file.read_text(encoding="utf-8"))
    if payload.get("fingerprint") != ceremony.fingerprint:
        raise RootRotationError(
            "root rotation ceremony fingerprint does not match contents"
        )
    return ceremony


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create or verify a Morva root trust-anchor rotation ceremony"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build")
    build.add_argument("previous_registry", type=Path)
    build.add_argument("new_registry", type=Path)
    build.add_argument("--new-root-private-key", type=Path, required=True)
    build.add_argument("--old-root-private-key", type=Path)
    build.add_argument("--recovery-anchor-private-key", type=Path)
    build.add_argument("--ceremony-id", required=True)
    build.add_argument("--effective-at", required=True)
    build.add_argument(
        "--transition-kind",
        choices=("scheduled_rotation", "emergency_recovery"),
        required=True,
    )
    build.add_argument(
        "--old-root-action",
        choices=("retire", "revoke"),
        required=True,
    )
    build.add_argument("--output", type=Path, required=True)

    verify = subparsers.add_parser("verify")
    verify.add_argument("ceremony", type=Path)
    verify.add_argument("previous_registry", type=Path)
    verify.add_argument("new_registry", type=Path)
    verify.add_argument("--old-root-public-key", type=Path, required=True)
    verify.add_argument("--new-root-public-key", type=Path, required=True)
    verify.add_argument("--recovery-anchor-public-key", type=Path)

    args = parser.parse_args()
    if args.command == "build":
        ceremony = build_ceremony(
            args.previous_registry,
            args.new_registry,
            args.new_root_private_key,
            args.ceremony_id,
            _load_datetime(args.effective_at),
            args.transition_kind,
            args.old_root_action,
            args.old_root_private_key,
            args.recovery_anchor_private_key,
        )
        write_ceremony(ceremony, args.output)
        print("M3.49 root trust-anchor rotation ceremony built")
        print(f"ceremony_id={ceremony.ceremony_id}")
        print(f"from_version={ceremony.from_version}")
        print(f"to_version={ceremony.to_version}")
        print(f"old_root_key_id={ceremony.old_root_key_id}")
        print(f"new_root_key_id={ceremony.new_root_key_id}")
        print(f"transition_kind={ceremony.transition_kind}")
        print(f"effective_at={ceremony.effective_at.isoformat()}")
        print(f"fingerprint={ceremony.fingerprint}")
        return 0

    ceremony = verify_ceremony(
        args.ceremony,
        args.previous_registry,
        args.new_registry,
        args.old_root_public_key,
        args.new_root_public_key,
        args.recovery_anchor_public_key,
    )
    print("M3.49 root trust-anchor rotation ceremony verified")
    print(f"ceremony_id={ceremony.ceremony_id}")
    print(f"fingerprint={ceremony.fingerprint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
