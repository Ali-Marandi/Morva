from datetime import date, datetime, timezone

import pytest

from morva.ledger.population_treatment import (
    PopulationScopedLedgerTreatment,
    PopulationTreatmentStatus,
)
from morva.ledger.treatments import LedgerComponent


FINGERPRINT = "a" * 64


def _treatment(**overrides: object) -> PopulationScopedLedgerTreatment:
    values = dict(
        component=LedgerComponent.TAX,
        population_id="public-teachers-1405",
        population_scope="ministry-teachers; active-assignment-snapshot",
        population_fingerprint=FINGERPRINT,
        rule_pack_version="1405.1",
        rule_pack_evidence_fingerprint=FINGERPRINT,
        source_id="TAX-1405",
        source_document_hash=FINGERPRINT,
        effective_from=date(2026, 3, 21),
        effective_to=None,
        retrieved_at=datetime(2026, 3, 22, 12, tzinfo=timezone.utc),
        reviewer_id="legal-reviewer",
        approver_id="finance-approver",
        regression_reference="regression://tax-1405/population-001",
        taxable=True,
        pensionable=True,
        insurable=True,
        status=PopulationTreatmentStatus.REVIEW_REQUIRED,
    )
    values.update(overrides)
    return PopulationScopedLedgerTreatment(**values)


def test_review_required_is_never_execution_ready():
    treatment = _treatment()

    treatment.validate()
    assert not treatment.execution_ready(
        expected_population_fingerprint=FINGERPRINT,
        expected_rule_pack_evidence_fingerprint=FINGERPRINT,
    )


def test_approved_requires_matching_population_and_rule_pack_evidence():
    treatment = _treatment(status=PopulationTreatmentStatus.APPROVED)

    assert treatment.execution_ready(
        expected_population_fingerprint=FINGERPRINT,
        expected_rule_pack_evidence_fingerprint=FINGERPRINT,
    )
    assert not treatment.execution_ready(
        expected_population_fingerprint="b" * 64,
        expected_rule_pack_evidence_fingerprint=FINGERPRINT,
    )
    assert not treatment.execution_ready(
        expected_population_fingerprint=FINGERPRINT,
        expected_rule_pack_evidence_fingerprint="b" * 64,
    )


def test_missing_immutable_scope_metadata_fails_closed():
    treatment = _treatment(population_scope=" ")

    with pytest.raises(ValueError, match="population_scope is required"):
        treatment.validate()
    assert not treatment.execution_ready(
        expected_population_fingerprint=FINGERPRINT,
        expected_rule_pack_evidence_fingerprint=FINGERPRINT,
    )


def test_invalid_hash_and_naive_timestamp_are_rejected():
    with pytest.raises(ValueError, match="source_document_hash"):
        _treatment(source_document_hash="short").validate()

    with pytest.raises(ValueError, match="retrieved_at must be timezone-aware"):
        _treatment(retrieved_at=datetime(2026, 3, 22, 12)).validate()


def test_reviewer_and_approver_must_be_distinct():
    with pytest.raises(ValueError, match="reviewer and approver must be distinct"):
        _treatment(reviewer_id="same", approver_id="same").validate()


def test_effective_period_must_be_ordered():
    with pytest.raises(ValueError, match="effective_to must not precede effective_from"):
        _treatment(
            effective_from=date(2026, 4, 1),
            effective_to=date(2026, 3, 31),
        ).validate()


def test_activation_fingerprint_is_deterministic_and_changes_on_binding_change():
    treatment = _treatment()
    first = treatment.activation_fingerprint()
    second = treatment.activation_fingerprint()

    assert first == second
    assert len(first) == 64
    assert first != _treatment(population_id="different-population").activation_fingerprint()
