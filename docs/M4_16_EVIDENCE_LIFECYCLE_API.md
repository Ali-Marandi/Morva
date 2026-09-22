# M4.16 — Evidence Lifecycle API

M4.16 turns the M4.15 lifecycle contract into a persisted, authenticated workflow.

## Contract

- Persist one append-only lifecycle relationship between an accepted predecessor and successor.
- Require the lifecycle actor to be distinct from the submitters of the linked evidence.
- Require exact organization-scope continuity and enforce scope isolation for non-ministry principals.
- Require MFA and the dedicated `evidence.lifecycle.write` permission.
- Validate the complete existing lifecycle chain before persisting a new relationship.
- Expose read-only lifecycle history and deterministic M4.15 assessment.
- Keep historical evidence and prior fingerprints unchanged.
- Fail closed on missing, rejected, tampered, cross-scope, branched or cyclic lineage.

## Endpoints

- `POST /api/v1/evidence-submissions/{evidence_id}/supersede`
- `GET /api/v1/evidence-submissions/lifecycle`

## Safety

This workflow changes only Morva's evidence metadata and lineage records. It does not upload external documents, call external providers, activate production evidence or grant production certification.
