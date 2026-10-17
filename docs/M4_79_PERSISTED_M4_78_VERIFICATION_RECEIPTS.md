# M4.79 — Persisted M4.78 Independent Verification Receipts

M4.79 persists the independently reconstructed M4.78 result as an append-only, fingerprint-idempotent receipt bound to the exact M4.77 verification receipt that was independently checked.

## Integrity boundary
- The M4.77 source receipt is loaded from persistence before reconstruction.
- The bound M4.75 snapshot is structurally revalidated.
- Every M4.74 source receipt inside the snapshot time boundary is re-verified.
- M4.78 is reconstructed independently; the M4.77 persistence repository is not trusted as reconstruction authority.
- Persisted M4.79 records are structurally revalidated on read, list and direct verification.
- History uses deterministic created_at + UUID cursor ordering.

## API boundary
The M4.79 API is authenticated and ministry-scoped. It exposes create, history and direct verification operations. A valid M4.79 receipt proves only consistency of the persisted M4.78 verification result with fresh reconstruction; it is not a legal, payment or production authorization decision.

## Safety
Verification/readiness metadata only. No provider execution, credentials, payment mutation, legal-rate inference or production authorization is introduced.

## Failure-mode and pagination hardening
- Cursor pagination requires both `before_created_at` and `before_id`; supplying only one fails closed.
- The persistence path rechecks the fingerprint after a uniqueness race and reuses a receipt only for the same actor.
- The POST response is materialized before the SQLAlchemy session closes.
- The TestClient success-path regression uses a cross-thread-safe in-memory engine and a fresh request session.
