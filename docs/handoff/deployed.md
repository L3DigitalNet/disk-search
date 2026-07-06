# Deployed State

Last updated: 2026-07-06

## Current Deployment

- The service deploys from `main` via the GitHub Actions Deploy workflow.
  Latest confirmed deployed increment: MS-1b (PR #10). The MS-1c merge (PR #11)
  deploy run was in progress at the 2026-07-06 session end — verify its outcome
  before relying on refdata features in production.
- Production runtime uses the deployment assets under `deploy/` and the Django
  settings in `src/hw_radar/settings.py`.
- The app exposes `/healthz` for release and database health checks.

## Public-Safe Boundary

Private hostnames, private IPs, container IDs, and credential values are not
recorded in this public repo. Store those facts in the private infrastructure
systems of record.
