from __future__ import annotations

import argparse
from pathlib import Path

from morva.runtime.release_deployment_evidence import (
    DeploymentEvidenceGateError,
    build_deployment_evidence_gate,
    load_attestation,
    load_release_receipt,
    write_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a fail-closed Morva deployment evidence gate"
    )
    parser.add_argument("--release-receipt", type=Path, required=True)
    parser.add_argument("--attestation", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = load_release_receipt(args.release_receipt)
        attestation = load_attestation(args.attestation)
        gate = build_deployment_evidence_gate(
            receipt=receipt,
            attestation=attestation,
            repository=args.repository,
            tag=args.tag,
            candidate_sha=args.candidate_sha,
        )
        write_gate(gate, args.output)
    except (DeploymentEvidenceGateError, OSError, ValueError) as exc:
        parser.exit(2, f"M3.56 deployment evidence gate blocked: {exc}\n")

    print("M3.56 deployment evidence gate verified")
    print(f"repository={gate.repository}")
    print(f"release_id={gate.release_id}")
    print(f"tag={gate.tag}")
    print(f"candidate_sha={gate.candidate_sha}")
    print(f"environment={gate.environment}")
    print(f"deployment_id={gate.deployment_id}")
    print(f"deployed_sha={gate.deployed_sha}")
    print(f"post_publication_fingerprint={gate.post_publication_fingerprint}")
    print(f"gate_fingerprint={gate.fingerprint}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
