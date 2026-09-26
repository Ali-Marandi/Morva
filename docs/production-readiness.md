# Morva Production Readiness Gates

**Current baseline:** main snapshot reviewed 2026-09-27
**Policy:** software evidence never substitutes for external legal, finance, security, integration, or operational approval.

| Gate | Measurable acceptance criteria | Current status | Blocking evidence |
|---|---|---|---|
| 1. Legal rules | Every production Rule Pack has immutable version/hash, effective period, approved legal source/evidence, distinct review/approval, regression evidence, historical replay coverage, and explicit retro-gap/arrears tests. | **BLOCKED — software controls present** | Authoritative primary legal corpus and formal legal/finance approval for active 1405 rules. |
| 2. Valid payroll samples / Master Data | Authoritative organization/personnel hierarchy accepted; imported source records have checksum/provenance; representative payroll samples reconcile to approved source reports; golden corpus is signed/accepted. | **BLOCKED** | Ministry master-data acceptance and formally approved payroll sample corpus. |
| 3. External integrations | Separate adapters for each provider; official schemas/endpoints/credentials; contract tests; idempotency; staging acknowledgements; failure/retry evidence. | **BLOCKED — fail-closed contracts present** | Official provider contracts, credentials and staging evidence. |
| 4. Security + audit | RBAC/SoD/MFA enforced; immutable audit chain verified; encryption at rest/in transit; managed secret/key rotation; independent security review. | **BLOCKED — application controls present** | Production KMS/HSM custody, storage encryption evidence, rotation evidence, independent security sign-off. |
| 5. Reconciliation | Payroll-to-source, payroll-to-payment, provider-to-ledger and bank reconciliation prove zero unexplained difference or approved exception with audit evidence. | **BLOCKED — foundations present** | Target-population reconciliation runs, bank/provider evidence and finance approval. |
| 6. Disaster recovery | Backup/WAL/PITR configured; restore drill completed; measured RPO/RTO within approved targets; recovery verification and rollback evidence retained. | **BLOCKED — executable drill foundation present** | Target-environment restore drill and operational sign-off. |

## Gate 1 evidence checklist

- [x] Rule engine resolves rules by effective date.
- [x] Production rejects callable rule formulas.
- [x] Rule Pack activation requires approved/published status and immutable source/rule hashes.
- [x] Legal evidence requires source hash, issuer, article, population scope, regression hash and distinct reviewer/approver.
- [x] Historical replay is snapshot-bound.
- [x] Snapshot-driven retro reconciliation requires original/revised artifacts and one immutable personnel snapshot.
- [x] Personnel orders retain issue_date and effective_date independently.
- [x] Retroactive date-gap detection and arrears calculation are covered by focused regression tests.
- [ ] Authoritative legal texts are imported and formally approved.
- [ ] Population-specific tax/pension/insurance treatments are approved.
- [ ] Independent finance/legal validation of the golden payroll corpus is completed.

**Gate decision:** remains BLOCKED until every unchecked external evidence item is satisfied. No code in this gate activates real payroll/payment authority.
