# M4.52 — Independent Receipt-History Verification Persistence

## Purpose

M4.52 persists the deterministic M4.51 independent verification result for each M4.50 receipt-history integrity snapshot.

## Contract

The persistence layer stores the complete M4.51 result as an append-only record keyed by its verification fingerprint. Before recording or verifying a receipt, it re-verifies the M4.50 snapshot, reconstructs the point-in-time M4.49 receipt history, re-verifies every source receipt, and invokes the M4.51 independent verifier.

History is newest-first with timestamp+UUID cursor pagination. A previously recorded verification fingerprint is idempotent for the same actor and rejected for a different actor.

## API surface

- Ministry-managed write of an M4.51 verification receipt for an M4.50 snapshot.
- Read-only, ministry-managed receipt-history listing with optional snapshot/valid filters.
- Direct receipt verification against the current M4.50 snapshot and reconstructed M4.49 source history.

## Safety boundary

M4.52 remains governance/readiness metadata only. It does not execute providers, use production credentials, calculate payroll, mutate payments, or grant production authorization.
