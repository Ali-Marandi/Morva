from __future__ import annotations

from datetime import datetime, timezone

from morva.runtime.historical_integrity_primitives import (
    canonical_sha256,
    canonical_utc_timestamp,
)


def test_canonical_utc_timestamp_normalizes_timezone() -> None:
    value = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
    assert canonical_utc_timestamp(value) == "2026-09-29T12:00:00+00:00"


def test_canonical_sha256_is_key_order_independent() -> None:
    assert canonical_sha256({"b": 2, "a": 1}) == canonical_sha256(
        {"a": 1, "b": 2}
    )
