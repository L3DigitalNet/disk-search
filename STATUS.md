# Project Status

Human-facing summary of what is complete and current. Agents maintain this file;
unfinished work stays in `TODO.md`.

## Completed

- MS-0 foundation is live: Django 6 app, TimescaleDB data model, web health/login/dashboard, APScheduler poller, deployment artifacts, and CI verification gate.
- MS-1a ingestion substrate is implemented: source/run models, scheduler lifecycle, FX support, pipeline runner, Scrapy integration, and poller service jobs.
- MS-1b matching layer is implemented: conservative normalization, MPN/OEM parsing, ladder rungs 0-2, append-only resolution ledger, and unknown-model backfill view.
- MS-1c catalog seed is complete and merged to `main` (PR #11): refdata pipeline (contracts/loader/persist/discovery/refresh) seeded with 3 families / 15 models / 17 aliases (Seagate Exos recertified full fan-out, IronWolf Pro, WD Ultrastar DC HC550 starter subset), C.3.4 discovery loop with length-guard, monthly refresh with resolver reconsider mode, matcher 2026.07.3, and a UTC-pinned poller schedule.
- Agent Handoff System v3 is adopted for this repo with tracked handoff docs and Claude/Codex SessionStart hooks.

## Current State

- Active branch model: work lands on `dev`; `main` remains PR-gated.
- The product surface is still operator-focused. Marketplace connectors and scoring are not complete yet.
- All tracked repo documentation must remain public-safe: no secrets, private hostnames, private IPs, or internal infrastructure addresses.

## Recent Changes

- 2026-07-05: Adopted Agent Handoff System v3 layout and replaced local-only handoff notes with tracked lifetime-scoped docs.
- 2026-07-05: Added the MS-1c catalog seed input ledger covering Seagate Exos/IronWolf Pro, WD Ultrastar/Gold, and Toshiba MG seed candidates.
- 2026-07-06: MS-1c catalog seed merged via PR #11 after a Codex-reviewed plan, per-task subagent reviews, and a final whole-branch review; scheduler now explicitly pinned to UTC.
- 2026-07-06: Pre-MS-1d catch-up — backfilled recorded test debt (distinct consecutive resolver errors, error-edge recovery, rung-2 decoder-capacity veto, admin permission methods) and pinned the append-only listing delete-protection contract. Owner-confirmed the append-only ledger posture as **intentional** (hard delete never; eBay delete-on-delist per spec IR-002 becomes a future Listing-grain soft-delete path). Accepted the WD `ultrastar` unreconciled-families entry as a **known cosmetic artifact** (documented at `refdata/persist.py::_unreconciled_families`); no code change.

## Notes For The Builder

- Use `TODO.md` for open work. Use `docs/handoff/state.md` only for short live state.
- DB-backed tests require TimescaleDB; on this workstation the dev DB commonly runs on `HW_RADAR_DB_PORT=5433`.
