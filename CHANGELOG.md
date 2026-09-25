## Unreleased — M4.61 Independent M4.60 Verification

### Readiness policy governance
- Independently verify persisted M4.60 results by reconstructing the M4.59 result from the M4.58 snapshot and point-in-time M4.57 source history.
- Emit deterministic mismatch blockers and a verification fingerprint through an authenticated read-only endpoint.

### Safety
- Governance/readiness metadata only; no provider execution, credentials, payment mutation or production authority.

## Unreleased — M4.60 Independent M4.59 Verification Persistence

### Readiness policy governance
- Persist M4.59 independent receipt-history verification results as append-only, fingerprint-idempotent receipts.
- Re-verify the M4.58 source snapshot and every point-in-time M4.57 source receipt before recording, listing or directly verifying a result.
- Expose ministry-managed cursor history and direct verification of persisted M4.59 results.

### Safety
- Governance/readiness metadata only; no provider execution, credentials, payment mutation or production authority.

## Unreleased — M4.59 Independent M4.58 Receipt-History Verification

### Readiness policy governance
- Independently reconstruct the point-in-time M4.57 receipt history behind each M4.58 snapshot.
- Reverify source verification receipts and compare deterministic counts, history fingerprint and integrity fingerprint with blocker codes and a verification fingerprint.

### Safety
- Governance/readiness metadata only; no provider execution, credentials, payment mutation or production authority.

## Unreleased — M4.58 M4.57 Verification Receipt-History Integrity Snapshot

### Readiness policy governance
- Capture deterministic point-in-time integrity snapshots over the complete M4.57 independent verification receipt history.
- Re-verify every M4.57 source receipt before capture, history exposure and direct snapshot verification.
- Preserve timestamp+UUID cursor history and append-only fingerprint-idempotent snapshots.

### Safety
- Governance/readiness metadata only; no provider execution, credentials, payment mutation or production authority.

## Unreleased — M4.57 Independent M4.56 Verification Persistence

### Readiness policy governance
- Persist M4.56 independent receipt-verification results as append-only, fingerprint-idempotent receipts.
- Re-verify the M4.55 source receipt, M4.53 snapshot and point-in-time M4.52 source history before recording, listing or directly verifying a result.
- Expose ministry-managed cursor history and direct verification of persisted M4.56 results.

### Safety
- Governance/readiness metadata only; no provider execution, credentials, payment mutation or production authority.

## Unreleased — M4.56 Independent M4.55 Receipt Verification

### Readiness policy governance
- Independently reconstruct M4.54 from the M4.53 snapshot and point-in-time M4.52 receipt history behind each M4.55 verification receipt.
- Compare persisted and reconstructed verification identities with deterministic blocker codes and a verification fingerprint.
- Expose authenticated read-only independent verification of M4.55 receipts.

### Safety
- Governance/readiness metadata only; no provider execution, credentials, payment mutation or production authority.

## Unreleased — M4.55 M4.54 Verification Receipt Persistence

### Readiness policy governance
- Persist M4.54 independent verification results as append-only, fingerprint-idempotent receipts over M4.53 snapshots.
- Re-verify the M4.53 source snapshot and every point-in-time M4.52 verification receipt before recording, listing or directly verifying a receipt.
- Expose ministry-managed cursor history and direct receipt verification.

### Safety
- Governance/readiness metadata only; no provider execution, credentials, payment mutation or production authority.

## Unreleased — M4.54 Independent M4.53 Receipt-History Verification

### Readiness policy governance
- Independently reconstruct the point-in-time M4.52 receipt history behind each M4.53 snapshot.
- Reverify source verification receipts and compare deterministic counts, history fingerprint and integrity fingerprint with blocker codes and a verification fingerprint.

### Safety
- Governance/readiness metadata only; no provider execution, credentials, payment mutation or production authority.

## Unreleased — M4.53 M4.52 Receipt-History Integrity Snapshot

### Readiness policy governance
- Capture deterministic point-in-time integrity snapshots over the complete M4.52 independent verification receipt history.
- Re-verify every M4.52 source receipt before capture, history exposure and direct snapshot verification.
- Preserve timestamp+UUID cursor history and append-only fingerprint-idempotent snapshots.

### Safety
- Governance/readiness metadata only; no provider execution, credentials, payment mutation or production authority.

## Unreleased — M4.52 Independent Receipt-History Verification Persistence

### Readiness policy governance
- Persist M4.51 independent receipt-history verification results as append-only, fingerprint-idempotent receipts.
- Re-verify the M4.50 snapshot and every point-in-time M4.49 source receipt before recording or verifying a receipt.
- Expose ministry-managed receipt creation, cursor history and direct verification.

### Safety
- Governance/readiness metadata only; no provider execution, credentials, payment mutation or production authority.

## Unreleased — M4.51 Independent Historical Verification Receipt History Integrity

### Readiness policy governance
- Independently reconstruct the point-in-time M4.49 receipt history behind each M4.50 snapshot.
- Reverify source receipts and compare deterministic counts, history fingerprint and integrity fingerprint with blocker codes and a verification fingerprint.

### Safety
- Governance/readiness metadata only; no provider execution, credentials, payment mutation or production authority.

## Unreleased — M4.50 Historical Independent Verification Receipt History Integrity

### Readiness policy governance
- Persist point-in-time integrity snapshots over the complete M4.49 independent verification receipt history.
- Re-verify every source receipt before capture, listing and direct snapshot verification; preserve ministry-managed cursor history.

### Safety
- Governance/readiness metadata only; no provider execution, credentials, payment mutation or production authority.

## Unreleased — M4.49 Independent Historical Verification History Integrity Receipts

### Readiness policy governance
- Persist independent M4.48 history-integrity verification results as append-only, fingerprint-idempotent receipts.
- Reconstruct and re-verify the point-in-time M4.46 source history whenever a receipt is recorded, listed or directly verified.
- Expose ministry-managed cursor history with deterministic validity filtering.

### Safety
- Governance/readiness metadata only; no provider execution, credentials, payment mutation or production authority.

## Unreleased — M4.48 Independent Historical Verification History Integrity

### Readiness policy governance
- Independently reconstruct the point-in-time M4.46 verification history behind an M4.47 integrity snapshot without invoking the M4.47 integrity builder.
- Compare aggregate counts, history fingerprint and integrity fingerprint with deterministic blocker codes and a verification fingerprint.
- Expose an authenticated read-only independent-verification endpoint and a dedicated CI gate.

### Safety
- Governance/readiness metadata only; no provider execution, credentials, payment mutation or production authority.

## 1.0.1 — Current distribution baseline

The canonical distribution identifier remains `1.0.1`, matching the published Git tag `v1.0.1` and its distributed package archives `morva_payroll-1.0.1-py3-none-any.whl` and `morva_payroll-1.0.1.tar.gz`. Development entries below remain separately marked `Unreleased`.

## Unreleased — Release Hygiene & Security Trust Hardening

### Process and transparency
- Add version/tag/distribution archive consistency validation and dedicated CI enforcement.
- Add real-vs-governance-scaffolding documentation and externally visible lint, test, migration, pip-audit and web-build badges.
- Add independent-review governance for security, rules, calculator and lifecycle changes.
- Add explicit MIT licensing and contribution/fork policy.
- Add a reusable local verification script covering dependency installation, Ruff, Pytest, pip-audit and the web build.

### Security
- Add HKDF-SHA256 derivation for new AES-GCM field ciphertexts with versioned envelopes.
- Preserve decryption of legacy unversioned ciphertexts and document decrypt-and-reencrypt migration.
- Add additive field-crypto and realistic `fixtures/1405-05` lifecycle/rule/audit integration coverage.

## Unreleased — M4.47 Historical Verification History Integrity Snapshots

### Readiness policy governance
- Persist a deterministic aggregate SHA-256 integrity snapshot over the complete M4.46 independent historical freshness verification history.
- Re-verify every M4.46 source record before snapshot capture, history listing and snapshot verification.
- Expose ministry-managed cursor history and point-in-time snapshot re-verification without adding production authority.

### Safety
- Governance/readiness metadata only; no provider execution, credentials, payment mutation or production authority.

## Unreleased — M4.46 Independent Verification Receipt Persistence

### Readiness policy governance
- Persist M4.45 independent historical freshness receipt verification as append-only, fingerprint-idempotent evidence.
- Expose ministry-managed cursor history with valid/chain-valid filters and source-chain re-verification.
- Keep the evidence boundary verification-only with no provider execution or production authority.

### Safety
- Governance/readiness metadata only; no provider execution, credentials, payment mutation or production authority.

## Unreleased — M4.45 Independent Historical Freshness Receipt Verification

### Readiness policy governance
- Independently reconstruct the M4.36 → M4.37 → M4.40 → M4.41 chain and compare it field-by-field with the persisted M4.44 verification receipt.
- Emit deterministic receipt-verification identity and mismatch state through a read-only API.
- Keep verification-only semantics with no provider execution, credentials or production authority.

### Safety
- Governance/readiness metadata only; no provider execution, credentials, payment mutation or production authority.

## Unreleased — M4.44 Historical Freshness Chain Verification Receipts

### Readiness policy governance
- Persist M4.43 historical freshness chain-verification results as append-only receipts with deterministic fingerprint idempotency.
- Reconstruct the underlying M4.36 → M4.37 → M4.40 → M4.41 chain before accepting or re-verifying each receipt.
- Expose ministry-managed cursor history and a direct authenticated receipt verification API.

### Safety
- Governance/readiness metadata only; no provider execution, credentials, payment mutation or production authority.

## Unreleased — M4.43 Historical Freshness Chain Verifier

### Readiness policy governance
- Independently reconstruct the M4.36 → M4.37 → M4.40 → M4.41 historical freshness chain.
- Emit deterministic verified/blocked state, blocker codes and a chain fingerprint.
- Expose an authenticated read-only chain-verification API without production authority.

### Safety
- Governance/readiness metadata only; no provider execution, credentials, payment mutation or production authority.

## Unreleased — M4.42 Historical Snapshot-Bound Freshness Receipt Lineage History

### Readiness policy governance
- Expose deterministic newest-first history for M4.41 lineage records with timestamp+UUID cursors and optional receipt/binding/snapshot filters.
- Re-verify every selected lineage record against its M4.40 receipt and M4.37 historical binding before exposure.
- Keep lineage-history access ministry-managed and read-only; no new production authority is introduced.

### Safety
- Governance/readiness metadata only; no provider execution, credentials, payment mutation or production authority.

## Unreleased — M4.41 Historical Snapshot-Bound Freshness Receipt Lineage

### Readiness policy governance
- Link each M4.40 historical freshness receipt to the exact M4.37 historical receipt-to-snapshot binding.
- Revalidate snapshot, registry and policy continuity across M4.37 and M4.40 before accepting lineage.
- Expose ministry-managed lineage creation and read-only independent verification.

### Safety
- Governance/readiness metadata only; no provider execution, credentials, payment mutation or production authority.

## Unreleased — M4.40 Historical Snapshot-Bound Freshness Receipts

### Readiness policy governance
- Persist M4.39 historical snapshot-bound freshness evaluations as append-only, fingerprint-idempotent receipts.
- Reconstruct the exact M4.36 snapshot and snapshot-resolved policy during independent receipt verification.
- Expose ministry-managed receipt creation plus read-only cursor history and verification APIs.

### Safety
- Governance/readiness metadata only; no provider execution, credentials, payment mutation or production authority.

## Unreleased — M4.39 Historical Snapshot-Bound Freshness Evaluation

### Readiness policy governance
- Evaluate convergence freshness using a policy resolved only from an independently reconstructed historical registry snapshot.
- Bind the result to the exact snapshot and registry identities with deterministic SHA-256.