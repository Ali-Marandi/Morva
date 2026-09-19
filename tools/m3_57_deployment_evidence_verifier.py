from __future__ import annotations

import argparse
from pathlib import Path

from morva.runtime.deployment_evidence_verifier import (
    write_verification_receipt,
    verify_deployment_evidence,
)
from morva.runtime.release_deployment_evidence import DeploymentEvidenceGateError


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Independently verify a Morva deployment evidence gate"
    )
    parser.add_argument("--gate", type=Path, required=True)
    parser.add_argument("--release-receipt", type=Path, required=True)
    parser.add_argument("--attestation", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        receipt = verify_deployment_evidence(
            gate_file=args.gate,
            release_receipt_file=args.release_receipt,
            attestation_file=args.attestation,
            repository=args.repository,
            tag=args.tag,
            candidate_sha=args.candidate_sha,
        )
        write_verification_receipt(receipt, args.output)
    except (DeploymentEvidenceGateError, OSError, ValueError) as exc:
        parser.exit(2, f"M3.57 deployment evidence verification blocked: {exc}\n")

    print("M3.57 deployment evidence independently verified")
    print(f"repository={receipt.repository}")
    print(f"release_id={receipt.release_id}")
    print(f"tag={receipt.tag}")
    print(f"candidate_sha={receipt.candidate_sha}")
    print(f"environment={receipt.environment}")
    print(f"deployment_id={receipt.deployment_id}")
    print(f"deployment_gate_fingerprint={receipt.deployment_gate_fingerprint}")
    print(f"verification_fingerprint={receipt.fingerprint}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
