from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from morva.runtime.authoritative_evidence_intake import (
    AuthoritativeEvidenceItem,
    build_registry,
)
from morva.runtime.masterdata_evidence_bridge import (
    MasterDataEvidenceBridgeError,
    build_master_data_evidence_binding,
)


NOW = datetime.fromisoformat("2026-09-22T12:00:00+00:00")
SHA = "a" * 64
ACCEPTANCE_ID = str(uuid4())


def _authority(**overrides):
    payload = {
        "intake_version": 1,
        "evidence_id": "MD-001",
        "source_type": "master_data",
        "source_uri": "https://authority.example/master-data/2026",
        "source_sha256": "b" * 64,
        "issuer": "authority",
        "population_scope": "teachers",
        "effective_from": "2026-01-01T00:00:00+00:00",
        "effective_to": "2027-01-01T00:00:00+00:00",
        "status": "accepted",
        "approved_by": "authority-approver",
        "approved_at": "2026-09-20T10:00:00+00:00",
        "expires_at": "2026-12-31T00:00:00+00:00",
    }
    payload.update(overrides)
    return AuthoritativeEvidenceItem(**payload)


def _record(**overrides):
    payload = {
        "id": ACCEPTANCE_ID,
        "status": "accepted",
        "submitted_by": "submitter",
        "accepted_by": "acceptance-confirmer",
        "accepted_at": NOW,
        "authority_confirmation_reference": "AUTH-CONF-001",
        "population_scope": "teachers",
        "dataset_sha256": "c" * 64,
        "evidence_sha256": "b" * 64,
        "evidence_fingerprint": "d" * 64,
        "integrity_snapshot_hash": "e" * 64,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


class _Session:
    def __init__(self, record):
        self.record = record

    def scalar(self, _query):
        return self.record


def test_binding_is_created_when_internal_and_external_hashes_match():
    record = _record()
    registry = build_registry((_authority(),), registered_at=NOW)
    session = _Session(record)
    binding = build_master_data_evidence_binding(
        session,
        registry,
        acceptance_id=ACCEPTANCE_ID,
        evidence_id="MD-001",
        bound_by="bridge-actor",
        bound_at=NOW,
    )
    assert binding.acceptance_id == ACCEPTANCE_ID
    assert binding.population_scope == "teachers"
    assert len(binding.fingerprint) == 64


def test_wrong_source_type_is_rejected():
    record = _record()
    registry = build_registry(
        (_authority(source_type="legal_rule"),),
        registered_at=NOW,
    )
    with pytest.raises(MasterDataEvidenceBridgeError, match="source type"):
        build_master_data_evidence_binding(
            _Session(record),
            registry,
            acceptance_id=ACCEPTANCE_ID,
            evidence_id="MD-001",
            bound_by="bridge-actor",
            bound_at=NOW,
        )


def test_hash_mismatch_is_rejected():
    record = _record()
    registry = build_registry(
        (_authority(source_sha256=SHA),),
        registered_at=NOW,
    )
    with pytest.raises(MasterDataEvidenceBridgeError, match="SHA-256"):
        build_master_data_evidence_binding(
            _Session(record),
            registry,
            acceptance_id=ACCEPTANCE_ID,
            evidence_id="MD-001",
            bound_by="bridge-actor",
            bound_at=NOW,
        )


def test_scope_mismatch_is_rejected():
    record = _record()
    registry = build_registry(
        (_authority(population_scope="school_support"),),
        registered_at=NOW,
    )
    with pytest.raises(MasterDataEvidenceBridgeError, match="scope"):
        build_master_data_evidence_binding(
            _Session(record),
            registry,
            acceptance_id=ACCEPTANCE_ID,
            evidence_id="MD-001",
            bound_by="bridge-actor",
            bound_at=NOW,
        )


def test_expired_external_evidence_is_rejected():
    record = _record()
    registry = build_registry(
        (_authority(expires_at="2026-09-21T23:59:59+00:00"),),
        registered_at=NOW,
    )
    with pytest.raises(MasterDataEvidenceBridgeError, match="expired"):
        build_master_data_evidence_binding(
            _Session(record),
            registry,
            acceptance_id=ACCEPTANCE_ID,
            evidence_id="MD-001",
            bound_by="bridge-actor",
            bound_at=NOW,
        )


def test_binding_actor_must_differ_from_internal_actors():
    record = _record()
    registry = build_registry((_authority(),), registered_at=NOW)
    with pytest.raises(MasterDataEvidenceBridgeError, match="differ"):
        build_master_data_evidence_binding(
            _Session(record),
            registry,
            acceptance_id=ACCEPTANCE_ID,
            evidence_id="MD-001",
            bound_by="submitter",
            bound_at=NOW,
        )
