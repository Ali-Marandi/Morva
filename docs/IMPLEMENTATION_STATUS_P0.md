# Morva — P0 Hardening Implementation Status

**Date:** 2026-09-01  
**Branch:** `p0-hardening`  
**Latest implementation commit at publication:** tracked by the branch head in GitHub.

## Completed in this stage

### Trust boundary

- Disabled `POST /api/v1/payroll/calculate` with HTTP 410.
- Added persisted `PayrollRun` creation and server-owned calculation entry point.
- Calculation now requires an approved/published Rule Pack and validates the Rule Pack hash when supplied.
- Payroll source lines must match the run currency.
- External export remains fail-closed until an approved production adapter exists.

### Lifecycle

The payroll state machine is unified around:

`draft -> data_received -> calculating -> validating -> reviewed -> approved -> frozen -> exported -> submitted -> payment_confirmed -> reconciled`

Terminal cancellation is retained. Approval cannot bypass review.

### Security

- Added OIDC/JWT bearer-token verification with issuer, audience, signature and required-claim validation.
- Protected all `/api/v1` routers with authenticated principal resolution.
- Added permission-oriented RBAC primitives and organization scope checks.
- Added MFA enforcement for privileged transitions.
- Added a separation-of-duties primitive and applied it to review/approval/freeze transitions.
- Unified the principal model used by authentication and policy layers.

### Audit

- Added persistent audit event storage.
- Added a persistent chain head to serialize sequence/hash updates.
- Persisted immutable event identifiers.
- Added chain verification.
- Business mutations and their corresponding audit events are committed in the same database transaction for the protected payroll-run operations.

### Database / operations

- Added PostgreSQL-oriented production validation.
- Added migration-managed production startup gate.
- Added Alembic baseline configuration and revision.
- Added explicit production environment variables for OIDC, migration readiness and demo-policy control.
- Production rejects SQLite, disabled MFA, missing OIDC configuration, demo policies and an unmanaged schema.

### Demo isolation / UI

- Demo payroll policy execution is disabled unless explicitly enabled in non-production.
- Demo policies cannot be enabled in production.
- Removed fabricated operational metrics and fake current-period status from the web dashboard.
- Added web build to CI.

### Tests / CI

Added or updated coverage for:

- legacy calculation route removal;
- persisted PayrollRun creation;
- unified lifecycle invariants;
- separation of duties and organization scope;
- production fail-closed configuration;
- persistent audit-chain round trip;
- Alembic migration execution;
- frontend build;
- dependency audit gate.

## What is intentionally not claimed

This stage does **not** certify Morva for real payroll or payment.

The following remain mandatory before any real production payroll decision:

1. authoritative legal-source import and formal finance/legal approval for every active Rule Pack;
2. master-data-driven payroll snapshots instead of direct source-line staging as the long-term authoritative calculation input;
3. complete import/quarantine workflow and authoritative source contracts;
4. complete SINA, accounting, treasury, bank, tax and insurance adapters with staging acknowledgements;
5. payment release controls and bank reconciliation;
6. encryption-at-rest/key management, operational secret management, backup/WAL/PITR and restore-drill evidence;
7. load, concurrency, security and disaster-recovery test evidence;
8. complete employee self-service, reports and operational UX.

## Verification state

GitHub Actions has been triggered for this branch. The web-build job has reached the build step successfully; the Python/PostgreSQL test jobs are still executing at the time this document was written. No green production-certification claim is made until the complete CI result is successful and the remaining production gates have formal evidence.
