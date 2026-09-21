from __future__ import annotations

from datetime import datetime

import pytest

from morva.runtime.authoritative_evidence_intake import (
    AuthoritativeEvidenceItem,
    build_registry,
)
from morva.rules.population_treatment_evidence import (
    REQUIRED_1405_COMPONENTS,
    PopulationTreatmentEvidence,
    PopulationTreatmentEvidenceError,
    build_treatment_set,
)


NOW = datetime.fromisoformat("2026-09-22T10:00:00+00:00")
SHA = "a" * 64
REPOSITORY = "Ali-Marandi/Morva"


def _authority(evidence_id: str = "LEGAL-001", **overrides):
    payload = {
        "intake_version": 1,
        "evidence_id": evidence_id,
        "source_type": "legal_rule",
        "source_uri": "https://authority.example/legal/1405",
        "source_sha256": SHA,
        "issuer": "authority",
        "population_scope": "teachers",
        "effective_from": "2026-01-01T00:00:00+00:00",
        "effective_to": "2027-01-01T00:00:00+00:00",
        "status": "accepted",
        "approved_by": "legal-approver",
        "approved_at": "2026-09-20T00:00:00+00:00",
        "expires_at": "2026-12-31T00:00:00+00:00",
    }
    payload.update(overrides)
    return AuthoritativeEvidenceItem(**payload)


def _treatment(component_code: str, **overrides):
    payload = {
        "evidence_version": 1,
        "component_code": component_code,
        "population_scope": "teachers",
        "authoritative_evidence_id": "LEGAL-001",
        "treatment": "earning" if component_code != "TAX" else "deduction",
        "taxable": component_code in {"JOB_RIGHT", "OVERTIME"},
        "pensionable": component_code in {"JOB_RIGHT", "RANK_ALLOWANCE"},
        "insurable": component_code in {"JOB_RIGHT", "RANK_ALLOWANCE"},
        "reviewer_id": "reviewer",
        "approver_id": "approver",
        "reviewed_at": "2026-09-19T10:00:00+00:00",
        "approved_at": "2026-09-20T10:00:00+00:00",
        "status": "approved",
    }
    payload.update(overrides)
    return PopulationTreatmentEvidence(**payload)


def _registry(*items):
    return build_registry(tuple(items), registered_at=NOW)


def test_complete_1405_population_treatment_is_activation_ready():
    authority = _authority()
    registry = _registry(
        *[
            AuthoritativeEvidenceItem(
                **{
                    **authority.__dict__ if hasattr(authority, "__dict__") else {},
                }
            )
        ]
    )
