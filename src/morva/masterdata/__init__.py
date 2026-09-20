"""Master-data package exports.

Public results are resolved lazily so importing a concrete master-data
submodule does not eagerly import the full readiness/drift dependency graph.
"""

from importlib import import_module

_EXPORTS = {
    "MasterDataDriftResult": (".drift", "MasterDataDriftResult"),
    "MasterDataReadinessResult": (".readiness", "MasterDataReadinessResult"),
    "detect_master_data_drift": (".drift", "detect_master_data_drift"),
    "verify_master_data_readiness": (".readiness", "verify_master_data_readiness"),
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
