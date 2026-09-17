# M3.40 — Aggregate release gate

## Scope

M3.40 composes the existing M3.36 security-assessment, M3.37 release-certification and M3.39 release-attestation contracts into one deterministic, fail-closed release gate.

## Required consistency

The aggregate gate requires the candidate Git commit SHA to match the SHA recorded by both the formal certification and the release attestation. Any mismatch is rejected before release readiness is evaluated.

## Required domains

The aggregate result is ready only when:

- the independent security assessment is release-ready;
- the formal finance/legal/operations certification is release-ready;
- the release provenance and signing attestation is release-ready.

The gate exposes structured blockers so missing evidence can be remediated without inferring or manufacturing approval.

## CLI and CI

`tools/m3_40_release_gate.py` evaluates a JSON evidence bundle containing the three underlying evidence domains. `.github/workflows/m3-40-release-gate.yml` runs Ruff, focused tests and tooling import checks.

This is a software governance gate. It does not create signatures, security assessments, DR evidence, performance certification, reconciliation evidence or human approvals.
