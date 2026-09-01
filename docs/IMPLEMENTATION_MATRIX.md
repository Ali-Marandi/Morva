# Morva Payroll Platform — 23-Item Implementation Matrix

This matrix is the execution contract for the requested production scope.

| # | Capability | Implementation target | State |
|---|---|---|---|
| 1 | Organization & Position Master Data | hierarchical orgs, positions, assignments, effective dates | implemented-foundation |
| 2 | Personnel Order Workflow | draft/review/approve/effective/cancel/revise | implemented-foundation |
| 3 | Legal Knowledge Base | source registry, citations, versions, supersession | implemented-foundation |
| 4 | Calculation Matrix | component metadata and treatment matrix | implemented-foundation |
| 5 | 1405 Rule Pack | rule-pack manifests, legal-review gate, versioning | review-required until source verification |
| 6 | Tax / Pension / Insurance | policy abstractions + ledger interfaces + tax engine | implemented-foundation |
| 7 | High-volume Payroll | batch runner, idempotency, chunking contract | implemented-foundation |
| 8 | Retro + Jalali | Jalali period model and monthly recomputation contract | implemented-foundation |
| 9 | Loans / Debts / Deductions | ledgers and installment schedules | implemented-foundation |
| 10 | Approval / SoD | role + scope + approval policy | implemented-foundation |
| 11 | SINA Adapter | typed port, fail-closed adapter boundary | interface-ready; credentials/endpoint required |
| 12 | Accounting / Treasury / Bank | typed ports, reconciliation boundaries | interface-ready; credentials/endpoint required |
| 13 | Employee Self-Service | profile, payslips, history, objections API contracts | implemented-foundation |
| 14 | Payslip Explanation | line-level explanations and source chain | implemented-foundation |
| 15 | Rule Sandbox UI | scenario API and approval gate | implemented-foundation |
| 16 | Management Dashboard | KPI/variance/validation DTOs | implemented-foundation |
| 17 | Anomaly Detection | deterministic rules + anomaly scoring interface | implemented-foundation |
| 18 | Forecast / Budget AI | scenario/forecast interfaces; AI advisory-only | implemented-foundation |
| 19 | Production Security | RBAC, SoD, audit chain, security config | implemented-foundation |
| 20 | DR / PITR | backup/restore runbook, PostgreSQL operational hooks | implemented-foundation |
| 21 | Load / Performance | benchmark scenarios and acceptance thresholds | implemented-foundation |
| 22 | Golden Regression | fixture-driven golden payroll suite | implemented-foundation |
| 23 | Real Payroll Reconciliation | authoritative sample import/reconciliation contract | interface-ready; real samples required |

## Production rule

Items marked `review-required` or `interface-ready` must not be represented as live legal truth until the required primary source, endpoint, credential, or authoritative payroll sample has been supplied and validated.
