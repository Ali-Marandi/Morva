# P0 Trust Boundary

## Purpose

Prevent caller-created payroll lines or legal treatments from becoming authoritative payroll results.

## Production rule

`POST /api/v1/payroll/calculate` is a development/test compatibility route only. In production it returns a conflict and requires a persisted, approved `PayrollRun` backed by an effective employee snapshot and an approved Rule Pack.

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

## Remaining P0 blocker

Persistent immutable audit writes, verified OIDC middleware, and full snapshot-driven calculation execution still require completion before production payroll authorization.

`TODO: NEEDS-LEGAL-SOURCE` applies to any legal rule for which the authoritative source has not been imported and approved.
