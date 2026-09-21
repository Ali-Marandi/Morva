from __future__ import annotations

from morva.runtime.production_boundary_policy import (
    ProductionBoundaryPolicyReceipt,
    ProductionBoundaryPolicyError,
    scan_repository,
)


M3_54_TO_M3_68_WORKFLOWS = tuple(
    f".github/workflows/m3-{number:02d}-"
    f"{suffix}.yml"
    for number, suffix in (
        (54, "release-publication-executor"),
        (55, "release-post-publication-integrity"),
        (56, "deployment-evidence-gate"),
        (57, "independent-deployment-evidence-verifier"),
        (58, "deployment-evidence-bundle"),
        (59, "production-promotion-gate"),
        (60, "independent-production-promotion-verifier"),
        (61, "production-boundary-policy"),
        (62, "technical-production-readiness"),
        (63, "evidence-freshness-gate"),
        (64, "final-technical-production-readiness"),
        (65, "independent-final-readiness"),
        (66, "external-certification-evidence"),
        (67, "production-certification-gate"),
        (68, "independent-production-certification-verifier"),
    )
)


def scan_full_production_boundary(
    *,
    root,
    repository: str,
) -> ProductionBoundaryPolicyReceipt:
    receipt = scan_repository(
        root=root,
        repository=repository,
        relative_paths=M3_54_TO_M3_68_WORKFLOWS,
    )
    if tuple(receipt.scanned_paths) != M3_54_TO_M3_68_WORKFLOWS:
        raise ProductionBoundaryPolicyError(
            "full production-boundary workflow coverage is incomplete"
        )
    return receipt
