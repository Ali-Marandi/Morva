# M3.46 Signed Trusted-Key Registry

## Scope

M3.46 adds a cryptographically signed trust registry above the M3.45 key-lifecycle
contract.

The trust chain is split into two roles:

- a **root signing key** signs the registry itself;
- a **release signing key** signs the release evidence bundle.

The root key is not required to be present inside the release-signing registry. It is supplied
as an out-of-band trust anchor to the independent verifier.

## Registry signature

The signed registry binds:

- registry identifier
- registry version
- complete registry fingerprint
- root key identifier
- signing algorithm
- timezone-aware signing timestamp

Only an Ed25519 signature is accepted.

## Independent verification

M3.44 now requires:

1. a signed trusted-key registry;
2. the root public key used to authenticate that registry;
3. the release signing public key;
4. the release bundle and its recorded source files.

The verifier first authenticates the registry with the root key, then checks that the bundle
signing key is registered and currently active/valid, and finally verifies the release bundle
signature and source-chain bindings.

An unsigned or tampered registry is rejected before a release signing key can be trusted.

## Rotation boundary

M3.45 remains responsible for active, retired and revoked signing keys, validity windows and
replacement relationships.

M3.46 protects the registry state itself. Registry changes therefore require a new signed
registry version rather than relying on an unsigned mutable trust file.

## Production boundary

The CI environment uses ephemeral root and signing keys only as a rehearsal mechanism.
No production private key is committed, uploaded or embedded in the repository.

Production trust anchors still require controlled key custody, secure distribution of the root
public key, documented rotation/revocation procedures and independent operational approval.
