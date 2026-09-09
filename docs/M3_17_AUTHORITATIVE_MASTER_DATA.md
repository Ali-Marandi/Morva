# M3.17 — Authoritative Master Data Integrity

## Objective

Strengthen the authoritative master-data boundary for organization, personnel assignment, teacher-rank and attendance records without manufacturing legal or organizational authority.

## Implemented scope

- Validate assignment organization and position references against the canonical master-data catalog.
- Block assignments that point to inactive organization units or inactive positions.
- Block invalid assignment date ranges.
- Block overlapping personnel assignments for the same employee.
- Require every active employee to retain an open-ended current assignment.
- Validate attendance employee references, `YYYY-MM` periods, workflow status, non-negative units, SHA-256 source fingerprints and approval evidence.
- Validate persisted teacher-rank decision provenance for decision/appeal states.
- Preserve fail-closed acceptance semantics: technical integrity does not itself prove organizational authority.

## Acceptance boundary

A dataset remains eligible only when its manifest and persisted integrity checks pass. Formal authority still requires an explicit confirmation reference supplied through the approved organizational source process.

## Governance boundary

This tranche does not infer employee status, rank, attendance treatment, payroll rates, tax treatment or any other legal entitlement. It validates provenance, referential integrity, temporal consistency and workflow evidence only.
