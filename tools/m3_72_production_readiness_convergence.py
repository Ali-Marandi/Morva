from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from morva.runtime.production_readiness_convergence import (
    ProductionReadinessConvergenceError,
    build_convergence,
    write_convergence,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build and verify Morva production-readiness convergence evidence"
    )
    for name in (
        "technical-readiness-gate",
        "final-readiness-receipt",
        "production-certification-receipt",
        "external-registry",
        "policy-receipt",
        "lineage-manifest",
        "lineage-verification-receipt",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--converged-at", default=None)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        converged_at = (
            datetime.fromisoformat(args.converged_at)
            if args.converged_at
            else datetime.now(timezone.utc)
        )
        convergence = build_convergence(
            technical_readiness_gate=args.technical_readiness_gate,
            final_readiness_receipt=args.final_readiness_receipt,
            production_certification_receipt=args.production_certification_receipt,
            external_registry=args.external_registry,
            policy_receipt=args.policy_receipt,
            lineage_manifest=args.lineage_manifest,
            lineage_verification_receipt=args.lineage_verification_receipt,
            repository=args.repository,
            tag=args.tag,
            candidate_sha=args.candidate_sha,
            converged_at=converged_at,
        )
        write_convergence(convergence, args.output)
    except (
        ProductionReadinessConvergenceError,
        OSError,
        ValueError,
    ) as exc:
        parser.exit(2, f"M3.72 convergence blocked: {exc}\n")

    print("M3.72 production-readiness evidence converged")
    print(f"repository={convergence.repository}")
    print(f"release_id={convergence.release_id}")
    print(f"tag={convergence.tag}")
    print(f"candidate_sha={convergence.candidate_sha}")
    print(f"convergence_fingerprint={convergence.fingerprint}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
