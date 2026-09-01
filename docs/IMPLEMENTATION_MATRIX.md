# Morva Payroll Platform — 23-Item Implementation Matrix

This matrix is the execution contract for the requested production scope. `Implemented` means an actual code path exists; it does not mean production certification.

| # | Capability | Implementation target | State |
|---|---|---|---|
| 1 | Organization & Position Master Data | hierarchical orgs, positions, assignments, effective dates | foundation; full hierarchy pending |
| 2 | Personnel Order Workflow | draft/review/approve/effective/cancel/revise | foundation; full durable workflow pending |
| 3 | Legal Knowledge Base | source registry, citations, versions, supersession | implemented; formal source verification pending |
| 4 | Calculation Matrix | component metadata and treatment matrix | foundation; complete legal matrix pending |
| 5 | 1405 Rule Pack | rule-pack manifests, legal-review gate, versioning | `review_required` for final activation |
| 6 | Tax / Pension / Insurance | policy abstractions + ledger interfaces + tax engine | foundation; population-specific approved rules pending |
| 7 | High-volume Payroll | batch runner, idempotency, chunking contract | contract/foundation; target-scale execution evidence pending |
| 8 | Retro + Jalali | Jalali period model and monthly recomputation contract | foundation; full snapshot-driven retro pending |
| 9 | Loans / Debts / Deductions | ledgers and installment schedules | foundation; authoritative ledgers pending |
| 10 | Approval / SoD | role + scope + approval policy | foundation implemented; durable lifecycle enforcement pending |
| 11 | SINA Adapter | typed port, fail-closed adapter boundary | fail-closed; official endpoint/schema/credential required |
| 12 | Accounting / Treasury / Bank | typed ports, reconciliation boundaries | fail-closed; official endpoint/schema/credential required |
| 13 | Employee Self-Service | profile, payslips, history, objections API contracts | contracts/foundation; complete production UX pending |
| 14 | Payslip Explanation | line-level explanations and source chain | foundation; persisted payslip artifact pending |
| 15 | Rule Sandbox UI | scenario API and approval gate | foundation; production hardening pending |
| 16 | Management Dashboard | KPI/variance/validation DTOs | foundation; authoritative live data wiring pending |
| 17 | Anomaly Detection | deterministic rules + anomaly scoring interface | foundation |
| 18 | Forecast / Budget AI | scenario/forecast interfaces; AI advisory-only | foundation |
| 19 | Production Security | RBAC, SoD, audit chain, security config | hardening foundation; operational security evidence pending |
| 20 | DR / PITR | backup/restore runbook, PostgreSQL operational hooks | runbook/foundation; restore-drill evidence pending |
| 21 | Load / Performance | benchmark scenarios and acceptance thresholds | fixtures/scenarios; target-environment execution pending |
| 22 | Golden Regression | fixture-driven golden payroll suite | foundation; expanded legal corpus pending |
| 23 | Real Payroll Reconciliation | authoritative sample import/reconciliation contract | ready for authoritative samples; not certified |

## Canonical lifecycle

`draft -> data_received -> calculating -> validating -> reviewed -> approved -> frozen -> exported -> submitted -> payment_confirmed -> reconciled`

`src/morva/payroll/lifecycle.py` is the sole state-machine implementation. `workflow.py` is compatibility-only and contains no independent state definition.

## Release position

Morva remains a **release candidate / controlled validation platform**. No real-payroll, bank-payment, legal-certification or SINA-certification claim is made. The platform stays fail-closed until legal approval, authoritative data, official integration evidence, security/DR/load evidence and all production gates are satisfied.
