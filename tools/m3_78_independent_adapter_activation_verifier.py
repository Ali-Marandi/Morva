from __future__ import annotations

import argparse
from pathlib import Path

from morva.runtime.independent_adapter_activation_verifier import (
    IndependentAdapterActivationVerificationError,
    verify_adapter_activation,
    write_receipt,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Independently verify a Morva adapter activation gate"
    )
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--activation-gate", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        receipt = verify_adapter_activation(
            registry_file=args.registry,
            activation_gate=args.activation_gate,
            repository=args.repository,
            candidate_sha=args.candidate_sha,
        )
        write_receipt(receipt, args.output)
    except (
        IndependentAdapterActivationVerificationError,
        OSError,
        ValueError,
    ) as exc:
        parser.exit(2, f"M3.78 activation verification blocked: {exc}\n")

    print("M3.78 adapter activation gate independently verified")
    print(f"repository={receipt.repository}")
    print(f"candidate_sha={receipt.candidate_sha}")
    print(f"target_environment={receipt.target_environment}")
    print(f"adapter_count={len(receipt.adapters)}")
    print(f"activation_gate_fingerprint={receipt.activation_gate_fingerprint}")
    print(f"verification_fingerprint={receipt.fingerprint}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
