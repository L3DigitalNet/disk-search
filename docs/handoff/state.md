# Handoff State

Last updated: 2026-07-06

## Live State

- Agent Handoff System v3 is adopted (tracked files under `docs/handoff/` plus
  root `STATUS.md`/`TODO.md`).
- MS-1a/b/c/d are implemented and MERGED to `main` (MS-1c PR #11; MS-1d PR #12,
  merge `0ff1b7f`). MS-1d landed five connectors + the ADR-0015 heartbeat
  subsystem; full gate green (357 tests / 93% branch). Detail in STATUS.md and
  the 2026-07 session log.
- **All sources ship `enabled=False`** — nothing auto-starts. Three pre-go-live
  gates hold before ANY source flips `enabled=True` (see `deployed.md` SA-004 +
  TODO): (1) SA-004 ops checklist (dumps/disk-alert/restore); (2) bounded-retention
  `expires_at` sweeper — ABSENT, hard-gates eBay (6h/DR-008); (3) eBay-only
  Listing-grain delete-on-delist soft-delete (IR-002). Also tracked: D1 cross-lane
  admission coupling (TODO).
- **MS-1e design spec written + Codex-converged** (4 adversarial passes, verdict
  "no significant findings remain"):
  `docs/superpowers/specs/2026-07-06-ms1e-validation-corpus-ratification-design.md`.
  It specifies the deterministic evaluation harness + `harvest_corpus` tooling;
  the live harvest, label audit, and ADR-0019 ratification are a deferred
  owner-in-the-loop step. `writing-plans` NOT yet run.
- Local DB: DB-backed tests need TimescaleDB; use `HW_RADAR_DB_PORT=5433` when the
  dev container maps to `127.0.0.1:5433`.

## Active Incidents

- None.

## Next Agent

1. Run `superpowers:writing-plans` on the converged MS-1e spec, then implement the
   harness + harvest tooling. The ratification test ships skip-guarded until a real
   corpus is harvested; the ADR-0019 flip is a later owner-in-the-loop step.
2. Before enabling any source in production, clear the three pre-go-live gates above
   (start with the bounded-retention sweeper — it hard-gates eBay).
3. Keep tracked docs public-safe.
