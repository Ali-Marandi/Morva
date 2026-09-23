from __future__ import annotations

from datetime import datetime

from pathlib import Path

from morva.persistence.integration_execution_readiness_records import (
    IntegrationExecutionReadinessVerificationRepository,
    IntegrationExecutionReadinessVerificationRecord,
)
from morva.runtime.independent_integration_execution_readiness_verifier_m4_21 import (
    IndependentIntegrationExecutionReadinessVerification,
    verify_integration_execution_readiness_assessment,
)


def persist_verified_integration_execution_readiness(
    repository: IntegrationExecutionReadinessVerificationRepository,
    assessment_path: Path,
    *,
    repository_name: str,
    candidate_sha: str,
    verified_at: datetime,
) -> tuple[
    IntegrationExecutionReadinessVerificationRecord,
    IndependentIntegrationExecutionReadinessVerification,
]:
    """Verify an M4.20 assessment independently, then persist only that receipt.

    The caller supplies the exact candidate SHA and verification time. The
    verification fingerprint is derived by M4.21 and is never accepted from
    the input assessment.
    """
    verification = verify_integration_execution_readiness_assessment(
        assessment_path,
        repository=repository_name,
        candidate_sha=candidate_sha,
        verified_at=verified_at,
    )
    record = repository.record(verification)
    return record, verification
