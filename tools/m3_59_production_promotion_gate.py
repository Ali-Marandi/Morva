from __future__ import annotations

import argparse
from pathlib import Path

from morva.runtime.production_promotion_gate import (
    ProductionPromotionGateError,
    build_production_promotion_gate,
    write_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the fail-closed Morva production-promotion gate"
    )
    parser.add_argument("--bundle-archive", type=Path, required=True)
    parser.add_argument("--bundle-metadata", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--deployment-attestation", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        gate = build_production_promotion_gate(
            bundle_archive=args.bundle_archive,
            bundle_metadata=args.bundle_metadata,
            authorization_file=args.authorization,
            deployment_attestation=args.deployment_attestation,
            repository=args.repository,
            tag=args.tag,
            candidate_sha=args.candidate_sha,
        )
        write_gate(gate, args.output)
    except (ProductionPromotionGateError, OSError, ValueError) as exc:
        parser.exit(2, f"M3.59 production promotion blocked: {exc}\n")

    print("M3.59 production-promotion gate verified")
    print(f"repository={gate.repository}")
    print(f"release_id={gate.release_id}")
    print(f"tag={gate.tag}")
    print(f"candidate_sha={gate.candidate_sha}")
    print(f"source_environment={gate.source_environment}")
    print(f"target_environment={gate.target_environment}")
    print(f"bundle_fingerprint={gate.bundle_fingerprint}")
    print(f"gate_fingerprint={gate.fingerprint}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
