# Morva Production Readiness Gates

**Scope:** engineering readiness tracker for release governance.  
**Current release line:** 1.0.1-rc1  
**Policy:** this document records evidence status; it does not grant production payroll or payment authority.

## Gate 1 — Legal rules and calculation correctness

**Status: BLOCKED**

- [x] Rule evaluation is effective-dated.
- [x] Rule Pack has explicit version/status and production eligibility checks.
- [x] Production RuleDefinition metadata must bind to the selected Rule Pack version.
- [x] Production rules must declare legal reference, approved/active review status, and regression case IDs.
- [x] Rule-result fingerprints include the rule version.
- [x] Snapshot-driven retro/replay guard requires immutable historical personnel snapshots.
- [ ] Primary-source legal evidence is present for every active rule.
- [ ] Formal legal/finance approval exists for the complete 1405 production Rule Pack.
- [ ] Certified golden corpus covers all legally active components and population variants.

**Release criterion:** no unresolved legal-reference, approval, version-binding, or golden-regression blocker.

## Gate 2 — Authoritative data and valid payroll samples

**Status: BLOCKED**

- [x] Import provenance/checksum foundation exists.
- [x] Personnel snapshots and source lineage exist.
- [x] 1405-05 anonymized fixture exists for engineering regression/integration use.
- [x] Quarantine/fail-closed behavior exists for missing or unmapped source data.
- [ ] Authoritative organization/personnel master hierarchy has formal acceptance.
- [ ] Complete approved population and attendance/order data is available.
- [ ] Payroll sample outputs are formally accepted as the golden reference.

**Release criterion:** complete authoritative data contracts plus signed acceptance evidence.

## Gate 3 — External integrations

**Status: BLOCKED**

- [x] Integration boundaries are modeled as adapters rather than payroll-domain owners.
- [x] Fail-closed behavior prevents unapproved external execution.
- [ ] Official pension/insurance provider schemas and endpoint contracts are accepted.
- [ ] Production credentials and secret-management paths are provisioned outside source control.
- [ ] Staging acknowledgements, idempotency, retries and failure handling are evidenced.
- [ ] Central Civil Servants Pension Fund adapter is validated.
- [ ] Social Security Organization adapter is validated.

**Release criterion:** official contracts + authorized staging/pilot evidence + idempotency/reconciliation evidence.

## Gate 4 — Security and auditability

**Status: BLOCKED**

- [x] OIDC/JWT verification and scoped authorization exist.
- [x] RBAC/SoD and privileged-transition controls exist.
- [x] Persistent audit chain and verification support exist.
- [x] AES-GCM field encryption and versioned key derivation exist.
- [x] Production configuration rejects demo policies and unmanaged schema state.
- [ ] Production KMS/HSM custody, rotation and retention evidence exists.
- [ ] Encryption-at-rest and database/backup encryption are verified in the target environment.
- [ ] Security test evidence exists at target deployment scale.

**Release criterion:** target-environment security evidence and independent security review complete.

## Gate 5 — Reconciliation

**Status: BLOCKED**

- [x] Population/component reconciliation foundations exist.
- [x] Payroll artifact fingerprints and historical replay foundations exist.
- [x] Payment/reconciliation lifecycle boundaries exist.
- [ ] Authoritative three-way Morva/Treasury/Bank reconciliation has zero unresolved mismatches.
- [ ] Pension/insurance reconciliation is evidenced against external settlement data.
- [ ] Payment return/reversal/exception cases are exercised and signed off.

**Release criterion:** zero unresolved critical reconciliation mismatches with retained evidence.

## Gate 6 — Disaster recovery and operational resilience

**Status: BLOCKED**

- [x] PostgreSQL production topology and migration gates are defined.
- [x] DR drill runbook and operational scripts exist under `ops/`.
- [ ] Backup/WAL/PITR restore has been demonstrated in the target environment.
- [ ] RPO/RTO targets are measured and met.
- [ ] Disaster-recovery drill results are retained as release evidence.
- [ ] Load/concurrency testing at target population scale is complete.

**Release criterion:** successful restore and DR drills with measured RPO/RTO plus target-scale performance evidence.

## Global release blockers

Production release remains blocked while any of the following are unresolved:

1. Missing or unapproved primary legal evidence for an active Rule Pack.
2. Missing authoritative master-data acceptance.
3. Missing official provider contracts, credentials, staging/pilot evidence or adapter validation.
4. Missing target-environment security, key-management or encryption evidence.
5. Any unresolved critical reconciliation mismatch.
6. Missing restore/DR evidence or unmet RPO/RTO.
7. Any regression that changes certified historical payroll results without an approved legal/rule change.

## Evidence discipline

Fixtures, demo rules, UI screens, adapter interfaces and CI success are engineering evidence only. None of them by itself constitutes legal, financial, organizational or production authorization.
