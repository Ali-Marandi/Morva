from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from morva.api.app import app
from morva.persistence.database import init_db
from morva.security.auth import get_current_principal
from morva.security.policy import Principal, Scope


def _principal(user_id: str) -> Principal:
    return Principal(user_id=user_id, role="admin", scope=Scope.MINISTRY, scope_id="ministry", mfa_verified=True)


def _use(user_id: str) -> None:
    app.dependency_overrides[get_current_principal] = lambda: _principal(user_id)


@pytest.fixture(autouse=True)
def _principal_override() -> None:
    _use("legal-admin")
    yield
    app.dependency_overrides.pop(get_current_principal, None)


client = TestClient(app)
init_db()


def test_rule_governance_is_fail_closed_until_full_approval_chain():
    suffix = uuid4().hex[:8]
    source_hash = "a" * 64
    regression_hash = "b" * 64
    pack_version = f"fixture-{suffix}"

    source = client.post(
        "/api/v1/rule-governance/legal-sources",
        json={
            "citation": f"FIXTURE-SOURCE-{suffix}",
            "issuer": "FIXTURE-ISSUER",
            "adoption_date": "2026-01-01",
            "effective_from": "2026-01-01",
            "document_hash": source_hash,
            "source_uri": "fixture://not-a-real-legal-source",
        },
    )
    assert source.status_code == 201
    source_id = source.json()["id"]

    _use("reviewer-1")
    assert client.post(f"/api/v1/rule-governance/legal-sources/{source_id}/review").status_code == 200
    _use("approver-1")
    assert client.post(f"/api/v1/rule-governance/legal-sources/{source_id}/approve").status_code == 200

    _use("legal-admin")
    pack = client.post("/api/v1/rule-governance/packs", json={"version": pack_version, "effective_from": "2026-01-01"})
    assert pack.status_code == 201

    _use("pack-reviewer")
    assert client.post(f"/api/v1/rule-governance/packs/{pack_version}/review").status_code == 200
    _use("pack-approver")
    blocked = client.post(f"/api/v1/rule-governance/packs/{pack_version}/approve")
    assert blocked.status_code == 409

    _use("legal-admin")
    evidence = client.post(
        "/api/v1/rule-governance/evidence",
        json={
            "rule_pack_version": pack_version,
            "component_code": f"FIXTURE-COMPONENT-{suffix}",
            "legal_source_id": source_id,
            "issuer": "FIXTURE-ISSUER",
            "article": "FIXTURE-ARTICLE",
            "population_scope": "fixture-population",
            "source_hash": source_hash,
            "regression_suite_hash": regression_hash,
        },
    )
    assert evidence.status_code == 201
    evidence_id = evidence.json()["id"]

    _use("evidence-reviewer")
    assert client.post(f"/api/v1/rule-governance/evidence/{evidence_id}/review").status_code == 200
    _use("evidence-approver")
    assert client.post(f"/api/v1/rule-governance/evidence/{evidence_id}/approve").status_code == 200

    _use("pack-approver")
    approved = client.post(f"/api/v1/rule-governance/packs/{pack_version}/approve")
    assert approved.status_code == 200
    ready = client.get(f"/api/v1/rule-governance/packs/{pack_version}/readiness")
    assert ready.status_code == 200
    assert ready.json()["ready"] is True


def test_rule_governance_rejects_source_hash_mismatch():
    suffix = uuid4().hex[:8]
    source = client.post(
        "/api/v1/rule-governance/legal-sources",
        json={
            "citation": f"FIXTURE-SOURCE-{suffix}",
            "issuer": "FIXTURE-ISSUER",
            "adoption_date": "2026-01-01",
            "effective_from": "2026-01-01",
            "document_hash": "c" * 64,
        },
    )
    assert source.status_code == 201
    source_id = source.json()["id"]
    _use("reviewer-x")
    assert client.post(f"/api/v1/rule-governance/legal-sources/{source_id}/review").status_code == 200
    _use("approver-x")
    assert client.post(f"/api/v1/rule-governance/legal-sources/{source_id}/approve").status_code == 200
    _use("legal-admin")
    pack = client.post("/api/v1/rule-governance/packs", json={"version": f"fixture-{suffix}"})
    assert pack.status_code == 201
    response = client.post(
        "/api/v1/rule-governance/evidence",
        json={
            "rule_pack_version": f"fixture-{suffix}",
            "component_code": "FIXTURE-COMPONENT",
            "legal_source_id": source_id,
            "issuer": "FIXTURE-ISSUER",
            "article": "FIXTURE-ARTICLE",
            "population_scope": "fixture-population",
            "source_hash": "d" * 64,
            "regression_suite_hash": "e" * 64,
        },
    )
    assert response.status_code == 409
