# Changelog

All notable Morva implementation and distribution changes are recorded here.

## Unreleased — 2026-09-02 hardening

- Corrected migration, API, integration, artifact and test lint defects blocking the CI quality gate.
- Synchronized enterprise status documentation with `main` and removed stale branch metadata.
- Added `docs/PROMPT_COMPLIANCE_MATRIX.md` to trace the two supplied prompts to implementation/evidence state.
- Preserved fail-closed production behavior for legal rules and external payment/export until authoritative evidence exists.

## 1.0.0 — Enterprise validation lineage

- Enterprise payroll hardening consolidated the canonical payroll lifecycle and fail-closed production boundaries.
- PostgreSQL migrations became part of the CI validation path.
- Durable audit chain, rule evidence, sensitive-field protections, hierarchical authorization and integration messaging foundations are maintained.
- Employee payroll artifacts, payslip provenance and deterministic historical replay are persisted.
- Production calculation remains blocked without approved legal Rule Sets, authoritative source data and required external certifications.

### Distribution status

- Package version: `1.0.0`.
- Canonical branch: `main`.
- GitHub Pages deployment is active for the web distribution.
- Versioned GitHub Releases are produced by `.github/workflows/release.yml` when a matching `vX.Y.Z` tag is published and the full release validation succeeds.

> Software versioning and distribution do not constitute authorization for real payroll or payment release.
