# M3.47 Evidence Trust-Registry Binding

## Scope

M3.47 binds every signed release evidence bundle to the exact trusted-key registry used to
authorize its release-signing key.

Each bundle now records and signs:

- `registry_id`
- `registry_version`
- `registry_fingerprint`

The bundle also hashes the Registry JSON file as an evidence file. This prevents a verifier from
silently substituting a different registry with the same release-signing key.

## Verification

The independent verifier now requires all of the following to agree:

1. the signed bundle metadata;
2. the serialized trusted-key registry;
3. the root signature protecting that registry;
4. the release-signing public key and its active validity;
5. the manifest, aggregate gate and rehearsal fingerprints;
6. the exact candidate Git SHA when supplied.

A different registry version or fingerprint, even when the release-signing key itself is known,
causes verification to fail.

## Production boundary

M3.47 strengthens provenance and trust binding; it does not grant production authorization.

Production still requires controlled root-key custody, real finance/legal/operations and
security evidence, approved deployment evidence and the other production-gate conditions.
