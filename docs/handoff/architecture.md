# Architecture Notes

Last updated: 2026-07-05

## Component Graph

- Django project core: `src/hw_radar/{settings,urls,wsgi}.py`
- Apps: `accounts`, `web`, `catalog`, `acquisition`, `matching`, and `poller`
- Data model: ADR-0010 identity ladder plus market/evidence tables and
  TimescaleDB `offer_snapshot` observations
- Runtime jobs: APScheduler poller service, daily maintenance/recovery jobs, and
  dead-man heartbeat support
- Deployment: systemd units, nginx config, and `deploy/deploy-remote.sh`

## Standing Backlog

- MS-1c catalog seed
- MS-1d connectors and heartbeat adapters
- MS-1e validation corpus and ADR-0019 ratification
- Later MS-1+ scoring, alerts, and operator-facing product UI
