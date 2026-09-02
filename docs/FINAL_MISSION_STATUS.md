# Morva — Enterprise Transformation Status

**Date:** 2026-09-02  
**Branch:** `p2-enterprise-payroll-work7`  
**Position:** Enterprise validation candidate; not yet production-certified for real payroll or payment.

## Canonical payroll lifecycle

`src/morva/payroll/lifecycle.py` is the sole payroll state-machine source. `workflow.py` is compatibility-only.

`draft -> data_received -> calculating -> validating -> reviewed -> approved -> frozen -> exported -> submitted -> payment_confirmed -> reconciled`

## Enterprise controls implemented

- Direct caller-supplied authoritative calculation is disabled.
- PayrollRun is persisted and scoped by period and organization.
- Calculation requires ready source import, approved mappings, effective personnel snapshots and an approved/published Rule Pack with immutable hashes.
- Employee-level payroll artifacts and payslip lines are persisted with snapshot/rule-pack/output hashes.
- Payslip line order is persisted so historical replay is deterministic.
- Historical replay verification is available and produces an audited mismatch when hashes differ.
- Per-run lifecycle events persist actor, role context, organization, reason, correlation and idempotency information.
- Critical lifecycle resource operations use row locking to reduce concurrent transition races.
- Rule evidence is stored per Rule Pack and component and must include legal source and regression evidence before artifact creation.
- Production rule execution rejects arbitrary callable formulas and requires the safe expression DSL.
- Sensitive identity encryption/HMAC primitives exist; production configuration requires managed keys and plaintext national-ID writes are guarded.
- Hierarchical organization-scope authorization exists for payroll resources.
- Transactional Outbox/Inbox and integration receipts are persisted with idempotency keys.
- Payment batches contain per-beneficiary payment items with encrypted bank-account material; duplicate batch creation is constrained by database uniqueness.
- Bank receipt ingestion and exact amount reconciliation foundations exist; external banking remains fail-closed without an approved adapter.
- PostgreSQL and migration gates, web build, dependency audit, tests and CI remain enforced.

## Legal-rule safety

No payroll rate, coefficient, tax threshold, insurance rate, pension treatment or allowance value is promoted from a fixture or research source. Current rule packs remain non-production until authoritative source documents, scope, effective dates, formal finance/legal review and regression evidence are present.

## Authoritative execution chain

`Source -> ImportBatch -> MasterData -> EffectivePersonnelSnapshot -> ApprovedRulePack -> PayrollRun -> PayrollArtifact -> PayslipLines -> Validation -> Review -> Approval -> Freeze -> PaymentBatch -> Outbox -> ExternalReceipt -> BankSettlement -> Reconciliation -> Audit`

## Production certification blockers

The following cannot be truthfully satisfied from source code alone and therefore remain hard gates:

1. Formal finance/legal approval for each active rule and each component's tax/insurance/pension/accounting treatment.
2. Authoritative real payroll samples and population-level reconciliation evidence.
3. Official SINA, accounting, treasury, bank, tax and insurance schemas/endpoints/credentials plus staging acknowledgement certification.
4. Final payment release implementation against an official provider, including reversal/return handling and bank-side reconciliation.
5. Production key management/rotation, encryption-at-rest, encrypted backup, WAL/PITR and restore-drill evidence.
6. Target-scale load, concurrency, security, mutation and disaster-recovery evidence.
7. Full authoritative organization/personnel/attendance/teaching/overtime/loan/deduction master-data coverage.
8. Complete employee self-service, reports and production operational UX.
9. Green CI for the exact branch head and successful review of all resulting checks.
10. Final finance/legal/operations sign-off.

Morva must remain **fail-closed** for real payment until every applicable gate is evidenced.
