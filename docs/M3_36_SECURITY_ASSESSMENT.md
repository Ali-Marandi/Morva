# M3.36 — Independent Security Assessment Preflight

## Purpose

M3.36 establishes the software evidence boundary required before an independent security assessment. It does **not** represent an independent assessment, a penetration test, a certification, or production approval.

## Required independent evidence

The release boundary requires a dated assessment record containing:

- a unique assessment identifier and immutable scope hash;
- the independent assessor identity;
- a retained report/evidence URI and independent signature timestamp;
- verification evidence for authentication, authorization, cryptography, auditability, supply chain, secrets and availability controls;
- a finding register with severity and disposition;
- no open critical or high findings;
- a deterministic assessment fingerprint.

The application contract in `src/morva/runtime/security_assessment.py` fails closed until all of those conditions are satisfied.

## Implemented preflight

`tools/m3_36_security_preflight.py` scans source, tests, tooling and operational scripts for high-confidence private-key and token signatures. It intentionally avoids broad password-word heuristics so normal test fixtures and configuration names do not create false positives.

`.github/workflows/m3-36-security-preflight.yml` runs the preflight, Ruff and the focused assessment contract tests.

The repository's broader CI already runs `pip-audit`; M3.36 does not treat dependency scanning as a substitute for an independent application security assessment.

## Current state

The repository is **not independently security-assessed** by this gate alone. Until an external assessor supplies the required report, signoff timestamp and finding disposition, `SecurityAssessment.release_ready` remains false and `assert_release_ready()` fails closed.

## External evidence still required

An independent assessor must perform the agreed threat-model, application, API, authentication/authorization, data-protection, dependency/supply-chain, operational-secret, backup/recovery and abuse-case review appropriate to the deployment environment. Findings must be tracked to remediation or documented false-positive disposition, with formal risk acceptance handled outside this code contract where applicable.
