# M3.54 — Release Publication Executor

## Purpose

M3.54 provides the final technical execution boundary between the verified M3.53 publication gate and a prospective GitHub Release.

The executor does not create a tag. The remote tag must already exist and resolve to the exact candidate commit SHA. This prevents accidental tag creation from a moving default branch.

## Pre-publication checks

Before execution, the executor:

- re-verifies the M3.53 publication gate and the full M3.52 artifact chain
- requires repository, tag and candidate SHA to match exactly
- resolves an annotated tag to its peeled commit when necessary
- rejects a remote tag pointing to any other commit
- rejects an already existing GitHub Release for the same tag
- requires an external publication authorization attestation bound to the exact M3.53 gate fingerprint

## Execution

The generated command uses GitHub CLI `gh release create` with `--verify-tag` and `--target <candidate_sha>`. It uploads the trust artifact archive, artifact metadata and M3.53 publication gate as release assets.

GitHub's current CLI documentation supports `--verify-tag`, `--target <branch-or-full-commit-sha>` and asset arguments for `gh release create`. citeturn107948search0

The executor uses subprocess argument arrays rather than a shell string, so repository, tag and asset paths are not interpolated into a shell command.

## Authorization boundary

`execute_publication` refuses to run without an authorization file containing a versioned approval record whose gate fingerprint and target scope match the verified M3.53 gate.

The authorization record is an external operational control; it does not itself establish legal authority. Formal finance, legal, security and operations approval evidence remains required by the production gate.

## CI boundary

M3.54 CI runs Ruff and the full executor regression suite only. It deliberately does not publish a GitHub Release and does not mutate tags.

Actual publication should use a separately authorized execution context after all applicable production gates have been satisfied.