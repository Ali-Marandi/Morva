# M4.78 — Independent M4.77 Verification

## Purpose

M4.78 independently verifies persisted M4.77 M4.76-verification receipts without using the M4.77 persistence repository as the reconstruction authority.

## Reconstruction boundary

The verifier validates the persisted M4.77 receipt structure and its bound M4.75 point-in-time snapshot. It independently reconstructs the timestamp-bounded M4.74 source receipt history, re-verifies each selected source receipt, and rebuilds the M4.76 verification result.

## Deterministic comparison

The verifier compares:

- M4.75 snapshot identity
- persisted and reconstructed M4.76 verification fingerprints
- persisted and reconstructed history fingerprints and counts
- valid state
- blocker sets
- M4.76 verification fingerprint

It emits deterministic M4.78 blocker codes for each mismatch.

## API and safety

M4.78 exposes an authenticated, ministry-scoped, read-only verification endpoint. It does not create credentials, execute providers, mutate payroll/payment state, infer legal rates or grant production authority.

## Validation

The dedicated CI gate runs Ruff, focused M4.78/M4.77 regression tests, Alembic upgrade validation and an explicit verification-only boundary assertion. Full repository CI remains the merge gate.
