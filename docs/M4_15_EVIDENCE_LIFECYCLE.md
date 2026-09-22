# M4.15 — Evidence Lifecycle

M4.15 defines a fail-closed lineage contract for renewal and supersession of authoritative evidence.

## Contract

- A lifecycle link connects one accepted predecessor to one accepted successor.
- Predecessor and successor must keep the same source type and exact population scope.
- A successor must have a later effective start than its predecessor.
- Lifecycle links are fingerprinted and cannot be future-dated relative to the assessment.
- Multiple successors for one predecessor and multiple predecessors for one successor are rejected.
- Cyclic supersession chains are rejected.
- Existing M4.13 submission fingerprints and M4.14 registry projections remain immutable; lifecycle state is evaluated separately.
- The assessment identifies lineage heads and superseded evidence IDs without deleting historical evidence.

## Safety

The lifecycle contract does not alter authoritative source data, upload documents, activate production evidence or grant production certification.

## Flow

`accepted evidence → lifecycle link → chain verification → lineage heads → downstream closure/convergence`
