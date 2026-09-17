from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from morva.runtime.release_manifest import ReleaseArtifact, ReleaseManifest


def _artifact(path: Path, root: Path) -> ReleaseArtifact:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return ReleaseArtifact(
        path=path.relative_to(root).as_posix(),
        sha256=digest.hexdigest(),
        size_bytes=path.stat().st_size,
    )


def build_manifest(
    artifact_dir: Path, release_id: str, tag: str, candidate_sha: str
) -> ReleaseManifest:
    root = artifact_dir.resolve()
    if not root.is_dir():
        raise ValueError(f"artifact directory does not exist: {root}")
    artifacts = tuple(
        _artifact(path, root)
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.name.startswith(".")
    )
    return ReleaseManifest(
        release_id=release_id,
        tag=tag,
        candidate_sha=candidate_sha,
        artifacts=artifacts,
    )


def load_manifest(path: Path) -> ReleaseManifest:
    payload = json.loads(path.read_text(encoding="utf-8"))
    manifest = ReleaseManifest(
        release_id=payload["release_id"],
        tag=payload["tag"],
        candidate_sha=payload["candidate_sha"],
        artifacts=tuple(ReleaseArtifact(**item) for item in payload["artifacts"]),
    )
    if payload.get("fingerprint") != manifest.fingerprint:
        raise ValueError("release manifest fingerprint does not match its contents")
    return manifest


def _write_manifest(manifest: ReleaseManifest, output: Path) -> None:
    payload = {
        "release_id": manifest.release_id,
        "tag": manifest.tag,
        "candidate_sha": manifest.candidate_sha,
        "artifacts": [
            {"path": item.path, "sha256": item.sha256, "size_bytes": item.size_bytes}
            for item in manifest.artifacts
        ],
        "fingerprint": manifest.fingerprint,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or verify a Morva release manifest")
    parser.add_argument("artifact_dir", type=Path)
    parser.add_argument("--release-id", required=False)
    parser.add_argument("--tag", required=False)
    parser.add_argument("--candidate-sha", default=os.getenv("GITHUB_SHA", ""))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", type=Path, help="Existing manifest JSON to verify")
    args = parser.parse_args()

    if args.verify:
        manifest = load_manifest(args.verify)
        manifest.assert_matches(args.candidate_sha)
        manifest.verify_files(args.artifact_dir)
        print(f"M3.41 release manifest verified: {args.verify}")
        print(f"fingerprint={manifest.fingerprint}")
        return 0

    if not args.release_id or not args.tag or not args.output or not args.candidate_sha:
        raise SystemExit("release-id, tag, candidate-sha and output are required for generation")
    manifest = build_manifest(args.artifact_dir, args.release_id, args.tag, args.candidate_sha)
    _write_manifest(manifest, args.output)
    print(f"M3.41 release manifest written: {args.output}")
    print(f"candidate_sha={manifest.candidate_sha}")
    print(f"artifacts={len(manifest.artifacts)}")
    print(f"fingerprint={manifest.fingerprint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
