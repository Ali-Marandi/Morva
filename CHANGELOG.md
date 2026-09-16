# Changelog

All notable Morva implementation and distribution changes are recorded here.

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
