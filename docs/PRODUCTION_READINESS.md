# Morva Production Readiness Gates

**Release line:** `1.0.1-rc1`  
**Policy:** this document records engineering evidence status; it does not grant production payroll or payment authority.

## Gate 1 — Legal rules and calculation correctness

**Status: BLOCKED**

1. [x] Rule evaluation is effective-dated.
2. [x] Rule Pack has explicit version/status and production eligibility checks.
3. [x] Every production RuleDefinition must bind to the selected Rule Pack version.
4. [x] Production rules must declare a legal reference, approved/active review status and regression case IDs.
5. [x] Rule-result fingerprints include the rule version, so a rule-version change changes regression identity.
6. [x] Snapshot-driven retro/replay requires immutable historical personnel snapshots and matching snapshot hashes.
7. [ ] Primary-source legal evidence is present for every active production rule.
8. [ ] Formal legal/finance approval exists for the complete 1405 production Rule Pack.
9. [ ] Certified golden corpus covers all legally active components and employee-population variants.

**Release criterion:** zero unresolved legal-source, approval, version-binding or golden-regression blockers.

## Gate 2 — Authoritative data and valid payroll samples

**Status: BLOCKED**

1. [x] Import provenance/checksum and source lineage foundations exist.
2. [x] Immutable personnel snapshots exist.
3. [x] The anonymized `fixtures/1405-05` fixture is available for regression/integration work.
4. [x] Missing or unmapped source data is quarantined/fail-closed.
5. [x] 1405-05 golden-fixture shape and supplied net arithmetic identity are regression-tested.
6. [x] Personnel-order effective/issue dates remain separate in the golden fixture.
7. [x] Explicit arrears-gap detection is covered by automated edge-case tests.
8. [ ] Authoritative organization/personnel master hierarchy has formal acceptance.
9. [ ] Complete approved population, attendance and personnel-order data is available.
10. [ ] Payroll sample outputs are formally accepted as golden references.

**Release criterion:** complete authoritative data contracts plus retained acceptance evidence.

## Gate 3 — External integrations

**Status: BLOCKED**

1. [x] External systems are isolated behind adapter boundaries.
2. [x] Unapproved external execution is fail-closed.
3. [x] Official adapter evidence is represented by the existing governed evidence boundary.
4. [x] Separate integration ports and treatment catalogs exist for the Central Civil Servants Pension Fund and Social Security Organization.
5. [ ] The six-layer architecture from the feasibility study is available in repository documentation or formally supplied for implementation.
6. [ ] Official Central Civil Servants Pension Fund schema/endpoint contract is accepted.
7. [ ] Official Social Security Organization schema/endpoint contract is accepted.
8. [ ] Non-production staging acknowledgements, retries and idempotency are evidenced.
9. [ ] Production credentials are provisioned through external secret management.

**Release criterion:** official contracts + authorized staging/pilot evidence + idempotent integration/reconciliation evidence.

## Gate 4 — Security and auditability

**Status: BLOCKED**

1. [x] OIDC/JWT verification and scoped authorization exist.
2. [x] RBAC/SoD controls exist for privileged workflows.
3. [x] Persistent audit-chain primitives and verification support exist.
4. [x] AES-GCM field encryption and versioned key derivation exist.
5. [x] Production configuration rejects demo policies and unmanaged schema state.
6. [ ] Target-environment KMS/HSM custody and key rotation are evidenced.
7. [ ] Database and backup encryption-at-rest are verified in the target environment.
8. [ ] Independent security assessment and target-scale abuse/security testing are complete.

**Release criterion:** independent security acceptance with target-environment evidence.

## Gate 5 — Reconciliation

**Status: BLOCKED**

1. [x] Population/component reconciliation foundations exist.
2. [x] Payroll artifacts carry deterministic fingerprints and replay provenance.
3. [x] Payment/reconciliation lifecycle boundaries and fail-closed exception guards exist.
4. [ ] Authoritative Morva ↔ Treasury ↔ Bank three-way reconciliation has zero unresolved critical mismatches.
5. [ ] Pension/insurance reconciliation is evidenced against external settlement data.
6. [ ] Payment return/reversal/exception cases are exercised and accepted.

**Release criterion:** zero unresolved critical reconciliation mismatches with retained evidence.

## Gate 6 — Disaster recovery and operational resilience

**Status: BLOCKED**

1. [x] PostgreSQL production topology and migration gates are defined.
2. [x] DR runbook/scripts exist under `ops/`.
3. [x] Backup/WAL/PITR verification is modeled as a fail-closed release boundary.
4. [ ] Target-environment backup restore and PITR drill are demonstrated.
5. [ ] RPO/RTO targets are measured and met.
6. [ ] DR drill evidence is retained and tied to the release evidence bundle.
7. [ ] Target-scale load/concurrency testing is complete.

**Release criterion:** successful restore/DR drills with measured RPO/RTO and target-scale performance evidence.

## Global blockers

Production release remains blocked by any unresolved item below:

- missing or unapproved primary legal evidence for an active Rule Pack;
- missing authoritative master-data acceptance;
- missing official external adapter contracts or staging/pilot evidence;
- missing target-environment security/key-management/encryption evidence;
- unresolved critical reconciliation mismatch;
- missing restore/DR evidence or unmet RPO/RTO;
- a historical regression that changes a certified payroll result without an approved legal/rule change.

## Evidence discipline

Fixtures, demo policies, UI screens, adapter interfaces, CI success and engineering rehearsals are evidence of software behavior only. They do not constitute legal, financial, organizational or production authorization.
