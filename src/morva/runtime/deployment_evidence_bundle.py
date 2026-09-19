from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import shutil
import tarfile
import tempfile

from morva.runtime.deployment_evidence_verifier import verify_deployment_evidence
from morva.runtime.release_deployment_evidence import (
    load_attestation,
    load_release_receipt,
)


_PRIVATE_KEY_MARKERS = (
    b"BEGIN PRIVATE KEY",
    b"BEGIN OPENSSH PRIVATE KEY",
    b"BEGIN RSA PRIVATE KEY",
    b"BEGIN EC PRIVATE KEY",
)


class DeploymentEvidenceBundleError(ValueError):
    """Raised when a deployment-evidence bundle is invalid."""


@dataclass(frozen=True, slots=True)
class BundleSource:
    name: str
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        if not self.name.strip() or Path(self.name).name != self.name:
            raise DeploymentEvidenceBundleError(
                "bundle source name must be a plain file name"
            )
        if len(self.sha256) != 64 or any(
            c not in "0123456789abcdef" for c in self.sha256.lower()
        ):
            raise DeploymentEvidenceBundleError(
                "bundle source sha256 must be a SHA-256 digest"
            )
        if self.size_bytes <= 0:
            raise DeploymentEvidenceBundleError(
                "bundle source size must be positive"
            )

    def to_payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "sha256": self.sha256.lower(),
            "size_bytes": self.size_bytes,
        }


@dataclass(frozen=True, slots=True)
class DeploymentEvidenceBundle:
    bundle_version: int
    bundle_id: str
    release_id: str
    tag: str
    candidate_sha: str
    environment: str
    source_manifest: tuple[BundleSource, ...]
    archive_filename: str
    archive_sha256: str
    archive_size_bytes: int

    def __post_init__(self) -> None:
        if self.bundle_version != 1:
            raise DeploymentEvidenceBundleError(
                "unsupported deployment evidence bundle version"
            )
        if not self.bundle_id.startswith("morva-deployment-evidence-v1-"):
            raise DeploymentEvidenceBundleError("invalid bundle_id")
        if not self.release_id.strip() or not self.tag.strip():
            raise DeploymentEvidenceBundleError(
                "release_id and tag are required"
            )
        if len(self.candidate_sha) != 40 or any(
            c not in "0123456789abcdef" for c in self.candidate_sha.lower()
        ):
            raise DeploymentEvidenceBundleError(
                "candidate_sha must be a Git commit SHA-1"
            )
        if self.environment not in {"staging", "pilot", "production"}:
            raise DeploymentEvidenceBundleError(
                "unsupported deployment environment"
            )
        if not self.source_manifest:
            raise DeploymentEvidenceBundleError(
                "source manifest cannot be empty"
            )
        names = [source.name for source in self.source_manifest]
        if len(names) != len(set(names)):
            raise DeploymentEvidenceBundleError(
                "bundle source names must be unique"
            )
        if (
            not self.archive_filename.strip()
            or Path(self.archive_filename).name != self.archive_filename
        ):
            raise DeploymentEvidenceBundleError(
                "archive_filename must be a plain file name"
            )
        for name, value in (
            ("archive_sha256", self.archive_sha256),
        ):
            if len(value) != 64 or any(
                c not in "0123456789abcdef" for c in value.lower()
            ):
                raise DeploymentEvidenceBundleError(
                    f"{name} must be SHA-256"
                )
        if self.archive_size_bytes <= 0:
            raise DeploymentEvidenceBundleError(
                "archive_size_bytes must be positive"
            )

    @staticmethod
    def bundle_id_for(bundle_fingerprint: str) -> str:
        if len(bundle_fingerprint) != 64 or any(
            c not in "0123456789abcdef" for c in bundle_fingerprint.lower()
        ):
            raise DeploymentEvidenceBundleError(
                "bundle fingerprint must be SHA-256"
            )
        return f"morva-deployment-evidence-v1-{bundle_fingerprint.lower()}"

    @property
    def manifest_payload(self) -> list[dict[str, object]]:
        return [
            source.to_payload()
            for source in sorted(self.source_manifest, key=lambda item: item.name)
        ]

    @property
    def bundle_fingerprint(self) -> str:
        payload = {
            "bundle_version": self.bundle_version,
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha.lower(),
            "environment": self.environment,
            "source_manifest": self.manifest_payload,
        }
        canonical = json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(canonical.encode("utf-8")).hexdigest()

    def to_payload(self) -> dict[str, object]:
        return {
            "bundle_version": self.bundle_version,
            "bundle_id": self.bundle_id,
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha,
            "environment": self.environment,
            "source_manifest": self.manifest_payload,
            "archive_filename": self.archive_filename,
            "archive_sha256": self.archive_sha256,
            "archive_size_bytes": self.archive_size_bytes,
            "bundle_fingerprint": self.bundle_fingerprint,
        }


def _hash_file(path: Path) -> tuple[str, int]:
    if not path.is_file():
        raise DeploymentEvidenceBundleError(
            f"bundle source does not exist: {path}"
        )
    data = path.read_bytes()
    for marker in _PRIVATE_KEY_MARKERS:
        if marker in data:
            raise DeploymentEvidenceBundleError(
                f"private-key material is forbidden in bundle source: {path.name}"
            )
    return sha256(data).hexdigest(), len(data)


def _source_manifest(paths: dict[str, Path]) -> tuple[BundleSource, ...]:
    sources: list[BundleSource] = []
    for name, path in sorted(paths.items()):
        digest, size = _hash_file(path)
        sources.append(
            BundleSource(name=name, sha256=digest, size_bytes=size)
        )
    return tuple(sources)


def _write_pack(directory: Path, bundle: DeploymentEvidenceBundle) -> None:
    payload = {
        "bundle_version": bundle.bundle_version,
        "bundle_id": bundle.bundle_id,
        "release_id": bundle.release_id,
        "tag": bundle.tag,
        "candidate_sha": bundle.candidate_sha,
        "environment": bundle.environment,
        "source_manifest": bundle.manifest_payload,
        "archive_filename": bundle.archive_filename,
        "archive_sha256": "0" * 64,
        "archive_size_bytes": 1,
        "bundle_fingerprint": bundle.bundle_fingerprint,
    }
    (directory / "pack.json").write_text(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2)
        + "\n",
        encoding="utf-8",
    )


def _load_pack(directory: Path) -> DeploymentEvidenceBundle:
    try:
        payload = json.loads(
            (directory / "pack.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise DeploymentEvidenceBundleError(
            "bundle pack.json is missing or invalid"
        ) from exc
    try:
        sources = tuple(
            BundleSource(
                name=item["name"],
                sha256=item["sha256"],
                size_bytes=int(item["size_bytes"]),
            )
            for item in payload["source_manifest"]
        )
        return DeploymentEvidenceBundle(
            bundle_version=int(payload["bundle_version"]),
            bundle_id=payload["bundle_id"],
            release_id=payload["release_id"],
            tag=payload["tag"],
            candidate_sha=payload["candidate_sha"],
            environment=payload["environment"],
            source_manifest=sources,
            archive_filename=payload["archive_filename"],
            archive_sha256=payload["archive_sha256"],
            archive_size_bytes=int(payload["archive_size_bytes"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise DeploymentEvidenceBundleError(
            "bundle pack structure is invalid"
        ) from exc


def _load_metadata(path: Path) -> DeploymentEvidenceBundle:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DeploymentEvidenceBundleError(
            "bundle metadata is missing or invalid"
        ) from exc
    try:
        sources = tuple(
            BundleSource(
                name=item["name"],
                sha256=item["sha256"],
                size_bytes=int(item["size_bytes"]),
            )
            for item in payload["source_manifest"]
        )
        bundle = DeploymentEvidenceBundle(
            bundle_version=int(payload["bundle_version"]),
            bundle_id=payload["bundle_id"],
            release_id=payload["release_id"],
            tag=payload["tag"],
            candidate_sha=payload["candidate_sha"],
            environment=payload["environment"],
            source_manifest=sources,
            archive_filename=payload["archive_filename"],
            archive_sha256=payload["archive_sha256"],
            archive_size_bytes=int(payload["archive_size_bytes"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise DeploymentEvidenceBundleError(
            "bundle metadata structure is invalid"
        ) from exc
    if payload.get("bundle_fingerprint") != bundle.bundle_fingerprint:
        raise DeploymentEvidenceBundleError(
            "bundle metadata fingerprint mismatch"
        )
    expected_id = DeploymentEvidenceBundle.bundle_id_for(bundle.bundle_fingerprint)
    if bundle.bundle_id != expected_id:
        raise DeploymentEvidenceBundleError(
            "bundle_id is not bound to bundle_fingerprint"
        )
    return bundle


def _extract_safely(archive_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, mode="r:gz") as archive:
        names: set[str] = set()
        for member in archive.getmembers():
            if not member.isfile():
                raise DeploymentEvidenceBundleError(
                    f"non-regular archive member is forbidden: {member.name}"
                )
            if member.name in names:
                raise DeploymentEvidenceBundleError(
                    f"duplicate archive member: {member.name}"
                )
            names.add(member.name)
            target = (destination / member.name).resolve()
            if destination.resolve() not in target.parents:
                raise DeploymentEvidenceBundleError(
                    "archive member escapes extraction root"
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is None:
                raise DeploymentEvidenceBundleError(
                    f"archive member has no data: {member.name}"
                )
            target.write_bytes(source.read())


def build_deployment_evidence_bundle(
    *,
    release_receipt_file: Path,
    deployment_gate_file: Path,
    attestation_file: Path,
    deployment_verification_receipt_file: Path,
    output_archive: Path,
    metadata_file: Path,
    repository: str,
    tag: str,
    candidate_sha: str,
) -> DeploymentEvidenceBundle:
    verification = verify_deployment_evidence(
        gate_file=deployment_gate_file,
        release_receipt_file=release_receipt_file,
        attestation_file=attestation_file,
        repository=repository,
        tag=tag,
        candidate_sha=candidate_sha,
    )
    if not deployment_verification_receipt_file.is_file():
        raise DeploymentEvidenceBundleError(
            "M3.57 verification receipt file is required"
        )
    try:
        verification_payload = json.loads(
            deployment_verification_receipt_file.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise DeploymentEvidenceBundleError(
            "M3.57 verification receipt is invalid"
        ) from exc
    if verification_payload.get("fingerprint") != verification.fingerprint:
        raise DeploymentEvidenceBundleError(
            "M3.57 verification receipt does not match re-verification"
        )

    receipt = load_release_receipt(release_receipt_file)
    attestation = load_attestation(attestation_file)
    if verification.environment != attestation.environment:
        raise DeploymentEvidenceBundleError(
            "verification environment does not match attestation"
        )

    source_paths = {
        "release_post_publication_receipt.json": release_receipt_file,
        "deployment_evidence_gate.json": deployment_gate_file,
        "deployment_attestation.json": attestation_file,
        "deployment_evidence_verification_receipt.json": (
            deployment_verification_receipt_file
        ),
    }
    sources = _source_manifest(source_paths)
    provisional = DeploymentEvidenceBundle(
        bundle_version=1,
        bundle_id="morva-deployment-evidence-v1-" + "0" * 64,
        release_id=receipt.release_id,
        tag=tag,
        candidate_sha=candidate_sha,
        environment=attestation.environment,
        source_manifest=sources,
        archive_filename=output_archive.name,
        archive_sha256="0" * 64,
        archive_size_bytes=1,
    )
    bundle = DeploymentEvidenceBundle(
        bundle_version=1,
        bundle_id=DeploymentEvidenceBundle.bundle_id_for(
            provisional.bundle_fingerprint
        ),
        release_id=provisional.release_id,
        tag=provisional.tag,
        candidate_sha=provisional.candidate_sha,
        environment=provisional.environment,
        source_manifest=provisional.source_manifest,
        archive_filename=provisional.archive_filename,
        archive_sha256=provisional.archive_sha256,
        archive_size_bytes=provisional.archive_size_bytes,
    )

    if output_archive.exists() or metadata_file.exists():
        raise DeploymentEvidenceBundleError(
            "bundle outputs are write-once"
        )
    with tempfile.TemporaryDirectory(prefix="morva-m3-58-") as temp:
        staging = Path(temp)
        _write_pack(staging, bundle)
        for name, path in source_paths.items():
            shutil.copyfile(path, staging / name)
        from morva.runtime.release_trust_artifact import create_deterministic_archive

        archive_hash = create_deterministic_archive(staging, output_archive)
    archive_size = output_archive.stat().st_size
    final = DeploymentEvidenceBundle(
        bundle_version=bundle.bundle_version,
        bundle_id=bundle.bundle_id,
        release_id=bundle.release_id,
        tag=bundle.tag,
        candidate_sha=bundle.candidate_sha,
        environment=bundle.environment,
        source_manifest=bundle.source_manifest,
        archive_filename=bundle.archive_filename,
        archive_sha256=archive_hash,
        archive_size_bytes=archive_size,
    )
    if final.bundle_fingerprint != bundle.bundle_fingerprint:
        raise DeploymentEvidenceBundleError(
            "bundle fingerprint changed during archive construction"
        )
    metadata_file.parent.mkdir(parents=True, exist_ok=True)
    metadata_file.write_text(
        json.dumps(
            final.to_payload(),
            ensure_ascii=True,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return final


def verify_deployment_evidence_bundle(
    *,
    archive_path: Path,
    metadata_file: Path,
    expected_repository: str,
    expected_tag: str,
    expected_sha: str,
) -> DeploymentEvidenceBundle:
    bundle = _load_metadata(metadata_file)
    if archive_path.name != bundle.archive_filename:
        raise DeploymentEvidenceBundleError(
            "bundle archive filename mismatch"
        )
    digest, size = _hash_file(archive_path)
    if digest != bundle.archive_sha256:
        raise DeploymentEvidenceBundleError(
            "bundle archive SHA-256 mismatch"
        )
    if size != bundle.archive_size_bytes:
        raise DeploymentEvidenceBundleError(
            "bundle archive size mismatch"
        )
    with tempfile.TemporaryDirectory(prefix="morva-m3-58-verify-") as temp:
        extracted = Path(temp)
        _extract_safely(archive_path, extracted)
        pack = _load_pack(extracted)
        if pack.bundle_fingerprint != bundle.bundle_fingerprint:
            raise DeploymentEvidenceBundleError(
                "bundle pack fingerprint mismatch"
            )
        source_by_name = {source.name: source for source in bundle.source_manifest}
        expected_members = set(source_by_name) | {"pack.json"}
        actual_members = {
            member.name
            for member in tarfile.open(archive_path, mode="r:gz").getmembers()
        }
        if actual_members != expected_members:
            raise DeploymentEvidenceBundleError(
                "bundle archive member set mismatch"
            )
        for name in source_by_name:
            path = extracted / name
            digest, size = _hash_file(path)
            expected = source_by_name[name]
            if digest != expected.sha256 or size != expected.size_bytes:
                raise DeploymentEvidenceBundleError(
                    f"bundle source integrity mismatch: {name}"
                )
        verification = verify_deployment_evidence(
            gate_file=extracted / "deployment_evidence_gate.json",
            release_receipt_file=extracted / "release_post_publication_receipt.json",
            attestation_file=extracted / "deployment_attestation.json",
            repository=expected_repository,
            tag=expected_tag,
            candidate_sha=expected_sha,
        )
        stored = json.loads(
            (
                extracted / "deployment_evidence_verification_receipt.json"
            ).read_text(encoding="utf-8")
        )
        if stored.get("fingerprint") != verification.fingerprint:
            raise DeploymentEvidenceBundleError(
                "embedded M3.57 receipt does not match re-verification"
            )
        if (
            pack.release_id != verification.release_id
            or pack.tag != verification.tag
            or pack.candidate_sha.lower() != verification.candidate_sha.lower()
            or pack.environment != verification.environment
        ):
            raise DeploymentEvidenceBundleError(
                "bundle identity does not match deployment evidence"
            )
    return bundle
