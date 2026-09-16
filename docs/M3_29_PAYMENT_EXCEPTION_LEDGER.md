# M3.29 — Payment Exception Resolution Ledger

## Scope

M3.29 adds a provider-neutral software boundary for recording resolution evidence for payment exceptions created by M3.28.

The tranche covers:

- immutable resolution-event records;
- explicit actor, reason and evidence requirements;
- timezone-aware event timestamps;
- deterministic SHA-256 event fingerprints;
- tamper verification;
- rejection of second resolution events for already-resolved exceptions;
- dedicated CI regression coverage.

## Safety boundary

This tranche does **not** define bank/Treasury APIs, provider-specific return codes, retry schedules, statutory amounts, settlement rules or real payment authority. Those remain blocked until authoritative contracts and operational evidence are available.

## Release behavior

M3.29 is a ledger/provenance foundation. It does not by itself authorize payment release. Existing M3.28 fail-closed exception handling and M3.27 three-way reconciliation remain mandatory release boundaries.
