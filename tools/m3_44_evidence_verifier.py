from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from morva.runtime.release_evidence import (
    ReleaseEvidenceBundle,
    ReleaseEvidenceError,
    load_evidence_bundle,
)
from morva.runtime.release_rehearsal import ReleaseRehearsal
from tools.m3_40_release_gate import load_release_gate
from tools.m3_41_release_manifest import load_manifest


def _load_rehearsal_summary(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_source_binding(
    bundle: ReleaseEvidenceBundle,
    manifest_file: Path,
    gate_file: Path,
    rehearsal_file: Path,
    root: Path,
) -> ReleaseRehearsal:
    manifest = load_manifest(manifest_file)
    gate = load_release_gate(gate_file)
    rehearsal = ReleaseRehearsal(manifest.candidate_sha, manifest.tag, manifest, gate)
    summary = _load_rehearsal_summary(rehearsal_file)
    expected = {
        "release_id": rehearsal.manifest.release_id,
        "tag": rehearsal.tag,
        "candidate_sha": rehearsal.candidate_sha,
        "manifest_fingerprint": rehearsal.manifest.fingerprint,
        "gate_fingerprint": rehearsal.gate.fingerprint,
        "rehearsal_fingerprint": rehearsal.fingerprint,
    }
    for name, value in expected.items():
        if summary.get(name) != value:
            raise ReleaseEvidenceError(
                f"rehearsal summary {name} does not match release contracts"
            )
    bundle.assert_matches_rehearsal(rehearsal)
    bundle.verify_files(root)
    source_paths = (manifest_file, gate_file, rehearsal_file)
    indexed = {item.path: item for item in bundle.evidence_files}
    for source in source_paths:
        relative = source.resolve().relative_to(root.resolve()).as_posix()
        item = indexed.get(relative)
        if item is None:
            raise ReleaseEvidenceError(
                f"source file is not listed in evidence bundle: {relative}"
            )
    return rehearsal


def _load_public_key(path: Path) -> Ed25519PublicKey:
    key = serialization.load_pem_public_key(path.read_bytes())
    if not isinstance(key, Ed25519PublicKey):
        raise TypeError("public key must be Ed25519")
    return key


def verify_bundle(
    bundle_file: Path,
    manifest_file: Path,
    gate_file: Path,
    rehearsal_file: Path,
    public_key_file: Path,
    root: Path,
    expected_sha: str = "",
) -> ReleaseEvidenceBundle:
    bundle = load_evidence_bundle(bundle_file)
    bundle.verify_signature(_load_public_key(public_key_file))
    rehearsal = _assert_source_binding(
        bundle, manifest_file, gate_file, rehearsal_file, root
    )
    if expected_sha and bundle.candidate_sha.lower() != expected_sha.lower():
        raise ReleaseEvidenceError("bundle candidate_sha does not match expected release commit")
    if not rehearsal.release_ready:
        return bundle
    raise ReleaseEvidenceError(
        "independent verifier refuses a rehearsal bundle that claims production readiness"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Independently verify a Morva signed release evidence bundle"
    )
    parser.add_argument("bundle_file", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--gate", type=Path, required=True)
    parser.add_argument("--rehearsal", type=Path, required=True)
    parser.add_argument("--public-key", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--expected-sha",
        default=os.getenv("GITHUB_SHA", ""),
        help="Expected Git commit SHA; defaults to GITHUB_SHA when present.",
    )
    args = parser.parse_args()

    bundle = verify_bundle(
        args.bundle_file,
        args.manifest,
        args.gate,
        args.rehearsal,
        args.public_key,
        args.root,
        args.expected_sha,
    )
    print("M3.44 independent evidence verifier passed")
    print(f"release_id={bundle.release_id}")
    print(f"tag={bundle.tag}")
    print(f"candidate_sha={bundle.candidate_sha}")
    print(f"bundle_fingerprint={bundle.fingerprint}")
    print(f"key_id={bundle.signature.key_id}")
    print("aggregate_gate_ready=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
