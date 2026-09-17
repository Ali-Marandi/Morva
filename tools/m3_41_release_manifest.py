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


def build_manifest(artifact_dir: Path, release_id: str, tag: str, candidate_sha: str) -> ReleaseManifest:
    root = artifact_dir.resolve()
    if not root.is_dir():
        raise ValueError(f"artifact directory does not exist: {root}")
    artifacts = tuple(
        _artifact(path, root)
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.name.startswith(".")
    )
    manifest = ReleaseManifest(
        release_id=release_id,
        tag=tag,
        candidate_sha=candidate_sha,
        artifacts=artifacts,
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a Morva release artifact manifest")
    parser.add_argument("artifact_dir", type=Path)
    parser.add_argument("--release-id", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--candidate-sha", default=os.getenv("GITHUB_SHA", ""))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if not args.candidate_sha:
        raise SystemExit("candidate SHA is required")
    manifest = build_manifest(args.artifact_dir, args.release_id, args.tag, args.candidate_sha)
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
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"M3.41 release manifest written: {args.output}")
    print(f"candidate_sha={manifest.candidate_sha}")
    print(f"artifacts={len(manifest.artifacts)}")
    print(f"fingerprint={manifest.fingerprint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
