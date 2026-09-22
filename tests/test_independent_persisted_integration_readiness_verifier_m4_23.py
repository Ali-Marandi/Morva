from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json

import pytest

from morva.runtime.independent_persisted_integration_readiness_verifier_m4_23 import (
    IndependentPersistedIntegrationReadinessVerificationError,
    verify_persisted_integration_execution_readiness,
)


def _assessment_fingerprint(data: dict[str, object]) -> str:
    payload = {
        "assessment_version": data["assessment_version"],
        "repository": data["repository"],
        "candidate_sha": str(data["candidate_sha"]).lower(),
        "target_environment": data["target_environment"],
        "checked_at": data["assessment_checked_at"]
        .astimezone(timezone.utc)
        .isoformat(),
        "evidence_readiness_fingerprint": str(
            data["evidence_readiness_fingerprint"]
        ).lower(),
        "binding_fingerprint": str(data["binding_fingerprint"]).lower(),
        "binding_verification_fingerprint": str(
            data["binding_verification_fingerprint"]
        ).lower(),
        "state": data["state"],
        "blockers": list(data["blockers"]),
    }
    return sha256(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _verification_fingerprint(
    assessment_fingerprint: str, verified_at: datetime
) -> str:
    payload = {
        "assessment_fingerprint": assessment_fingerprint.lower(),
        "verified_at": verified_at.astimezone(timezone.utc).isoformat(),
    }
    return sha256(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _receipt() -> dict[str, object]:
    checked_at = datetime(2026, 9, 22, 20, 0, tzinfo=timezone.utc)
    verified_at = datetime(2026, 9, 22, 20, 1, tzinfo=timezone.utc)
    data: dict[str, object] = {
        "repository": "Ali-Marandi/Morva",
        "candidate_sha": "a" * 40,
        "target_environment": "staging",
        "assessment_version": 1,
        "assessment_checked_at": checked_at,
        "verified_at": verified_at,
        "created_at": datetime(2026, 9, 22, 20, 2, tzinfo=timezone.utc),
        "evidence_readiness_fingerprint": "1" * 64,
        "binding_fingerprint": "2" * 64,
        "binding_verification_fingerprint": "3" * 64,
        "state": "blocked",
        "blockers": ("AUTHORITATIVE_EVIDENCE_CLOSURE_INCOMPLETE",),
    }
    assessment_fingerprint = _assessment_fingerprint(data)
    data["assessment_fingerprint"] = assessment_fingerprint
    data["verification_fingerprint"] = _verification_fingerprint(
        assessment_fingerprint, verified_at
    )
    return data


def _verify(data: dict[str, object]):
    return verify_persisted_integration_execution_readiness(**data)


def test_m4_23_independently_verifies_persisted_receipt():
    result = _verify(_receipt())

    assert result.ready is False
    assert result.independent_assessment_fingerprint == result.assessment_fingerprint
    assert (
        result.independent_verification_fingerprint
        == result.verification_fingerprint
    )
    assert result.to_payload()["verified"] is True


@pytest.mark.parametrize(
    "field",
    ["assessment_fingerprint", "verification_fingerprint"],
)
def test_m4_23_rejects_tampered_fingerprints(field: str):
    data = _receipt()
    data[field] = "f" * 64

    with pytest.raises(IndependentPersistedIntegrationReadinessVerificationError):
        _verify(data)


def test_m4_23_rejects_naive_persistence_timestamp():
    data = _receipt()
    data["created_at"] = datetime(2026, 9, 22, 20, 2)

    with pytest.raises(IndependentPersistedIntegrationReadinessVerificationError):
        _verify(data)


def test_m4_23_rejects_future_assessment_verification_order():
    data = _receipt()
    data["assessment_checked_at"] = data["verified_at"] + timedelta(minutes=1)

    with pytest.raises(IndependentPersistedIntegrationReadinessVerificationError):
        _verify(data)


def test_m4_23_rejects_ready_receipt_with_blockers():
    data = _receipt()
    data["state"] = "ready"
    data["blockers"] = ()

    data["assessment_fingerprint"] = _assessment_fingerprint(data)
    data["verification_fingerprint"] = _verification_fingerprint(
        str(data["assessment_fingerprint"]),
        data["verified_at"],
    )
    data["blockers"] = ("unexpected-blocker",)

    with pytest.raises(IndependentPersistedIntegrationReadinessVerificationError):
        _verify(data)
