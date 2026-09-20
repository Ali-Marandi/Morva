from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from morva.runtime.release_rehearsal import ReleaseRehearsal
from tools.m3_40_release_gate import load_release_gate
from tools.m3_41_release_manifest import load_manifest


def _write_summary(rehearsal: ReleaseRehearsal, output: Path) -> None:
    payload = {
        "release_id": rehearsal.manifest.release_id,
        "tag": rehearsal.tag,
        "candidate_sha": rehearsal.candidate_sha,
        "manifest_fingerprint": rehearsal.manifest.fingerprint,
        "gate_fingerprint": rehearsal.gate.fingerprint,
        "rehearsal_fingerprint": rehearsal.fingerprint,
        "aggregate_gate_ready": rehearsal.release_ready,
        "blockers": list(rehearsal.blockers),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compose and verify a Morva release manifest with its aggregate gate"
    )
    parser.add_argument("manifest_file", type=Path)
    parser.add_argument("gate_file", type=Path)
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        help="Built-artifact directory to re-hash against the manifest",
    )
    parser.add_argument(
        "--expected-sha",
        default=os.getenv("GITHUB_SHA", ""),
        help="Expected Git commit SHA; defaults to GITHUB_SHA when present.",
    )
    parser.add_argument("--output", type=Path, help="Write rehearsal evidence summary JSON")
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help="Fail unless the aggregate release gate is fully production-ready",
    )
    args = parser.parse_args()

    manifest = load_manifest(args.manifest_file)
    gate = load_release_gate(args.gate_file)
    rehearsal = ReleaseRehearsal(manifest.candidate_sha, manifest.tag, manifest, gate)

    if args.expected_sha:
        rehearsal.manifest.assert_matches(args.expected_sha)

    rehearsal.assert_consistent(args.artifact_dir)
    if args.require_ready:
        rehearsal.assert_release_ready(args.artifact_dir)

    if args.output:
        _write_summary(rehearsal, args.output)

    print("M3.42 release rehearsal consistency verified")
    print(f"release_id={rehearsal.manifest.release_id}")
    print(f"tag={rehearsal.tag}")
    print(f"candidate_sha={rehearsal.candidate_sha}")
    print(f"manifest_fingerprint={rehearsal.manifest.fingerprint}")
    print(f"gate_fingerprint={rehearsal.gate.fingerprint}")
    print(f"rehearsal_fingerprint={rehearsal.fingerprint}")
    print(f"aggregate_gate_ready={rehearsal.release_ready}")
    if rehearsal.blockers:
        print("blockers=" + " | ".join(rehearsal.blockers))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
