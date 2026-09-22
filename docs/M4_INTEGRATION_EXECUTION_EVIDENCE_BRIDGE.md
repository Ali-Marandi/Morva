# M4 Integration Execution Evidence Bridge

This bridge connects the externally executed M3.84/M3.85/M3.86 staging-or-pilot evidence chain to the M4.1 authoritative evidence registry.

## What it binds

The bridge creates one deterministic binding covering:

- the exact Morva repository and candidate Git commit SHA;
- the non-production execution environment (`staging` or `pilot`);
- the M3.84 execution-evidence fingerprint;
- the M3.85 independent-verification fingerprint;
- the M3.86 execution-readiness fingerprint;
- the current M4.1 registry fingerprint; and
- one distinct, accepted `adapter_contract` evidence item for each of the six canonical adapters.

The binding itself is immutable in memory and fingerprinted. It can be persisted by a later controlled evidence-storage workflow without changing the external execution boundary.

## Fail-closed rules

The bridge rejects:

- malformed or tampered M3.86 readiness receipts;
- repository or candidate-SHA mismatches;
- production as an execution environment;
- stale execution-readiness evidence;
- missing or duplicate adapter-to-evidence mappings;
- adapter evidence that is not present in the current M4.1 registry;
- non-`adapter_contract` evidence;
- pending, future-dated, not-yet-effective or expired authority evidence.

## Safety boundary

This component does **not** execute any provider adapter, load credentials, contact external endpoints, mutate production systems or manufacture execution evidence.

Real staging/pilot evidence must still be produced by an authorized external execution and independently verified before it can enter this bridge.

## Relationship to M4.18

M4.18 remains the canonical evidence readiness/remediation layer. This bridge supplies the missing cross-boundary identity needed to connect a verified integration execution to the already accepted adapter-contract evidence represented in the M4 registry.

No production certification is implied by a successful bridge evaluation.
