# M3.23 — Authoritative Master-Data Population Attestation

## Objective

M3.23 closes the software-side gap between an accepted master-data artifact and an explicit authority statement that the persisted population is complete for the declared scope.

The contract is evidence-only: it does not introduce ministry data, employee records, legal rates or population counts into Git.

## Attestation contract

An authority attestation binds to an already `accepted` M3.20 master-data assessment and records:

- the accepted assessment identifier;
- an authority confirmation reference;
- a distinct authority actor identifier;
- a timezone-aware attestation timestamp;
- expected counts for every persisted master-data dimension;
- explicit completeness attestation for every required dimension.

The required dimensions are organization units, positions, employees, assignments, personnel snapshots, attendance facts and teacher-rank cases.

## Fail-closed validation

The attestation is eligible only when:

1. the referenced M3.20 assessment exists and is `accepted`;
2. every required coverage dimension is present exactly once in the attestation;
3. every required dimension is explicitly declared complete;
4. expected counts are non-negative integers;
5. expected counts exactly match both the persisted database population and the accepted assessment evidence;
6. the authority actor differs from the original dataset submitter and the acceptance confirmer;
7. the attestation timestamp carries timezone information.

The validator returns a deterministic SHA-256 fingerprint over the accepted assessment identity, authority evidence, coverage declaration and integrity snapshot. It does not mutate or re-accept master data.

## Operational boundary

M3.23 provides the application control required to consume a formally attested authoritative population. It does not claim that an authoritative external population has already been delivered. Real organizational, personnel, attendance and rank artifacts remain outside Git and must enter through the approved import/provenance path with formal source evidence.
