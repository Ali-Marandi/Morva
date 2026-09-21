from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from morva.runtime.release_evidence import EvidenceFile, ReleaseEvidenceBundle, load_evidence_bundle  # noqa: E402
from morva.runtime.release_rehearsal import ReleaseRehearsal  # noqa: E402
from tools.m3_40_release_gate import load_release_gate  # noqa: E402
from tools.m3_41_release_manifest import load_manifest  # noqa: E402
from tools.m3_46_signed_trusted_registry import load_signed_registry  # noqa: E402


def _hash_file(path: Path, root: Path) -> EvidenceFile:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return EvidenceFile(
        path.relative_to(root).as_posix(),
        digest.hexdigest(),
        path.stat().st_size,
    )


def _load_rehearsal_summary(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_registry_binding(
    bundle: ReleaseEvidenceBundle,
    registry_file: Path,
) -> None:
    registry = load_signed_registry(registry_file).registry
    if bundle.registry_id != registry.registry_id:
        raise ValueError("bundle registry_id does not match trusted registry")
    if bundle.registry_version != registry.version:
        raise ValueError("bundle registry_version does not match trusted registry")
    if bundle.registry_fingerprint != registry.fingerprint:
        raise ValueError("bundle registry_fingerprint does not match trusted registry")


def build_bundle(
    manifest_file: Path,
    gate_file: Path,
    rehearsal_file: Path,
    registry_file: Path,
    root: Path,
) -> ReleaseEvidenceBundle:
    manifest = load_manifest(manifest_file)
    gate = load_release_gate(gate_file)
    registry = load_signed_registry(registry_file)
    rehearsal = ReleaseRehearsal(manifest.candidate_sha, manifest.tag, manifest, gate)
    summary = _load_rehearsal_summary(rehearsal_file)

    expected = {
        "release_id": manifest.release_id,
        "tag": manifest.tag,
        "candidate_sha": manifest.candidate_sha,
        "manifest_fingerprint": manifest.fingerprint,
        "gate_fingerprint": gate.fingerprint,
        "rehearsal_fingerprint": rehearsal.fingerprint,
    }
    for name, value in expected.items():
        if summary.get(name) != value:
            raise ValueError(f"rehearsal summary {name} does not match release contracts")

    files = tuple(
        _hash_file(path.resolve(), root.resolve())
        for path in (manifest_file, gate_file, rehearsal_file, registry_file)
    )
    bundle = ReleaseEvidenceBundle(
        release_id=rehearsal.manifest.release_id,
        tag=rehearsal.tag,
        candidate_sha=rehearsal.candidate_sha,
        manifest_fingerprint=rehearsal.manifest.fingerprint,
        gate_fingerprint=rehearsal.gate.fingerprint,
        rehearsal_fingerprint=rehearsal.fingerprint,
        registry_id=registry.registry.registry_id,
        registry_version=registry.registry.version,
        registry_fingerprint=registry.registry.fingerprint,
        evidence_files=files,
    )
    bundle.verify_files(root)
    return bundle


def _write_bundle(bundle: ReleaseEvidenceBundle, output: Path) -> None:
    signature = None
    if bundle.signature is not None:
        signature = {
            "algorithm": bundle.signature.algorithm,
            "key_id": bundle.signature.key_id,
            "signature_b64": bundle.signature.signature_b64,
            "signed_at": bundle.signature.signed_at.isoformat(),
        }
    payload = {
        "release_id": bundle.release_id,
        "tag": bundle.tag,
        "candidate_sha": bundle.candidate_sha,
        "manifest_fingerprint": bundle.manifest_fingerprint,
        "gate_fingerprint": bundle.gate_fingerprint,
        "rehearsal_fingerprint": bundle.rehearsal_fingerprint,
        "registry_id": bundle.registry_id,
        "registry_version": bundle.registry_version,
        "registry_fingerprint": bundle.registry_fingerprint,
        "evidence_files": [
            {
                "path": item.path,
                "sha256": item.sha256,
                "size_bytes": item.size_bytes,
            }
            for item in bundle.evidence_files
        ],
        "fingerprint": bundle.fingerprint,
        "signature": signature,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _load_private_key(path: Path) -> Ed25519PrivateKey:
    key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise TypeError("private key must be Ed25519")
    return key


def _load_public_key(path: Path) -> Ed25519PublicKey:
    key = serialization.load_pem_public_key(path.read_bytes())
    if not isinstance(key, Ed25519PublicKey):
        raise TypeError("public key must be Ed25519")
    return key


def main() -> int:
    parser = argparse.ArgumentParser(description="Build, sign or verify a Morva evidence bundle")
    parser.add_argument("bundle_file", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--gate", type=Path)
    parser.add_argument("--rehearsal", type=Path)
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--private-key", type=Path)
    parser.add_argument("--public-key", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--expected-sha", default=os.getenv("GITHUB_SHA", ""))
    args = parser.parse_args()

    if args.verify:
        if not args.public_key or not args.registry:
            raise SystemExit("--public-key and --registry are required with --verify")
        bundle = load_evidence_bundle(args.bundle_file)
        bundle.verify_files(args.root)
        bundle.verify_signature(_load_public_key(args.public_key))
        _assert_registry_binding(bundle, args.registry)
        if args.expected_sha and bundle.candidate_sha.lower() != args.expected_sha.lower():
            raise SystemExit("candidate_sha does not match the expected release commit")
        print("M3.43 signed evidence bundle verified")
        print(f"release_id={bundle.release_id}")
        print(f"candidate_sha={bundle.candidate_sha}")
        print(f"registry={bundle.registry_id}@{bundle.registry_version}")
        print(f"bundle_fingerprint={bundle.fingerprint}")
        print(f"key_id={bundle.signature.key_id}")
        return 0

    if not (
        args.manifest
        and args.gate
        and args.rehearsal
        and args.registry
        and args.private_key
        and args.output
    ):
        raise SystemExit(
            "--manifest, --gate, --rehearsal, --registry, --private-key and --output are required"
        )
    bundle = build_bundle(
        args.manifest,
        args.gate,
        args.rehearsal,
        args.registry,
        args.root,
    )
    if args.expected_sha and bundle.candidate_sha.lower() != args.expected_sha.lower():
        raise SystemExit("candidate_sha does not match the expected release commit")
    signed = bundle.sign(_load_private_key(args.private_key), datetime.now(timezone.utc))
    _write_bundle(signed, args.output)
    print("M3.43 signed evidence bundle written")
    print(f"release_id={signed.release_id}")
    print(f"candidate_sha={signed.candidate_sha}")
    print(f"registry={signed.registry_id}@{signed.registry_version}")
    print(f"bundle_fingerprint={signed.fingerprint}")
    print(f"key_id={signed.signature.key_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
