from __future__ import annotations

import argparse
import json
from pathlib import Path

from morva.runtime.independent_adapter_activation_verifier import (
    verify_adapter_activation,
)
from morva.runtime.integration_adapter_runtime import (
    IntegrationAdapterRuntime,
    IntegrationRuntimeActivationError,
    VerifiedAdapterRuntime,
)
from morva.runtime.official_adapter_evidence import REQUIRED_ADAPTERS


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify Morva adapter runtime activation boundary"
    )
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--activation-gate", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--adapter", choices=REQUIRED_ADAPTERS, required=True)
    args = parser.parse_args()

    try:
        receipt = verify_adapter_activation(
            registry_file=args.registry,
            activation_gate=args.activation_gate,
            repository=args.repository,
            candidate_sha=args.candidate_sha,
        )
        runtime = IntegrationAdapterRuntime(
            verification=VerifiedAdapterRuntime.from_verification(receipt)
        )
        runtime.assert_configured(args.adapter)
    except (IntegrationRuntimeActivationError, Exception) as exc:
        parser.exit(2, f"M3.79 runtime activation blocked: {exc}\n")

    print("M3.79 runtime activation boundary verified")
    print(f"adapter={args.adapter}")
    print(f"repository={args.repository}")
    print(f"candidate_sha={args.candidate_sha}")
    print(f"verified_adapters={len(runtime.activated_adapters)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
