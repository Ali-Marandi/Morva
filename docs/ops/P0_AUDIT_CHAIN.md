# P0 — Durable Audit Chain

Morva payroll state changes must be auditable after process restart and independently verifiable from PostgreSQL.

## Implemented

- `AuditEventRecord` stores sequence, actor, entity, correlation id, payload, previous hash, current hash, and timestamp.
- `AuditChainHeadRecord` stores the current sequence/hash tail and is locked during append transactions.
- `append_audit_event()` computes a canonical JSON representation and SHA-256 hash for every event.
- `verify_audit_chain()` replays the full ordered event stream and detects sequence gaps, broken links, hash tampering, or a mismatched persisted tail.
- Payroll-run creation and state transitions append durable audit events in the same transaction as the business mutation.

## Production migration

Apply `ops/sql/001_p0_audit_chain.sql` before deploying the application version that writes the audit head table. The migration refuses to create the unique sequence index when legacy duplicate sequence numbers exist.

## Integrity boundary

Audit events are append-only by application contract. The database role used by Morva production should not have ordinary UPDATE/DELETE rights on `audit_events`; operational repair must use a separately controlled break-glass procedure with independent review and evidence.
