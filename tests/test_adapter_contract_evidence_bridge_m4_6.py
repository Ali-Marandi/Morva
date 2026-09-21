from __future__ import annotations

from datetime import datetime

import pytest

from morva.runtime.authoritative_evidence_intake import (
    AuthoritativeEvidenceItem,
    build_registry,
)
from morva.runtime.official_adapter_evidence import AdapterEvidence
from morva.runtime.adapter_contract_evidence_bridge import (
    AdapterContractEvidenceBridgeError,
    build_adapter_contract_evidence_binding,
)

NOW = datetime.fromisoformat("2026-09-22T12:00:00+00:00")
SHA = "a" * 64


def _authority(**overrides):
    payload = {
        "intake_version": 1,
        "evidence_id": "ADAPTER-SINA-001",
        "source_type": "adapter_contract",
        "source_uri": "https://authority.example/contracts/sina",
        "source_sha256": SHA,
        "issuer": "adapter-authority",
        "population_scope": "enterprise",
        "effective_from": "2026-01-01T00:00:00+00:00",
        "effective_to": "2027-01-01T00:00:00+00:00",
        "status": "accepted",
        "approved_by": "contract-approver",
        "approved_at": "2026-09-20T10:00:00+00:00",
        "expires_at": "2026-12-31T00:00:00+00:00",
    }
    payload.update(overrides)
    return AuthoritativeEvidenceItem(**payload)


def _adapter(**overrides):
    payload = {
        "evidence_version": 1,
        "adapter": "sina",
        "provider": "provider-sina",
        "repository": "Ali-Marandi/Morva",
        "candidate_sha": "b" * 40,
        "schema_version": "v1",
        "contract_source": "https://authority.example/contracts/sina",
        "digest_sha256": SHA,
        "verified_at": "2026-09-21T10:00:00+00:00",
        "expires_at": "2026-12-31T00:00:00+00:00",
    }
    payload.update(overrides)
    return AdapterEvidence(**payload)


def _registry(item=None):
    return build_registry((item or _authority(),), registered_at=NOW)


def test_binding_accepts_matching_adapter_contract_evidence():
    binding = build_adapter_contract_evidence_binding(
        _adapter(),
        _registry(),
        authoritative_evidence_id="ADAPTER-SINA-001",
        bound_by="bridge-actor",
        bound_at=NOW,
    )
    assert binding.adapter == "sina"
    assert binding.authoritative_evidence_id == "ADAPTER-SINA-001"
    assert len(binding.fingerprint) == 64


def test_wrong_source_type_is_rejected():
    with pytest.raises(AdapterContractEvidenceBridgeError, match="source type"):
        build_adapter_contract_evidence_binding(
            _adapter(),
            _registry(_authority(source_type="master_data")),
            authoritative_evidence_id="ADAPTER-SINA-001",
            bound_by="bridge-actor",
            bound_at=NOW,
        )


def test_hash_mismatch_is_rejected():
    with pytest.raises(AdapterContractEvidenceBridgeError, match="digest"):
        build_adapter_contract_evidence_binding(
            _adapter(digest_sha256="c" * 64),
            _registry(),
            authoritative_evidence_id="ADAPTER-SINA-001",
            bound_by="bridge-actor",
            bound_at=NOW,
        )


def test_source_uri_mismatch_is_rejected():
    with pytest.raises(AdapterContractEvidenceBridgeError, match="source"):
        build_adapter_contract_evidence_binding(
            _adapter(contract_source="https://other.example/contracts/sina"),
            _registry(),
            authoritative_evidence_id="ADAPTER-SINA-001",
            bound_by="bridge-actor",
            bound_at=NOW,
        )


def test_future_approval_is_rejected():
    with pytest.raises(AdapterContractEvidenceBridgeError, match="future"):
        build_adapter_contract_evidence_binding(
            _adapter(),
            _registry(
                _authority(approved_at="2026-09-23T10:00:00+00:00")
            ),
            authoritative_evidence_id="ADAPTER-SINA-001",
            bound_by="bridge-actor",
            bound_at=NOW,
        )


def test_expired_authority_is_rejected():
    with pytest.raises(AdapterContractEvidenceBridgeError, match="expired"):
        build_adapter_contract_evidence_binding(
            _adapter(),
            _registry(
                _authority(expires_at="2026-09-21T23:59:59+00:00")
            ),
            authoritative_evidence_id="ADAPTER-SINA-001",
            bound_by="bridge-actor",
            bound_at=NOW,
        )


def test_missing_authority_id_is_rejected():
    with pytest.raises(AdapterContractEvidenceBridgeError, match="not present"):
        build_adapter_contract_evidence_binding(
            _adapter(),
            _registry(),
            authoritative_evidence_id="ADAPTER-BANK-001",
            bound_by="bridge-actor",
            bound_at=NOW,
        )


def test_future_effective_authority_is_rejected():
    with pytest.raises(AdapterContractEvidenceBridgeError, match="not yet"):
        build_adapter_contract_evidence_binding(
            _adapter(),
            _registry(
                _authority(
                    effective_from="2026-09-23T00:00:00+00:00",
                    effective_to="2027-01-01T00:00:00+00:00",
                )
            ),
            authoritative_evidence_id="ADAPTER-SINA-001",
            bound_by="bridge-actor",
            bound_at=NOW,
        )
