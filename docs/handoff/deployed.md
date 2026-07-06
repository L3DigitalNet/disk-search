# Deployed State

Last updated: 2026-07-05

## Current Deployment

- MS-0 is deployed through the repository's GitHub Actions CD workflow.
- Production runtime uses the deployment assets under `deploy/` and the Django
  settings in `src/hw_radar/settings.py`.
- The app exposes `/healthz` for release and database health checks.

## Public-Safe Boundary

Private hostnames, private IPs, container IDs, and credential values are not
recorded in this public repo. Store those facts in the private infrastructure
systems of record.
