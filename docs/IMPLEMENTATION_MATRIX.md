# Morva Payroll Platform — Enterprise Implementation Matrix

`Implemented` means an actual code path exists. `Validated` means the required automated and environment evidence exists. `Production Certified` requires legal/finance/security/operations/integration sign-off. No item is marked production-certified by source code alone.

| # | Capability | State |
|---|---|---|
| 1 | Organization & Position Master Data | foundation; hierarchical-scope primitive added; full authoritative master pending |
| 2 | Personnel Order Workflow | foundation; durable effective-dated workflow pending |
| 3 | Legal Knowledge Base | implemented foundation; authoritative source verification and approval pending |
| 4 | Calculation Matrix | foundation; complete legal treatment matrix pending |
| 5 | 1405 Rule Pack | `review_required` until formal legal/finance approval |
| 6 | Tax / Pension / Insurance | persisted tax, pension and insurance ledger foundations added; approved population-specific rule sets pending |
| 7 | High-volume Payroll | batch/chunk foundations; target-scale execution evidence pending |
| 8 | Retro + Jalali | deterministic period/replay foundations; complete snapshot-driven retro pending |
| 9 | Loans / Debts / Deductions | persisted loan and deduction ledger foundations added; authoritative ledgers/policies pending |
| 10 | Approval / SoD | permission + privileged + distinct-actor controls implemented; durable enterprise IAM workflow pending |
| 11 | SINA Adapter | fail-closed typed contract; official schema/endpoint/credential and staging evidence required |
| 12 | Accounting / Treasury / Bank | typed six-provider boundary + transactional outbox/inbox foundations; official adapters required |
| 13 | Employee Self-Service | role-aware RTL web shell and API foundations; complete authenticated production UX pending |
| 14 | Payslip Explanation | persisted payroll artifact + ordered line explanation implemented; legal source linking pending |
| 15 | Rule Sandbox UI | foundation; production hardening pending |
| 16 | Management Dashboard | UI foundation; authoritative live data wiring pending |
| 17 | Anomaly Detection | deterministic/scoring foundation |
| 18 | Forecast / Budget AI | advisory-only foundations |
| 19 | Production Security | OIDC/JWT, MFA gate, permissions, sensitive-field crypto primitives implemented; operational hardening and independent review pending |
| 20 | DR / PITR | executable PostgreSQL drill script + runbook added; target-environment restore evidence pending |
| 21 | Load / Performance | fixtures/scenarios; target-environment execution pending |
| 22 | Golden Regression | unit/integration/property-based foundation; expanded authoritative legal corpus pending |
| 23 | Real Payroll Reconciliation | reconciliation foundations; authoritative three-way production certification pending |
| 24 | Persistent Payroll Artifacts | implemented; employee-level deterministic result and payslip-line persistence |
| 25 | Transactional Integration Messaging | implemented foundation; official provider delivery and acknowledgement pending |
| 26 | Historical Payroll Replay | implemented foundation; production legal-rule replay certification pending |

## Canonical payroll lifecycle

`draft -> data_received -> calculating -> validating -> reviewed -> approved -> frozen -> exported -> submitted -> payment_confirmed -> reconciled`

`src/morva/payroll/lifecycle.py` is the sole state-machine implementation. `workflow.py` is compatibility-only.

## Release position

Morva is an **enterprise validation candidate**, not yet a production-certified payment system. The application deliberately remains fail-closed until legal approval, authoritative data reconciliation, official integrations, security/DR/load evidence and final finance/legal sign-off are complete.
