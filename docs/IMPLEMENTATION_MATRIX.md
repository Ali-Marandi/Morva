# Morva Payroll Platform — Enterprise Implementation Matrix

`Implemented` means an actual code path exists. `Validated` means the required automated and environment evidence exists. `Production Certified` requires legal/finance/security/operations/integration sign-off. No item is marked production-certified by source code alone.

| # | Capability | State |
|---|---|---|
| 1 | Organization & Position Master Data | authenticated registry APIs + persisted master data + deterministic integrity validation + manifest acceptance contract implemented; M3.17 adds assignment target activity, invalid-range, overlap and active-employee assignment cardinality checks; authoritative ministry dataset and acceptance confirmation evidence pending |
| 2 | Personnel Order Workflow | **M3.18 adds persisted, versioned and source-bound organizational approval policy with deterministic policy fingerprint, exact submission/decision-role enforcement and policy-bound immutable submission/decision evidence; authoritative order schema and real organizational approval policy remain pending** |
| 3 | Legal Knowledge Base | persisted legal-source/rule-evidence governance workflow added with review, approval, SHA-256 linkage and fail-closed Rule Pack readiness; authoritative source corpus pending |
| 4 | Calculation Matrix | persisted rule-pack/component/population matrix with treatment, safe expression, effective dates, legal source/article, regression-suite hash, review/approval workflow and readiness gate implemented; authoritative population-specific legal matrix pending |
| 5 | 1405 Rule Pack | governed lifecycle foundation; remains `review_required` until authoritative legal/finance approval |
| 6 | Tax / Pension / Insurance | persisted ledger foundations plus explicit fail-closed treatment governance for `taxable/pensionable/insurable`; approved population-specific rule sets and primary-source evidence pending |
| 7 | High-volume Payroll | batch/chunk foundations; target-scale execution evidence pending |
| 8 | Retro + Jalali | immutable PersonnelSnapshot persistence + deterministic snapshot-driven retro reconciliation + snapshot-bound historical replay guard implemented; complete historical replay corpus and certification pending |
| 9 | Loans / Debts / Deductions | persisted loan and deduction ledger foundations plus explicit fail-closed treatment governance; authoritative ledgers/policies pending |
| 10 | Approval / SoD | permission + privileged + distinct-actor controls implemented for personnel-order decisions; durable enterprise IAM workflow pending |
| 11 | SINA Adapter | fail-closed typed contract; official schema/endpoint/credential and staging evidence required |
| 12 | Accounting / Treasury / Bank | typed six-provider boundary + transactional outbox/inbox foundations; official adapters required |
| 13 | Employee Self-Service | **M3.15 implemented authenticated self profile, approved/frozen payroll artifact listing/detail, immutable snapshot verification, personnel-order read view and artifact-bound PDF download; M3.16 adds period filtering, detailed payslip/provenance presentation and resilient download UX; identity-directory reconciliation remains pending** |
| 14 | Payslip Explanation | persisted payroll artifact + ordered line explanation implemented; employee self-service exposes line explanations and provenance hashes; authoritative legal source linking remains pending |
| 15 | Rule Sandbox UI | foundation; production hardening pending |
| 16 | Management Dashboard | authenticated employee/payroll/approval summary APIs wired to the operational dashboard; historical charts and broader operational KPIs pending |
| 17 | Anomaly Detection | deterministic/scoring foundation |
| 18 | Forecast / Budget AI | advisory-only foundations |
| 19 | Production Security | **M3.33 adds a versioned managed application key ring, AES-256-GCM authenticated field encryption, context-bound HMAC-SHA-256 lookup tokens, retained-key decrypt support for rotation, and fail-closed production enforcement of versioned key-ring configuration; infrastructure KMS/HSM custody, database/storage encryption-at-rest evidence, automated secret-rotation workflow, backup-key segregation, retention evidence and independent security review remain pending** |
| 20 | DR / PITR | executable PostgreSQL drill script + runbook added; target-environment restore evidence pending |
| 21 | Load / Performance | fixtures/scenarios; target-environment execution pending |
| 22 | Golden Regression | unit/integration/property-based foundation; expanded authoritative legal corpus pending |
| 23 | Real Payroll Reconciliation | reconciliation foundations; authoritative three-way production certification pending |
| 24 | Persistent Payroll Artifacts | implemented; employee-level deterministic result and payslip-line persistence |
| 25 | Transactional Integration Messaging | implemented foundation; official provider delivery and acknowledgement pending |
| 26 | Historical Payroll Replay | snapshot-bound deterministic replay guard implemented; production legal-rule replay certification pending |
| 27 | Core HR Employee Profile API | implemented read APIs for employee, employment, assignment, education, experience and dependents; automated API coverage added; production master-data validation pending |
| 28 | Core HR Effective Snapshots | implemented immutable period snapshot creation/read API with deterministic content hash; payroll/order population integration and production master-data evidence pending |
| 29 | Employee Objection / Case Management | **M3.15 implemented persistent case creation/list/detail/status lifecycle, employee-only self access, organization-hierarchy authorization for staff handling, resolution requirements and audit events; formal enterprise grievance policy/SLA evidence pending** |
| 30 | Employee Payslip PDF | **M3.15 implemented deterministic artifact-bound PDF download behind authenticated self-service and snapshot/hash verification; M3.16 adds a tested user-facing detail/provenance view and resilient download workflow; typography/localization and production document-template certification pending** |
| 31 | Release Trust / Key Rotation | **M3.48 adds a deterministic fail-closed rotation ceremony binding consecutive signed trust-registry versions to the exact old/new key IDs, effective replacement-key time and root trust anchor; M3.49 adds root trust-anchor handoff and independent Recovery Anchor emergency-recovery authorization; M3.50 adds independent full-chain verification across three signed Registry versions and the release evidence bundle; M3.51 adds a deterministic release trust evidence pack with exact public verification sources, SHA-256/size manifest, chain receipt binding, unexpected-file rejection and private-key exclusion; M3.52 adds a deterministic write-once USTAR/GZIP release-trust artifact, archive digest/size binding, safe extraction verification and rehearsal-only immutable GitHub artifact publication attestation; M3.53 adds a fail-closed publication-input gate binding repository, release ID, tag, exact candidate SHA and M3.52 artifact identity; M3.54 adds a safe release publication executor with external authorization, exact remote tag binding, existing-release rejection and non-shell GitHub CLI execution; M3.55 adds a read-only post-publication verifier that rechecks the live Release, exact tag/SHA, release state, exact three-asset set, asset size/digest and write-once evidence receipt; M3.56 adds a write-once deployment evidence gate bound to the M3.55 receipt, exact deployed SHA, deployment status, health-check digest and verified rollback target; M3.57 independently re-verifies the Gate against the M3.55 receipt and external attestation; M3.58 packages the M3.55/M3.56/M3.57 evidence chain into a deterministic write-once bundle with source hashes and safe re-verification; production key custody and authorization evidence remain pending** |

| 33 | Production Promotion Evidence | **M3.59 adds a fail-closed promotion gate bound to the deterministic M3.58 evidence bundle, exact candidate SHA, staging/pilot source environment, production target, external Boolean approval, timezone-aware approval time and distinct promotion/deployment actors; promotion/deployment itself remains outside this code path and formal production certification remains pending** |\n\n| 34 | Independent Production Promotion Verification | **M3.60 independently re-verifies the M3.59 promotion gate against the M3.58 bundle, external promotion authorization and embedded/external deployment attestation; no production promotion is executed by the verifier** |\n\n| 35 | Production Boundary Policy | **M3.61 scans the M3.54–M3.61 release/deployment workflows for direct mutation commands, write permissions and common credential/private-key markers; the result is a deterministic write-once policy receipt** |\n\n| 36 | Technical Production Readiness | **M3.62 aggregates verified M3.58 deployment evidence, M3.59/M3.60 promotion evidence and M3.61 policy coverage into a deterministic write-once technical readiness gate; it performs no production promotion and does not replace formal external certification** |\n\n| 37 | Evidence Freshness | **M3.63 adds an explicit freshness gate for published-release, promotion-approval and deployment evidence with timezone-aware timestamps, configurable age windows, future-timestamp rejection and write-once output; policy adequacy remains external** |\n\n| 38 | Final Technical Production Readiness | **M3.64 binds M3.62 technical readiness and M3.63 evidence freshness into one final software-only Gate with a common bundle fingerprint, candidate SHA, policy fingerprint and timezone-aware final check; it does not execute production promotion** |\n\n| 41 | Independent Production Certification Verification | **M3.68 independently re-verifies M3.67 against M3.65 final readiness and the complete M3.66 external certification evidence registry, including evidence freshness and exact repository/tag/SHA binding; verification-only** |

## Canonical payroll lifecycle

`draft -> data_received -> calculating -> validating -> reviewed -> approved -> frozen -> exported -> submitted -> payment_confirmed -> reconciled`

`src/morva/payroll/lifecycle.py` is the sole state-machine implementation. `workflow.py` is compatibility-only.

## Core HR phase-1 chain

`Person -> Employee -> Employment -> Organization -> Position -> Assignment -> Education -> Experience -> Dependents`

The current implementation provides the historical persistence models, authenticated read APIs, immutable effective snapshots, durable personnel-order registry, approval-gated effective orders with immutable final decisions, authenticated organization/position master-data registry APIs, deterministic integrity validation, persisted manifest-level acceptance, M3.17 assignment integrity checks, attendance integrity checks, persisted teacher-rank decision provenance verification and personnel-order fingerprint binding. M3.18 additionally persists and enforces versioned organizational approval-policy provenance for personnel orders. Authoritative ministry master data, the official personnel-order schema and real enterprise approval policy remain pending acceptance evidence.

## Personnel Order Lifecycle Governance / M3.17–M3.18

Each registered personnel order receives a deterministic SHA-256 content fingerprint covering order identity, employee, dates, type, reference, reason and line payload. Submission and final decision records persist the same fingerprint. Final approval/rejection remains one-time and requires distinct actors; rejection requires a reason. M3.18 requires an explicitly selected persisted policy in `approved` status. The policy is versioned and source-bound, covers explicit order types, declares required submission and decision roles, and carries its own SHA-256 fingerprint. Submission and decision evidence persist the policy code/hash and actor role; role mismatch, missing approval evidence, policy tampering or policy/order fingerprint mismatch fails closed. Effective-state queries remain blocked unless both order and approval evidence are internally consistent. This establishes software integrity/provenance controls without asserting legal authority for the schema or policy.

## Calculation Matrix Governance

Each executable component mapping is required to bind a Rule Pack and population scope to a safe expression, effective dates, legal source/article, tax/pension/insurance treatment and a regression-suite fingerprint. Legal source and rule evidence must already be approved, and matrix entries require distinct review and approval actors before the matrix readiness gate can pass.

## Ledger Treatment Governance

`TAX`, `PENSION`, `INSURANCE`, `LOAN` and `COURT_ORDER` now have an explicit treatment-governance boundary. Classification flags are explicit rather than inferred, and approval requires primary-source metadata, effective dates, independent review/approval and regression evidence. Missing approval leaves execution fail-closed. This does not constitute legal approval or populate rates/thresholds.

## Snapshot-Driven Retro / Historical Replay Governance

M3.13 binds historical payroll evidence to the immutable `PersonnelSnapshotRecord` for the applicable employee and period. Replay fails closed when the snapshot is missing, has a different employee/period, or its hash differs from the payroll artifact. Retroactive reconciliation requires original and revised persisted artifacts for every period and requires both artifacts to reference the same immutable snapshot; current HR state is never substituted silently. Legal rates/formulas are not inferred or activated by this boundary.

## Authenticated Operational Web Governance

M3.14 removes hardcoded dashboard and employee-list business data from the primary operational views. The dashboard consumes authenticated employee, payroll and approval statistics plus the latest payroll records through the existing API client/query layer; the employee view consumes authenticated employee statistics and paginated employee records. API failures render explicit error states and missing data renders `—`/empty states rather than invented demo values. This tranche does not establish production certification or authoritative master-data acceptance.

## Employee Self-Service / Case Governance

M3.15 adds an authenticated employee boundary at `/api/v1/self` and `/api/v1/cases/self`. Employee identity must resolve to an existing personnel record; otherwise the request fails closed. Employee payroll views expose only artifacts attached to approved-or-later payroll lifecycle states and verify the immutable `PersonnelSnapshotRecord` hash before detail or PDF access. Objections/cases persist employee ownership, lifecycle status, priority and resolution evidence; staff case handling is restricted through the existing hierarchical personnel authorization boundary and each creation/status change/download appends an audit event. M3.16 hardens the web presentation with server-backed period filtering, on-demand payslip detail, visible snapshot/provenance hashes, explicit loading/error states and resilient PDF download lifecycle. The PDF remains a document-generation foundation: template localization, typography, retention and formal document certification remain separate operational requirements.

## Authoritative Master Data / M3.17 Governance

M3.17 extends the master-data integrity gate with fail-closed assignment checks: organization and position targets must resolve and be active; assignment ranges must be valid; assignment intervals for the same employee may not overlap; and an active employee must have exactly one open-ended assignment. Attendance remains blocked on missing employee reference, invalid period/status, negative units, invalid SHA-256 source hash or missing approval evidence. Persisted teacher-rank decision and appeal states remain blocked when decision provenance is absent or tampered. These controls prove technical integrity and provenance only; authoritative organizational confirmation remains an explicit acceptance step.

## Production Key Management / M3.33 Governance

M3.33 provides an application-side `ManagedKeyRing` that carries a single active version plus retained versions needed to decrypt existing ciphertext during rotation. Field encryption uses AES-256-GCM with a random 96-bit nonce and optional associated data; lookup values use context-bound HMAC-SHA-256 rather than reversible plaintext indexes. Ciphertexts carry their key version and fail closed when that version is not retained. Production configuration requires versioned encryption and lookup key maps and rejects undersized/mismatched key material. This is application-side cryptographic hardening only: KMS/HSM custody, database/storage encryption-at-rest, automated secret rotation, backup-key segregation, operational retention attestation and independent security review remain deployment requirements.

## Release position

Morva is an **enterprise validation candidate**, not yet a production-certified payment system. The application deliberately remains fail-closed until legal approval, authoritative data reconciliation, official integrations, security/DR/load evidence and final finance/legal sign-off are complete.
