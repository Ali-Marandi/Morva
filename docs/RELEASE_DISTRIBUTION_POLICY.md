# Morva Release and Distribution Policy

## Objective

Every implementation step that is intended to become part of the shared Morva product must be traceable from source commit to validated build and distributable artifact.

## Required lifecycle

```text
change
  -> commit on main
  -> automated CI
  -> exact-head verification
  -> version/tag
  -> GitHub Release
  -> versioned Python artifacts
  -> public web deployment when the change affects web
```

A step is not considered distributed merely because its code exists in a commit. The corresponding CI evidence and distribution state must also be recorded.

## Release rules

1. Every release tag must match `src/morva.__version__` exactly as `v<version>`.
2. Release validation runs compilation, linting, PostgreSQL migrations, tests and dependency audit.
3. Python source distributions and wheels are built from the tagged source.
4. The GitHub Release contains the versioned Python distribution artifacts.
5. Web changes are published through the GitHub Pages workflow from `main`.
6. Real payroll data, credentials and unredacted employee information are never release assets.
7. Production authorization remains independent from software release and requires all controls in `docs/PRODUCTION_READINESS.md`.

## Current distribution position

The repository currently has version `1.0.0` in the Python package metadata and `main` is the canonical shared branch. The release workflow is now installed and will publish a GitHub Release whenever an existing `vX.Y.Z` tag passes the complete release validation pipeline.

At the time this policy was added, GitHub reported no existing Release object for the repository. Therefore this change establishes the publication mechanism; it does not retroactively invent a release object without a version tag.

## Release evidence

For every future release, the commit, tag, CI run, artifact names and public web deployment result must be recorded in the release notes or adjacent release evidence document.
