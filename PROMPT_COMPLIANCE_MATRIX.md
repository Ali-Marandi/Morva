# Morva Improvement Prompt — Compliance Matrix

This matrix tracks the release-hygiene, security and trust-hardening scope as additive controls. It does not authorize legal rates, production integrations, payment mutation or any existing fail-closed gate.

| Task | Implementation | Verification |
|---|---|---|
| 1. Version consistency | `pyproject.toml` remains `1.0.1`; CHANGELOG has a versioned `1.0.1` baseline; published tag is `v1.0.1`; published package archives are `morva_payroll-1.0.1-py3-none-any.whl` and `morva_payroll-1.0.1.tar.gz`; `scripts/check_release_hygiene.py` validates these on CI/release events | `.github/workflows/release-hygiene.yml`, main CI release-hygiene step |
| 2. Real vs. governance scaffolding | README and architecture identify real lifecycle, rules, calculator, JWT/OIDC auth and field crypto paths, and link the canonical implementation matrix for fail-closed placeholders | `README.md`, `docs/ARCHITECTURE.md`, `docs/IMPLEMENTATION_MATRIX.md` |
| 3. CI visibility | Dedicated externally visible GitHub Actions badges for lint, tests, migrations, pip-audit and web build | `README.md`, `.github/workflows/*.yml` |
| 4. Key derivation hardening | New ciphertexts use HKDF-SHA256 with explicit key-version context; legacy unversioned ciphertexts remain decryptable; decrypt-and-reencrypt is the migration path | `src/morva/security/field_crypto.py`, `tests/test_field_crypto.py` |
| 5. Independent review hooks | CONTRIBUTING requires a second independent review for security/rules/calculator/lifecycle changes and explicit self-merge disclosure until a second reviewer is onboarded | `CONTRIBUTING.md`, `.github/pull_request_template.md` |
| 6. Explicit license | MIT license file and project metadata are declared; contributions and forks are explicitly welcomed within the safety boundary | `LICENSE`, `pyproject.toml`, `CONTRIBUTING.md` |
| 7. PR/branch consolidation | Future M-series work is to be grouped into coherent tranche PRs; old history is not retroactively rewritten | `CONTRIBUTING.md` |
| 8. Realistic-data integration test | Additive test uses the existing anonymized `fixtures/1405-05` sample, drives draft→reconciled, evaluates a research/demo Rule Engine expression, calculates with Decimal, and binds every lifecycle step into the audit chain | `tests/test_1405_end_to_end_lifecycle.py` |
| 9. Local verification script | One command installs dev dependencies, runs Ruff, Pytest, pip-audit and web build, then emits a single pass/fail summary | `scripts/verify_local.sh` |

## Acceptance controls

- Existing regression suites are not removed or weakened.
- Monetary arithmetic remains Decimal-based.
- No legal rates, coefficients or thresholds are added or activated.
- No fail-closed production gate is softened.
- AI/automation remains advisory.
- Legacy field ciphertexts remain decryptable during HKDF migration.
