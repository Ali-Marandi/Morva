from __future__ import annotations

import argparse
from pathlib import Path

from morva.runtime.technical_readiness_gate import (
    TechnicalReadinessGateError,
    build_technical_readiness_gate,
    write_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the Morva technical production readiness gate"
    )
    parser.add_argument("--bundle-archive", type=Path, required=True)
    parser.add_argument("--bundle-metadata", type=Path, required=True)
    parser.add_argument("--promotion-gate", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--deployment-attestation", type=Path, required=True)
    parser.add_argument("--policy-receipt", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        gate = build_technical_readiness_gate(
            bundle_archive=args.bundle_archive,
            bundle_metadata=args.bundle_metadata,
            promotion_gate=args.promotion_gate,
            authorization=args.authorization,
            deployment_attestation=args.deployment_attestation,
            policy_receipt=args.policy_receipt,
            repository=args.repository,
            tag=args.tag,
            candidate_sha=args.candidate_sha,
        )
        write_gate(gate, args.output)
    except (TechnicalReadinessGateError, OSError, ValueError) as exc:
        parser.exit(2, f"M3.62 technical readiness blocked: {exc}\n")

    print("M3.62 technical production readiness gate verified")
    print(f"repository={gate.repository}")
    print(f"release_id={gate.release_id}")
    print(f"tag={gate.tag}")
    print(f"candidate_sha={gate.candidate_sha}")
    print(f"source_environment={gate.source_environment}")
    print(f"target_environment={gate.target_environment}")
    print(f"bundle_fingerprint={gate.bundle_fingerprint}")
    print(f"promotion_verification_fingerprint={gate.promotion_verification_fingerprint}")
    print(f"policy_fingerprint={gate.policy_fingerprint}")
    print(f"gate_fingerprint={gate.fingerprint}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
