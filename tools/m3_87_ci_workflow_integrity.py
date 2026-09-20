from __future__ import annotations

import argparse
from pathlib import Path

from morva.runtime.ci_workflow_integrity import (
    CIWorkflowIntegrityError,
    scan_workflows,
    write_receipt,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Morva GitHub Actions workflow integrity")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--repository", default="Ali-Marandi/Morva")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        receipt = scan_workflows(args.root, args.repository)
        if args.output:
            write_receipt(receipt, args.output)
    except (CIWorkflowIntegrityError, OSError, ValueError) as exc:
        parser.exit(2, f"M3.87 workflow integrity blocked: {exc}\n")

    print("M3.87 CI workflow integrity verified")
    print(f"repository={receipt.repository}")
    print(f"workflow_count={len(receipt.scanned_paths)}")
    print(f"fingerprint={receipt.fingerprint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
