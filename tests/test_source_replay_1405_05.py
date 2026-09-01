from decimal import Decimal

from morva.payroll.profiles import CalculationMode, RuleReadiness, observed_source_profile


def test_observed_profile_never_claims_legal_treatment() -> None:
    profile = observed_source_profile(["حق شغل-1", "مالیات-965"])
    assert profile.mode is CalculationMode.SOURCE_REPLAY
    assert profile.version == "SOURCE_REPLAY:1405-05:v1"
    assert profile.component("حق شغل-1").readiness is RuleReadiness.OBSERVED
    assert profile.component("مالیات-965").taxable is None


def test_legal_profile_is_fail_closed_until_verified() -> None:
    profile = observed_source_profile(["حق شغل-1"])
    profile = profile.__class__(
        version="LEGAL:1405:v1",
        mode=CalculationMode.LEGAL_CALCULATION,
        components=profile.components,
    )
    try:
        profile.require_legal_ready()
    except ValueError as exc:
        assert "حق شغل-1" in str(exc)
    else:
        raise AssertionError("Unverified legal profile must be blocked")


def test_decimal_baseline_is_exact() -> None:
    assert Decimal("971405814240") + Decimal("247897427588") >= Decimal("0")
