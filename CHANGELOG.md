## Unreleased — M4.12 Evidence Convergence

### Evidence convergence
- Converge certification-role receipts against the exact M4.1 registry fingerprint.
- Require canonical binding kinds, correct authoritative source types, current accepted evidence and matching population scope.
- Preserve explicitly blocked roles when real external evidence has not yet been supplied.
- Produce a deterministic convergence fingerprint for the current evidence state.

### Safety
- No approval, legal evidence, payroll sample, adapter execution, security assessment or DR drill is synthesized.
- Convergence is a readiness artifact, not production certification.

## Unreleased — M4.11 Load Validation Evidence

### Performance evidence closure
- Bind target-scale load results to exact workload profile and population scope.
- Require processed population to equal target population and enforce a minimum 10,000-employee validation target.
- Require throughput to be numerically consistent with target population and measured elapsed time.
- Require distinct reviewer/approver provenance and accepted authoritative `load_validation` evidence.

### Safety
- No production capacity certification, live workload data or employee records are introduced.

## Unreleased — M4.10 Security Evidence Bridge

### Security evidence closure
- Bind a release-ready `SecurityAssessment` to accepted M4.1 `security_assessment` evidence.
- Require complete verified controls, no open critical/high findings and independent assessor/report/signature metadata.
- Require exact report URI and canonical assessment fingerprint binding.
- Fail closed on future-dated signatures, expired/unaccepted authority and identity mismatches.

### Safety
- No external security assessment is executed and no findings are invented.
- No credentials, production access or security secrets are introduced.

## Unreleased — M4.9 Disaster-Recovery Evidence Bridge

### Recovery evidence closure
- Bind a recorded DR drill to accepted M4.1 `dr_report` evidence.
- Require RPO/RTO compliance, WAL replay, point-in-time verification and encrypted-backup verification.
- Bind the canonical drill fingerprint and evidence URI to the authoritative evidence item.
- Preserve fail-closed approval, effective-window and expiry checks.

### Safety
- No production restore, infrastructure mutation, backup access or real DR certification is performed.

## Unreleased — M4.8 Three-Way Reconciliation Evidence

### Reconciliation evidence closure
- Bind Morva entitlement, Treasury/PFM instruction and bank settlement artifacts with three independent SHA-256 identities.
- Bind a separate SHA-256 for the authoritative reconciliation-evidence document.
- Require explicit reconciled status, comparison fingerprint and exact population/period scope.
- Keep live payment, Treasury and bank execution outside the bridge.

### Safety
- No production payment, Treasury call, bank call, financial record or employee record is introduced.

## Unreleased — M4.7 Authoritative Payroll Sample Evidence

### Payroll validation evidence
- Bind approved reference samples to exact population scope and Jalali payroll period.
- Bind input/expected-output/comparison identities with SHA-256 fingerprints.
- Require distinct reviewer/approver provenance and current accepted M4.1 `payroll_sample` evidence.
- Keep real payroll records and amounts outside the repository.

### Safety
- No employee record, payroll amount, statutory rate or production payment authority is introduced.

## Unreleased — M4.6 Adapter-Contract Evidence Bridge

### Integration evidence closure
- Bind official adapter evidence to accepted authoritative adapter-contract evidence.
- Require exact contract-source URI and SHA-256 artifact identity.
- Validate authority approval, effective window and expiry at binding time.
- Preserve provider, schema version, repository and candidate SHA from the existing adapter-evidence contract.
- Keep provider activation and credential use outside the bridge.

### Safety
- No endpoint activation, live integration call, credential or production mutation is introduced.

## Unreleased — M4.5 Rule-Pack Evidence Bridge

### Legal evidence closure
- Bind 1405 Rule Pack component evidence to accepted M4.1 `legal_rule` evidence.
- Require exact source URI, issuer and SHA-256 identity plus population scope.
- Preserve explicit treatment classification and distinct reviewer/approver provenance.
- Keep Rule Pack activation `review_required` until formal activation evidence exists.

### Safety
- No statutory numeric rate, threshold, exemption amount, ministry dataset, employee record or production activation is introduced.

## Unreleased — M4.4 Master-Data Evidence Bridge

### Authoritative master-data closure
- Bind accepted M4.1 `master_data` evidence to the internal master-data acceptance assessment.
- Require exact population-scope and SHA-256 equality, authority confirmation and preserved integrity fingerprints.
- Require a distinct binding actor and current approval/effective/expiry validation.
- Fail closed on missing, unaccepted, future, expired, out-of-scope or hash-inconsistent evidence.

### Safety
- No employee records, national identifiers, ministry datasets, credentials or production mutation is introduced.

## Unreleased — M4.3 Population-Scoped Treatment Evidence

### Legal treatment closure
- Bind each 1405 payroll component to accepted authoritative legal evidence for an exact population scope.
- Require explicit earning/deduction and tax/pension/insurance treatment classification.
- Require distinct reviewer/approver provenance and fail-closed effective/approval/expiry validation.
- Keep activation blocked until the underlying authoritative evidence is current and approved.

### Safety
- No statutory numeric rate, threshold, exemption amount, ministry dataset, employee record or production activation is introduced.

## Unreleased — M4.2 Evidence Closure Matrix

### Evidence closure
- Map all twelve production-certification roles to canonical provider-neutral evidence source types.
- Evaluate only accepted, currently effective, approved and non-expired evidence from the M4.1 registry.
- Produce deterministic closure assessments bound to the exact registry fingerprint.
- Add regression coverage and a dedicated CI gate.

### Safety
- No real external authority, ministry dataset, employee record, statutory rate, credential or production activation is introduced.
- A complete closure assessment is not itself production certification; underlying authoritative evidence and approvals remain external prerequisites.

## Unreleased — M4.1 Authoritative Evidence Intake

### Evidence closure
- Add a provider-neutral authoritative evidence intake contract with stable evidence IDs, source URI, SHA-256 source identity and exact population scope.
- Record effective validity windows, issuer, approval actor/time, status and optional expiry without embedding real external evidence.
- Add deterministic item/registry fingerprints, duplicate-ID protection, write-once registry output and explicit fail-closed activation-readiness evaluation.
- Add focused regression coverage and a dedicated CI gate.

### Safety
- No ministry datasets, employee records, statutory rates, credentials, external provider activation or production payment mutation is introduced.
- Activation readiness only reflects the software contract; authoritative evidence still requires real external artifacts and independent approval.

## Unreleased — M3.89 Readiness Verifier Contract Hardening

### Integration readiness
- Harden the M3.88 receipt boundary with canonical adapter identity, candidate-SHA validation, SHA-256 fingerprint checks and timezone-aware verification time.
- Add regression coverage for tampered readiness evidence and non-canonical adapter sets.

### Safety
- Verification-only; no provider activation, production credentials or deployment mutation is introduced.

# Changelog

All notable Morva implementation and distribution changes are recorded here.

## Unreleased — M3.90 Dynamic Workflow Execution Hardening

### Security / CI integrity
- Reject indirect dynamic shell execution patterns in GitHub Actions workflow scans.
- Extend the production-boundary scanner with the same fail-closed dynamic execution policy.
- Add dedicated regression coverage and a focused M3.90 CI gate.

### Safety
- Static verification only; no external integration activation, credentials or production mutation is introduced.
### Compatibility / verification follow-up
- Align M3.58–M3.67 fixture contracts with timezone-aware evidence and environment binding.
- Preserve exact validation failures while hardening persisted verifier fingerprint checks.
- Keep legacy CI tooling Ruff-clean while retaining fail-closed production-boundary behavior.

## Unreleased — M3.33 Managed Key Hardening

### Production security
- Add a provider-neutral, versioned `ManagedKeyRing` with exactly one active application key version and retained versions for rotation compatibility.
- Encrypt sensitive application fields with AES-256-GCM using a random 96-bit nonce and optional associated data.
- Generate context-bound HMAC-SHA-256 lookup tokens so sensitive lookup values do not require reversible plaintext indexes.
- Bind encrypted values to their key version and fail closed when the referenced version is no longer retained.
- Require matched, correctly sized encryption/HMAC key material and versioned key maps in production configuration.
- Add a configurable minimum managed-key retention window of 30 days, defaulting to 90 days.
- Document the separation between application cryptography and infrastructure responsibilities such as KMS/HSM custody, storage encryption-at-rest, backup-key segregation and automated secret rotation.

### CI / verification
- Add dedicated M3.33 regression coverage for encryption/decryption, context binding, key rotation, retired-key failure and production configuration enforcement.
- Add a dedicated M3.33 GitHub Actions hardening gate.

### Safety
- No provider-specific bank/Treasury credentials, payment authority, statutory rates or live settlement behavior are introduced.
- Production certification remains blocked pending operational key custody, database/storage encryption evidence, rotation/retention evidence, independent security review and the other release gates in `docs/ROADMAP.md`.

## Unreleased — M3.31 Payment Exception API Workflow

### Payment exception operations
- Add authenticated provider-neutral API endpoints to create and list payment exceptions.
- Add immutable resolution event-history endpoint for operational/audit views.
- Add resolution endpoint requiring actor, reason, evidence reference and `Idempotency-Key`.
- Enforce RBAC through the existing `payroll.payment.reconcile` permission boundary.
- Preserve idempotent replay behavior without duplicating the resolution audit event.
- Add dedicated M3.31 API regression CI gate covering create/list/resolve/replay/second-resolution behavior.

### Safety
- No live bank/Treasury integration, provider-specific contract, statutory amount, retry policy or production payment authority is introduced.
- Settlement-linked payment-item/batch operations remain pending until authoritative provider contracts are available.
- M3.27 reconciliation and M3.28/M3.29/M3.30 exception controls remain mandatory.

## Unreleased — M3.30 Payment Exception Persistence

### Payment exception persistence
- Persist provider-neutral payment exception state in SQLAlchemy/PostgreSQL-compatible schema.
- Persist immutable resolution events with actor, reason, evidence reference, timezone-aware timestamp and deterministic fingerprint.
- Add a transactional resolution boundary with idempotency-key replay safety.
- Keep payment-item release fail-closed while any exception remains open or blocked.
- Add Alembic migration `0021_payment_exception_persistence` and dedicated regression CI coverage.

### Safety
- No live bank/Treasury integration, provider-specific contract, statutory amount, retry policy or production payment authority is introduced.
- M3.27 reconciliation and M3.28/M3.29 exception controls remain mandatory.

## Unreleased — M3.29 Payment Exception Resolution Ledger

### Payment exception governance
- Add immutable provider-neutral payment exception resolution events.
- Require explicit resolution actor, reason and evidence reference.
- Require timezone-aware event timestamps.
- Add deterministic SHA-256 event fingerprints and tamper verification.
- Reject second resolution-event creation for already-resolved exceptions.
- Add dedicated M3.29 CI regression gate.

### Safety
- No live bank/Treasury integration, provider-specific contract, statutory amount, retry policy or production payment authority is introduced.
- M3.27 reconciliation and M3.28 fail-closed exception release controls remain mandatory.

## 1.0.1 — 2026-09-06 Security & CI Patch Release

### Security
- Upgrade `cryptography` from the vulnerable 46.x constraint to the audited 50.x line.
- Dependency audit is now clean in the release-candidate CI path.

### CI/CD
- Python 3.12 and 3.13 test suites pass.
- Alembic migration validation passes.
- Ruff lint passes.
- Web production build passes.
- `pip-audit` passes.

### Compatibility
- Align the API lifecycle regression test with the canonical `draft -> data_received` state boundary.
- Preserve production authentication and fail-closed payroll controls.

### Distribution status
- **Package version:** `1.0.1`
- **Canonical branch:** `main`
- **Release tag:** `v1.0.1`
