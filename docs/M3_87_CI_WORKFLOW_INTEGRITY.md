# M3.87 — CI Workflow Integrity Gate

M3.87 statically validates every GitHub Actions workflow for a valid top-level
workflow name, a non-empty jobs section, scoped main-branch push triggers outside
the explicitly allowed core workflows, read-only repository contents permissions,
and direct release/deployment mutation commands.

The gate is read-only and prevents recurrence of workflows that parse or trigger
without executable jobs. It does not change deployment, release or production state.
