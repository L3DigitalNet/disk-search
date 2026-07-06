# Architecture Notes

Last updated: 2026-07-06

## Component Graph

- Django project core: `src/hw_radar/{settings,urls,wsgi}.py`
- Apps: `accounts`, `web`, `catalog`, `acquisition`, `matching`, and `poller`
- Reference-data module: `refdata` (ADR-0018 truncated pipeline — seed
  documents, importer, discovery loop, monthly refresh; not a Django app)
- Data model: ADR-0010 identity ladder plus market/evidence tables and
  TimescaleDB `offer_snapshot` observations
- Runtime jobs: APScheduler poller service (UTC-pinned), daily
  maintenance/recovery jobs, monthly refdata refresh, and dead-man heartbeat
  support
- Deployment: systemd units, nginx config, and `deploy/deploy-remote.sh`

## Standing Backlog

- MS-1d connectors and heartbeat adapters
- MS-1e validation corpus and ADR-0019 ratification
- Later MS-1+ scoring, alerts, and operator-facing product UI
