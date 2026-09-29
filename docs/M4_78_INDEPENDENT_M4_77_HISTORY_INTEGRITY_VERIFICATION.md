# M4.78 — Independent M4.77 History-Integrity Verification

## Purpose

M4.78 independently verifies persisted M4.77 point-in-time integrity snapshots without invoking the M4.77 snapshot builder or trusting its persistence repository for reconstruction.

## Source boundary

The verifier reads the persisted M4.77 snapshot as the claimed source-of-truth values, then independently reconstructs the point-in-time M4.76 result history whose creation timestamp is earlier than the snapshot timestamp. Each M4.76 record is structurally validated directly.

## Deterministic comparisons

The verifier independently calculates the complete history SHA-256 fingerprint, source record count, valid source record count and the aggregate M4.77 integrity fingerprint.

It emits deterministic blockers:

- M477_HISTORY_FINGERPRINT_MISMATCH
- M477_RECORD_COUNT_MISMATCH
- M477_VALID_COUNT_MISMATCH
- M477_INTEGRITY_FINGERPRINT_MISMATCH

A deterministic verification fingerprint binds the snapshot identity, persisted/reconstructed identity values, validity and blocker set.

## API and safety

M4.78 exposes an authenticated read-only verification endpoint for ministry-managed integrity snapshots. The feature is verification/readiness metadata only and does not execute providers, introduce credentials, mutate payroll/payment state or grant production authority.
