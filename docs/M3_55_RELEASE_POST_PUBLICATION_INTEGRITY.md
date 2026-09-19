# M3.55 — Release Post-Publication Integrity Verifier

## Purpose

M3.55 adds an independent, read-only verification boundary after GitHub Release
publication. It revalidates the local M3.52 trust artifact and M3.53 publication gate,
then reads the live GitHub Release and remote tag and proves that the published object
still matches the exact candidate that was authorized for publication.

## Verification contract

The verifier requires all of the following:

- the M3.53 publication gate verifies against the M3.52 artifact and exact repository/tag/SHA;
- the remote tag exists and resolves to the exact candidate commit, including annotated-tag peeling;
- a GitHub Release exists for that tag and has the expected release name;
- draft is false, prerelease is false and published_at is present;
- target_commitish equals the exact candidate commit SHA;
- the Release contains exactly the three expected assets: the M3.52 archive, its metadata
  and the M3.53 publication gate;
- every expected asset is uploaded, has the exact local byte size and has the exact
  GitHub SHA-256 digest;
- the verifier writes a deterministic receipt fingerprint whose semantic contents exclude
  the verification timestamp.

GitHub's current REST release response exposes tag_name, target_commitish, draft,
prerelease, published_at, release identity fields and the asset size and digest values
used by this contract. The current API documentation also documents release lookup by tag
and release-asset digest metadata. citeturn891953search0turn891953search1

## Safety properties

The verifier is strictly read-only. It uses git ls-remote and gh api only; there is
no Release creation, edit, delete, asset upload or tag mutation path.

Verification receipts are write-once so a later run cannot silently replace an earlier
evidence record at the same path.

## CI boundary

M3.55 CI runs the verifier regression suite and scans its workflow for GitHub mutation
commands. The CI workflow is a contract test and does not require a real production
Release to exist. A real post-publication verification is run separately with the
generated evidence files after an authorized Release has actually been published.

## Production boundary

M3.55 does not itself establish legal, finance, security or operations approval. It proves
only that a published GitHub Release remains byte- and identity-consistent with the
already-authorized release inputs.
