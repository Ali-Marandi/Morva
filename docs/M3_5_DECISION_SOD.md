# M3.5 — Teacher Rank Decision SoD

## Scope

This tranche hardens the teacher-rank decision transition without introducing any legal rank values or statutory treatment.

## Invariants

A final teacher-rank decision is fail-closed unless committee approval provenance exists and records distinct committee approver, committee reviewer and final decision actor identities.

Committee approval stores governance provenance alongside the submitted committee evidence. Existing `require_distinct_actors` policy enforcement is reused for all pairwise actor separation required by this gate.

## Production posture

This is an authorization and provenance control only. It does not certify legal sources, rank catalogs, payroll coefficients or payment integrations.
