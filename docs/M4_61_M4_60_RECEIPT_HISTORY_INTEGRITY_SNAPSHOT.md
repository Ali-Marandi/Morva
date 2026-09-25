# M4.61 — M4.60 Receipt-History Integrity Snapshot

## Purpose

M4.61 captures deterministic point-in-time integrity snapshots over the complete persisted M4.60 independent verification receipt history.

## Contract

Capture re-verifies every M4.60 source receipt before building the canonical history identity. The snapshot is append-only and fingerprint-idempotent.

Later history listing and direct verification reconstruct only M4.60 receipts created before the snapshot timestamp, re-verify every source receipt, and compare the deterministic history and aggregate fingerprints.

## API surface

- Ministry-managed M4.60 receipt-history snapshot capture.
- Read-only ministry-managed cursor history with timestamp+UUID cursors.
- Direct snapshot verification against the point-in-time M4.60 receipt history.

## Safety boundary

M4.61 remains governance/readiness metadata only. It does not execute providers, use production credentials, calculate payroll, mutate payments, or grant production authorization.
