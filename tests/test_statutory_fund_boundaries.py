from __future__ import annotations

import pytest

from morva.integrations.ports import IntegrationPayload
from morva.integrations.statutory_funds import (
    FailClosedStatutoryFundAdapter,
    StatutoryFund,
    StatutoryFundIntegrationNotConfigured,
    StatutoryFundTreatment,
    StatutoryFundTreatmentCatalog,
)


def test_fund_treatment_catalog_cannot_mix_providers() -> None:
    treatment = StatutoryFundTreatment(
        fund=StatutoryFund.SOCIAL_SECURITY,
        component_code="INSURANCE",
        source="synthetic-source",
        reference="synthetic-ref",
        effective_from="1405-01",
    )
    with pytest.raises(ValueError, match="different statutory fund"):
        StatutoryFundTreatmentCatalog(
            fund=StatutoryFund.CENTRAL_CIVIL_SERVANTS_PENSION,
            treatments=(treatment,),
        )


def test_fund_treatment_catalog_is_independent_and_fail_closed_until_approved() -> None:
    pension = StatutoryFundTreatmentCatalog(
        fund=StatutoryFund.CENTRAL_CIVIL_SERVANTS_PENSION,
        treatments=(
            StatutoryFundTreatment(
                fund=StatutoryFund.CENTRAL_CIVIL_SERVANTS_PENSION,
                component_code="PENSION",
                source="synthetic-source",
                reference="synthetic-ref",
                effective_from="1405-01",
            ),
        ),
    )
    social = StatutoryFundTreatmentCatalog(
        fund=StatutoryFund.SOCIAL_SECURITY,
        treatments=(
            StatutoryFundTreatment(
                fund=StatutoryFund.SOCIAL_SECURITY,
                component_code="INSURANCE",
                source="synthetic-source",
                reference="synthetic-ref",
                effective_from="1405-01",
            ),
        ),
    )

    assert pension.execution_ready("PENSION") is False
    assert social.execution_ready("INSURANCE") is False
    assert pension.fund is not social.fund


def test_fail_closed_adapter_never_executes_external_submission() -> None:
    adapter = FailClosedStatutoryFundAdapter(StatutoryFund.SOCIAL_SECURITY)
    payload = IntegrationPayload(
        operation="submit-contribution",
        correlation_id="test-correlation",
        idempotency_key="test-idempotency",
        body={"amount": "100"},
    )

    with pytest.raises(StatutoryFundIntegrationNotConfigured, match="social_security"):
        adapter.submit_contribution(payload)

    assert adapter.health() is False
