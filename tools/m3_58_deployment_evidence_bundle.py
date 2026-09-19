from __future__ import annotations

import argparse
from pathlib import Path

from morva.runtime.deployment_evidence_bundle import (
    DeploymentEvidenceBundleError,
    build_deployment_evidence_bundle,
    verify_deployment_evidence_bundle,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build or verify the Morva deployment-evidence bundle"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build")
    build.add_argument("--release-receipt", type=Path, required=True)
    build.add_argument("--deployment-gate", type=Path, required=True)
    build.add_argument("--attestation", type=Path, required=True)
    build.add_argument("--verification", type=Path, required=True)
    build.add_argument("--repository", required=True)
    build.add_argument("--tag", required=True)
    build.add_argument("--candidate-sha", required=True)
    build.add_argument("--archive", type=Path, required=True)
    build.add_argument("--metadata", type=Path, required=True)

    verify = subparsers.add_parser("verify")
    verify.add_argument("--archive", type=Path, required=True)
    verify.add_argument("--metadata", type=Path, required=True)
    verify.add_argument("--repository", required=True)
    verify.add_argument("--tag", required=True)
    verify.add_argument("--candidate-sha", required=True)

    args = parser.parse_args()
    try:
        if args.command == "build":
            bundle = build_deployment_evidence_bundle(
                release_receipt_file=args.release_receipt,
                deployment_gate_file=args.deployment_gate,
                attestation_file=args.attestation,
                deployment_verification_receipt_file=args.verification,
                output_archive=args.archive,
                metadata_file=args.metadata,
                repository=args.repository,
                tag=args.tag,
                candidate_sha=args.candidate_sha,
            )
        else:
            bundle = verify_deployment_evidence_bundle(
                archive_path=args.archive,
                metadata_file=args.metadata,
                expected_repository=args.repository,
                expected_tag=args.tag,
                expected_sha=args.candidate_sha,
            )
    except (DeploymentEvidenceBundleError, OSError, ValueError) as exc:
        parser.exit(2, f"M3.58 deployment-evidence bundle blocked: {exc}\n")

    print("M3.58 deployment-evidence bundle verified")
    print(f"bundle_id={bundle.bundle_id}")
    print(f"release_id={bundle.release_id}")
    print(f"tag={bundle.tag}")
    print(f"candidate_sha={bundle.candidate_sha}")
    print(f"environment={bundle.environment}")
    print(f"bundle_fingerprint={bundle.bundle_fingerprint}")
    print(f"archive_sha256={bundle.archive_sha256}")
    print(f"archive_size_bytes={bundle.archive_size_bytes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
