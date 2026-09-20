"""Morva persistence models and database services.

Exports are loaded lazily to avoid package-import cycles between audit,
persistence, payroll and master-data modules.
"""

from importlib import import_module

_EXPORTS = {
    "PaymentExceptionEventRecord": (".payment_exception_records", "PaymentExceptionEventRecord"),
    "PaymentExceptionRecord": (".payment_exception_records", "PaymentExceptionRecord"),
    "PaymentExceptionRepository": (".payment_exception_records", "PaymentExceptionRepository"),
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
