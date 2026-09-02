# Morva Payroll Platform

سامانه جامع، قانون‌محور و قابل حسابرسی حقوق و دستمزد کارکنان آموزش‌وپرورش.

## Current distribution

**Morva 1.0.0**

Canonical shared branch: `main`

Public web target:

`https://ali-marandi.github.io/Morva/`

The repository uses GitHub Pages for the public web distribution and a gated tag-based release workflow for versioned Python distributions.

Every product step follows the distribution chain documented in `docs/RELEASE_DISTRIBUTION_POLICY.md`:

`commit -> CI -> exact-head verification -> version/tag -> GitHub Release -> versioned artifacts -> web deployment`

A GitHub Release is created only after a matching `vX.Y.Z` tag passes release validation. The current repository version is `1.0.0`; the release object is created by the tag-driven workflow rather than assumed from the package version alone.

## P0 safety boundary

The authoritative payroll calculation API no longer accepts caller-supplied payroll lines. Create a persisted `PayrollRun`, import approved source data, calculate from server-owned records, then move through validation, review, approval and freeze. External export remains fail-closed until an approved production adapter exists.

Production also requires PostgreSQL, versioned migrations, MFA, OIDC authentication, explicit integration enablement and non-demo rule packs.

## Local web

```bash
cd web
npm install
npm run dev
```

## Build

```bash
cd web
npm install
npm run build
```

## Backend

```bash
python -m pip install -e '.[dev]'
pytest -q
ruff check .
```

## Database migrations

Fresh environments should use:

```bash
alembic upgrade head
```

Production startup fails closed unless `MORVA_MIGRATIONS_READY=true` is set after the approved migration procedure has completed.

## Production authentication

Configure an OIDC issuer, audience and JWKS URL through environment variables. Morva verifies the bearer token signature, issuer, audience and required claims before protected API routes execute.

Never commit production credentials, employee data, raw payroll files or unredacted sensitive logs.

## Safety notice

Morva must not be used for real payroll until all legal, data, security, operational, reconciliation, integration and disaster-recovery production gates in `docs/PRODUCTION_READINESS.md` have passed and have formal evidence.
