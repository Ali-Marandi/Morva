from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from morva.runtime.final_production_readiness import (
    FinalProductionReadinessError,
    build_final_readiness_gate,
    write_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the final Morva technical production-readiness gate"
    )
    parser.add_argument("--technical-gate", type=Path, required=True)
    parser.add_argument("--freshness-gate", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--checked-at", required=False)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    checked_at = (
        datetime.fromisoformat(args.checked_at)
        if args.checked_at
        else datetime.now(timezone.utc)
    )

    try:
        gate = build_final_readiness_gate(
            technical_gate=args.technical_gate,
            freshness_gate=args.freshness_gate,
            repository=args.repository,
            tag=args.tag,
            candidate_sha=args.candidate_sha,
            checked_at=checked_at,
        )
        write_gate(gate, args.output)
    except (FinalProductionReadinessError, OSError, ValueError) as exc:
        parser.exit(2, f"M3.64 final readiness blocked: {exc}\n")

    print("M3.64 final technical production-readiness gate verified")
    print(f"repository={gate.repository}")
    print(f"release_id={gate.release_id}")
    print(f"tag={gate.tag}")
    print(f"candidate_sha={gate.candidate_sha}")
    print(f"bundle_fingerprint={gate.bundle_fingerprint}")
    print(f"freshness_gate_fingerprint={gate.freshness_gate_fingerprint}")
    print(f"fingerprint={gate.fingerprint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
