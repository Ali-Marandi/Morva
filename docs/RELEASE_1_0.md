# Morva 1.0.0 Release Candidate

## Release intent
Morva 1.0.0-rc1 is the production-oriented release candidate for the payroll platform. The application architecture, domain boundaries, auditability, validation, operations and integration contracts are included.

## Included
- Core HR and organization/position foundations
- Effective-dated personnel orders and workflow
- Versioned legal/rule governance
- Payroll calculation, validation, batch execution and deterministic fingerprints
- Tax/pension/insurance policy boundaries
- Retroactive payroll and Jalali monthly periods
- Loans, debts and deduction ledger foundations
- Approval and segregation-of-duties controls
- SINA, accounting, treasury and bank adapter ports
- Employee self-service and payslip explanation contracts
- Rule sandbox, budget scenarios, management KPIs
- Deterministic anomaly detection and advisory forecasting
- RBAC, audit chain and production security controls
- PostgreSQL, backup/PITR and disaster-recovery runbook
- Load-test and golden-regression fixtures

## Hard production blockers
The release MUST remain blocked until:
1. The 1405 rule pack is approved by the responsible legal/finance authorities.
2. Current official tax, pension, insurance and deduction instructions are loaded and regression-tested for every employee population.
3. Real SINA/accounting/treasury/bank non-production endpoints and credentials are configured and tested.
4. At least one authoritative payroll sample per employee population is reconciled line-by-line with zero unexplained differences.
5. Security, MFA, backup/restore, load and disaster-recovery acceptance tests pass in the target environment.

## Data safety
No real employee, bank, payroll or credential data belongs in Git. Production data admission requires provenance, checksum, schema validation and audit metadata.

## AI boundary
AI is advisory only. It may forecast or flag anomalies, but it cannot activate legal rules, alter calculations, approve payroll, or release payment.
