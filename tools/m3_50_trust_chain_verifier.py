from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from morva.runtime.root_trust_rotation import RootRotationCeremony
from morva.runtime.trust_chain import (
    TrustChainVerification,
    TrustChainVerificationError,
    verify_trust_chain,
)
from morva.runtime.trust_rotation import TrustRegistryRotationCeremony
from tools.m3_44_evidence_verifier import verify_bundle
from tools.m3_45_trusted_key_registry import load_public_key
from tools.m3_46_signed_trusted_registry import load_signed_registry


def _load_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise TrustChainVerificationError("verification timestamps must be timezone-aware")
    return parsed


def _load_signing_rotation(path: Path) -> TrustRegistryRotationCeremony:
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


def _load_root_rotation(path: Path) -> RootRotationCeremony:
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


def write_verification(result: TrustChainVerification, path: Path) -> None:
    payload = {
        "release_id": result.release_id,
        "tag": result.tag,
        "candidate_sha": result.candidate_sha,
        "previous_registry_fingerprint": result.previous_registry_fingerprint,
        "intermediate_registry_fingerprint": result.intermediate_registry_fingerprint,
        "current_registry_fingerprint": result.current_registry_fingerprint,
        "signing_key_rotation_fingerprint": result.signing_key_rotation_fingerprint,
        "root_rotation_fingerprint": result.root_rotation_fingerprint,
        "bundle_fingerprint": result.bundle_fingerprint,
        "fingerprint": result.fingerprint,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def verify_chain(
    *,
    bundle_file: Path,
    manifest_file: Path,
    gate_file: Path,
    rehearsal_file: Path,
    public_key_file: Path,
    previous_registry_file: Path,
    intermediate_registry_file: Path,
    current_registry_file: Path,
    signing_key_rotation_file: Path,
    root_rotation_file: Path,
    old_root_public_key_file: Path,
    new_root_public_key_file: Path,
    root: Path,
    expected_sha: str,
    verified_at: datetime,
) -> TrustChainVerification:
    previous = load_signed_registry(previous_registry_file)
    intermediate = load_signed_registry(intermediate_registry_file)
    current = load_signed_registry(current_registry_file)
    signing_rotation = _load_signing_rotation(signing_key_rotation_file)
    root_rotation = _load_root_rotation(root_rotation_file)
    old_root = load_public_key(old_root_public_key_file)
    new_root = load_public_key(new_root_public_key_file)

    bundle = verify_bundle(
        bundle_file=bundle_file,
        manifest_file=manifest_file,
        gate_file=gate_file,
        rehearsal_file=rehearsal_file,
        public_key_file=public_key_file,
        registry_file=current_registry_file,
        root=root,
        expected_sha=expected_sha,
        verified_at=verified_at,
        registry_root_public_key=new_root_public_key_file,
    )
    result = verify_trust_chain(
        previous=previous,
        intermediate=intermediate,
        current=current,
        signing_key_rotation=signing_rotation,
        root_rotation=root_rotation,
        release_bundle=bundle,
        release_signing_public_key=load_public_key(public_key_file),
        old_root_public_key=old_root,
        new_root_public_key=new_root,
        verified_at=verified_at,
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Independently verify the complete Morva release trust chain"
    )
    parser.add_argument("bundle_file", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--gate", type=Path, required=True)
    parser.add_argument("--rehearsal", type=Path, required=True)
    parser.add_argument("--public-key", type=Path, required=True)
    parser.add_argument("--previous-registry", type=Path, required=True)
    parser.add_argument("--intermediate-registry", type=Path, required=True)
    parser.add_argument("--current-registry", type=Path, required=True)
    parser.add_argument("--signing-key-rotation", type=Path, required=True)
    parser.add_argument("--root-rotation", type=Path, required=True)
    parser.add_argument("--old-root-public-key", type=Path, required=True)
    parser.add_argument("--new-root-public-key", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--expected-sha", default="")
    parser.add_argument("--verified-at", default="")
    parser.add_argument("--output", type=Path)

    args = parser.parse_args()
    verified_at = (
        _load_datetime(args.verified_at)
        if args.verified_at
        else datetime.now(timezone.utc)
    )
    result = verify_chain(
        bundle_file=args.bundle_file,
        manifest_file=args.manifest,
        gate_file=args.gate,
        rehearsal_file=args.rehearsal,
        public_key_file=args.public_key,
        previous_registry_file=args.previous_registry,
        intermediate_registry_file=args.intermediate_registry,
        current_registry_file=args.current_registry,
        signing_key_rotation_file=args.signing_key_rotation,
        root_rotation_file=args.root_rotation,
        old_root_public_key_file=args.old_root_public_key,
        new_root_public_key_file=args.new_root_public_key,
        root=args.root,
        expected_sha=args.expected_sha,
        verified_at=verified_at,
    )
    if args.output:
        write_verification(result, args.output)
    print("M3.50 independent trust-chain verification passed")
    print(f"release_id={result.release_id}")
    print(f"tag={result.tag}")
    print(f"candidate_sha={result.candidate_sha}")
    print(f"chain_fingerprint={result.fingerprint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
