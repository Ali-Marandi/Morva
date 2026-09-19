# M3.49 Root Trust-Anchor Rotation and Recovery Ceremony

## Scope

M3.49 extends the M3.46 root-signed registry model to cover rotation of the root trust anchor itself.
A new registry version can therefore move from an old Root key to a different Root key without making
the new key trusted merely because it appears in a file.

The ceremony binds:

- source and target registry versions;
- the exact previous and new registry fingerprints;
- the old and new Root key IDs;
- the effective transition time;
- the transition type;
- the required action for the old Root;
- authorization signatures over one canonical handoff payload.

## Scheduled rotation

A planned Root rotation requires two signatures over the same canonical payload:

1. the old Root authorizes the handoff;
2. the new Root accepts the same handoff.

The source registry must be signed by the old Root and the target registry must be signed by the new Root.
The previous registry must have been signed no later than the ceremony effective time.

The old Root action is the value retire. This path is intended for controlled, pre-authorized key replacement.

## Emergency recovery

Emergency recovery is designed for the case where the old Root can no longer be trusted operationally.
It does not require an old-Root ceremony signature.

Instead, the recovery ceremony requires:

1. the target registry to be signed by the new Root;
2. a separately provisioned Recovery Anchor to authorize the handoff;
3. the old Root action to be the value revoke.

The Recovery Anchor is an out-of-band trust material boundary and is not created or approved by M3.49 CI.

## Fail-closed checks

Verification rejects:

- non-consecutive registry versions;
- changed registry IDs;
- mismatched source or target fingerprints;
- wrong old/new Root public keys;
- a target registry signed by the old Root;
- an old registry signed after the declared effective time;
- missing or invalid handoff signatures;
- invalid scheduled/emergency authorization policy;
- a tampered serialized ceremony fingerprint.

The ceremony does not mutate either registry. It records and verifies the transition between already-signed registry versions.

## Production boundary

The CI workflow is rehearsal-only and generates ephemeral keys. Production requires independent Root/Recovery
Anchor custody, separation of duties, authorization records, protected storage and backup, incident response,
revocation procedures, recovery drills and formal security/operations approval.
