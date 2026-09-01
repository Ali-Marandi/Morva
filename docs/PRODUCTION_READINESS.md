# Morva Production Readiness Gates

## Cannot be bypassed

Morva is not production payroll-ready until all of the following are true:

1. Every active Rule has a primary legal source, article/clause, effective dates, review owner and regression tests.
2. Annual 1405 Rule Pack is reconciled against official circulars/tables used by the employing organization.
3. Tax, pension, insurance and deduction treatments are verified against current official instructions for each employee population.
4. At least one authoritative payroll sample for each employee population has been reconciled line-by-line.
5. The Payroll Run passes validation with zero unresolved critical findings.
6. Independent approval and separation-of-duties checks pass.
7. External integration credentials/endpoints are configured and connectivity is tested in a non-production environment first.
8. SINA/order/payslip exports are verified against authoritative schemas and acknowledgements.
9. Accounting, treasury and bank totals reconcile within approved tolerance.
10. Backup, WAL archive, PITR restore and disaster-recovery drills have passed.
11. Load tests meet the agreed throughput and latency target for the expected employee population.
12. Security review, MFA, RBAC, audit logging and secrets management are enabled.

## Current implementation progress

The payroll-run lifecycle now writes durable hash-linked audit events to PostgreSQL through `AuditEventRecord` plus a serialized `AuditChainHeadRecord`. Chain replay verification detects sequence gaps, broken links, event tampering and tail divergence. This advances gate 12, but does not satisfy the full gate: production authorization, MFA, security review and database privilege hardening still require deployment controls and independent acceptance.

The production calculation endpoint remains fail-closed until persisted employee snapshots and an approved legal ruleset are present. No legal value is activated from research-only material.

## Real-data admission

Real employee or payroll data must enter through an approved import contract with validation, checksum, provenance and audit metadata. No real sample is committed to Git.

## Advisory AI boundary

Forecasting and anomaly detection can recommend or flag. They cannot activate a payroll rule, alter a legal calculation, approve a payroll run or release payment.
