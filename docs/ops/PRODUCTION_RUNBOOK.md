# Morva Production Runbook

## Security
- TLS is mandatory at every external boundary.
- MFA is required for privileged roles.
- RBAC is scoped by organization hierarchy.
- Separation of duties blocks self-approval and payment release by the actor who prepared the batch.
- Secrets are environment-managed; no credentials belong in Git.
- Sensitive payloads must be encrypted at rest and access logged.
- Production rule activation requires legal + finance review and regression evidence.

## Payroll release gate
1. Freeze the personnel snapshot.
2. Calculate the payroll run.
3. Run validation and anomaly checks.
4. Resolve all critical findings.
5. Obtain independent approval.
6. Freeze the payroll fingerprint.
7. Export through approved adapters.
8. Reconcile external totals.
9. Release payment only after reconciliation passes.
10. Archive the immutable evidence bundle.

## Backup / PITR
PostgreSQL must run with WAL archiving and point-in-time recovery enabled. Maintain encrypted daily full backups and continuous WAL shipping. Perform restore drills at least quarterly and retain a documented RPO/RTO result.

## Disaster Recovery
- Primary and recovery environments are isolated.
- Rule packs and application artifacts are versioned independently of database backups.
- Recovery validation must include an application health check, database integrity check, payroll fingerprint replay, and reconciliation fixture.

## Operations
- Monitor API latency, worker throughput, database connections, failed payroll lines, blocked payroll runs, integration failures and reconciliation mismatches.
- Never bypass a production gate through a direct database edit.
