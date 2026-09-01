# Morva — P0/P1 Implementation Status

**Date:** 2026-09-01  
**Branch:** `p1-import-personnel-chain`  
**Status:** hardening implementation branch; not certified for real payroll/payment.

## Completed implementation

### Trust boundary

- Disabled `POST /api/v1/payroll/calculate` with HTTP 410.
- Added persisted `PayrollRun` creation and server-owned calculation entry point.
- Calculation requires an approved/published Rule Pack, immutable source import, personnel snapshot, approved payroll-line mappings and matching currency.
- External export remains fail-closed until an approved production adapter exists.

### Canonical payroll lifecycle

There is now exactly one state-machine implementation in `src/morva/payroll/lifecycle.py`:

`draft -> data_received -> calculating -> validating -> reviewed -> approved -> frozen -> exported -> submitted -> payment_confirmed -> reconciled`

`cancelled` is terminal. `src/morva/payroll/workflow.py` is compatibility-only and re-exports the canonical implementation; it contains no independent state enum or transition table.

The API now cannot jump directly from `draft` to `calculating`; validated source projection advances the run to `data_received`, and calculation can begin only from that state.

### Security

- OIDC/JWT bearer-token verification with issuer/audience/signature/required-claim validation.
- Authenticated principal resolution at the API boundary.
- Permission-oriented RBAC primitives with organization-scope checks.
- MFA enforcement for privileged transitions.
- Separation-of-duties checks for review/approval/freeze transitions.

### Audit

- Persistent audit-event storage.
- Persistent chain head and sequence/hash continuity.
- Immutable event identifiers.
- Verification support.
- Payroll-run mutations and audit events are committed within the same transaction where implemented.

### Database / operations

- PostgreSQL production guard.
- Migration-managed production startup gate.
- Alembic revisions for baseline and P1 provenance structures.
- Production rejects SQLite, disabled MFA, missing OIDC configuration, demo policies and unmanaged schema state.

### Import / data lineage

- `ImportBatch` manifest/provenance/checksum contract.
- Durable `ImportRecord` source layer.
- `EmployeeRecord.source_employee_key` mapping.
- Immutable per-period `PersonnelSnapshot` foundation.
- Source projection into payroll lines with explicit provenance.
- Unmapped components and missing master data are quarantined.
- Unreviewed mappings remain `review_required` and cannot be calculated.
- Jalali period keys remain textual/canonical; no accidental Gregorian coercion.

## Tests and CI

Coverage added or aligned for:

- canonical lifecycle and invalid transitions;
- import provenance and checksum behavior;
- quarantine/fail-closed projection;
- source-to-payroll lineage;
- persistent PayrollRun controls;
- security/SoD invariants;
- Alembic migration execution;
- dependency audit and frontend build.

## Remaining mandatory production gates

These are not safely completable by code alone and therefore remain explicit gates:

1. Primary-source legal evidence and formal finance/legal approval for every active Rule Pack.
2. Complete authoritative Master Data hierarchy and source contracts for the employing organization.
3. Full tax, pension, insurance, loan and judicial-deduction policy implementations with approved legal treatment.
4. Durable employee-level payroll result/payslip artifacts and historical replay evidence.
5. Complete SINA, accounting, treasury, bank, tax and insurance adapters using official schemas/credentials, staging acknowledgements and idempotency tests.
6. Payment release and bank reconciliation controls.
7. Encryption-at-rest, production key management, secret management and rotation.
8. Backup/WAL/PITR restore evidence and disaster-recovery drills.
9. Load, concurrency, mutation and security test evidence at target population scale.
10. Complete enterprise operational UX/self-service/reporting.

**Safety rule:** none of the above gates is implied to be passed merely because an interface, fixture, runbook or adapter contract exists. Morva must remain fail-closed until evidence exists.
