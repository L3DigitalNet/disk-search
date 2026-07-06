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
- **MS-1d is MERGED to `main`** (PR #12, 2026-07-06T10:09Z; merge commit `0ff1b7f`; `dev` fast-forwarded to match). Plan `docs/superpowers/plans/2026-07-06-ms1d-connectors.md` (Codex-reviewed, 2 rounds) executed subagent-driven: 22 tasks, each spec+quality reviewed; final whole-branch review READY TO MERGE; the PR's Copilot reviewer's 7 findings all fixed pre-merge (`7ef8eb0`+`2691238`: broken `docs/prompts` relative links → `../`, honest-UA header precedence in `http.py`, and connector `parse()` now skips malformed entries instead of `KeyError`-crashing a run). Landed: five connectors (ServerPartDeals/goHardDrive/WD/Seagate/eBay), ADR-0015 heartbeat subsystem (migrations 0009 models / 0010 TimescaleDB hypertable+cagg / 0011 flag flips), shared infra (`acquisition/http.py` robots guard, `httpx.TransportError`→TRANSIENT, `expires_at` threading, per-item raw payloads, per-grain counts), poller heartbeat scheduling (`run_heartbeat` + two-job model), and `tests/db/test_ms1_acceptance.py`. Full gate green (357 tests / 93% branch). **All sources `enabled=False`** — nothing auto-starts.
- **Pre-go-live gates before ANY source flips `enabled=True`** (see `docs/handoff/deployed.md` SA-004 section + TODO): (1) SA-004 operational checklist (dumps/disk-alert/restore); (2) bounded-retention `expires_at` sweeper — ABSENT, required for bounded-class sources (esp. eBay 6h/DR-008); (3) eBay-only: Listing-grain delete-on-delist soft-delete (IR-002). Also tracked: D1 cross-lane admission coupling (a slow-repair-job failure can backoff-silence the fast heartbeat up to 24h — per-lane scheduling redesign, out of MS-1d scope).
- Recon carry-forwards (in TODO): goHardDrive `CATEGORY_URL` + WD `query=recertified` (surfaces consumer recert, not the enterprise facet) need live-selector confirmation at go-live.
- Local DB note: DB-backed tests need TimescaleDB. On this workstation, use
  `HW_RADAR_DB_PORT=5433` when the container is mapped to `127.0.0.1:5433`.

## Active Incidents

- None. (The prior `docs/prompts/*.md` broken-relative-link caveat is now
  FIXED in PR #12: the links used `](docs/…)` which GitHub resolved to
  `docs/prompts/docs/…`; corrected to `](../…)`. Flagged by the PR's Copilot
  reviewer — an earlier in-session assessment that called them "correct" was
  wrong; GitHub renders relative links file-relative, not repo-root-relative.)

## Next Agent

1. Read `TODO.md` and `docs/handoff/specs-plans.md`.
2. MS-1d is merged. The next milestone is **MS-1e** (validation corpus + ADR-0019 ratification) per `docs/superpowers/specs/2026-07-05-ms1-ingestion-design.md` §MS-1e — harvest ~150–200 real titles across the 5 sources into a labeled JSONL fixture, then compute rung-0–2 auto-accept precision (≥99.5% on ≥100 decisions ratifies ADR-0019).
3. Before enabling any source in production, clear the three pre-go-live gates above (start with the bounded-retention sweeper — it hard-gates eBay).
4. Keep tracked docs public-safe.
