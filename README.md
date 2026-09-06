# Morva Payroll Platform

سامانه جامع، قانون‌محور و قابل حسابرسی حقوق و دستمزد کارکنان آموزش‌وپرورش.

> **Production safety:** Morva is an enterprise validation candidate, not a production-authorized payment system. Real payroll and payment release remain fail-closed until the legal, data, integration, security, reconciliation, DR and operational gates are formally evidenced.

## Current status

**Version:** `1.0.1`  
**Default branch:** `main`  
**Public repository:** `Ali-Marandi/Morva`  
**Public web:** `https://ali-marandi.github.io/Morva/`

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
