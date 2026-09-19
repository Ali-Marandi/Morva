from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import shutil
import tempfile

from morva.runtime.release_trust_artifact import (
    ReleaseTrustArtifact,
    ReleaseTrustArtifactError,
    create_deterministic_archive,
    verify_archive_member_safety,
)
from tools.m3_51_release_trust_pack import verify_pack


def _hash_file(path: Path) -> tuple[str, int]:
    data = path.read_bytes()
    return sha256(data).hexdigest(), len(data)


def _load_metadata(path: Path) -> ReleaseTrustArtifact:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if int(payload.get("artifact_version", 0)) != 1:
        raise ReleaseTrustArtifactError("unsupported release trust artifact version")
    artifact = ReleaseTrustArtifact(
        artifact_id=payload["artifact_id"],
        release_id=payload["release_id"],
        tag=payload["tag"],
        candidate_sha=payload["candidate_sha"],
        pack_fingerprint=payload["pack_fingerprint"],
        archive_filename=payload["archive_filename"],
        archive_sha256=payload["archive_sha256"],
        archive_size_bytes=int(payload["archive_size_bytes"]),
    )
    if payload.get("fingerprint") != artifact.fingerprint:
        raise ReleaseTrustArtifactError(
            "release trust artifact metadata fingerprint mismatch"
        )
    expected_id = ReleaseTrustArtifact.artifact_id_for(artifact.pack_fingerprint)
    if artifact.artifact_id != expected_id:
        raise ReleaseTrustArtifactError("artifact_id is not bound to pack_fingerprint")
    return artifact


def _write_metadata(artifact: ReleaseTrustArtifact, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(artifact.to_payload(), ensure_ascii=True, sort_keys=True, indent=2)
        + "\n",
        encoding="utf-8",
    )


def _extract_safely(archive_path: Path, destination: Path) -> None:
    import tarfile

    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, mode="r:gz") as archive:
        names: set[str] = set()
        for member in archive.getmembers():
            if not member.isfile():
                raise ReleaseTrustArtifactError(
                    f"non-regular archive member is forbidden: {member.name}"
                )
            verify_name = member.name
            if verify_name in names:
                raise ReleaseTrustArtifactError(
                    f"duplicate archive member: {verify_name}"
                )
            names.add(verify_name)
            target = (destination / verify_name).resolve()
            if destination.resolve() not in target.parents:
                raise ReleaseTrustArtifactError("archive member escapes extraction root")
            target.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is None:
                raise ReleaseTrustArtifactError(f"cannot read archive member: {verify_name}")
            target.write_bytes(source.read())


def build_artifact(
    *,
    pack_directory: Path,
    output_archive: Path,
    metadata_file: Path,
    expected_sha: str,
) -> ReleaseTrustArtifact:
    pack = verify_pack(pack_directory=pack_directory, expected_sha=expected_sha)
    archive_hash = create_deterministic_archive(pack_directory, output_archive)
    archive_size = output_archive.stat().st_size
    artifact = ReleaseTrustArtifact(
        artifact_id=ReleaseTrustArtifact.artifact_id_for(pack.fingerprint),
        release_id=pack.release_id,
        tag=pack.tag,
        candidate_sha=pack.candidate_sha,
        pack_fingerprint=pack.fingerprint,
        archive_filename=output_archive.name,
        archive_sha256=archive_hash,
        archive_size_bytes=archive_size,
    )
    _write_metadata(artifact, metadata_file)
    return artifact


def verify_artifact(
    *,
    archive_path: Path,
    metadata_file: Path,
    expected_sha: str = "",
) -> ReleaseTrustArtifact:
    artifact = _load_metadata(metadata_file)
    if archive_path.name != artifact.archive_filename:
        raise ReleaseTrustArtifactError("archive filename does not match metadata")
    digest, size = _hash_file(archive_path)
    if digest != artifact.archive_sha256.lower():
        raise ReleaseTrustArtifactError("artifact archive sha256 mismatch")
    if size != artifact.archive_size_bytes:
        raise ReleaseTrustArtifactError("artifact archive size mismatch")
    verify_archive_member_safety(archive_path)
    with tempfile.TemporaryDirectory(prefix="morva-m3-52-") as temp_dir:
        extracted = Path(temp_dir)
        _extract_safely(archive_path, extracted)
        pack = verify_pack(
            pack_directory=extracted,
            expected_sha=expected_sha or artifact.candidate_sha,
        )
    if pack.fingerprint != artifact.pack_fingerprint:
        raise ReleaseTrustArtifactError("artifact pack fingerprint mismatch")
    if pack.release_id != artifact.release_id or pack.tag != artifact.tag:
        raise ReleaseTrustArtifactError("artifact release identity mismatch")
    if pack.candidate_sha.lower() != artifact.candidate_sha.lower():
        raise ReleaseTrustArtifactError("artifact candidate SHA mismatch")
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build or verify the Morva M3.52 release trust artifact"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build")
    build.add_argument("pack_directory", type=Path)
    build.add_argument("output_archive", type=Path)
    build.add_argument("metadata_file", type=Path)
    build.add_argument("--expected-sha", required=True)

    verify = subparsers.add_parser("verify")
    verify.add_argument("archive", type=Path)
    verify.add_argument("metadata", type=Path)
    verify.add_argument("--expected-sha", default="")

    args = parser.parse_args()
    if args.command == "build":
        artifact = build_artifact(
            pack_directory=args.pack_directory,
            output_archive=args.output_archive,
            metadata_file=args.metadata_file,
            expected_sha=args.expected_sha,
        )
        print("M3.52 release trust artifact built")
        print(f"artifact_id={artifact.artifact_id}")
        print(f"candidate_sha={artifact.candidate_sha}")
        print(f"archive_sha256={artifact.archive_sha256}")
        print(f"artifact_fingerprint={artifact.fingerprint}")
        return 0

    artifact = verify_artifact(
        archive_path=args.archive,
        metadata_file=args.metadata,
        expected_sha=args.expected_sha,
    )
    print("M3.52 release trust artifact verified")
    print(f"artifact_id={artifact.artifact_id}")
    print(f"candidate_sha={artifact.candidate_sha}")
    print(f"archive_sha256={artifact.archive_sha256}")
    print(f"artifact_fingerprint={artifact.fingerprint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())