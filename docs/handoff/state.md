# Handoff State

Last updated: 2026-07-05

## Live State

- Agent Handoff System v3 has been adopted in this repo. The old local-only
  `docs/handoff.md` model was split into tracked lifetime-scoped files under
  `docs/handoff/`, plus root `STATUS.md` and `TODO.md`.
- Current product direction: continue MS-1 with the catalog seed work, then
  connectors/heartbeat and validation/ADR-0019 ratification.
- MS-1c seed inputs are now compiled in
  `docs/research/2026-07-05-ms1c-catalog-seed-inputs.md`; the next step is the
  implementation plan and importer/fixture work.
- Local DB note: DB-backed tests need TimescaleDB. On this workstation, use
  `HW_RADAR_DB_PORT=5433` when the container is mapped to `127.0.0.1:5433`.

## Active Incidents

- None.

## Next Agent

1. Read `TODO.md` and `docs/handoff/specs-plans.md`.
2. For MS-1c, start from `docs/research/2026-07-05-ms1c-catalog-seed-inputs.md`
   and `docs/superpowers/specs/2026-07-05-ms1-ingestion-design.md`.
3. Keep tracked docs public-safe.
