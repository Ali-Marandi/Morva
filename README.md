# Morva Payroll Platform

سامانه جامع، قانون‌محور و قابل حسابرسی حقوق و دستمزد کارکنان آموزش‌وپرورش.

> **Production safety:** Morva is an enterprise validation candidate, not a production-authorized payment system. Real payroll and payment release remain fail-closed until the legal, data, integration, security, reconciliation, DR and operational gates are formally evidenced.

## Current status

**Version:** `1.0.1`  
**Default branch:** `main`  
**Public repository:** `Ali-Marandi/Morva`  
**Public web:** `https://ali-marandi.github.io/Morva/`

**Latest `main` activity (2026-09-22):**
- Latest main commit: `3bb6d16` — `feat: M4.1 authoritative evidence intake (#67)`
- Main now includes M3.90 dynamic workflow-execution hardening, M3.89 readiness-verifier hardening, and the M4.1 authoritative evidence-intake boundary.
- CI and release gates remain fail-closed for any real payroll/payment authority.

**Latest Changes (v1.0.1):**
- ✅ Security dependency update: `cryptography` 50.x
- ✅ Python 3.12/3.13 CI green
- ✅ `pip-audit` green
- ✅ Web production build green
- ✅ Canonical payroll lifecycle regression test aligned

The current codebase contains the enterprise payroll foundation: persisted payroll artifacts and payslip lines, effective-dated personnel/master-data foundations, legal Rule Pack governance, hierarchical authorization, encrypted sensitive-field primitives, lifecycle audit, transactional Outbox/Inbox, payment-batch controls, reconciliation foundations, historical replay, PostgreSQL migrations, automated tests, CI/CD pipeline and **world-class web platform**.

The authoritative execution chain is:

```text
Source
  -> ImportBatch
  -> MasterData
  -> EffectivePersonnelSnapshot
  -> ApprovedRulePack
  -> PayrollRun
  -> EmployeePayrollArtifact
  -> PayslipLines
  -> Validation
  -> Review
  -> Approval
  -> Freeze
  -> PaymentBatch
  -> Outbox
  -> ExternalReceipt
  -> BankSettlement
  -> Reconciliation
  -> ImmutableAudit
```

## What is implemented

| Area | Current state |
|---|---|
| Payroll lifecycle | Canonical persisted state machine with review/approval/freeze controls |
| Payroll calculation | Decimal-safe engine with production trust boundary and persisted artifacts |
| Employee snapshots | Immutable/provenance-aware snapshot boundary for authoritative execution |
| Rule governance | Versioned Rule Packs, source evidence and activation controls |
| Legal safety | Unapproved or unsupported legal rules remain non-active / fail-closed |
| Personnel & organization | Effective-dated foundations plus hierarchical organization scope |
| Payroll explanation | Persisted payslip line ordering and provenance for deterministic explanation/replay |
| Retro / replay | Deterministic period and historical replay foundations |
| Reconciliation | Earnings/deductions comparison, payment and bank reconciliation foundations |
| Security | OIDC/JWT verification boundary, MFA gate, RBAC/ABAC primitives, sensitive-field crypto |
| Audit | Persistent hash-linked lifecycle/audit records with tamper verification |
| Integrations | Typed contracts, receipts, idempotency and transactional Outbox/Inbox |
| Payment | Payment-batch gates and per-beneficiary payment-item foundations; external release remains fail-closed |
| Database | PostgreSQL-first production model with Alembic migrations |
| Quality | Python 3.12/3.13 CI, migrations, tests, linting and dependency audit |
| Web | RTL-compatible React 18/TypeScript/Tailwind CSS web distribution with 14 components, 6 pages, 7 routes, production-optimized Vite build, deployed through GitHub Pages |

The implementation matrix in [`docs/IMPLEMENTATION_MATRIX.md`](docs/IMPLEMENTATION_MATRIX.md) is the source of truth for capability-level status.

## Official project roadmap

The following roadmap is the canonical delivery sequence for taking Morva from the current enterprise validation candidate to controlled production readiness. Each stage is intended to be a reviewable, evidence-driven increment rather than a one-shot release.

### Acceptance gates

The final acceptance model is based on four gates:

1. **Legal rules** — every active rule has a valid, reviewed `legal_source`; no unresolved `TODO: NEEDS-LEGAL-SOURCE` remains in the authoritative execution path.
2. **Authoritative payroll samples** — every production rule set is verified against approved real-world payroll reference samples, line by line, for each applicable employee population.
3. **External integrations** — every required adapter is contract-tested, failure-mode tested and exercised in an authorized staging/pilot environment.
4. **Security, compliance and recovery** — independent security evidence, disaster-recovery evidence with documented RTO/RPO, and clean three-way reconciliation are complete.

### Delivery sequence

| Stage | Roadmap milestone | Target outcome |
|---|---|---|
| 1 | Rules engine + payroll calculation core | Validate the versioned Rule Pack model and calculation engine against the existing golden fixtures; preserve fail-closed legal behavior. |
| 2 | Explainable payslip | Deliver line-item provenance with a user-facing **«این عدد از کجا آمد؟»** explanation path. |
| 3 | Karmand Iran + national government SSO | Establish authoritative employment/personnel identity and government authentication integrations through isolated adapters. |
| 4 | Two pension funds + comparison reporting | Complete the shared adapter/data model while keeping each fund's legal treatment isolated and auditable. |
| 5 | Teacher ranking + retroactive arrears | Connect approved rank decisions to payroll with snapshot-driven retrospective recalculation and automatic arrears/adjustment artifacts. |
| 6 | Treasury/payment + three-way reconciliation | Separate entitlement, treasury instruction and actual settlement; automatically flag every mismatch. |
| 7 | Security hardening + disaster recovery + pilot | Complete production security controls, restore drills and an authorized regional/organizational pilot. |
| 8 | Gradual province-by-province rollout | Expand under controlled operational monitoring, preserving the same evidence and acceptance gates for every deployment scope. |

### Current execution focus

The current implementation has established major software-side foundations through M3.90, including the M3.73–M3.90 readiness, release, deployment, integration and CI-integrity chain. M3.89, M4.1, M4.2, M4.3, M4.4, M4.5 and M4.6 are now represented on the active delivery line; M4.6 binds official-adapter contract evidence to accepted authoritative adapter-contract evidence without activating providers. These controls do not constitute legal, organizational or production certification on their own.

The current implementation has established major software-side foundations through the M3.17–M3.26 governance tranches, including master-data integrity, personnel-order approval provenance, 1405 evidence governance, identity-directory reconciliation, authoritative population attestation, population-scoped ledger governance and snapshot-bound replay certification. These controls improve integrity and provenance but do not constitute legal, organizational or production certification on their own.

The next execution queue remains focused on closing the evidence boundary, beginning with the M4.1 intake contract, the M4.2 closure matrix and the M4.3 population-treatment evidence boundary: authoritative master-data confirmation, formal legal Rule Pack approval, approved population-specific ledger treatments, certified historical replay corpus, official external adapters and staging/pilot evidence, full three-way reconciliation, payment return/reversal workflows, production key management and retention, DR/PITR drills, target-scale testing, independent security assessment, and formal finance/legal/operations certification.

> **Important:** The roadmap is a target sequence, not a claim that every stage is already completed. Morva must remain fail-closed for real payroll and real payment until the applicable evidence and approvals are complete.

## Canonical payroll lifecycle

```text
draft
  -> data_received
  -> calculating
  -> validating
  -> reviewed
  -> approved
  -> frozen
  -> exported
  -> submitted
  -> payment_confirmed
  -> reconciled
```

`src/morva/payroll/lifecycle.py` is the canonical state-machine implementation. Compatibility workflow code must not bypass this lifecycle.

Critical state changes carry actor/role context, organization scope, reason, correlation information and audit evidence. Segregation of duties prevents a creator from approving the same payroll run.

## Authoritative calculation boundary

Production calculation does **not** accept arbitrary caller-created payroll lines as authoritative input.

The required sequence is:

1. create a persisted `PayrollRun` for the Jalali payroll period and organization scope;
2. admit approved source data through the import contract;
3. establish the effective employee/personnel snapshot;
4. prove the required Rule Pack is approved/published for the applicable scope and effective dates;
5. calculate from server-owned persisted records;
6. persist the employee-level artifact and ordered payslip lines;
7. validate, review, approve, freeze and only then prepare external payment/export.

The application remains fail-closed when any authoritative prerequisite is missing.

## Legal and payroll-rule governance

Morva deliberately does not infer legal rates, coefficients, thresholds or contribution treatment from fixtures, examples or model guesses.

Every authoritative Rule must have, at minimum:

- a primary legal/administrative source;
- article/section reference where applicable;
- effective dates and population scope;
- review/approval evidence;
- regression coverage before activation.

Where the authoritative source is unavailable, the project uses the explicit marker:

```text
TODO: NEEDS-LEGAL-SOURCE
```

## Release posture

`v1.0.1` is a security and CI patch release. It improves dependency hygiene and release reliability but does **not** authorize real payroll execution or payment release.

The following production gates remain mandatory:

- approved 1405 legal/rule pack;
- authoritative payroll samples reconciled line-by-line for each employee population;
- real non-production external integration tests;
- independent security acceptance;
- backup/restore and DR evidence;
- three-way Morva/Treasury/bank reconciliation with no unresolved mismatches.

See:

- [`docs/PRODUCTION_READINESS.md`](docs/PRODUCTION_READINESS.md)
- [`docs/RELEASE_1_0.md`](docs/RELEASE_1_0.md)
- [`docs/IMPLEMENTATION_MATRIX.md`](docs/IMPLEMENTATION_MATRIX.md)
- [`docs/ROADMAP.md`](docs/ROADMAP.md)

> **Security:** Never commit credentials, tokens, payroll records, national identifiers or bank data to Git.
