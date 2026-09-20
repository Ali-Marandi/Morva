# M3.90 — Dynamic Workflow Execution Hardening

M3.90 extends the CI workflow integrity and production-boundary policy scanners to
fail closed on indirect shell execution patterns that can hide mutation commands.

## Covered patterns

- `eval`
- `bash -c`
- `sh -c`

The scanner remains conservative: these patterns are treated as integrity findings in
GitHub Actions workflow files and therefore cannot silently bypass the existing direct
mutation-command policy.

## Safety

This is a static verification-only control. It does not execute shell commands,
activate integrations, introduce credentials or perform production changes.
