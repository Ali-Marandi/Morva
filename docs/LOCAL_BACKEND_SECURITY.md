# Local Backend Security Boundary

`backend/` is a development-only adapter for local Excel imports. It is not a production payroll API and must not be exposed as an internet-facing service.

## Required configuration

Set these environment variables before starting the backend:

- `MORVA_LOCAL_ADMIN_EMAIL`
- `MORVA_LOCAL_ADMIN_PASSWORD`
- `MORVA_LOCAL_CORS_ORIGIN` (defaults to `http://localhost:5173`)
- `PORT` (defaults to `5000`)

The backend fails fast when the local administrator credentials are not configured.

## Authentication boundary

`/imports/summary` and `/imports/upload` require a Bearer access token returned by the local login endpoint. The access token is generated randomly for each backend process and is never persisted as a source-code constant.

`/health` is intentionally unauthenticated and only reports local service health.

## Data boundary

Imported Excel data is stored only under the ignored local `backend/data/` directory. This backend does not constitute an authoritative payroll data store and must not be connected to production databases, banking adapters, SINA, or other official integrations.
