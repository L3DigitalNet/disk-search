# Handoff State

Last updated: 2026-07-06

## Live State

- Agent Handoff System v3 has been adopted in this repo. The old local-only
  `docs/handoff.md` model was split into tracked lifetime-scoped files under
  `docs/handoff/`, plus root `STATUS.md` and `TODO.md`.
- MS-1c is MERGED to `main` (PR #11, 2026-07-06 UTC; CD deploy run was in
  progress at session end): refdata pipeline
  (contracts/loader/persist/discovery/refresh), curated seed corpus (3
  families / 15 models / 17 aliases), C.3.4 discovery loop, monthly refresh
  with resolver reconsider mode, matcher 2026.07.3, and a UTC-pinned poller
  schedule. Manual refresh entry point: `manage.py import_refdata --refresh`.
- 2026-07-06 pre-MS-1d catch-up (259ada1..2044ba0): resolver/admin test-debt
  backfill + pinned append-only listing delete-protection. Deletion posture
  owner-confirmed INTENTIONAL (hard delete never; eBay IR-002 → future
  Listing-grain soft-delete). WD `ultrastar` unreconciled-families entry
  accepted as a cosmetic artifact (documented at `refdata/persist.py`). Drift
  smoke test LOW → full consistency workflow skipped.
- Next work: MS-1d connectors — re-verify source endpoints and run an eBay
  smoke check at plan time (per design S-4), then heartbeat adapters and
  ADR-0019 validation/ratification.
- Local DB note: DB-backed tests need TimescaleDB. On this workstation, use
  `HW_RADAR_DB_PORT=5433` when the container is mapped to `127.0.0.1:5433`.

## Active Incidents

- None. Caveat: a concurrent agent left `docs/prompts/*.md` dirty (uncommitted)
  with reworded prompts that BROKE relative links (`docs/specs/…` should be
  `../specs/…`); not this session's work — review before committing.

## Next Agent

1. Read `TODO.md` and `docs/handoff/specs-plans.md`.
2. For MS-1d, start from `docs/superpowers/specs/2026-07-05-ms1-ingestion-design.md`
   (§S-4) and the MS-1c plan under `docs/superpowers/plans/`.
3. Keep tracked docs public-safe.
