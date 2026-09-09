import pytest

from morva.ledger.treatments import (
    REQUIRED_LEDGER_COMPONENTS,
    LedgerComponent,
    LedgerTreatment,
    LedgerTreatmentCatalog,
    TreatmentStatus,
)


def _review_required(component: LedgerComponent) -> LedgerTreatment:
    return LedgerTreatment(
        component=component,
        taxable=False,
        pensionable=False,
        insurable=False,
        source="TODO: NEEDS-LEGAL-SOURCE",
        reference="TODO: NEEDS-LEGAL-SOURCE",
        effective_from="1405-01-01",
    )


def test_catalog_requires_all_five_ledger_components_to_be_explicitly_representable():
    catalog = LedgerTreatmentCatalog(tuple(_review_required(component) for component in REQUIRED_LEDGER_COMPONENTS))

    assert {item.component for item in catalog.treatments} == set(REQUIRED_LEDGER_COMPONENTS)
    assert not any(catalog.execution_ready(component) for component in REQUIRED_LEDGER_COMPONENTS)


def test_review_required_treatment_is_fail_closed():
    treatment = _review_required(LedgerComponent.TAX)

    treatment.validate()
    with pytest.raises(RuntimeError, match="not approved; execution remains fail-closed"):
        treatment.assert_approved()


def test_approved_treatment_requires_independent_review_approval_and_regression_evidence():
    with pytest.raises(ValueError, match="approved treatment requires reviewer"):
        LedgerTreatment(
            component=LedgerComponent.PENSION,
            taxable=False,
            pensionable=True,
            insurable=True,
            source="primary-source",
            reference="article-1",
            effective_from="1405-01-01",
            status=TreatmentStatus.APPROVED,
            approver="finance",
            regression_suite_hash="sha256:test",
        ).validate()

    with pytest.raises(ValueError, match="reviewer and approver must be distinct"):
        LedgerTreatment(
            component=LedgerComponent.PENSION,
            taxable=False,
            pensionable=True,
            insurable=True,
            source="primary-source",
            reference="article-1",
            effective_from="1405-01-01",
            status=TreatmentStatus.APPROVED,
            reviewer="same-user",
            approver="same-user",
            regression_suite_hash="sha256:test",
        ).validate()

    with pytest.raises(ValueError, match="approved treatment requires regression_suite_hash"):
        LedgerTreatment(
            component=LedgerComponent.INSURANCE,
            taxable=False,
            pensionable=False,
            insurable=True,
            source="primary-source",
            reference="article-1",
            effective_from="1405-01-01",
            status=TreatmentStatus.APPROVED,
            reviewer="legal",
            approver="finance",
        ).validate()


def test_approved_treatment_can_be_execution_ready_only_with_explicit_evidence():
    treatment = LedgerTreatment(
        component=LedgerComponent.LOAN,
        taxable=False,
        pensionable=False,
        insurable=False,
        source="primary-source",
        reference="loan-policy-1",
        effective_from="1405-01-01",
        status=TreatmentStatus.APPROVED,
        reviewer="legal",
        approver="finance",
        regression_suite_hash="sha256:test",
    )
    catalog = LedgerTreatmentCatalog((treatment,))

    assert catalog.execution_ready(LedgerComponent.LOAN)
    treatment.assert_approved()


def test_catalog_rejects_duplicate_components():
    treatment = _review_required(LedgerComponent.COURT_ORDER)

    with pytest.raises(ValueError, match="duplicate treatment"):
        LedgerTreatmentCatalog((treatment, treatment))
