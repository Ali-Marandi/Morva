from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable


class SettlementBlockedError(RuntimeError):
    """Raised when an unresolved payment exception blocks settlement release."""


@dataclass(frozen=True, slots=True)
class PaymentBatch:
    """Provider-neutral payment batch identity and its payment-item members."""

    batch_id: str
    payment_item_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        batch_id = self.batch_id.strip()
        item_ids = tuple(item_id.strip() for item_id in self.payment_item_ids)
        if not batch_id:
            raise ValueError("batch_id is required")
        if not item_ids or any(not item_id for item_id in item_ids):
            raise ValueError("payment_item_ids must contain at least one non-empty id")
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("payment_item_ids must be unique")
        object.__setattr__(self, "batch_id", batch_id)
        object.__setattr__(self, "payment_item_ids", item_ids)


@dataclass(frozen=True, slots=True)
class SettlementDecision:
    """Deterministic release decision without invoking an external provider."""

    batch_id: str
    allowed: bool
    blocked_item_ids: tuple[str, ...]

    @property
    def reason(self) -> str:
        if self.allowed:
            return "no unresolved payment exceptions"
        return "unresolved payment exceptions block settlement"


def evaluate_batch_release(
    batch: PaymentBatch,
    *,
    release_is_allowed: Callable[[str], bool],
) -> SettlementDecision:
    """Evaluate every payment item before settlement; never performs settlement itself."""
    blocked = tuple(item_id for item_id in batch.payment_item_ids if not release_is_allowed(item_id))
    return SettlementDecision(batch.batch_id, not blocked, blocked)


def assert_batch_release_is_allowed(
    batch: PaymentBatch,
    *,
    release_is_allowed: Callable[[str], bool],
) -> SettlementDecision:
    """Fail closed when any member item still has an unresolved exception."""
    decision = evaluate_batch_release(batch, release_is_allowed=release_is_allowed)
    if not decision.allowed:
        raise SettlementBlockedError(
            f"settlement blocked for batch {batch.batch_id}: "
            f"unresolved exceptions on {','.join(decision.blocked_item_ids)}"
        )
    return decision


def blocked_payment_items(
    payment_item_ids: Iterable[str],
    *,
    release_is_allowed: Callable[[str], bool],
) -> tuple[str, ...]:
    """Return only blocked item ids while preserving deterministic input order."""
    return tuple(item_id.strip() for item_id in payment_item_ids if item_id.strip() and not release_is_allowed(item_id.strip()))
