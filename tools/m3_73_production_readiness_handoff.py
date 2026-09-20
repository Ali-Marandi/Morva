from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from morva.runtime.production_readiness_handoff import (
    ProductionReadinessHandoffError,
    build_handoff,
    load_handoff,
    verify_handoff_sources,
    write_handoff,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build or verify a Morva production-readiness handoff manifest"
    )
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--handoff", type=Path, required=True)
    parser.add_argument("--repository", required=False)
    parser.add_argument("--release-id", required=False)
    parser.add_argument("--tag", required=False)
    parser.add_argument("--candidate-sha", required=False)
    parser.add_argument("--convergence-fingerprint", required=False)
    parser.add_argument("--source", action="append", default=[])
    parser.add_argument("--created-at", default=None)
    args = parser.parse_args()

    try:
        if args.mode == "build":
            required = (
                args.repository,
                args.release_id,
                args.tag,
                args.candidate_sha,
                args.convergence_fingerprint,
            )
            if any(value is None for value in required):
                parser.error(
                    "build mode requires repository, release-id, tag, "
                    "candidate-sha and convergence-fingerprint"
                )
            created_at = (
                datetime.fromisoformat(args.created_at)
                if args.created_at
                else datetime.now(timezone.utc)
            )
            handoff = build_handoff(
                root=args.root,
                source_paths=tuple(args.source),
                repository=args.repository,
                release_id=args.release_id,
                tag=args.tag,
                candidate_sha=args.candidate_sha,
                convergence_fingerprint=args.convergence_fingerprint,
                created_at=created_at,
            )
            write_handoff(handoff, args.handoff)
        else:
            handoff = load_handoff(args.handoff)
            verify_handoff_sources(handoff=handoff, root=args.root)
    except (
        ProductionReadinessHandoffError,
        OSError,
        ValueError,
    ) as exc:
        parser.exit(2, f"M3.73 handoff blocked: {exc}\n")

    print("M3.73 production-readiness handoff verified")
    print(f"repository={handoff.repository}")
    print(f"release_id={handoff.release_id}")
    print(f"tag={handoff.tag}")
    print(f"candidate_sha={handoff.candidate_sha}")
    print(f"source_count={len(handoff.sources)}")
    print(f"handoff_fingerprint={handoff.fingerprint}")
    print(f"output={args.handoff}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
