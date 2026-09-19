from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from morva.runtime.release_publication_gate import (
    ReleasePublicationGate,
    ReleasePublicationGateError,
)
from tools.m3_52_release_trust_artifact import verify_artifact


def _load_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ReleasePublicationGateError(
            "verified_at must be timezone-aware"
        )
    return parsed


def _load_gate(path: Path) -> ReleasePublicationGate:
    payload = json.loads(path.read_text(encoding="utf-8"))
    gate = ReleasePublicationGate(
        gate_version=int(payload.get("gate_version", 0)),
        repository=payload["repository"],
        release_id=payload["release_id"],
        tag=payload["tag"],
        candidate_sha=payload["candidate_sha"],
        artifact_id=payload["artifact_id"],
        artifact_fingerprint=payload["artifact_fingerprint"],
        archive_sha256=payload["archive_sha256"],
        archive_size_bytes=int(payload["archive_size_bytes"]),
        verified_at=_load_datetime(payload["verified_at"]),
        publication_target=payload.get("publication_target", ""),
    )
    if payload.get("release_ref") != gate.release_ref:
        raise ReleasePublicationGateError(
            "release_ref does not match tag"
        )
    if payload.get("fingerprint") != gate.fingerprint:
        raise ReleasePublicationGateError(
            "publication gate fingerprint mismatch"
        )
    return gate


def _write_gate(gate: ReleasePublicationGate, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(gate.to_payload(), ensure_ascii=True, sort_keys=True, indent=2)
        + "\n",
        encoding="utf-8",
    )


def build_gate(
    *,
    repository: str,
    archive_path: Path,
    artifact_metadata: Path,
    output_gate: Path,
    expected_sha: str,
    expected_tag: str,
    verified_at: datetime,
) -> ReleasePublicationGate:
    if output_gate.exists():
        raise ReleasePublicationGateError("publication gate is write-once")
    artifact = verify_artifact(
        archive_path=archive_path,
        metadata_file=artifact_metadata,
        expected_sha=expected_sha,
    )
    if artifact.tag != expected_tag:
        raise ReleasePublicationGateError(
            "artifact tag does not match expected publication tag"
        )
    gate = ReleasePublicationGate(
        gate_version=1,
        repository=repository,
        release_id=artifact.release_id,
        tag=artifact.tag,
        candidate_sha=artifact.candidate_sha,
        artifact_id=artifact.artifact_id,
        artifact_fingerprint=artifact.fingerprint,
        archive_sha256=artifact.archive_sha256,
        archive_size_bytes=artifact.archive_size_bytes,
        verified_at=verified_at,
    )
    _write_gate(gate, output_gate)
    return gate


def verify_gate(
    *,
    gate_file: Path,
    archive_path: Path,
    artifact_metadata: Path,
    expected_repository: str,
    expected_tag: str,
    expected_sha: str = "",
) -> ReleasePublicationGate:
    gate = _load_gate(gate_file)
    if gate.repository != expected_repository:
        raise ReleasePublicationGateError(
            "publication repository mismatch"
        )
    if gate.tag != expected_tag:
        raise ReleasePublicationGateError(
            "publication tag mismatch"
        )
    artifact = verify_artifact(
        archive_path=archive_path,
        metadata_file=artifact_metadata,
        expected_sha=expected_sha or gate.candidate_sha,
    )
    gate.assert_matches_artifact(artifact)
    return gate


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build or verify the Morva M3.53 release publication gate"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build")
    build.add_argument("repository")
    build.add_argument("archive", type=Path)
    build.add_argument("metadata", type=Path)
    build.add_argument("output", type=Path)
    build.add_argument("--expected-sha", required=True)
    build.add_argument("--expected-tag", required=True)
    build.add_argument("--verified-at", default="")

    verify = subparsers.add_parser("verify")
    verify.add_argument("gate", type=Path)
    verify.add_argument("archive", type=Path)
    verify.add_argument("metadata", type=Path)
    verify.add_argument("--repository", required=True)
    verify.add_argument("--tag", required=True)
    verify.add_argument("--expected-sha", default="")

    args = parser.parse_args()
    if args.command == "build":
        result = build_gate(
            repository=args.repository,
            archive_path=args.archive,
            artifact_metadata=args.metadata,
            output_gate=args.output,
            expected_sha=args.expected_sha,
            expected_tag=args.expected_tag,
            verified_at=(
                _load_datetime(args.verified_at)
                if args.verified_at
                else datetime.now(timezone.utc)
            ),
        )
        print("M3.53 release publication gate built")
        print(f"release_id={result.release_id}")
        print(f"release_ref={result.release_ref}")
        print(f"candidate_sha={result.candidate_sha}")
        print(f"artifact_id={result.artifact_id}")
        print(f"archive_sha256={result.archive_sha256}")
        print(f"gate_fingerprint={result.fingerprint}")
        return 0

    result = verify_gate(
        gate_file=args.gate,
        archive_path=args.archive,
        artifact_metadata=args.metadata,
        expected_repository=args.repository,
        expected_tag=args.tag,
        expected_sha=args.expected_sha,
    )
    print("M3.53 release publication gate verified")
    print(f"release_ref={result.release_ref}")
    print(f"candidate_sha={result.candidate_sha}")
    print(f"artifact_id={result.artifact_id}")
    print(f"gate_fingerprint={result.fingerprint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())