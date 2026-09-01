# Morva — Mission Status

**Date:** 2026-09-01  
**Branch:** `p1-import-personnel-chain`  
**Position:** controlled validation / release-candidate engineering state; not certified for real payroll or payment.

## Canonical payroll lifecycle

`src/morva/payroll/lifecycle.py` is the sole source of truth for payroll status and transition rules:

`draft -> data_received -> calculating -> validating -> reviewed -> approved -> frozen -> exported -> submitted -> payment_confirmed -> reconciled`

`cancelled` is terminal. `src/morva/payroll/workflow.py` contains no implementation and only re-exports the canonical lifecycle for compatibility. A regression test asserts object identity between both modules.

## Mission controls implemented in code

- Direct caller-supplied authoritative payroll calculation endpoint disabled.
- PayrollRun is persisted and scoped to organization and period.
- Calculation is fail-closed unless an immutable source import, personnel snapshot, approved mapping and approved/published Rule Pack exist.
- Source imports carry batch identity, template version, SHA-256 and provenance metadata.
- Unmatched source records/components are quarantined rather than silently inferred.
- Personnel snapshot provenance and hashes are persisted.
- Payroll-line source provenance and mapping status are persisted.
- Rule Pack hash is bound to a PayrollRun when provided.
- Monetary arithmetic uses Decimal and explicit ISO currency code fields.
- Production configuration rejects SQLite, missing OIDC, disabled MFA, demo policies and unmanaged schema state.
- OIDC/JWT authentication is enforced at the API boundary.
- Organization scope and privileged MFA checks exist.
- Separation-of-duties checks are applied to lifecycle approvals.
- Persistent audit events and persistent chain head are implemented.
- External export remains fail-closed until an approved production adapter exists.
- CI runs PostgreSQL, migrations, Ruff, pytest, dependency audit and web build.

## Legal-rule safety

No legal rate, threshold, allowance, insurance treatment or pension treatment is promoted merely because it appears in a fixture, source report or research document. Rules lacking authoritative primary-source evidence and formal finance/legal approval remain `review_required` and cannot drive real payroll.

The current 1405 rule catalog therefore remains a validation input, not a production legal authority.

## Data lineage target

`source -> import batch -> import record -> master identity -> personnel snapshot -> approved component mapping -> payroll line -> payroll run -> validation -> review -> approval -> freeze -> external export -> acknowledgement -> payment confirmation -> reconciliation -> audit`

## Production certification blockers that cannot be honestly marked complete from repository code alone

1. Formal finance/legal approval of every active Rule Pack and every component's tax/insurance/pension/accounting treatment.
2. Authoritative real-world source samples and organization-specific reconciliation evidence.
3. Official SINA/accounting/treasury/bank/tax/insurance schemas, endpoints and credentials, followed by staging certification.
4. Full payment-batch implementation and bank settlement/reversal reconciliation.
5. Production encryption-at-rest, key management, backup/WAL/PITR and successful restore drills.
6. Target-scale load/concurrency/security/mutation/DR evidence.
7. Full master-data hierarchy and all required personnel/attendance/teaching/overtime/loan/deduction ledgers.
8. Complete employee self-service, reporting and operational UX.
9. Final CI success for the branch head and review of any resulting failures.

These are gates, not deferred claims. Morva remains fail-closed until the evidence exists.
