# Contributing to Morva

Morva targets government/education payroll workloads. Contributions and forks are welcome for engineering, interoperability, documentation, testing, research and governance work, provided that no contribution activates unverified legal rates, production integrations or payment authority.

## Local verification

From the repository root:

```bash
python -m pip install -e '.[dev]'
ruff check .
pytest -q
python -m pip install pip-audit
pip-audit
./scripts/verify_local.sh
```

For the web application:

```bash
cd web
npm ci
npm run build
```

`./scripts/verify_local.sh` is the canonical one-command local reproduction of the release-hygiene checks and the core CI quality gates.

## Branch and pull-request convention

Use a focused branch named after the coherent tranche, for example `feat/m4-44-<topic>` or `fix/<topic>`. Group related M-series changes into one logically complete PR instead of creating many single-purpose PRs. Retroactive squashing of older history is not required.

Every PR should explain:
- what changed and why;
- the affected fail-closed boundary, if any;
- the tests and verification commands run locally;
- whether the change is production-authoritative or governance/demo-only.

Do not merge a change merely because the code compiles. CI must remain green and existing regression fixtures must remain intact.

## Independent review requirement

A second independent review is required for any change touching:
- `security/`;
- `rules/`;
- `payroll/calculator.py`;
- `payroll/lifecycle.py`.

The independent reviewer may be a second human reviewer, a second automated review pass, or an external contributor when no second human reviewer is yet onboarded. The review must explicitly examine security boundaries, fail-closed behavior, backward compatibility and regression coverage.

Until a second reviewer is formally onboarded, any self-merged PR must be disclosed as **self-merged** in the PR description and release evidence. Self-merge disclosure does not waive the independent-review requirement for the changed code; it records the current governance limitation transparently.

## Safety rules

Do not add, infer or activate legal rates, coefficients, thresholds or production credentials. Do not weaken existing production gates. Keep monetary arithmetic in `Decimal`. AI and automation are advisory only.
