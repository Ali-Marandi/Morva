# Morva — Technical & Production Assessment Refresh

**Assessment date:** 2026-09-25  
**Repository:** `Ali-Marandi/Morva`  
**Canonical branch:** `main`  
**Assessed development head:** `b575f689a8ba459bfae4807d962305112b41ec8c`  
**Assessment basis:** M4.19–M4.44 persisted integration-readiness/freshness/history line, release/security hardening, and the current cumulative CI state

> **Safety statement:** This refresh is an engineering assessment only. It does not certify Morva for real payroll or payment. Legal rules, authoritative source status, external integration authority, operational controls and organizational approvals remain subject to independent evidence and formal approval.

## Executive assessment

The M4 readiness line has progressed from persisted integration-execution evidence through scope-bound convergence, explicit freshness-policy identity, historical registry reconstruction, receipt-to-snapshot binding, historical freshness receipts, lineage history and the M4.43 independent chain verifier.

At the assessed head, M4.43 independently reconstructs the M4.36 → M4.37 → M4.40 → M4.41 identity chain and produces deterministic verified/blocked blocker codes and a chain fingerprint through a read-only verification boundary. The complete CI matrix for this head finished with **55/55 workflow runs successful, 0 failures and no queued/in-progress runs**.

The repository therefore has strong automated integrity for the implemented and tested software paths. M4.44 additionally persists the M4.43 verification result as a fingerprint-idempotent receipt, exposes ministry-managed cursor history with re-verification, and provides a direct receipt verification API. This remains distinct from production certification. The principal unresolved production dependencies are still external: authoritative population and legal evidence, official provider contracts and staging/pilot execution evidence, operational key custody, disaster-recovery/load/security certification, live three-way financial reconciliation, and formal finance/legal/operations approval.

## Current maturity snapshot

| Area | Assessment | Evidence / remaining boundary |
|---|---|---|
| Architecture and domain foundations | Strong | Persisted payroll lifecycle, effective-dated rule evaluation, Decimal calculation, scoped authorization and durable audit/integration foundations are implemented |
| Integration-readiness governance | Strong | M3.82–M3.88 and M4.19–M4.27 provide typed contracts, independent verification, persisted readiness, scope binding and convergence controls; live provider execution remains external |
| Freshness and historical integrity | Strong | M4.28–M4.43 add explicit policy identity, registry integrity, historical snapshot reconstruction, lineage persistence/history and independent chain verification |
| Security / cryptography | Strong in application scope | Versioned field encryption, managed-key primitives, fail-closed configuration and security gates are implemented; KMS/HSM custody, operational rotation and independent production security assessment remain pending |
| Web operational readiness | Strong | Primary operational views and employee self-service are API-backed with resilient error/empty handling and artifact/provenance controls; broader enterprise certification remains pending |
| Master-data / legal authority | Governance-ready, externally incomplete | Integrity and evidence contracts exist, but authoritative datasets, legal matrices and formal approvals remain outside the codebase |
| External integrations | Evidence-bound, not activated | Official adapter contract/evidence verification exists; authoritative endpoints, credentials and staging/pilot execution evidence remain pending |
| DR / performance / operations | Partially implemented | CI covers executable controls and rehearsals; target-environment RPO/RTO, scale certification and operational drills remain pending |
| Release / production trust | Strong verification boundary | Release evidence, signing/trust-chain and production-readiness verification layers are present; external certification and authorized publication/deployment evidence remain pending |
| Overall position | **Enterprise validation candidate** | Not production-certified and must remain fail-closed for real payroll/payment authority |

## Closed or materially strengthened findings since the previous assessment

- M4.19–M4.27 formalize the software-side bridge from independently verified staging/pilot execution evidence to scope-bound persisted readiness and convergence observations.
- M4.28–M4.35 make freshness explicit, versioned and registry-integrity-bound rather than relying on hidden operational windows.
- M4.36–M4.40 establish immutable historical registry snapshots, exact membership reconstruction, historical policy resolution, historical freshness evaluation and persisted historical receipts.
- M4.41–M4.42 add historical freshness lineage and deterministic, ministry-managed lineage history with source-record re-verification.
- M4.43 independently reconstructs the complete historical freshness identity chain and exposes deterministic verification status through a read-only API.
- M4.44 persists M4.43 results as append-only, fingerprint-idempotent receipts, re-verifies persisted receipts against the underlying historical chain, and exposes ministry-managed history plus direct receipt verification.
- Release/security hardening adds explicit version consistency checks, HKDF-based new field-encryption derivation with legacy decrypt compatibility, reproducible local verification and independent-review governance hooks.
- The assessed head completed the repository workflow matrix with **55 successful runs out of 55**, with 0 failures and no queued/in-progress runs.

## Remaining high-priority gaps

1. Authoritative organization/personnel/rank/attendance source confirmation and complete approved population evidence.
2. Official personnel-order schema and real organizational approval policy confirmation with formal sign-off.
3. Primary-source annual legal Rule Packs and approved population-specific tax/pension/insurance/deduction treatments.
4. Certified historical replay corpus and approved retroactive calculation evidence.
5. Official SINA/accounting/treasury/bank/tax/insurance adapters with authoritative contracts and authorized staging/pilot execution.
6. End-to-end three-way reconciliation and complete payment return/reversal/exception operational certification.
7. Production KMS/HSM custody, automated secret rotation, encryption-at-rest, retention and recovery-key segregation evidence.
8. Target-environment load/concurrency, DR/PITR execution, RPO/RTO evidence and independent security assessment.
9. Formal finance/legal/operations certification and controlled production release/deployment evidence.

## Production position

A fully green CI matrix demonstrates engineering integrity for the tested repository paths; it does not establish legal, financial, operational or production authority.

Morva must remain fail-closed for real payroll and real payment until the applicable authoritative evidence, external integration contracts, operational controls, reconciliation evidence and formal approvals are independently supplied, verified and approved.
