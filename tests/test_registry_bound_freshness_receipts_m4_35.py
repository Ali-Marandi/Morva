from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from morva.persistence.models import Base
from morva.persistence.registry_bound_policy_readiness_freshness_records_m4_35 import (
    RegistryBoundPolicyReadinessFreshnessPersistenceError,
    RegistryBoundPolicyReadinessFreshnessRepository,
)
from morva.runtime.policy_bound_readiness_freshness_m4_29 import (
    build_policy_bound_freshness,
)
from morva.runtime.readiness_convergence_freshness_m4_28 import (
    ReadinessConvergenceFreshnessAssessment,
)
from morva.runtime.readiness_convergence_freshness_policy_m4_29 import (
    build_freshness_policy,
)
from morva.runtime.registry_bound_policy_readiness_freshness_m4_34 import (
    build_registry_bound_policy_readiness_freshness,
)


NOW = datetime(2026, 9, 24, 0, 0, tzinfo=timezone.utc)


def _assessment(observed_at: datetime, convergence_fingerprint: str) -> ReadinessConvergenceFreshnessAssessment:
    policy = build_freshness_policy(
        policy_id="integration-staging-v1",
        policy_version=1,
        max_age_seconds=3600,
    )
    checked_at = NOW - timedelta(minutes=5)
    age_seconds = max(
        int((observed_at - checked_at).total_seconds()),
        0,
    )
    blockers = ()
    state = "fresh"
    fingerprint = _fingerprint(
        convergence_fingerprint=convergence_fingerprint,
        checked_at=checked_at,
        observed_at=observed_at,
        max_age_seconds=policy.max_age_seconds,
        age_seconds=age_seconds,
        state=state,
        blockers=blockers,
    )
    return ReadinessConvergenceFreshnessAssessment(
        freshness_version=1,
        convergence_fingerprint=convergence_fingerprint,
        checked_at=checked_at,
        observed_at=observed_at,
        max_age_seconds=policy.max_age_seconds,
        age_seconds=age_seconds,
        state=state,
        blockers=blockers,
        fingerprint=fingerprint,
    )


def _fingerprint(
    *,
    convergence_fingerprint: str,
    checked_at: datetime,
    observed_at: datetime,
    max_age_seconds: int,
    age_seconds: int,
    state: str,
    blockers: tuple[str, ...],
) -> str:
    import hashlib
    import json

    payload = {
        "freshness_version": 1,
        "convergence_fingerprint": convergence_fingerprint.lower(),
        "checked_at": checked_at.astimezone(timezone.utc).isoformat(),
        "observed_at": observed_at.astimezone(timezone.utc).isoformat(),
        "max_age_seconds": max_age_seconds,
        "age_seconds": age_seconds,
        "state": state,
        "blockers": list(blockers),
    }
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _freshness(observed_at: datetime, convergence_fingerprint: str, registry_fingerprint: str):
    policy = build_freshness_policy(
        policy_id="integration-staging-v1",
        policy_version=1,
        max_age_seconds=3600,
    )
    assessment = _assessment(observed_at, convergence_fingerprint)
    policy_bound = build_policy_bound_freshness(
        policy,
        type(
            "Convergence",
            (),
            {
                "fingerprint": convergence_fingerprint,
                "checked_at": assessment.checked_at,
                "state": "converged",
            },
        )(),
        observed_at=observed_at,
    )
    return build_registry_bound_policy_readiness_freshness(
        policy_bound,
        registry_integrity_version=1,
        registry_policy_count=1,
        registry_fingerprint=registry_fingerprint,
    )


def test_m4_35_receipt_round_trip_and_idempotency():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        repository = RegistryBoundPolicyReadinessFreshnessRepository(session)
        freshness = _freshness(
            NOW,
            "a" * 64,
            "b" * 64,
        )
        first = repository.record(
            repository="Ali-Marandi/Morva",
            candidate_sha="c" * 40,
            target_environment="staging",
            organization_scope="district",
            organization_scope_id="district-1",
            freshness=freshness,
            recorded_by="ministry-user",
        )
        second = repository.record(
            repository="Ali-Marandi/Morva",
            candidate_sha="c" * 40,
            target_environment="staging",
            organization_scope="district",
            organization_scope_id="district-1",
            freshness=freshness,
            recorded_by="ministry-user",
        )
        session.commit()

        assert first.id == second.id
        assert second.to_freshness().fingerprint == freshness.fingerprint

        records, has_more = repository.list(
            organization_scope="district",
            organization_scope_id="district-1",
            limit=1,
        )
        assert has_more is False
        assert len(records) == 1
        assert records[0].to_freshness().to_payload()["registry"]["fingerprint"] == "b" * 64


def test_m4_35_receipt_rejects_different_actor_for_same_binding():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        repository = RegistryBoundPolicyReadinessFreshnessRepository(session)
        freshness = _freshness(
            NOW,
            "d" * 64,
            "e" * 64,
        )
        repository.record(
            repository="Ali-Marandi/Morva",
            candidate_sha="f" * 40,
            target_environment="pilot",
            organization_scope="province",
            organization_scope_id="province-1",
            freshness=freshness,
            recorded_by="first-actor",
        )
        try:
            repository.record(
                repository="Ali-Marandi/Morva",
                candidate_sha="f" * 40,
                target_environment="pilot",
                organization_scope="province",
                organization_scope_id="province-1",
                freshness=freshness,
                recorded_by="second-actor",
            )
        except RegistryBoundPolicyReadinessFreshnessPersistenceError as exc:
            assert "different actor" in str(exc)
        else:
            raise AssertionError("expected actor mismatch rejection")


def test_m4_35_openapi_receipt_contracts_are_registered():
    from morva.api.app import app

    paths = app.openapi()["paths"]
    post_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-bound-integrity/receipts"
    )
    history_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-bound-integrity/receipts"
    )
    assert post_path in paths
    assert history_path in paths
    assert (
        paths[post_path]["post"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]["$ref"]
        == "#/components/schemas/RegistryBoundPolicyReadinessFreshnessReceiptResponse"
    )
    history_params = {
        parameter["name"] for parameter in paths[history_path]["get"]["parameters"]
    }
    assert {
        "candidate_sha",
        "target_environment",
        "organization_scope",
        "organization_scope_id",
        "before_created_at",
        "before_id",
        "limit",
    } <= history_params
