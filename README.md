# Morva Payroll Platform

سامانه جامع، قانون‌محور و قابل حسابرسی حقوق و دستمزد کارکنان آموزش‌وپرورش.

> **Production safety:** Morva is an enterprise validation candidate, not a production-authorized payment system. Real payroll and payment release remain fail-closed until the legal, data, integration, security, reconciliation, DR and operational gates are formally evidenced.

## Current status

**Version:** `1.0.0`  
**Default branch:** `main`  
**Public repository:** `Ali-Marandi/Morva`  
**Public web:** `https://ali-marandi.github.io/Morva/`

**Latest Changes (v1.0.0):**
- ✅ Enterprise-grade web platform (React 18 + TypeScript + Tailwind CSS)
- ✅ 14 components, 6 pages, 7 routes implemented
- ✅ Production-ready build configuration (Vite with optimizations)
- ✅ Comprehensive documentation for deployment and certification
- ✅ All core payroll lifecycle and calculation engine operational
- ✅ PostgreSQL migrations and audit foundations complete

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

Current 1405 rules remain non-production until the responsible finance/legal authorities approve the complete rule evidence set.

See:

- [`docs/legal/LAW_CATALOG.md`](docs/legal/LAW_CATALOG.md)
- [`docs/domain/CALCULATION_MATRIX.md`](docs/domain/CALCULATION_MATRIX.md)
- [`docs/domain/PAYROLL_COMPONENT_CATALOG.yml`](docs/domain/PAYROLL_COMPONENT_CATALOG.yml)

## Security model

Production configuration is designed around:

- PostgreSQL rather than SQLite;
- OIDC/JWT-based verified identity;
- MFA as a production gate;
- hierarchical organization-scope authorization;
- least-privilege permissions and separation of duties;
- encryption/HMAC for sensitive identity fields and managed key material;
- append-only / tamper-evident audit records;
- idempotent external messaging;
- no production secrets, raw payroll files or unredacted sensitive logs in Git.

The committed production configuration template is [` .env.production.example`](.env.production.example).

## Data and privacy

The repository may contain privacy-safe schemas, regression metadata and anonymized reconciliation summaries, but it must not contain real employee names, national IDs, bank accounts, credentials or raw payroll exports.

Production data admission must preserve provenance, checksums, schema validation and audit metadata.

The 1405-05 reconciliation documentation is intentionally privacy-safe and uses aggregate/control evidence rather than publishing raw personnel records.

## Integrations

Morva exposes typed boundaries for the external payroll ecosystem, including SINA, accounting, treasury, banking, tax/insurance and related provider workflows.

External messaging follows:

```text
Application transaction
      -> Transactional Outbox
      -> Provider adapter
      -> External acknowledgement / receipt
      -> Inbox / receipt persistence
      -> Reconciliation
```

Retries must be idempotent and must never silently create a duplicate payment.

Official schemas, endpoints, credentials and staging acknowledgements are deployment-time prerequisites; they are not fabricated in source code.

## Database and migrations

Production uses PostgreSQL with versioned Alembic migrations.

Fresh environments:

```bash
python -m pip install -e '.[dev]'
alembic upgrade head
```

The migration chain lives under [`alembic/`](alembic/). Application startup is configured to fail closed when the required migrated-schema gate has not been satisfied.

## Local development

### Backend

```bash
python -m pip install -e '.[dev]'
ruff check .
pytest -q
```

### Web

```bash
cd web
npm install
npm run dev
```

Production-like web build:

```bash
cd web
npm install
npm run build
```

## CI and quality gates

Every push and pull request runs the repository quality pipeline. The current CI includes:

```text
Python 3.12 + PostgreSQL
Python 3.13 + PostgreSQL
    -> compileall
    -> ruff
    -> Alembic migration
    -> pytest
    -> pip-audit

Web
    -> npm install
    -> npm run build
```

See [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

The web distribution is built and published by [`.github/workflows/web-pages.yml`](.github/workflows/web-pages.yml).

## Versioned distribution policy

Development is intentionally distributed in small, reviewable steps.

```text
Implementation
   -> commit on main
   -> CI on exact commit
   -> exact-head verification
   -> version/tag
   -> GitHub Release
   -> versioned Python artifacts
   -> web deployment
```

The release policy and workflow are documented in [`docs/RELEASE_DISTRIBUTION_POLICY.md`](docs/RELEASE_DISTRIBUTION_POLICY.md).

A package version such as `1.0.0` is not treated as proof that a GitHub Release exists; release publication is an explicit, traceable operation.

## Production certification gates

Morva must remain **fail-closed** for real payroll until the applicable gates below have formal evidence:

1. finance/legal approval for every active Rule and payroll component treatment;
2. authoritative payroll samples for each employee population with line-by-line zero-unexplained-difference reconciliation;
3. official SINA, accounting, treasury, bank, tax and insurance contracts/endpoints plus staging evidence;
4. final payment provider implementation, acknowledgement, reversal/return handling and bank-side reconciliation;
5. production key management, rotation, encrypted backups, WAL/PITR and restore-drill evidence;
6. target-scale load, concurrency, security and mutation testing;
7. full authoritative master-data coverage for organization, personnel, attendance, teaching/overtime, loans and deductions;
8. complete employee self-service, reporting and production operations UX;
9. green CI for the exact release head and review of all resulting checks;
10. final finance/legal/operations sign-off.

The detailed control list is maintained in [`docs/PRODUCTION_READINESS.md`](docs/PRODUCTION_READINESS.md) and [`docs/FINAL_MISSION_STATUS.md`](docs/FINAL_MISSION_STATUS.md).

## Current release position

`1.0.0` is an **enterprise validation candidate**. It should not be represented as authorization for real payroll or payment release.

The project intentionally separates three states:

- **implemented** — code path exists;
- **validated** — required automated/environment evidence exists;
- **production_certified** — legal, finance, security, operations, integrations and formal sign-off are complete.

## Project documentation

| Document | Purpose |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System architecture and design boundaries |
| [`docs/IMPLEMENTATION_MATRIX.md`](docs/IMPLEMENTATION_MATRIX.md) | Capability-by-capability implementation status |
| [`docs/FINAL_MISSION_STATUS.md`](docs/FINAL_MISSION_STATUS.md) | Enterprise transformation and production blockers |
| [`docs/PRODUCTION_READINESS.md`](docs/PRODUCTION_READINESS.md) | Production acceptance gates |
| [`docs/RELEASE_DISTRIBUTION_POLICY.md`](docs/RELEASE_DISTRIBUTION_POLICY.md) | Commit/CI/tag/release/distribution rules |
| [`docs/RELEASE_1_0.md`](docs/RELEASE_1_0.md) | 1.0 release scope and hard blockers |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Remaining delivery roadmap |
| [`docs/ENTERPRISE_TRANSFORMATION.md`](docs/ENTERPRISE_TRANSFORMATION.md) | Enterprise control model |
| [`docs/data-import/1405-05-full-reconciliation.md`](docs/data-import/1405-05-full-reconciliation.md) | Privacy-safe reconciliation evidence |

## Safety statement

Morva is a payroll system. Incorrect legal interpretation, incorrect employee master data, duplicate payment, missing reconciliation, weak access control or failed recovery can cause material financial harm.

Accordingly, the repository favors explicit evidence and fail-closed controls over optimistic status claims.

**Do not use Morva to process real payroll or release real payments until the formal production gates have passed.**
