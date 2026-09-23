# Morva Payroll Platform — Delivery Roadmap

**Canonical branch:** `main`  
**Current position:** enterprise validation candidate; M4.27 persists scope-bound convergence observations and exposes deterministic convergence history; not production-certified for real payroll/payment.

## Completed implementation foundations

- Modular-monolith structure and API v1 boundary
- Decimal-safe payroll calculator and reproducible fingerprints
- Effective-dated rule and Rule Pack foundations with fail-closed legal readiness
- Persisted PayrollRun and canonical payroll lifecycle
- Caller-supplied authoritative calculation disabled
- Import manifest, checksum, provenance and quarantine foundations
- Effective PersonnelSnapshot and source-to-payroll provenance
- Persisted employee payroll artifacts and ordered payslip lines
- Persistent hash-linked audit ledger and verification
- OIDC/JWT boundary, hierarchical authorization, MFA and SoD controls
- Transactional Outbox/Inbox, integration receipts and idempotency foundations
- Payment-batch and encrypted beneficiary-account foundations
- Bank receipt and exact amount reconciliation foundations
- PostgreSQL/Alembic production schema gate
- RTL web distribution through GitHub Pages
- CI for Python 3.12/3.13, PostgreSQL, migrations, Ruff, pytest, pip-audit and web build
- Living implementation, production-readiness and prompt-compliance documentation
- M3.12 ledger treatment governance boundary with explicit fail-closed classification and approval evidence requirements
- M3.13 snapshot-driven retro/replay provenance boundary with immutable historical snapshot binding and dedicated CI gate
- M3.14 authenticated operational dashboard/employee views with explicit API loading/error/empty states
- M3.15 authenticated employee self-service, objection/case persistence and artifact-bound payslip PDF endpoint with dedicated CI gate
- M3.16 employee self-service UX hardening with payslip detail/provenance presentation, period filtering, resilient PDF download handling and dedicated web quality gate
- M3.17 authoritative master-data integrity hardening across organization/personnel assignment, attendance and persisted teacher-rank provenance controls
- M3.18 personnel-order integrity hardening with immutable order fingerprints, approval-evidence binding, SoD/rejection controls and fail-closed effective-state verification
- M3.19 reusable fail-closed master-data readiness bound to payroll calculation
- M3.20 explicit authoritative master-data acceptance evidence and drift-detection contract with deterministic coverage deltas and integrity fingerprint verification
- M3.21 1405 primary-source evidence intake contract, source-family register, deterministic provenance validation and dedicated CI gate
- M3.22 deterministic employee identity-directory reconciliation with fail-closed self-service mapping and dedicated CI gate
- M3.23 authoritative master-data population attestation contract with exact coverage binding, explicit completeness declarations, SoD checks and deterministic attestation fingerprinting
- M3.24 1405 Rule-Pack evidence boundary with component-to-source binding, immutable source hashes, explicit treatment metadata, SoD and deterministic evidence fingerprints
- M3.25 population-scoped ledger treatment activation boundary with immutable population/Rule Pack evidence binding and fail-closed execution readiness
- M3.26 snapshot-driven replay certification boundary with immutable snapshot/Rule Pack/input/output hashes, deterministic certification fingerprinting and fail-closed status
- M3.27 three-way reconciliation release boundary with exact payroll/accounting/payment batch, employee-count and amount matching plus hard-stop release behavior
- M3.28 payment exception lifecycle foundation with provider-neutral return/reject/partial-settlement/reversal/unresolved-mismatch states, explicit resolution evidence and fail-closed release guard
- M3.29 payment exception resolution ledger foundation with immutable event records, explicit resolution evidence, timezone-aware timestamps, deterministic fingerprints and tamper verification
- M3.30 persisted payment exception state and resolution events with transactional idempotency boundary and dedicated Alembic/pytest gate
- M3.31 provider-neutral payment exception API workflow with authenticated create/list/event-history/resolve operations, resolution evidence, RBAC boundary and idempotent audit behavior
- M3.32 provider-neutral payment-batch settlement hard-stop boundary with deterministic per-item release evaluation and fail-closed unresolved-exception blocking
- M3.33 versioned managed application key ring with AES-256-GCM field encryption, context-bound HMAC-SHA-256 lookup tokens, retained-key decryption during rotation and production fail-closed enforcement of versioned key-ring configuration
- M3.34 disaster-recovery evidence contract plus PostgreSQL encrypted-backup/PITR operational scripts and dedicated recovery CI gate
- M3.35 target-scale payroll batch evidence, parallel deterministic calculation tests, financial property-based invariants and a targeted mutation-killing gate
- M3.36 independent security assessment preflight contract with fail-closed signoff/finding/control gates, high-confidence secret preflight and dedicated CI gate
- M3.37 formal release-certification contract with finance/legal/operations signoffs, evidence binding, domain gates and deterministic certification fingerprint
- M3.38 release-candidate evidence bundle verifier bound to an exact Git commit SHA with fail-closed delegation to M3.37 certification
- M3.39 release provenance and signing attestation contract with artifact hashes and deterministic final-release fingerprint
- M3.40 aggregate release gate composing M3.36 security, M3.37 certification and M3.39 attestation with exact candidate-SHA consistency and structured fail-closed blockers
- M3.41 release package integrity contract with deterministic artifact manifest, exact candidate-SHA binding, tamper detection and dedicated build/verify CI gate
- M3.42 release rehearsal contract binding the concrete artifact manifest to the aggregate release gate, with exact SHA/tag/release-ID/artifact matching, re-hashing and fail-closed rehearsal evidence
- M3.43 signed release evidence bundle contract with canonical Ed25519 signing, public-key-derived key identifiers, evidence-file hashing and fail-closed signature verification
- M3.44 independent evidence verifier that reconstructs the M3.41 → M3.40 → M3.42 chain and verifies the signed bundle using only recorded sources, a public key and optional exact SHA
- M3.45 versioned trusted Ed25519 signing-key registry with active/retired/revoked states, validity windows, explicit rotation/revocation operations, independent key fingerprints and verifier enforcement
- M3.46 root-signed trusted-key registry with a separate trust anchor, canonical Ed25519 registry signature, authenticated registry serialization and mandatory verifier validation before release-signing-key trust
- M3.47 exact trust-registry binding inside the signed release evidence bundle, including registry ID/version/fingerprint and a hashed registry source file verified by the independent verifier
- M3.48 deterministic trusted-key rotation ceremony contract binding consecutive registry versions, exact old/new key IDs, effective time, root trust anchor and fail-closed transition verification
- M3.49 root trust-anchor rotation and emergency-recovery ceremony with dual scheduled handoff signatures, independent Recovery Anchor authorization for emergency revoke, exact registry fingerprints and fail-closed continuity checks
- M3.50 independent trust-chain verification composing M3.43/M3.47 signed release evidence with M3.48 signing-key rotation and M3.49 root trust-anchor transition across three exact Registry versions
- M3.51 deterministic release trust evidence pack that records the full M3.50 trust chain, exact public verification sources, SHA-256/size manifest and fail-closed pack verification without private-key material
- M3.52 deterministic immutable release-trust archive artifact with write-once output, normalized USTAR/GZIP representation, archive digest/size metadata, safe extraction verification and rehearsal-only GitHub Actions publication attestation
- M3.53 fail-closed release publication gate binding repository, release ID, tag, exact candidate SHA and M3.52 artifact identity into a deterministic publication-input fingerprint
- M3.54 safe release publication executor requiring an externally supplied authorization attestation, exact remote tag-to-SHA binding, existing-release rejection and non-shell GitHub CLI execution
- M3.55 read-only post-publication integrity verifier bound to M3.52/M3.53, exact remote tag and candidate SHA, published non-prerelease Release state, exact three-asset set, GitHub-reported SHA-256 digests and write-once verification receipt
- M3.56 deterministic deployment evidence gate bound to the M3.55 receipt, exact deployed SHA, succeeded deployment status, health-check digest and explicit rollback verification
- M3.57 independent deployment evidence verifier that reconstructs and rechecks the M3.56 gate against the M3.55 release receipt and external deployment attestation
- M3.58 deterministic deployment-evidence bundle packaging the M3.55/M3.56/M3.57 chain with source hashes, private-key exclusion, safe extraction and write-once metadata
- M3.59 fail-closed production-promotion gate bound to the exact M3.58 bundle, candidate SHA, staging/pilot source environment, production target, external authorization and distinct approval/deployment actors
- M3.60 independent production-promotion verifier that reconstructs the M3.59 gate and rechecks bundle, authorization and deployment attestation consistency
- M3.61 production-boundary policy scanner covering the M3.54–M3.61 release/deployment workflows for direct mutation commands, write permissions and sensitive credential/private-key markers
- M3.62 technical production readiness gate aggregating M3.58 deployment evidence, M3.59/M3.60 promotion evidence and M3.61 policy coverage without performing production promotion
- M3.63 evidence freshness gate with explicit release, approval and deployment age windows, timezone-aware timestamps and future-timestamp rejection
- M3.64 final technical production-readiness gate binding M3.62 and M3.63 with the common bundle/candidate/policy identity before any external production certification
- M3.65 independent final readiness verifier that reconstructs M3.62/M3.63 fingerprints and rechecks the common production-readiness identity
- M3.66 external certification evidence contract requiring a complete twelve-role, exact-SHA-bound, timestamped and optionally expiring evidence registry
- M3.67 production certification evidence gate binding final readiness to the complete M3.66 external evidence registry without executing production promotion
- M3.68 independent production certification verifier rechecking M3.67, M3.66 and the M3.65 final readiness chain
- M3.69 full production-boundary policy scan extending coverage across the M3.54–M3.68 release/deployment workflow set
- M3.70 production release lineage manifest consolidating final readiness, certification, external evidence and full policy fingerprints
- M3.71 independent production release lineage verifier reconstructing and rechecking the M3.70 lineage from its source evidence
- M3.72 production-readiness convergence object binding M3.71 verification, M3.69 full boundary policy and complete external evidence for controlled external handoff
- M3.73 readiness handoff manifest and fail-closed handoff gate
- M3.74 independent readiness-handoff verifier
- M3.75 official adapter evidence contract
- M3.76 independent adapter-evidence verifier
- M3.77 adapter activation gate
- M3.78 independent adapter activation verifier
- M3.79 fail-closed integration adapter runtime boundary
- M3.80 integration contract manifest
- M3.81 independent integration-contract verifier
- M3.82 integration readiness gate
- M3.83 independent integration-readiness verifier
- M3.84 staging/pilot integration execution evidence contract
- M3.85 independent integration execution verifier
- M3.86 integration execution readiness gate
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
## Current execution queue

1. Keep exact `main` head green across compilation, Ruff, PostgreSQL migrations, pytest, pip-audit and web build; the active development line now extends the M4.30 freshness-policy registry through M4.37 receipt-to-historical-snapshot binding.
2. Maintain the  as the software baseline; real authoritative artifacts and staging/pilot execution remain external to the codebase and must be independently supplied, independently verified, approved and validated before any production authority is granted.
3. Refresh the technical assessment after each material implementation tranche. **M3.16/M3.17 refresh recorded in `docs/ASSESSMENT_2026-09-09.md`; M3.18 personnel-order governance recorded in `docs/M3_17_PERSONNEL_ORDER_LIFECYCLE.md`.**
4. Complete authoritative organization/personnel/rank/attendance master data. **M3.17 strengthened referential, temporal and workflow-integrity gates; M3.19 added accepted/current/untampered readiness; M3.20 adds explicit drift detection against accepted evidence; M3.23 adds exact population attestation. Authoritative source confirmation and complete population evidence remain pending outside the codebase.**
5. Complete personnel-order lifecycle and approval evidence. **M3.18 implemented immutable order fingerprint binding and fail-closed effective-state verification; authoritative order schema and organizational approval policy remain pending.**
6. Complete legal component matrix and annual Rule Packs from primary sources. **M3.21 enforces the primary-source evidence contract, M3.24 binds every required 1405 component to source evidence; exact primary artifacts and formal approvals remain pending.**
7. Complete tax, pension, insurance, loans and judicial-deduction ledgers with approved treatments. **M3.12 governance boundary and M3.25 population-scoped activation boundary are implemented; authoritative treatment evidence, immutable population bindings and approved population-specific rules remain pending.**
8. Complete snapshot-driven retroactive recalculation and certified historical replay corpus. **M3.13 software provenance/reconciliation controls and M3.26 replay certification boundary are implemented; authoritative historical replay corpus, certified retro cases and approval evidence remain pending.**
9. Remove remaining demonstration-only frontend behavior and wire operational views to authenticated APIs. **M3.14 completed for the primary dashboard/employee views.**
10. Complete employee self-service, objection/case management and production PDF/reporting. **M3.15 foundation and M3.16 UX hardening implemented: authenticated self-service profile/payslips/orders, artifact-bound PDF download, persistent employee cases, payslip detail/provenance view, period filter and resilient download UX. M3.22 identity-directory reconciliation is now implemented; broader reporting, document-template certification and enterprise grievance policy/SLA evidence remain pending.**
11. Implement official SINA, accounting, treasury, bank, tax and insurance adapters only from authoritative contracts.
4. Run staging tests for every adapter and at least one pilot environment where authorized. **M4.19 provides the fail-closed M4 bridge and independent verifier; M4.20 provides the software-side readiness composition. Neither executes providers or fabricates external evidence.**
13. Complete end-to-end three-way reconciliation: Morva entitlement ↔ Treasury/PFM instruction ↔ Bank settlement. **M3.27 software hard-stop contract is implemented; M3.32 now blocks settlement at the payment-batch boundary when any member item has an unresolved exception. Live adapter evidence and authorized staging/pilot settlement remain pending.**
14. Extend M3.30 from persisted exception/resolution state into API/UI workflows and settlement-linked payment-item/batch operations. **M3.31 adds authenticated provider-neutral API workflows for exception creation, open/all listing, immutable event history and idempotent resolution. M3.32 adds a provider-neutral batch/item release guard that consumes the existing exception state and fails closed. Provider-specific settlement behavior remains prohibited without authoritative contracts.**
15. Complete production key-management, encryption-at-rest, secret rotation and retention controls. **M3.33 implements the application-side versioned key-ring, authenticated encryption/lookup primitives, retained-key rotation compatibility and production configuration gate. Infrastructure-managed database/storage encryption, KMS/HSM custody, automated secret rotation, backup-key segregation, retention evidence and independent security validation remain pending operational work.**
16. Execute encrypted backup, WAL/PITR restore and disaster-recovery drills with recorded RTO/RPO evidence. **M3.34 adds the immutable recovery-evidence contract, encrypted PostgreSQL backup script, PITR restore preparation script and CI validation of isolated PostgreSQL backup/restore. Actual production WAL/PITR drill execution and approved RPO/RTO evidence remain pending operational certification.**
17. Execute target-scale load/concurrency, mutation and financial property-based tests. **M3.35 adds 10,000+ employee batch evidence, parallel calculator replay coverage, Hypothesis financial invariants and four targeted mutation checks. Representative production workload targets, database/queue contention and independent performance certification remain pending.**
18. Complete independent security assessment and close critical findings. **M3.36 adds the fail-closed assessment contract, high-confidence secret preflight, focused security regression tests and a dedicated CI gate. An actual independent assessment/report, independent signoff, remediation evidence and environment-specific penetration/abuse-case testing remain pending.**
19. Obtain formal finance/legal/operations certification; then produce the matching software tag, GitHub Release, artifacts and deployment evidence. **M3.37 adds the fail-closed release certification contract, M3.38 adds exact-commit evidence-bundle verification, M3.39 binds final artifacts and signing provenance, M3.40 composes these into one aggregate fail-closed release gate, M3.41 builds/verifies the concrete Release artifacts against a SHA-256 manifest, M3.42 rehearses the complete build → manifest → gate composition while keeping CI fixtures explicitly non-production, and M3.43 signs/verifies the resulting evidence bundle with an ephemeral CI Ed25519 key for rehearsal, M3.44 independently reconstructs/verifies that bundle and its source chain without any private signing capability, M3.45 adds versioned trusted-key registry enforcement with rotation/revocation semantics, and M3.46 authenticates the registry itself with a separate root-signed trust anchor, and M3.47 binds each signed evidence bundle to that exact registry ID, version and fingerprint, and M3.48 adds a deterministic rotation ceremony proving the exact N→N+1 registry transition, root trust-anchor continuity and effective replacement-key time, and M3.49 adds a root trust-anchor handoff plus emergency-recovery path using an independent Recovery Anchor, and M3.50 adds an independent verifier that composes the full signed release trust chain across three Registry versions. Real finance/legal/operations approvals, verified external evidence artifacts, cryptographic signing, publication and deployment evidence remain pending; M3.51–M3.55 remain verification/rehearsal boundaries and do not establish production publication.**

## Production gate

Morva must not be used for real payroll or real payment until all applicable legal, authoritative-data, integration, security, operational, reconciliation, load and recovery evidence is complete and formally approved.
