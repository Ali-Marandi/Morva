# M3.38 — Release candidate evidence bundle

## Purpose

M3.38 adds a deterministic verifier for a release-certification evidence bundle. It binds the evidence to an exact Git commit and then delegates readiness to the fail-closed M3.37 release certification contract.

## Evidence bundle shape

The verifier expects a JSON object containing:

- `release_id`
- `candidate_sha`
- `required_evidence`
- `verified_evidence`
- `security_signoff_complete`
- `disaster_recovery_signoff_complete`
- `load_signoff_complete`
- `reconciliation_signoff_complete`
- `signoffs` with exactly one finance, legal and operations record; each record contains `role`, `signer`, `signed_at` and `evidence_uri`.

All signoff timestamps must include an explicit timezone. The candidate SHA must be a 40-character hexadecimal Git commit SHA.

## Verification

Run:

```bash
python tools/m3_38_release_candidate_check.py path/to/release-evidence.json --expected-sha "$GITHUB_SHA"
```

When `--expected-sha` is omitted, the verifier uses `GITHUB_SHA` when present. A supplied expected SHA must exactly match the evidence bundle candidate SHA.

The verifier calls `ReleaseCertification.assert_release_ready()` and therefore fails closed when evidence is missing, a required domain is incomplete, a formal signoff is absent, or a certification condition is otherwise unmet.

## Certification boundary

M3.38 verifies the consistency and completeness of a submitted evidence bundle. It does not create or infer security, finance, legal, operations, DR, performance or reconciliation evidence. Those artifacts and approvals must be produced by their responsible authorities before release.
