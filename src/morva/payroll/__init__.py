"""Morva payroll package exports.

The package intentionally uses lazy attribute resolution. This keeps concrete
payroll submodule imports acyclic while preserving the public top-level API.
"""

from importlib import import_module

_EXPORTS = {
    "CalculationMode": (".profiles", "CalculationMode"),
    "ComponentRule": (".profiles", "ComponentRule"),
    "ContributionPolicy": (".policies", "ContributionPolicy"),
    "EffectiveOrder": (".snapshot", "EffectiveOrder"),
    "EmployeeDiff": (".diff", "EmployeeDiff"),
    "LineDiff": (".diff", "LineDiff"),
    "PaymentBatch": (".payment_settlement", "PaymentBatch"),
    "PaymentException": (".payment_exceptions", "PaymentException"),
    "PaymentExceptionEvent": (".payment_exception_ledger", "PaymentExceptionEvent"),
    "PaymentExceptionStatus": (".payment_exceptions", "PaymentExceptionStatus"),
    "PaymentExceptionType": (".payment_exceptions", "PaymentExceptionType"),
    "PayrollCalculation": (".calculator", "PayrollCalculation"),
    "PayrollCalculationProfile": (".profiles", "PayrollCalculationProfile"),
    "PayrollCalculator": (".calculator", "PayrollCalculator"),
    "PayrollLine": (".models", "PayrollLine"),
    "PayrollResult": (".models", "PayrollResult"),
    "PayrollService": (".service", "PayrollService"),
    "PayrollSnapshot": (".snapshot", "PayrollSnapshot"),
    "PopulationReconciliation": (".reconciliation_engine", "PopulationReconciliation"),
    "RetroPeriod": (".retro", "RetroPeriod"),
    "RetroResult": (".retro", "RetroResult"),
    "RuleReadiness": (".profiles", "RuleReadiness"),
    "SettlementBlockedError": (".payment_settlement", "SettlementBlockedError"),
    "SettlementDecision": (".payment_settlement", "SettlementDecision"),
    "SourceReplay": (".source_replay", "SourceReplay"),
    "SourceReplayCalculator": (".source_replay", "SourceReplayCalculator"),
    "TaxBracket": (".policies", "TaxBracket"),
    "TaxPolicy": (".policies", "TaxPolicy"),
    "assert_batch_release_is_allowed": (".payment_settlement", "assert_batch_release_is_allowed"),
    "calculate_retroactive": (".retro", "calculate_retroactive"),
    "compare_snapshots": (".diff", "compare_snapshots"),
    "demo_iranian_policy_pack": (".policies", "demo_iranian_policy_pack"),
    "evaluate_batch_release": (".payment_settlement", "evaluate_batch_release"),
    "flatten_diffs": (".reconciliation_engine", "flatten_diffs"),
    "latest_effective_order": (".snapshot", "latest_effective_order"),
    "observed_source_profile": (".profiles", "observed_source_profile"),
    "population_component_totals": (".diff", "population_component_totals"),
    "record_resolution": (".payment_exception_ledger", "record_resolution"),
    "reconcile_population": (".reconciliation_engine", "reconcile_population"),
    "replay_many": (".source_replay", "replay_many"),
    "verify_event": (".payment_exception_ledger", "verify_event"),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str):
    try:
        module_name, attribute_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    value = getattr(import_module(module_name, __name__), attribute_name)
    globals()[name] = value
    return value
