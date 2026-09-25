# Morva Payroll Platform — Delivery Roadmap

**Canonical branch:** `main`  
**Current position:** enterprise validation candidate; M4.62 independently verifies M4.61 point-in-time integrity snapshots over the complete M4.60 receipt history while preserving the governance/readiness-only boundary; not production-certified for real payroll/payment.

## Completed implementation foundations

- M3.87 CI workflow integrity gate
- M3.88 independent integration-execution readiness verifier
- M3.89 readiness-verifier receipt-contract hardening
- M3.90 dynamic workflow execution hardening for CI integrity and production-boundary scanners


- M3.90 dynamic workflow execution hardening for CI integrity and production-boundary scanners (`eval`, `bash -c`, `sh -c`) with dedicated regression coverage
- M4.1 authoritative evidence intake contract with immutable source provenance, SHA-256 identity, effective windows, approval metadata, deterministic fingerprints and fail-closed activation readiness
- M4.2 evidence closure matrix binding the twelve certification roles to canonical evidence source types with deterministic, fail-closed closure assessment
- M4.3 population-scoped treatment evidence binding approved legal evidence to 1405 components without embedding statutory numeric values
- M4.4 master-data evidence bridge binding accepted external master-data evidence to the internal acceptance assessment, exact population scope and integrity fingerprints
- M4.5 Rule Pack evidence bridge binding each 1405 component evidence record to accepted authoritative legal evidence with exact source identity, population scope and fail-closed activation state
- M4.6 adapter-contract evidence bridge binding official adapter evidence to accepted authoritative adapter-contract evidence with exact source URI/SHA-256 identity and fail-closed temporal validation
- M4.7 authoritative payroll sample evidence binding approved reference-sample identities, population scope and Jalali period to M4.1 evidence
- M4.14 accepted-evidence registry bridge projecting controlled M4.13 submissions into canonical M4.1 evidence items with fingerprint verification, deterministic ordering, scope isolation and a read-only registry API
- M4.15 evidence lifecycle contract for fingerprinted renewal/supersession lineage, exact source/population continuity, cycle rejection and deterministic lineage-head assessment
- M4.16 persisted evidence lifecycle API with append-only lineage events, MFA/SoD/scope controls, deterministic assessment and dedicated CI gate
- M4.17 persisted evidence role bindings with canonical role/source binding, accepted/current evidence enforcement, exact registry fingerprint binding, MFA/SoD/scope controls and dedicated CI gate
- M4.18 deterministic evidence readiness/remediation assessment with lifecycle-aware supersession blocking, role-binding convergence and read-only readiness API
- M4.19 integration-execution evidence bridge plus independent binding verifier, binding verified M3.84/M3.85/M3.86 staging-or-pilot execution to the M4.1 authoritative registry with deterministic reconstruction and fail-closed controls
- M4.20 integration-execution readiness assessment composing independently verified execution-binding identity with canonical evidence readiness, deterministic blockers and fail-closed readiness state
- M4.21 independent integration-execution readiness verifier with direct fingerprint reconstruction, exact repository/SHA binding, ready-state consistency and verification-time ordering
- M4.22 append-only persistence of independently verified integration-execution readiness receipts with fingerprint revalidation and a ministry-scoped read-only readiness API
- M4.23 deterministic paginated history API for persisted readiness receipts with candidate/environment filters and fail-closed validation
- M4.24 controlled verified-readiness persistence service that forces assessment-file ingestion through independent M4.21 verification before persistence
- M4.25 organization-scope binding for persisted readiness receipts with scope-bound fingerprints and read/history isolation across school, district, province and ministry domains
- M4.26 scope-bound readiness convergence that rebuilds current evidence readiness for the exact receipt scope, replays its fingerprint at the persisted observation timestamp and fails closed on evidence drift or incomplete evidence
- M4.27 append-only persistence of scope-bound convergence observations with MFA-protected recording, fingerprint revalidation and deterministic history
- M4.28 explicit freshness gate over persisted scope-bound convergence observations with caller-supplied age policy and fail-closed stale handling
- M4.29 explicit versioned freshness-policy identity binding for convergence observations without embedding a default operational window
- M4.30 persisted freshness-policy registry with deterministic policy fingerprints and registry-bound convergence freshness evaluation
- M4.31 deterministic, cursor-paginated freshness-policy registry history with fail-closed policy reconstruction
- M4.32 explicit positive policy-version support across runtime, persistence and freshness-policy APIs
- M4.33 deterministic aggregate integrity snapshot for the persisted freshness-policy registry
- M4.34 registry-integrity-bound freshness evaluation with deterministic binding across policy, assessment and registry snapshot identities
- M4.35 append-only persistence and cursor history for registry-integrity-bound freshness evaluation receipts with idempotent fingerprint binding
- M4.36 historical registry snapshot anchoring with exact member-ID manifests and independent fail-closed reconstruction
- M4.37 receipt-to-historical-snapshot binding with exact M4.35 receipt identity, M4.36 membership continuity and independent re-verification
- M4.38 historical snapshot policy resolution against exact immutable member-ID membership
- M4.39 historical snapshot-bound freshness evaluation using snapshot-resolved policy identity
- M4.40 append-only persistence of historical snapshot-bound freshness evaluations with exact snapshot/policy identity, fingerprint idempotency, cursor history and independent fail-closed verification
- M4.41 historical freshness receipt lineage binding M4.40 to the exact M4.37 receipt-to-snapshot binding with independent continuity verification
- M4.42 deterministic, ministry-managed history for M4.41 lineage records with timestamp+UUID cursor pagination, source-record re-verification and receipt/binding/snapshot filters
- M4.43 independent historical freshness chain verifier reconstructing M4.36 → M4.37 → M4.40 → M4.41 identity continuity with deterministic blockers and fingerprint
- M4.44 append-only persistence of M4.43 chain-verification receipts with idempotent fingerprint binding, ministry-managed cursor history, tamper re-verification and a direct receipt verification API
- M4.45 independent re-verification of persisted M4.44 receipts against a separately reconstructed M4.36 → M4.37 → M4.40 → M4.41 chain with deterministic verification fingerprint
- M4.46 append-only persistence of M4.45 independent-verification results with deterministic fingerprint idempotency, ministry-managed history and source-chain re-verification
- M4.47 append-only, fingerprinted integrity snapshots over the complete M4.46 verification history with full-history reconstruction, cursor history and re-verification
- M4.48 independent re-verification of M4.47 history-integrity snapshots against a separately reconstructed point-in-time M4.46 history with deterministic mismatch blockers and verification fingerprint
- M4.49 append-only, fingerprint-idempotent persistence of independent M4.48 verification results with ministry-managed cursor history and direct re-verification
- M4.50 append-only, fingerprinted point-in-time integrity snapshots over the complete M4.49 independent verification receipt history with source re-verification and cursor history
- M4.51 independent re-verification of M4.50 snapshots against a separately reconstructed point-in-time M4.49 receipt history with deterministic blocker codes and verification fingerprint
- M4.52 append-only, fingerprint-idempotent persistence of M4.51 independent receipt-history verification results with M4.50 snapshot and M4.49 source re-verification
- M4.53 point-in-time integrity snapshots over the complete M4.52 receipt history with deterministic fingerprinting, cursor history and source re-verification
- M4.54 independent re-verification of M4.53 snapshots against a separately reconstructed point-in-time M4.52 receipt history with deterministic blocker codes and verification fingerprint
- M4.55 append-only, fingerprint-idempotent persistence of M4.54 independent verification results with ministry-managed cursor history, M4.53 snapshot re-verification and M4.52 source re-verification
- M4.56 independent re-verification of persisted M4.55 receipts by reconstructing M4.54 from M4.53 and point-in-time M4.52 evidence with deterministic blocker codes and verification fingerprint
- M4.57 append-only, fingerprint-idempotent persistence of M4.56 receipt-verification results with M4.55 source re-verification and M4.53/M4.52 source re-verification
- M4.58 point-in-time integrity snapshots over the complete M4.57 receipt history with deterministic fingerprinting, cursor history and source re-verification
- M4.59 independent re-verification of M4.58 snapshots against a separately reconstructed point-in-time M4.57 receipt history with deterministic blocker codes and verification fingerprint
- M4.60 append-only, fingerprint-idempotent persistence of M4.59 independent receipt-history verification results with M4.58 snapshot and M4.57 source re-verification
- M4.61 point-in-time integrity snapshots over the complete M4.60 receipt history with deterministic fingerprinting, cursor history and source re-verification
- M4.62 independent re-verification of M4.61 snapshots against a separately reconstructed point-in-time M4.60 receipt history with deterministic blocker codes and verification fingerprint
## Current execution queue

1. Keep exact `main` head green across compilation, Ruff, PostgreSQL migrations, pytest, pip-audit and web build; the active development line now extends the M4.30 freshness-policy registry through M4.62 independent re-verification of M4.61 M4.60 receipt-history integrity snapshots.
2. Maintain the exact `main` head as the software baseline; real authoritative artifacts and staging/pilot execution remain external to the codebase and must be independently supplied, independently verified, approved and validated before any production authority is granted.
3. Refresh the technical assessment after each material implementation tranche. **M3.16/M3.17 refresh recorded in `docs/ASSESSMENT_2026-09-09.md`; M3.18 personnel-order governance recorded in `docs/M3_17_PERSONNEL_ORDER_LIFECYCLE.md`; M4.19–M4.43 refresh recorded in `docs/ASSESSMENT_2026-09-24.md`; the M4.47–M4.62 verification-history integrity tranche is recorded in `docs/ASSESSMENT_2026-09-25.md`.**
4. Complete authoritative organization/personnel/rank/attendance master data. **M3.17 strengthened referential, temporal and workflow-integrity gates; M3.19 added accepted/current/untampered readiness; M3.20 adds explicit drift detection against accepted evidence; M3.23 adds exact population attestation. Authoritative source confirmation and complete population evidence remain pending outside the codebase.**
5. Complete personnel-order lifecycle and approval evidence. **M3.18 implemented immutable order fingerprint binding and fail-closed effective-state verification; authoritative order schema and organizational approval policy remain pending.**
6. Complete legal component matrix and annual Rule Packs from primary sources. **M3.21 enforces the primary-source evidence contract, M3.24 binds every required 1405 component to source evidence; exact primary artifacts and formal approvals remain pending.**
7. Complete tax, pension, insurance, loans and judicial-deduction ledgers with approved treatments. **M3.12 governance boundary and M3.25 population-scoped activation boundary are implemented; authoritative treatment evidence, immutable population bindings and approved population-specific rules remain pending.**
8. Complete snapshot-driven retroactive recalculation and certified historical replay corpus. **M3.13 software provenance/reconciliation controls and M3.26 replay certification boundary are implemented; authoritative historical replay corpus, certified retro cases and approval evidence remain pending.**
9. Remove remaining demonstration-only frontend behavior and wire operational views to authenticated APIs. **M3.14 completed for the primary dashboard/employee views.**
10. Complete employee self-service, objection/case management and production PDF/reporting. **M3.15 foundation and M3.16 UX hardening implemented: authenticated self-service profile/payslips/orders, artifact-bound PDF download, persistent employee cases, payslip detail/provenance view, period filter and resilient download UX. M3.22 identity-directory reconciliation is now implemented; broader reporting, document-template certification and enterprise grievance policy/SLA evidence remain pending.**
11. Implement official SINA, accounting, treasury, bank, tax and insurance adapters only from authoritative contracts.
12. Run staging tests for every adapter and at least one pilot environment where authorized. **M4.19 provides the fail-closed M4 bridge and independent verifier; M4.20 provides the software-side readiness composition. Neither executes providers or fabricates external evidence.**
13. Complete end-to-end three-way reconciliation: Morva entitlement ↔ Treasury/PFM instruction ↔ Bank settlement. **M3.27 software hard-stop contract is implemented; M3.32 now blocks settlement at the payment-batch boundary when any member item has an unresolved exception. Live adapter evidence and authorized staging/pilot settlement remain pending.**
14. Extend M3.30 from persisted exception/resolution state into API/UI workflows and settlement-linked payment-item/batch operations. **M3.31 adds authenticated provider-neutral API workflows for exception creation, open/all listing, immutable event history and idempotent resolution. M3.32 adds a provider-neutral batch/item release guard that consumes the existing exception state and fails closed. Provider-specific settlement behavior remains prohibited without authoritative contracts.**
15. Complete production key-management, encryption-at-rest, secret rotation and retention controls. **M3.33 implements the application-side versioned key-ring, authenticated encryption/lookup primitives, retained-key rotation compatibility and production configuration gate. Infrastructure-managed database/storage encryption, KMS/HSM custody, automated secret rotation, backup-key segregation, retention evidence and independent security validation remain pending operational work.**
16. Execute encrypted backup, WAL/PITR restore and disaster-recovery drills with recorded RTO/RPO evidence. **M3.34 adds the immutable recovery-evidence contract, encrypted PostgreSQL backup script, PITR restore preparation script and CI validation of isolated PostgreSQL backup/restore. Actual production WAL/PITR drill execution and approved RPO/RTO evidence remain pending operational certification.**
17. Execute target-scale load/concurrency, mutation and financial property-based tests. **M3.35 adds 10,000+ employee batch evidence, parallel calculator replay coverage, Hypothesis financial invariants and four targeted mutation checks. Representative production workload targets, database/queue contention and independent performance certification remain pending.**
18. Complete independent security assessment and close critical findings. **M3.36 adds the fail-closed assessment contract, high-confidence secret preflight, focused security regression tests and a dedicated CI gate. An actual independent assessment/report, independent signoff, remediation evidence and environment-specific penetration/abuse-case testing remain pending.**
19. Obtain formal finance/legal/operations certification; then produce the matching software tag, GitHub Release, artifacts and deployment evidence. **M3.37 adds the fail-closed release certification contract, M3.38 adds exact-commit evidence-bundle verification, M3.39 binds final artifacts and signing provenance, M3.40 composes these into one aggregate fail-closed release gate, M3.41 builds/verifies the concrete Release artifacts against a SHA-256 manifest, M3.42 rehearses the complete build → manifest → gate composition while keeping CI fixtures explicitly non-production, and M3.43 signs/verifies the resulting evidence bundle with an ephemeral CI Ed25519 key for rehearsal, M3.44 independently reconstructs/verifies that bundle and its source chain without any private signing capability, M3.45 adds versioned trusted-key registry enforcement with rotation/revocation semantics, and M3.46 authenticates the registry itself with a separate root-signed trust anchor, and M3.47 binds each signed evidence bundle to that exact registry ID, version and fingerprint, and M3.48 adds a deterministic rotation ceremony proving the exact N→N+1 registry transition, root trust-anchor continuity and effective replacement-key time, and M3.49 adds a root trust-anchor handoff plus emergency-recovery path using an independent Recovery Anchor, and M3.50 adds an independent verifier that composes the full signed release trust chain across three Registry versions. Real finance/legal/operations approvals, verified external evidence artifacts, cryptographic signing, publication and deployment evidence remain pending; M3.51–M3.55 remain verification/rehearsal boundaries and do not establish production publication.**

## Production gate

Morva must not be used for real payroll or real payment until all applicable legal, authoritative-data, integration, security, operational, reconciliation, load and recovery evidence is complete and formally approved.