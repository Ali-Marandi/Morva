# Morva Payroll Platform — Delivery Roadmap

**Canonical branch:** `main`  
**Current position:** enterprise validation candidate; not production-certified for real payroll/payment.

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
- CI for Python 3.12/3.13, PostgreSQL, migrations, Ruff, pytest, dependency audit and web build
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

## Current execution queue

1. Keep exact `main` head green across compilation, Ruff, PostgreSQL migrations, pytest, pip-audit and web build.
2. Refresh the technical assessment after each material implementation tranche. **M3.16/M3.17 refresh recorded in `docs/ASSESSMENT_2026-09-09.md`; M3.18 personnel-order governance recorded in `docs/M3_17_PERSONNEL_ORDER_LIFECYCLE.md`.**
3. Complete authoritative organization/personnel/rank/attendance master data. **M3.17 strengthened referential, temporal and workflow-integrity gates; M3.19 added accepted/current/untampered readiness; M3.20 adds explicit drift detection against accepted evidence; M3.23 adds exact population attestation. Authoritative source confirmation and complete population evidence remain pending outside the codebase.**
4. Complete personnel-order lifecycle and approval evidence. **M3.18 implemented immutable order fingerprint binding and fail-closed effective-state verification; authoritative order schema and organizational approval policy remain pending.**
5. Complete legal component matrix and annual Rule Packs from primary sources. **M3.21 enforces the primary-source evidence contract, M3.24 binds every required 1405 component to source evidence; exact primary artifacts and formal approvals remain pending.**
6. Complete tax, pension, insurance, loans and judicial-deduction ledgers with approved treatments. **M3.12 governance boundary and M3.25 population-scoped activation boundary are implemented; authoritative treatment evidence, immutable population bindings and approved population-specific rules remain pending.**
7. Complete snapshot-driven retroactive recalculation and certified historical replay corpus. **M3.13 software provenance/reconciliation controls and M3.26 replay certification boundary are implemented; authoritative historical replay corpus, certified retro cases and approval evidence remain pending.**
8. Remove remaining demonstration-only frontend behavior and wire operational views to authenticated APIs. **M3.14 completed for the primary dashboard/employee views.**
9. Complete employee self-service, objection/case management and production PDF/reporting. **M3.15 foundation and M3.16 UX hardening implemented: authenticated self-service profile/payslips/orders, artifact-bound PDF download, persistent employee cases, payslip detail/provenance view, period filter and resilient download UX. M3.22 identity-directory reconciliation is now implemented; broader reporting, document-template certification and enterprise grievance policy/SLA evidence remain pending.**
10. Implement official SINA, accounting, treasury, bank, tax and insurance adapters only from authoritative contracts.
11. Run staging tests for every adapter and at least one pilot environment where authorized.
12. Complete end-to-end three-way reconciliation: Morva entitlement ↔ Treasury/PFM instruction ↔ Bank settlement. **M3.27 software hard-stop contract is implemented; M3.32 now blocks settlement at the payment-batch boundary when any member item has an unresolved exception. Live adapter evidence and authorized staging/pilot settlement remain pending.**
13. Extend M3.30 from persisted exception/resolution state into API/UI workflows and settlement-linked payment-item/batch operations. **M3.31 adds authenticated provider-neutral API workflows for exception creation, open/all listing, immutable event history and idempotent resolution. M3.32 adds a provider-neutral batch/item release guard that consumes the existing exception state and fails closed. Provider-specific settlement behavior remains prohibited without authoritative contracts.**
14. Complete production key-management, encryption-at-rest, secret rotation and retention controls.
15. Execute encrypted backup, WAL/PITR restore and disaster-recovery drills with recorded RTO/RPO evidence.
16. Execute target-scale load/concurrency, mutation and financial property-based tests.
17. Complete independent security assessment and close critical findings.
18. Obtain formal finance/legal/operations certification; then produce the matching software tag, GitHub Release, artifacts and deployment evidence.

## Production gate

Morva must not be used for real payroll or real payment until all applicable legal, authoritative-data, integration, security, operational, reconciliation, load and recovery evidence is complete and formally approved.
