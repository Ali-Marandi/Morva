# P0 Trust Boundary

## Purpose

Prevent caller-created payroll lines or legal treatments from becoming authoritative payroll results.

## Production rule

`POST /api/v1/payroll/calculate` is a development/test compatibility route only. In production it returns a conflict and requires a persisted, approved `PayrollRun` backed by an immutable employee payroll snapshot and an approved Rule Set.

## Authentication

Production configuration requires `MORVA_AUTH_MODE=oidc`. Header-based development principals are rejected in production. The OIDC/SSO verifier must be implemented at the deployment boundary before privileged routes are enabled.

## Durable PayrollRun lifecycle

```text
draft
 -> data_received
 -> calculated
 -> validated
 -> reviewed
 -> approved
 -> frozen
 -> exported
 -> submitted
 -> payment_confirmed
 -> reconciled
```

Every transition records actor, role, reason, correlation ID and version. The creator cannot approve the same run.

## Snapshot boundary

Employee payroll inputs are admitted only while a run is `draft` and are keyed by `(payroll_run_id, employee_no)`. Each snapshot stores a source-manifest hash and a canonical payload hash. Re-submitting the same payload is idempotent; a different payload for the same employee/run is rejected. Calculation verifies the stored hash and source provenance before reading payroll lines.

A persisted calculation also requires an explicit `RuleSetApprovalRecord(status="approved")` covering the run's population scope. No legal formula, tax rate, pension rate or insurance rate is inferred from an unapproved pack.

## Snapshot-driven endpoints

- `POST /api/v1/payroll-runs/{run_id}/snapshots` — admit one immutable employee snapshot.
- `POST /api/v1/payroll-runs/{run_id}/admit` — move the run from `draft` to `data_received` through the central lifecycle service.
- `POST /api/v1/payroll-runs/{run_id}/calculate/{employee_no}` — calculate only from the persisted snapshot, then move the run to `calculated` through the same lifecycle service.

## Remaining P0 blockers

Verified OIDC middleware, deployment-time DB privilege enforcement for append-only snapshots, full legal Rule Set execution, external integrations, authoritative samples, security acceptance and DR/PITR drills remain required before production payroll authorization.

`TODO: NEEDS-LEGAL-SOURCE` applies to any legal rule for which the authoritative source has not been imported and approved.
