# Morva Payroll Platform — Delivery Roadmap

## Completed foundation
- Modular monolith structure
- FastAPI API v1
- Pydantic domain models
- SQLAlchemy persistence models
- Versioned and effective-dated rule engine
- Explainable payroll calculations
- Payroll fingerprinting for reproducibility
- Tax/contribution policy abstractions
- Retroactive payroll difference model
- Personnel order and rank foundations
- Audit event persistence
- CI, Docker and PostgreSQL development stack
- RTL web dashboard foundation

## Next production-critical work
1. Complete personnel and organization master data plus approval workflow.
2. Build the full personnel-order lifecycle.
3. Replace demo policies with reviewed annual legal rule packs from primary sources.
4. Implement the full component eligibility matrix.
5. Implement annual coefficients, minimum/maximum pay, rank and allowance rules as versioned data.
6. Implement payroll lifecycle: draft -> calculate -> validate -> approve -> freeze -> export -> paid.
7. Implement retroactive recalculation across arbitrary Jalali monthly ranges.
8. Add tax, pension, insurance and loan ledgers with reconciliation.
9. Add SINA/external-system adapters behind stable ports.
10. Add authorization, MFA hooks, immutable audit policies, backup and disaster recovery.
11. Build employee self-service: payslips, history, explanations, objections and documents.
12. Build finance dashboards, anomaly detection and budget simulation.

## Production gate
Morva must not be used for real payroll until every annual rule pack has legal source references, effective dates, review metadata, regression cases and reconciliation results against authoritative payroll samples.
