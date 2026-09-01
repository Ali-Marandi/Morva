# Morva — Comprehensive Technical & Production Assessment

**Assessment date:** 2026-09-01  
**Repository:** `Ali-Marandi/Morva`  
**Branch:** `main`  
**Assessed commit:** `1f49cff3c9b66124a816a18c7c2beecbad2d51e1`  
**Release marker:** `1.0.0-rc1`

> **Safety statement:** This assessment does not certify Morva for real payroll or payment. No legal rule is promoted to active status by this document. Any rule without primary-source evidence and formal finance/legal approval remains `review_required`.

## 1. Executive assessment

Morva has a strong enterprise-oriented foundation: a modular-monolith architecture, explicit payroll lifecycle, effective-dated personnel/rule concepts, decimal monetary arithmetic, source reconciliation, privacy-safe fixtures, audit-chain primitives, fail-closed integration adapters, CI with PostgreSQL, and a documented production gate.

The main gap is not architectural direction; it is the distance between the current foundation/RC implementation and a controlled production payroll platform. The highest risks are: API trust boundaries that still permit caller-supplied payroll lines, security controls not yet enforced at every endpoint, in-memory audit chaining rather than a persistent immutable audit ledger, absence of a full persisted payroll-run workflow, incomplete integration implementations, incomplete legal approval evidence, and a web UI that still contains hard-coded demonstration metrics.

### Current maturity (engineering judgement)

| Area | Current assessment | Target |
|---|---:|---:|
| Architecture/domain foundations | 8.5/10 | 9.5/10 |
| Payroll calculation foundation | 8/10 | 9.5/10 |
| Reconciliation/import foundation | 8.5/10 | 9.5/10 |
| Legal governance | 8.5/10 | 10/10 |
| Security/IAM enforcement | 5/10 | 9.5/10 |
| Persistence/workflow durability | 5.5/10 | 9.5/10 |
| External integrations | 4/10 | 9/10 |
| Web product readiness | 5/10 | 9/10 |
| Production/DR readiness | 5/10 | 9.5/10 |
| Overall | **~6.5/10** | **9.5+/10** |

These scores are engineering assessments, not compliance certifications.

## 2. Scope actually inspected

The requested areas were inspected against the `main` tree and implementation files, including:

- `docs/ARCHITECTURE.md`
- `docs/PRODUCTION_READINESS.md`
- `docs/legal/*`
- `docs/data-import/*`
- `src/morva/api/*`
- `src/morva/security/*`
- `src/morva/payroll/*`
- `src/morva/integrations/*`
- `web/src/*`
- related runtime configuration, CI, persistence, tests and root packaging files needed to validate the requested claims.

## 3. Capability classification

### 3.1 Real implementation present

The following are implemented as code-level capabilities, although several are not production-ready yet:

- FastAPI application and versioned API routing.
- Payroll calculation using `Decimal`.
- Effective-dated rule resolution.
- Safe expression-based rule execution through the project rule engine.
- Payroll fingerprint generation.
- Payroll snapshots and source replay primitives.
- Population reconciliation and component-level diffing.
- Payroll workflow transition rules.
- Personnel-order/effective-state foundations.
- Rule readiness profiles (`observed`, `review_required`, `verified`).
- Privacy-safe import transformation using surrogate identifiers.
- Integration ports with explicit correlation and idempotency fields.
- Fail-closed default external adapter.
- RBAC/role and scope primitives and MFA checks for privileged policy calls.
- CI running Python 3.12/3.13, PostgreSQL service, Ruff and pytest.

### 3.2 Demonstration/UI capabilities

The current web application is still a release-candidate foundation. Metrics such as employee count, pending orders and financial warnings are hard-coded in the frontend and therefore must not be interpreted as live operational facts.

The payroll API also exposes an explicit `apply_demo_policy` path. That capability is useful for development but must never become a production calculation path.

### 3.3 Contractual/planned capabilities

The documentation defines stronger production capabilities than the current code fully implements, including durable payroll-run persistence, complete personnel-order lifecycle, complete annual legal rule packs, full taxation/pension/insurance/loan ledgers, SINA/accounting/treasury/bank adapters, MFA/RBAC enforcement across all APIs, immutable audit persistence, encrypted backup/WAL/PITR, full employee self-service, production analytics, load targets and disaster-recovery drills.

## 4. Rule Pack status model

Morva correctly distinguishes observed/source-replay data from legal-calculation readiness. The current policy is that research/fixture values do not constitute approved law.

### Status interpretation

| Status/category | Meaning | May drive real payroll? |
|---|---|---|
| `candidate` / research | Under analysis | **No** |
| `review_required` | Primary source/effective date/review incomplete | **No** |
| `approved` / `verified` | Source, scope, treatment and regression evidence approved | **Only after production gates pass** |
| `published` | Released approved pack | **Only in an authorized production release** |
| `retired` / `superseded` | Historical only | **No for new runs; yes for historical replay where authorized** |
| demo fixture | Development/test-only | **No** |

The current legal catalog marks the identified base, teacher-ranking, tax, payroll-execution and SINA-related sources as `review_required`. Therefore they are not production authorities.

## 5. P0 findings

### P0-01 — Untrusted caller-supplied payroll lines

`POST /api/v1/payroll/calculate` currently accepts payroll lines directly from the request and passes them into the calculator. This violates the required trust boundary for production payroll. A caller must not be able to manufacture an earning/deduction line and receive a payroll result merely by marking flags such as `taxable`, `pensionable` or `insurable`.

**Required remediation:** calculate from a persisted, approved employee snapshot + effective personnel order + approved rule pack + period + validated source inputs. The API should accept a calculation/run identifier, not arbitrary authoritative payroll lines.

### P0-02 — Demo policy must be isolated from production

`apply_demo_policy` is explicitly development-only today, but the presence of a demo branch in the calculation API creates an avoidable production hazard.

**Required remediation:** move demo policies behind a development/test-only dependency boundary and make production configuration fail closed if any demo rule pack or fixture mode is selected.

### P0-03 — Security is not yet endpoint-wide

Security code exists, but the inspected API route handlers do not show authentication/authorization dependencies applied to every sensitive endpoint. Policy helpers alone do not secure a FastAPI route.

**Required remediation:** enforce authentication, MFA for privileged actions, RBAC+ABAC scope checks, separation of duties and audit context in the application/API boundary.

### P0-04 — Audit chain is not durable/immutable yet

The current `AuditChain` links events in memory through the previous hash. This is a useful primitive but not a persistent audit ledger.

**Required remediation:** persist append-only audit events with sequence, timestamp, actor, correlation/request ID, previous hash, current digest, verification tooling and protected retention. Sensitive audit payloads must be minimized and redacted.

### P0-05 — Payroll lifecycle is not yet a durable business process

A workflow transition enum exists, but the production requirement is a persisted per-period/per-population lifecycle:

`draft -> data_received -> calculated -> validated -> reviewed -> approved -> frozen -> exported -> submitted -> payment_confirmed -> reconciled`

The current status enum is useful but does not by itself persist run state, actor/reason/evidence, optimistic locking or approval history.

### P0-06 — Integration layer is only a contract, not a production adapter suite

SINA, accounting, treasury and bank ports exist with correlation and idempotency concepts, and a fail-closed adapter prevents unconfigured calls. However, this is not evidence of production connectivity or acknowledgement semantics.

**Required remediation:** implement versioned adapters only from authoritative schemas/credentials, use staging first, and enforce outbox/inbox, retry policy, idempotency, acknowledgement matching and duplicate-payment protection.

### P0-07 — Production database/DR gates require implementation evidence

The architecture and production-readiness documents correctly require PostgreSQL, migrations, encrypted backups, WAL/PITR and restore drills. These must become executable operational controls with recorded test evidence before production approval.

### P0-08 — Frontend contains fabricated operational state

The current UI embeds sample metrics and status labels in the source code. This is acceptable as a release-candidate mock, but it conflicts with the requirement that operational screens be backed by authoritative data.

**Required remediation:** remove all hard-coded business metrics from production builds; bind screens to authenticated API data and show explicit `no data`/`not evaluated` states where data is unavailable.

## 6. Data-flow model

The target system should treat payroll as a controlled data lineage pipeline:

```text
Authoritative sources
  -> ImportBatch / Manifest
  -> Schema + checksum + provenance validation
  -> Quarantine on mismatch
  -> Canonical master data
  -> Effective personnel state
  -> Approved Rule Pack
  -> Payroll Run Snapshot
  -> Deterministic Calculation
  -> Validation / Exception Queue
  -> Human Review
  -> Approval / SoD
  -> Freeze
  -> Accounting / Treasury / Bank export
  -> External acknowledgement
  -> Payment confirmation
  -> Bank reconciliation
  -> Immutable audit / historical replay
```

### Source map

| Source/domain | Canonical destination | Key controls |
|---|---|---|
| Personnel | Employee/Employment | identity, employment status, privacy controls |
| Organization | OrganizationUnit/CostCenter | hierarchy/effective dates |
| Personnel orders | PersonnelOrder | issue/effective dates, version, approval |
| Teacher ranking | RankCase/Assessment | five-rank business model, committee, appeal, effect date |
| Attendance | AttendanceFact | source authority, period, corrections |
| Teaching/overtime | VariableEarning | approval, evidence, eligibility |
| Deductions | DeductionLedger | source, authority, ceiling, period |
| Loans | Loan/Installment | opening/remaining balance, payment idempotency |
| Insurance | InsuranceLedger | population-specific treatment |
| Pension fund | PensionLedger | fund/population rule mapping |
| Tax | TaxLedger | approved annual tax pack |
| Accounting | AccountingBatch | document/reference + reconciliation |
| Treasury | PaymentBatch | approval + SoD + unique payment batch |
| Bank | BankPayment/Reconciliation | acknowledgement + settlement matching |
| SINA | IntegrationMessage | schema version, correlation, receipt |

## 7. Domain model gaps to close

The target domain should make the following first-class and effective-dated:

- ministry / province / district-region / school / finance unit / cost center
- employee, employment, position, service status, financial accounts
- personnel order history with immutable versions
- teacher rank case, evidence, assessment, committee, appeal, decision and retroactive effect
- payroll component catalog with eligibility and legal treatment matrix
- payroll period, payroll run, employee snapshot, payslip, adjustment and retro result
- loan, installment, supplementary insurance, health insurance, pension, social security, tax and legal deductions
- budget, cost center, accounting document, treasury request, bank batch, acknowledgement and bank reconciliation
- employee objection/case with evidence and resolution
- import batch, source file manifest, validation issue and quarantine record

## 8. Payroll component / legal matrix

Every component must have a machine-readable record with at least:

`code, title, eligibility, basis, formula/reference, tax treatment, insurance treatment, pension treatment, accounting mapping, legal source, authority, adoption date, effective_from, effective_to, review status, approver, regression cases`.

The observed 1405-05 source bundle contains 27 observed earning columns and 10 observed deduction columns. These observed columns establish source coverage only; they do not establish legal eligibility or treatment.

### Initial component families requiring formal legal review

- حق شغل
- حق شاغل
- رتبه‌بندی
- عائله‌مندی
- اولاد
- حق‌التدریس
- اضافه‌کار
- مناطق کمتر توسعه‌یافته / محروم
- فوق‌العاده‌ها
- مالیات
- بیمه‌ها
- صندوق بازنشستگی
- وام
- کسورات قضایی

No component family should become production-active solely because it appears in the observed source data.

## 9. Current data-quality baseline

The supplied 1405-05 validation documentation reports:

- 3,329 payroll rows
- 2,193 supplementary-insurance rows
- 20,671 loan-installment rows
- 22,696 personnel-order rows
- 2,197 health-insurance rows
- 1,116 social-security rows

The recorded joins show full payroll-to-order coverage, partial coverage for several insurance sources, and incomplete health/social joins. These are reconciliation facts about the supplied population, not legal conclusions.

The documented golden controls require, per source payroll row, exact earnings-component-to-gross equality and gross-minus-deductions-to-net equality.

## 10. API assessment

### Good

- API versioning boundary exists (`/api/v1`).
- Pydantic validation is present.
- Decimal values are represented as strings in many responses where exactness matters.
- Reconciliation API models snapshots and returns population-level deltas/classifications.

### Must change

- Add authenticated principal context to every sensitive route.
- Remove direct caller authority over payroll lines and legal treatments.
- Persist calculation requests/runs before execution.
- Bind calculations to an approved Rule Pack and effective personnel snapshot.
- Add idempotency and correlation identifiers to state-changing endpoints.
- Standardize error envelopes and prevent sensitive data leakage.
- Add endpoint-level audit events and SoD enforcement.

## 11. Security assessment

### Existing foundation

- Roles and scopes exist.
- MFA flag exists for privileged policy checks.
- Integration ports fail closed by default.
- Production config rejects SQLite, disabled MFA and disabled integrations.

### Gaps

- Authentication provider/session/token verification is not present in the inspected API route boundary.
- Scope checks are not demonstrably applied to all routes.
- Permission model is still role-centric rather than permission-centric RBAC+ABAC.
- SoD is not a durable policy over the lifecycle.
- Audit context is not yet consistently generated from the authenticated request.
- Secret management, encryption-at-rest configuration and database/key rotation controls require operational implementation.

## 12. Monetary correctness

The project correctly uses `Decimal` for payroll arithmetic. This must be preserved end-to-end.

Production requirements:

- store explicit currency unit and monetary scale;
- define one canonical internal unit (recommended: IRR) and make all UI/API conversions explicit;
- forbid implicit ریال/تومان conversion;
- define rounding rules per calculation stage and source authority;
- test threshold/rounding behavior with golden cases.

## 13. Execution plan

### Phase P0 — Trust boundary and safety

**Deliverables:** remove direct payroll-line authority from public calculate API; isolate demo policy; enforce auth/RBAC/ABAC/MFA; durable audit event schema; fail-closed production checks; persisted payroll-run state skeleton.

**Acceptance:** no unauthenticated sensitive endpoint; no production route can calculate from caller-created authoritative lines; demo policy is impossible in production; every privileged state change has actor + reason + timestamp + organization scope + audit event; invalid configuration blocks startup/readiness.

**Risk:** highest. Changes here may expose latent integration/API contract assumptions.

### Phase P1 — Durable payroll lifecycle

**Deliverables:** `PayrollPeriod`, `PayrollRun`, `EmployeePayrollSnapshot`, state transitions, approvals, optimistic locking, freeze semantics, review queues.

**Acceptance:** one canonical lifecycle; persisted state; no conflicting status implementation; historical runs are reconstructible.

**Risk:** high data-model migration risk.

### Phase P2 — Master data and authoritative import

**Deliverables:** organization/personnel/order/rank master data, import manifest, schema contracts, quarantine, provenance, checksums, reconciliation cases.

**Acceptance:** every imported batch is traceable and repeatable; invalid joins cannot silently enter payroll.

**Risk:** high source-data variability.

### Phase P3 — Legal Rule Platform

**Deliverables:** rule metadata schema, review workflow, source attachments/references, approved pack publication, regression corpus, component matrix, historic pack retention.

**Acceptance:** no active production rule without primary source + scope + effective dates + review approvals + regression evidence.

**Risk:** very high legal correctness risk; requires domain-expert sign-off.

### Phase P4 — Payroll engine completion

**Deliverables:** employee snapshot-driven calculation, taxes, pension, insurance, loans, variable earnings, retroactive recalculation, explanation tree and exception engine.

**Acceptance:** golden payroll cases reconcile line-by-line and in aggregate; historical replay reproduces the exact prior result.

**Risk:** high rule complexity and edge cases.

### Phase P5 — Integrations and financial controls

**Deliverables:** SINA, accounting, treasury, bank, tax and insurance adapters; outbox/inbox; staging certification; payment-batch controls.

**Acceptance:** all external messages are versioned/idempotent; duplicate submissions do not duplicate payment; receipts reconcile to the originating batch.

**Risk:** highest external dependency risk.

### Phase P6 — Enterprise UX and self-service

**Deliverables:** role-based work queues for finance, HR, approver, auditor and employee; Persian RTL; accessibility; PDF/print; search/filter/history/objections.

**Acceptance:** zero fabricated metrics; every displayed value has a source and state; permissions are enforced server-side.

**Risk:** medium; UX should follow stabilized APIs/domain contracts.

### Phase P7 — Production certification

**Deliverables:** load tests, security tests, migration rehearsals, backup/WAL/PITR, restore drills, monitoring/alerting, incident runbook, release checklist.

**Acceptance:** every production-readiness gate has recorded evidence and sign-off.

**Risk:** operational readiness and organizational dependency risk.

## 14. Required expert decisions

The following cannot be decided safely by software implementation alone and must be approved by designated financial/legal owners before activation:

- legal source and exact article/clause for each payroll component;
- effective date and retroactivity of each rule;
- eligibility by employment population and organization;
- tax/pension/insurance treatment;
- annual tax thresholds and rates;
- minimum/maximum/ceiling behavior;
- rank allowances and evidence/committee rules;
- accounting chart mappings;
- treatment of loans, legal deductions and exceptional deductions;
- authoritative SINA/export schemas and acknowledgement states;
- acceptable reconciliation tolerances;
- official bank/treasury settlement semantics.

## 15. Acceptance-test catalogue

At minimum CI should include:

1. Payroll lifecycle happy path and invalid transitions.
2. Same-input deterministic replay with identical fingerprint.
3. Promotion/rank upgrade with retroactive effect.
4. Order correction without rewriting prior history.
5. Transfer of organization/service location.
6. Leave/return/termination/reinstatement.
7. Different pension/insurance populations.
8. Teaching/overtime/loan/supplementary-insurance/legal deduction cases.
9. Tax bracket threshold and non-recurring payment cases.
10. Duplicate integration message and idempotent retry.
11. Bank rejection/return and reconciliation mismatch.
12. Quarantine and manual resolution of unmatched source data.
13. Migration forward/backward safety where supported.
14. Security authorization matrix and privileged MFA.
15. Backup restore and point-in-time recovery verification.
16. Load test at agreed regional/provincial population scale.
17. Property-based arithmetic/reconciliation invariants.
18. Mutation testing for critical payroll rules.

## 16. Explicit non-goals for the current RC

Until the production gates are satisfied, the following claims must not be made:

- “ready for real payroll”
- “legally verified”
- “bank-payment ready”
- “SINA certified”
- “zero-error payroll”

The correct status is **release candidate / development and controlled validation platform**.

## 17. Decision

**Proceed with incremental hardening; do not rewrite the platform.**

The existing modular-monolith direction is appropriate. The immediate priority is to close the P0 trust, security, durability and production-safety gaps, then build the legal-rule and authoritative-data layers on the same foundation.

The highest-value next implementation slice is **P0: canonical persisted payroll run + trusted calculation boundary + endpoint security/SoD + durable audit + production fail-closed controls**. Only after that should new payroll features be added.
