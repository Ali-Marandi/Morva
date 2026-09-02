# Morva — Two-Prompt Execution Compliance Matrix

**Basis:** the two implementation prompts supplied with the project.  
**Current branch:** `main`  
**Assessment date:** 2026-09-02  
**Status vocabulary:** `implemented` = code/doc path exists; `validated` = automated/environment evidence exists; `blocked` = deliberately fail-closed pending authoritative evidence.

This document is a traceability index, not a production certification.

| # | Requirement family | Current evidence | Status | Remaining acceptance |
|---|---|---|---|---|
| 1 | Repo-wide assessment and living documentation | `docs/ASSESSMENT.md`, architecture/readiness/matrix/status docs | implemented | refresh assessment against every subsequent implementation commit |
| 2 | Single canonical payroll lifecycle | `payroll/lifecycle.py`, persisted `PayrollRun`, lifecycle events | implemented | end-to-end integration test from draft through reconciliation |
| 3 | Trusted calculation boundary | legacy caller-supplied calculate endpoint blocked; persisted run + source + snapshot + Rule Pack gates | implemented | production-scale scenario certification |
| 4 | Authentication / RBAC / ABAC / MFA / SoD | OIDC/JWT boundary, hierarchical authorization, MFA and distinct-actor checks | implemented | real IdP/MFA integration and independent security evidence |
| 5 | Sensitive-data protection and immutable audit | field encryption/HMAC primitives; persistent audit chain and verifier | implemented | production key management, retention controls and restore evidence |
| 6 | PostgreSQL / migrations / operational database controls | PostgreSQL guard, Alembic migrations, CI migration gate | implemented | production backup/WAL/PITR and recovery drill |
| 7 | Demo isolation / fail-closed production | production configuration rejects unsafe modes; export remains fail-closed | implemented | prove production deployment configuration in target environment |
| 8 | Effective-dated master-data foundation | employee, personnel order, snapshots and provenance records | implemented | complete authoritative organization/personnel/rank/attendance coverage |
| 9 | Component legal/calculation matrix | `docs/domain/CALCULATION_MATRIX.md`, component catalog and Rule Pack evidence model | implemented | every active rule backed by primary legal source and approved regression corpus |
| 10 | Rule engine / versioning / safe execution | versioned Rule Packs, readiness state, safe expression path, hashes | implemented | complete 1405 legal pack and publication/retirement operational workflow |
| 11 | Retroactive calculation / historical replay | retro model, deterministic replay foundation, artifact hashes | implemented | historical legal-pack replay and certified retro cases |
| 12 | Import contract / checksum / quarantine / provenance | import batch, records, issues, source hashes and mapping gates | implemented | secured raw-data admission service and target-source validation |
| 13 | Financial reconciliation | component diffing and payroll/bank reconciliation foundations | implemented | full three-way Morva/Treasury/Bank evidence with zero unresolved mismatch |
| 14 | External integrations | typed boundaries, Outbox/Inbox, receipts and idempotency | implemented / blocked | official schemas, credentials, staging and pilot evidence for required adapters |
| 15 | Operational UI / self-service / explainability | web build, RTL foundation, persisted payslip provenance | partial | remove fabricated metrics; wire authenticated live data; complete role-based UX and PDF/accessibility |
| 16 | Test and quality framework | unit/integration/security/invariant tests plus CI and web build | partial | property-based finance tests, expanded golden corpus, load, security and DR evidence; exact-head CI must be green |
| 17 | Production certification gates | `docs/PRODUCTION_READINESS.md` and fail-closed configuration | implemented as gates | formal finance/legal approval, authoritative samples, integrations, security, DR, load and sign-off |
| 18 | Versioned push / release / publish / distribute | release workflow, release policy, Pages workflow, changelog | implemented as mechanism | green exact-head CI, matching tag, GitHub Release artifact publication and evidence record for each software release |

## Mandatory non-negotiables from the prompts

- No invented legal rates, coefficients, thresholds or circular references.
- No real employee identifiers, bank accounts, credentials or raw payroll exports in Git.
- All payroll monetary arithmetic remains `Decimal`/explicit currency.
- AI remains advisory and cannot alter legal calculation, approve payroll or release payment.
- Real payment remains fail-closed until the production gates are formally evidenced.
- Existing regression fixtures are not deleted or weakened as a shortcut to a green build.

## Current release gate

The current `main` line has active CI runs after the lint corrections. A software release is not marked complete until the exact head passes compilation, Ruff, PostgreSQL migrations, pytest, dependency audit and web build. Production authorization remains a separate gate.
