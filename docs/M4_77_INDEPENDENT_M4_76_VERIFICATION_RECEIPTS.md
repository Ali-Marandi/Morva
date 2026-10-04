# M4.77 — Independent M4.76 Verification Receipt Persistence

## Purpose

M4.77 persists the independent M4.76 verification result for each M4.75 point-in-time integrity snapshot as an append-only, fingerprint-idempotent receipt.

## Integrity source chain

Each receipt binds to an exact M4.75 snapshot. Recording reconstructs M4.76 from the snapshot timestamp boundary and re-verifies every selected M4.74 source receipt before persistence.

## Stored identity

The receipt stores the persisted and independently reconstructed M4.75 fingerprints, history fingerprints, record counts, valid counts, validity, blocker codes and the M4.76 verification fingerprint.

## Persistence semantics

- Duplicate verification fingerprints are idempotent for the same actor.
- Reuse by a different actor fails closed.
- History is ministry-managed and cursor-paginated by timestamp + UUID.
- Listing and direct verification re-run source reconstruction before returning a persisted receipt.
- Tampered source receipts, snapshots or persisted receipt payloads fail closed.

## API

- POST/GET on the m4-75-verification-receipt-history-integrity-snapshots/{snapshot_id}/verification-receipts path.
- GET on the same path with /{verification_receipt_id}/verify for direct verification.

## Safety boundary

Verification/readiness metadata only. No provider execution, credentials, payment mutation, legal-rate inference or production authorization.
