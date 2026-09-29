# Morva Payroll Platform — Delivery Roadmap

**Canonical branch:** `main`  
**Current position:** enterprise validation candidate; M4.76 persists independent M4.75 verification results with point-in-time source re-verification while preserving the governance/readiness-only boundary; not production-certified for real payroll/payment.

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
- M4.63 append-only, fingerprint-idempotent persistence of M4.62 independent receipt-history verification results with ministry-managed cursor history, M4.61 snapshot re-verification and M4.60 source re-verification
- M4.64 point-in-time integrity snapshots over the complete M4.63 receipt history with deterministic fingerprinting, cursor history and source re-verification
- M4.65 independent re-verification of M4.64 snapshots against a separately reconstructed point-in-time M4.63 receipt history with deterministic blocker codes and verification fingerprint
- M4.66 append-only, fingerprint-idempotent persistence of M4.65 independent receipt-history verification results with M4.64 snapshot and M4.63 source re-verification
- M4.67 independent verification of M4.66 persisted receipts against fresh M4.65 reconstruction with deterministic blocker codes and verification fingerprint
- M4.68 append-only, fingerprint-idempotent persistence of M4.67 independent verification results with M4.66 receipt, M4.64 snapshot and M4.63 source re-verification
- M4.69 point-in-time integrity snapshots over the complete M4.68 verification-result history with deterministic fingerprinting, cursor history and source re-verification
- M4.70 independently verifies persisted M4.69 verification-history integrity snapshots against a separately reconstructed point-in-time M4.68 source history with deterministic blockers and a verification fingerprint.
- M4.71 persists those M4.70 independent verification results as append-only, fingerprint-idempotent receipts with ministry-managed cursor history and direct re-verification.
- M4.72 captures deterministic point-in-time integrity snapshots over the complete M4.71 verification-receipt history with source re-verification and cursor history.
- M4.73 independently verifies persisted M4.72 verification-receipt history integrity snapshots against the point-in-time M4.71 receipt history with deterministic blocker codes and a verification fingerprint.
- M4.74 persists M4.73 independent verification results as append-only, fingerprint-idempotent receipts with ministry-managed cursor history, direct re-verification and point-in-time source reconstruction.
- M4.75 independently verifies persisted M4.74 verification receipts by reconstructing M4.73 from the M4.72 snapshot and point-in-time M4.71 receipt history with deterministic mismatch blockers and a verification fingerprint.
## Current execution queue

1. Keep exact `main` head green across compilation, Ruff, PostgreSQL migrations, pytest, pip-audit and web build; the active development line now extends the M4.30 freshness-policy registry through M4.76 persistence of independent M4.75 verification results.
2. Maintain the exact `main` head as the software baseline; real authoritative artifacts and staging/pilot execution remain external to the codebase and must be independently supplied, independently verified, approved and validated before any production authority is granted.
3. Refresh the technical assessment after each material implementation tranche. The M4.47–M4.76 verification-history integrity line is recorded in `docs/ASSESSMENT_2026-09-25.md`.

## Production gate

Morva must not be used for real payroll or real payment until all applicable legal, authoritative-data, integration, security, operational, reconciliation, load and recovery evidence is complete and formally approved.
