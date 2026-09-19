from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from morva.runtime.production_certification_gate import (
    ProductionCertificationGateError,
    build_production_certification_gate,
    load_registry,
    write_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the Morva production-certification gate"
    )
    parser.add_argument("--final-technical-gate", type=Path, required=True)
    parser.add_argument("--final-freshness-gate", type=Path, required=True)
    parser.add_argument("--final-gate", type=Path, required=True)
    parser.add_argument("--external-registry", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--certified-at")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        certified_at = (
            datetime.fromisoformat(args.certified_at)
            if args.certified_at
            else datetime.now(timezone.utc)
        )
        registry = load_registry(args.external_registry)
        gate = build_production_certification_gate(
            final_technical_gate=args.final_technical_gate,
            final_freshness_gate=args.final_freshness_gate,
            final_gate=args.final_gate,
            external_registry=registry,
            final_readiness_repository=args.repository,
            tag=args.tag,
            candidate_sha=args.candidate_sha,
            certified_at=certified_at,
        )
        write_gate(gate, args.output)
    except (ProductionCertificationGateError, OSError, ValueError) as exc:
        parser.exit(2, f"M3.67 production certification blocked: {exc}\n")

    print("M3.67 production certification evidence gate verified")
    print(f"repository={gate.repository}")
    print(f"release_id={gate.release_id}")
    print(f"tag={gate.tag}")
    print(f"candidate_sha={gate.candidate_sha}")
    print(f"roles={len(gate.verified_roles)}")
    print(f"final_readiness_fingerprint={gate.final_readiness_fingerprint}")
    print(f"external_evidence_fingerprint={gate.external_evidence_fingerprint}")
    print(f"fingerprint={gate.fingerprint}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
