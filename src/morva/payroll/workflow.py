"""Compatibility module for the canonical payroll lifecycle.

There is exactly one payroll state-machine implementation in Morva:
:mod:`morva.payroll.lifecycle`. This module deliberately contains no status
enum and no transition table; it only preserves legacy imports.
"""

from .lifecycle import PayrollStatus, can_transition, transition

__all__ = ["PayrollStatus", "can_transition", "transition"]
