from datetime import date, datetime

import pytest

from morva.rules.calendar_adapter import (
    CalendarAdapterContractError,
    CalendarDateResolution,
    resolve_case_effective_on,
)
from morva.rules.regression_cases import RegressionCase


def _case() -> RegressionCase:
    return RegressionCase(
        case_id="synthetic-calendar-case",
        rule_pack_version="TEST-CALENDAR-1",
        component_code="TEST_COMPONENT",
        population_scope="all",
        effective_date="1405-01-01",
        status="approved",
        input_values={},
        expected_output=None,
        input_fingerprint=None,
        expected_output_fingerprint=None,
        legal_source_hash=None,
        legal_article=None,
        legal_clause=None,
    )


def _resolution(**overrides: object) -> CalendarDateResolution:
    values: dict[str, object] = {
        "source_calendar": "jalali",
        "target_calendar": "gregorian",
        "source_value": "1405-01-01",
        "effective_on": date(2030, 6, 1),
        "adapter_id": "synthetic-test-adapter",
        "adapter_version": "test-1",
        "authority_reference": "synthetic-test-evidence",
        "evidence_sha256": "a" * 64,
        "approval_status": "approved",
        "reviewed_by": "synthetic-reviewer",
        "reviewed_at": datetime(2026, 1, 1, 10, 0, 0),
        "approved_by": "synthetic-approver",
        "approved_at": datetime(2026, 1, 2, 10, 0, 0),
    }
    values.update(overrides)
    return CalendarDateResolution(**values)


class _SyntheticAdapter:
    def __init__(self, resolution: CalendarDateResolution) -> None:
        self.resolution = resolution
        self.received_source_value: str | None = None

    def resolve_jalali_date(self, source_value: str) -> CalendarDateResolution:
        self.received_source_value = source_value
        return self.resolution


class _SyntheticVerifier:
    def __init__(self, result: bool = True) -> None:
        self.result = result
        self.calls = 0

    def verify(self, resolution: CalendarDateResolution) -> bool:
        self.calls += 1
        return self.result


def test_calendar_contract_passes_original_date_verbatim_to_injected_adapter():
    case = _case()
    adapter = _SyntheticAdapter(_resolution())
    verifier = _SyntheticVerifier()

    effective_on = resolve_case_effective_on(
        case,
        adapter=adapter,
        evidence_verifier=verifier,
    )

    assert adapter.received_source_value == "1405-01-01"
    assert effective_on == date(2030, 6, 1)
    assert verifier.calls == 1
    assert case.effective_date == "1405-01-01"


def test_calendar_contract_requires_an_independent_evidence_verifier():
    with pytest.raises(CalendarAdapterContractError, match="independent calendar evidence"):
        resolve_case_effective_on(
            _case(),
            adapter=_SyntheticAdapter(_resolution()),
            evidence_verifier=None,  # type: ignore[arg-type]
        )


def test_calendar_contract_rejects_unverified_evidence():
    with pytest.raises(CalendarAdapterContractError, match="not independently verified"):
        resolve_case_effective_on(
            _case(),
            adapter=_SyntheticAdapter(_resolution()),
            evidence_verifier=_SyntheticVerifier(False),
        )


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"source_calendar": "gregorian"}, "source must be jalali"),
        ({"target_calendar": "jalali"}, "target must be gregorian"),
        ({"source_value": "1405-1-1"}, "preserve the original source date"),
        ({"effective_on": datetime(2030, 6, 1)}, "date, not a datetime"),
        ({"effective_on": "2030-06-01"}, "date, not a datetime"),
        ({"adapter_id": ""}, "adapter_id is required"),
        ({"authority_reference": ""}, "authority_reference is required"),
        ({"evidence_sha256": "0" * 64}, "non-placeholder SHA-256"),
        ({"evidence_sha256": "not-a-hash"}, "non-placeholder SHA-256"),
        ({"approval_status": "review_required"}, "not approved/published"),
        ({"approval_status": []}, "not approved/published"),
        ({"approved_by": "synthetic-reviewer"}, "must be distinct"),
        ({"approved_at": datetime(2025, 12, 31)}, "cannot precede its review"),
    ],
)
def test_calendar_contract_rejects_invalid_or_unapproved_resolutions(changes, message):
    resolution = _resolution(**changes)

    with pytest.raises(CalendarAdapterContractError, match=message):
        resolve_case_effective_on(
            _case(),
            adapter=_SyntheticAdapter(resolution),
            evidence_verifier=_SyntheticVerifier(),
        )


def test_calendar_contract_rejects_non_calendar_adapter():
    with pytest.raises(CalendarAdapterContractError, match="explicit Jalali calendar adapter"):
        resolve_case_effective_on(
            _case(),
            adapter=object(),  # type: ignore[arg-type]
            evidence_verifier=_SyntheticVerifier(),
        )


def test_calendar_contract_rejects_non_golden_case_inputs():
    with pytest.raises(CalendarAdapterContractError, match="loaded RegressionCase"):
        resolve_case_effective_on(
            object(),  # type: ignore[arg-type]
            adapter=_SyntheticAdapter(_resolution()),
            evidence_verifier=_SyntheticVerifier(),
        )
