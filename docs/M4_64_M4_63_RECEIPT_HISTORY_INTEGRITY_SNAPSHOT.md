# M4.64 — M4.63 Receipt-History Integrity Snapshot

## Purpose

M4.64 captures deterministic point-in-time integrity snapshots over the complete persisted M4.63 independent verification receipt history.

## Contract

Capture verifies every M4.63 receipt first, then builds a canonical history identity containing the complete verification result, actor and timestamp. The snapshot is append-only and fingerprint-idempotent.

Later history listing and direct verification reconstruct only M4.63 receipts created before the snapshot timestamp, re-verify every source receipt, and compare deterministic history and aggregate fingerprints.

## API surface

- Ministry-managed snapshot capture over M4.63 verification receipts.
- Read-only ministry-managed cursor history with timestamp+UUID cursors.
- Direct snapshot verification against the point-in-time M4.63 receipt history.

## Safety boundary

M4.64 remains governance/readiness metadata only. It does not execute providers, use production credentials, calculate payroll, mutate payments, or grant production authorization.
