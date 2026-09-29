# M4.77 — M4.76 Verification-Result History Integrity

## Purpose

M4.77 captures a deterministic point-in-time integrity snapshot over the complete persisted M4.76 independent-verification result history.

## Source boundary

Each source result is re-verified through the M4.76 persistence repository before it participates in a snapshot. The snapshot therefore binds to the exact persisted M4.76 state visible at the capture timestamp.

## Deterministic identity

The history fingerprint canonicalizes every source result in timestamp/UUID order and includes:

- M4.75 verification receipt identity;
- persisted and independently reconstructed fingerprints;
- persisted and reconstructed M4.72 snapshot identities;
- persisted/reconstructed validity;
- deterministic blocker list;
- M4.75 verification fingerprint;
- recording actor and creation timestamp.

The aggregate snapshot fingerprint binds the integrity version, source record count, valid count and history fingerprint using SHA-256.

## Persistence and verification

Snapshots are append-only and fingerprint-idempotent. Re-capturing an identical history returns the existing snapshot for the same actor and rejects a different actor attempting to claim the same fingerprint. Listing and direct verification re-verify the complete point-in-time source history before returning a snapshot.

## API

The authenticated ministry-managed endpoints provide snapshot capture, cursor-paginated history and direct verification.

## Safety boundary

M4.77 is verification/readiness metadata only. It does not execute providers, introduce credentials, mutate payroll/payment state or grant production authority.
