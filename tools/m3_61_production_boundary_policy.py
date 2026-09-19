from __future__ import annotations

import argparse
from pathlib import Path

from morva.runtime.production_boundary_policy import (
    ProductionBoundaryPolicyError,
    scan_repository,
    write_receipt,
)


WORKFLOW_PATHS = (
    ".github/workflows/m3-54-release-publication-executor.yml",
    ".github/workflows/m3-55-release-post-publication-integrity.yml",
    ".github/workflows/m3-56-deployment-evidence-gate.yml",
    ".github/workflows/m3-57-independent-deployment-evidence-verifier.yml",
    ".github/workflows/m3-58-deployment-evidence-bundle.yml",
    ".github/workflows/m3-59-production-promotion-gate.yml",
    ".github/workflows/m3-60-independent-production-promotion-verifier.yml",
    ".github/workflows/m3-61-production-boundary-policy.yml",
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan Morva production-boundary workflows"
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--repository", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        receipt = scan_repository(
            root=args.root,
            repository=args.repository,
            relative_paths=WORKFLOW_PATHS,
        )
        write_receipt(receipt, args.output)
    except (ProductionBoundaryPolicyError, OSError, ValueError) as exc:
        parser.exit(2, f"M3.61 policy scan blocked: {exc}\n")

    print("M3.61 production-boundary policy passed")
    print(f"repository={receipt.repository}")
    print(f"scanned_paths={len(receipt.scanned_paths)}")
    print(f"findings={len(receipt.findings)}")
    print(f"fingerprint={receipt.fingerprint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
