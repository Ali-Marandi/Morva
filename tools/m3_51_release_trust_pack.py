from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil

from morva.runtime.release_trust_pack import (
    ReleaseTrustEvidencePack,
    ReleaseTrustPackError,
    TrustPackSource,
    reject_private_key_material,
)
from tools.m3_50_trust_chain_verifier import (
    verify_chain,
    write_verification,
)


def _load_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ReleaseTrustPackError("verification timestamps must be timezone-aware")
    return parsed


def _hash_file(path: Path) -> tuple[str, int]:
    data = path.read_bytes()
    return sha256(data).hexdigest(), len(data)


def _relative_source(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ReleaseTrustPackError(
            f"source must be under the declared root: {path}"
        ) from exc


def _copy_source(
    source: Path,
    root: Path,
    destination_root: Path,
) -> str:
    relative = _relative_source(source, root)
    destination = destination_root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return (Path("sources") / relative).as_posix()


def _copy_sources(
    *,
    root: Path,
    output: Path,
    inputs: dict[str, Path],
) -> tuple[TrustPackSource, ...]:
    sources_root = output / "sources"
    sources_root.mkdir(parents=True, exist_ok=True)
    entries: list[TrustPackSource] = []
    for role, source in inputs.items():
        target_path = _copy_source(source, root, sources_root)
        if target_path == "sources/__m3_50__/chain_verification.json":
            raise ReleaseTrustPackError("source path is reserved for the M3.50 receipt")
        digest, size = _hash_file(output / target_path)
        entries.append(TrustPackSource(role, target_path, digest, size))

    return tuple(sorted(entries, key=lambda item: item.role))


def _write_pack(pack: ReleaseTrustEvidencePack, output: Path) -> None:
    payload = {
        "pack_version": 1,
        "pack_id": pack.pack_id,
        "release_id": pack.release_id,
        "tag": pack.tag,
        "candidate_sha": pack.candidate_sha,
        "verified_at": pack.verified_at.isoformat(),
        "bundle_fingerprint": pack.bundle_fingerprint,
        "signing_key_rotation_fingerprint": pack.signing_key_rotation_fingerprint,
        "root_rotation_fingerprint": pack.root_rotation_fingerprint,
        "chain_fingerprint": pack.chain_fingerprint,
        "previous_registry_fingerprint": pack.previous_registry_fingerprint,
        "intermediate_registry_fingerprint": pack.intermediate_registry_fingerprint,
        "current_registry_fingerprint": pack.current_registry_fingerprint,
        "sources": [
            {
                "role": item.role,
                "path": item.path,
                "sha256": item.sha256,
                "size_bytes": item.size_bytes,
            }
            for item in pack.sources
        ],
        "fingerprint": pack.fingerprint,
    }
    output.joinpath("pack.json").write_text(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _load_pack(path: Path) -> ReleaseTrustEvidencePack:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if int(payload.get("pack_version", 0)) != 1:
        raise ReleaseTrustPackError("unsupported trust pack version")
    pack = ReleaseTrustEvidencePack(
        pack_id=payload["pack_id"],
        release_id=payload["release_id"],
        tag=payload["tag"],
        candidate_sha=payload["candidate_sha"],
        verified_at=_load_datetime(payload["verified_at"]),
        bundle_fingerprint=payload["bundle_fingerprint"],
        signing_key_rotation_fingerprint=payload["signing_key_rotation_fingerprint"],
        root_rotation_fingerprint=payload["root_rotation_fingerprint"],
        chain_fingerprint=payload["chain_fingerprint"],
        previous_registry_fingerprint=payload["previous_registry_fingerprint"],
        intermediate_registry_fingerprint=payload["intermediate_registry_fingerprint"],
        current_registry_fingerprint=payload["current_registry_fingerprint"],
        sources=tuple(TrustPackSource(**item) for item in payload["sources"]),
    )
    if payload.get("fingerprint") != pack.fingerprint:
        raise ReleaseTrustPackError(
            "release trust pack fingerprint does not match its contents"
        )
    return pack


def build_pack(
    *,
    output: Path,
    root: Path,
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
    expected_sha: str,
    verified_at: datetime,
    pack_id: str,
) -> ReleaseTrustEvidencePack:
    if output.exists():
        raise ReleaseTrustPackError(
            "output directory already exists; trust packs are immutable"
        )
    output.mkdir(parents=True)
    inputs = {
        "release_bundle": bundle_file,
        "manifest": manifest_file,
        "gate": gate_file,
        "rehearsal": rehearsal_file,
        "release_signing_public_key": public_key_file,
        "previous_registry": previous_registry_file,
        "intermediate_registry": intermediate_registry_file,
        "current_registry": current_registry_file,
        "signing_key_rotation": signing_key_rotation_file,
        "root_rotation": root_rotation_file,
        "old_root_public_key": old_root_public_key_file,
        "new_root_public_key": new_root_public_key_file,
    }
    for path in inputs.values():
        if not path.is_file():
            raise ReleaseTrustPackError(f"missing source file: {path}")
    sources = _copy_sources(
        root=root,
        output=output,
        inputs=inputs,
    )
    source_map = {item.role: item.path for item in sources}

    def source(role: str) -> Path:
        return output / source_map[role]

    source_root = output / "sources"
    verify_chain(
        bundle_file=source("release_bundle"),
        manifest_file=source_root
        / Path(source_map["manifest"].removeprefix("sources/")),
        gate_file=source_root
        / Path(source_map["gate"].removeprefix("sources/")),
        rehearsal_file=source_root
        / Path(source_map["rehearsal"].removeprefix("sources/")),
        public_key_file=source("release_signing_public_key"),
        previous_registry_file=source("previous_registry"),
        intermediate_registry_file=source("intermediate_registry"),
        current_registry_file=source("current_registry"),
        signing_key_rotation_file=source("signing_key_rotation"),
        root_rotation_file=source("root_rotation"),
        old_root_public_key_file=source("old_root_public_key"),
        new_root_public_key_file=source("new_root_public_key"),
        root=source_root,
        expected_sha=expected_sha,
        verified_at=verified_at,
    )
    receipt_path = source_root / "__m3_50__" / "chain_verification.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    write_verification(result, receipt_path)
    digest, size = _hash_file(receipt_path)
    sources = tuple(
        sorted(
            (
                *sources,
                TrustPackSource(
                    "chain_verification_receipt",
                    receipt_path.relative_to(output).as_posix(),
                    digest,
                    size,
                ),
            ),
            key=lambda item: item.role,
        )
    )
    reject_private_key_material(output)
    pack = ReleaseTrustEvidencePack(
        pack_id=pack_id,
        release_id=result.release_id,
        tag=result.tag,
        candidate_sha=result.candidate_sha,
        verified_at=verified_at,
        bundle_fingerprint=result.bundle_fingerprint,
        signing_key_rotation_fingerprint=result.signing_key_rotation_fingerprint,
        root_rotation_fingerprint=result.root_rotation_fingerprint,
        chain_fingerprint=result.fingerprint,
        previous_registry_fingerprint=result.previous_registry_fingerprint,
        intermediate_registry_fingerprint=result.intermediate_registry_fingerprint,
        current_registry_fingerprint=result.current_registry_fingerprint,
        sources=sources,
    )
    pack.verify_files(output)
    _write_pack(pack, output)
    return pack


def verify_pack(
    *,
    pack_directory: Path,
    expected_sha: str = "",
) -> ReleaseTrustEvidencePack:
    pack = _load_pack(pack_directory / "pack.json")
    pack.verify_files(pack_directory)
    reject_private_key_material(pack_directory)
    root_dir = pack_directory / "sources"
    source_map = pack.source_map

    def path(role: str) -> Path:
        return pack_directory / source_map[role].path

    chain_receipt = json.loads(
        path("chain_verification_receipt").read_text(encoding="utf-8")
    )
    verified_at = pack.verified_at
    result = verify_chain(
        bundle_file=path("release_bundle"),
        manifest_file=root_dir / Path(
            source_map["manifest"].path.removeprefix("sources/")
        ),
        gate_file=root_dir / Path(
            source_map["gate"].path.removeprefix("sources/")
        ),
        rehearsal_file=root_dir / Path(
            source_map["rehearsal"].path.removeprefix("sources/")
        ),
        public_key_file=path("release_signing_public_key"),
        previous_registry_file=path("previous_registry"),
        intermediate_registry_file=path("intermediate_registry"),
        current_registry_file=path("current_registry"),
        signing_key_rotation_file=path("signing_key_rotation"),
        root_rotation_file=path("root_rotation"),
        old_root_public_key_file=path("old_root_public_key"),
        new_root_public_key_file=path("new_root_public_key"),
        root=root_dir,
        expected_sha=expected_sha or pack.candidate_sha,
        verified_at=verified_at,
    )

    expected = {
        "release_id": pack.release_id,
        "tag": pack.tag,
        "candidate_sha": pack.candidate_sha,
        "bundle_fingerprint": pack.bundle_fingerprint,
        "signing_key_rotation_fingerprint": pack.signing_key_rotation_fingerprint,
        "root_rotation_fingerprint": pack.root_rotation_fingerprint,
        "chain_fingerprint": pack.chain_fingerprint,
        "previous_registry_fingerprint": pack.previous_registry_fingerprint,
        "intermediate_registry_fingerprint": pack.intermediate_registry_fingerprint,
        "current_registry_fingerprint": pack.current_registry_fingerprint,
    }
    actual = {
        "release_id": result.release_id,
        "tag": result.tag,
        "candidate_sha": result.candidate_sha,
        "bundle_fingerprint": result.bundle_fingerprint,
        "signing_key_rotation_fingerprint": result.signing_key_rotation_fingerprint,
        "root_rotation_fingerprint": result.root_rotation_fingerprint,
        "chain_fingerprint": result.fingerprint,
        "previous_registry_fingerprint": result.previous_registry_fingerprint,
        "intermediate_registry_fingerprint": result.intermediate_registry_fingerprint,
        "current_registry_fingerprint": result.current_registry_fingerprint,
    }
    if expected != actual:
        raise ReleaseTrustPackError("trust pack identity does not match verified trust chain")
    if chain_receipt.get("fingerprint") != result.fingerprint:
        raise ReleaseTrustPackError(
            "M3.50 verification receipt does not match the reconstructed chain"
        )
    return pack


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build or independently verify a Morva release trust evidence pack"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build")
    build.add_argument("output", type=Path)
    for name in (
        "bundle",
        "manifest",
        "gate",
        "rehearsal",
        "public-key",
        "previous-registry",
        "intermediate-registry",
        "current-registry",
        "signing-key-rotation",
        "root-rotation",
        "old-root-public-key",
        "new-root-public-key",
    ):
        build.add_argument(f"--{name}", type=Path, required=True)
    build.add_argument("--root", type=Path, default=Path("."))
    build.add_argument("--expected-sha", default=os.getenv("GITHUB_SHA", ""))
    build.add_argument("--verified-at", default="")
    build.add_argument("--pack-id", default="morva-release-trust-pack")

    verify = subparsers.add_parser("verify")
    verify.add_argument("pack_directory", type=Path)
    verify.add_argument("--expected-sha", default="")

    args = parser.parse_args()
    if args.command == "build":
        verified_at = (
            _load_datetime(args.verified_at)
            if args.verified_at
            else datetime.now(timezone.utc)
        )
        build_pack(
            output=args.output,
            root=args.root,
            bundle_file=args.bundle,
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
            expected_sha=args.expected_sha,
            verified_at=verified_at,
            pack_id=args.pack_id,
        )
        print("M3.51 release trust evidence pack built")
        return 0

    pack = verify_pack(
        pack_directory=args.pack_directory,
        expected_sha=args.expected_sha,
    )
    print("M3.51 release trust evidence pack verified")
    print(f"release_id={pack.release_id}")
    print(f"candidate_sha={pack.candidate_sha}")
    print(f"pack_fingerprint={pack.fingerprint}")
    print(f"chain_fingerprint={pack.chain_fingerprint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
