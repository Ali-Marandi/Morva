from __future__ import annotations

import argparse
from pathlib import Path

from morva.runtime.production_boundary_policy_v2 import (
    scan_full_production_boundary,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan the complete M3.54-M3.68 production boundary"
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--repository", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        receipt = scan_full_production_boundary(
            root=args.root,
            repository=args.repository,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            __import__("json").dumps(
                receipt.to_payload(),
                ensure_ascii=True,
                sort_keys=True,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    except Exception as exc:
        parser.exit(2, f"M3.69 full policy scan blocked: {exc}\n")

    print("M3.69 full production-boundary policy passed")
    print(f"repository={receipt.repository}")
    print(f"scanned_paths={len(receipt.scanned_paths)}")
    print(f"fingerprint={receipt.fingerprint}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
