# Morva Payroll Platform — 23-Item Implementation Matrix

This matrix is the execution contract for the requested production scope.

| # | Capability | Implementation target | State |
|---|---|---|---|
| 1 | Organization & Position Master Data | hierarchical orgs, positions, assignments, effective dates | implemented |
| 2 | Personnel Order Workflow | draft/review/approve/effective/cancel/revise | implemented |
| 3 | Legal Knowledge Base | source registry, citations, versions, supersession | implemented |
| 4 | Calculation Matrix | component metadata and treatment matrix | implemented |
| 5 | 1405 Rule Pack | rule-pack manifests, legal-review gate, versioning | review-required for final activation |
| 6 | Tax / Pension / Insurance | policy abstractions + ledger interfaces + tax engine | implemented |
| 7 | High-volume Payroll | batch runner, idempotency, chunking contract | implemented |
| 8 | Retro + Jalali | Jalali period model and monthly recomputation contract | implemented |
| 9 | Loans / Debts / Deductions | ledgers and installment schedules | implemented |
| 10 | Approval / SoD | role + scope + approval policy | implemented |
| 11 | SINA Adapter | typed port, fail-closed adapter boundary | integration-ready; official endpoint/credential required |
| 12 | Accounting / Treasury / Bank | typed ports, reconciliation boundaries | integration-ready; official endpoint/credential required |
| 13 | Employee Self-Service | profile, payslips, history, objections API contracts | implemented |
| 14 | Payslip Explanation | line-level explanations and source chain | implemented |
| 15 | Rule Sandbox UI | scenario API and approval gate | implemented |
| 16 | Management Dashboard | KPI/variance/validation DTOs | implemented |
| 17 | Anomaly Detection | deterministic rules + anomaly scoring interface | implemented |
| 18 | Forecast / Budget AI | scenario/forecast interfaces; AI advisory-only | implemented |
| 19 | Production Security | RBAC, SoD, audit chain, security config | implemented-foundation; target deployment hardening required |
| 20 | DR / PITR | backup/restore runbook, PostgreSQL operational hooks | implemented-runbook |
| 21 | Load / Performance | benchmark scenarios and acceptance thresholds | implemented-fixtures; target environment execution required |
| 22 | Golden Regression | fixture-driven golden payroll suite | implemented |
| 23 | Real Payroll Reconciliation | authoritative sample import/reconciliation contract | ready; real authoritative samples required |

## Release position

Morva is now a **1.0.0-rc1 Production Release Candidate**. The remaining blockers are external evidence/configuration, not hidden application behavior: final legal approval of active 1405 rules, real official integration endpoints/credentials, and authoritative payroll samples.
