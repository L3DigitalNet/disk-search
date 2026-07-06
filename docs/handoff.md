# Session Handoff — Hardware Radar

_Local, git-ignored. Last updated: 2026-07-05g (session: **two autonomous TODO items cleared on `dev`** — poller refactor `bb2a7ad` + test-env teardown-warning fix `a68c8e0`, pushed to origin/dev; MS-1a PR #8 still merged, deploy run still awaiting the production environment approval)._

## This session (2026-07-05g) — autonomous TODO cleanup on `dev` ✅

MS-1a plan (`docs/superpowers/plans/2026-07-05-ms1a-substrate.md`) confirmed **fully merged** (PR #8 `c1af1a2`) — nothing to re-apply. Owner said "work TODO items that can be done autonomously" → cleared the two that qualified (the rest need an operator, sys76, or the not-yet-built MS-1b matcher). Both pushed to `origin/dev`; both GPG-signed; gate green after each.

- **Poller refactor** (`bb2a7ad`, TDD): extracted the implementation from `poller/__init__.py` into new **`poller/service.py`**; the package `__init__` is now a docstring only, killing the import-time `django.setup()` hack (runpy imports the package before `__main__` runs, so the root had bootstrapped Django for its module-level ORM imports). `__main__.py` imports `run()` from `.service` after `django.setup()`; both poller test files repointed to `.service`. New subprocess regression guard (`test_poller_package_init_is_import_light`) asserts `import hw_radar.poller` pulls no `catalog.models`. `python -m hw_radar.poller` smoke-tested (clean SIGTERM start→stop). **Logger namespace moved to `hw_radar.poller.service`.**
- **Test-env teardown warning** (`a68c8e0`, systematic-debugging): the pre-existing `OperationalError: database "test_hw_radar" is being accessed by other users` PytestWarning was `sync_to_async`'s single process-wide executor thread holding a DB connection Django never closes off a request boundary → survived to session teardown and blocked `DROP DATABASE`. Fixed with a session-scoped autouse fixture in **new `tests/db/conftest.py`** that closes that thread's connection (via `sync_to_async`; depends on `django_db_setup` for LIFO-before-drop ordering); confined to `tests/db/` so unit runs stay DB-free. Suite now **147 passed, 0 warnings**.

## Previous session (2026-07-05f) — MS-1 design ratified + MS-1a ingestion substrate implemented ✅

Owner said "Proceed with MS-1" → brainstorm → design doc → Codex review loops → MS-1a plan → subagent-driven execution. All on `dev`.

- **MS-1 design ratified** (`docs/superpowers/specs/2026-07-05-ms1-ingestion-design.md`): 5 sub-milestones (1a substrate → 1b matcher → 1c catalog seed → 1d connectors+heartbeat → 1e validation/ADR-0019 ratification), PR per sub-milestone. Owner decisions S-1..S-6 incl. **OQ21 resolved** (`httpx` approved; spec §8.6 row; next OQ = 22). **eBay production Browse access verified live** (PRD keyset, token mint + search 200) — re-smoke at MS-1d plan time.
- **Codex review loops converged:** spec 4 rounds, MS-1a plan 3 rounds (audits in `docs/codex-reviews/`, git-ignored). Drove real corrections: **spec v0.10–v0.12** (fast-lane starting set fixed to FR-002's rule — SPD is churning, heartbeat-at-tier-cadence, NOT fast-laned; eBay+WD/Seagate are the set; MS-1 acceptance gained the ≥100-decision denominator + per-source family+ resolution floor) + the same fix in **ADR-0015** + OQ9 parenthetical.
- **MS-1a substrate implemented** (plan `docs/superpowers/plans/2026-07-05-ms1a-substrate.md`, commits `7a93d1c..85d7ac4`, 12 commits): ops models (`SourceConfig` w/ separate `heartbeat_enabled`/`fast_lane`, `ScraperRun`, `FxRateDaily`, `SchedulerCheckpoint`; migrations 0004/0005 — **all 6 seeded sources disabled**), pure scheduling (buckets/backoff/ADR-0017 lifecycle/admission), C.1 contracts + §12.1 classifier, Frankfurter FX service, pipeline runner (fetch-timeout, resolver isolation, DR-005 append-only), Scrapy via **AsyncCrawlerRunner** on the shared loop (walking-skeleton demo source, two-consecutive-crawls proof), poller rewrite (5 service jobs incl. daily recovery probes + Kuma dead-man push; reschedule-on-ramp). Gate green throughout (146 tests, coverage >85%, basedpyright strict 0).
- **Review discipline:** per-task subagent reviews (2 fix rounds: FX coverage gaps; observed_at reverted to fetch-time semantics) + final whole-branch review (verdict READY AFTER FIXES → EC-007 per-item median basis fixed in `85d7ac4`). Follow-ups recorded in `TODO.md ## Claude`.
- **Merge deploys as a behavioral no-op** (all sources disabled; poller gains service jobs only). Deploy's `production` environment gate needs owner approval.

## Previous session (2026-07-05e) — pre-MS-1 repo hygiene sweep ✅ (PR #7 merged)

Owner-directed "clean, drift-free, MS-1-ready" workflow → **5-agent parallel drift audit** (spec↔code · links/IDs · meta-docs · toolchain/CI · provisional markers; Opus for judgment, Sonnet for mechanical). **Headline: the repo was already in good shape** — code faithful to ADR-0010, spec markers all legitimate, IDs/links clean. Drift was concentrated in stale *status/config* text. Fixed in **PR #7** (merged `dde5303`; CI green on the corrected 2.28.2 image):
- **🔴 CI TimescaleDB parity:** `check.yml` was still `2.27.0` (PR #6 bumped only `compose.yaml`) → `2.28.2-pg17`. Now dev/CI/prod all match.
- **README** §Status "provisioning pending" → live; **AGENTS.md** "VM" → LXC container (ADR-0003); **pyproject** header "not started/skeleton" dropped.
- **spec v0.9:** TLS reconciled to **Model A** (host terminates TLS; in-CT NGINX plain `:80`; `X-Forwarded-Proto`) across §8.1 / §8.2.2 diagram / §18.1 (spec had shown TLS inside the CT).
- **research docs:** prompt #10/#11 superseded-recommendation banners (ADR-0007 / ADR-0013); dead spec anchor in orchestration report; `research/README` count 31→36 + 9 unlisted 2026-07-04 reports added.
- **Local files:** corrected TODO's wrong "check.yml doesn't run on dev pushes" (it does; `dependency-review` is the PR-only one) + stale squash-merge/auto-delete entry; handoff no longer mislabels `AGENTS.md` as git-ignored.

**Reviewed — intentional, left as-is (revisit only if desired):** (a) `drive_unit` grain stores serial/SMART without `retention_class` — reads as an identity grain (opportunistic v1 population), not an evidence stream under DR-001; (b) ADR-0019 frontmatter `status: 'active'` (doc-lifecycle) vs body `proposed` (MADR decision) — intentional two-axis split (ADR-0001 declines the frontmatter standard).

## Earlier sessions (condensed)

- **2026-07-05d — pre-MS-1 close-out** (PR #6): spec v0.8 MS-0 doc close-out; compose TimescaleDB 2.28.2 parity. **Local-workstation DB (no compose provider here):** `podman run -d --rm --name hw-radar-db -e POSTGRES_DB=hw_radar -e POSTGRES_USER=hw_radar -e POSTGRES_PASSWORD=hw_radar -p 127.0.0.1:5432:5432 docker.io/timescale/timescaledb:2.28.2-pg17`.

## Earlier sessions (condensed — full detail in the spec, ADRs, merged PRs, and the homelab repo)

- **2026-07-05c — MS-0 provisioned + deployed + LIVE** at `https://hw-radar.l3digital.net` (Hetzner CT 116, Debian 13 unpriv, PG17 + TimescaleDB 2.28.2 TSL). Serving = **Model A** (host terminates TLS; NAT'd CT can't answer ACME). bao-agent renders `/run/bao-agent/hw-radar.env`; secrets at bao-services `services/apps/hw-radar/{config,superuser}`. CI→prod pipeline green (fixed a NAT↔NAT `tailscale ping` → retrying SSH probe). TimescaleDB-aware dumps + 24-monthly `hwradar-moat` snapshot wired. PRs #4/#5; homelab `6b4eb7e`.
- **2026-07-05b — MS-0 plan-conformance review** (3 parallel reviewers, all merge-ready) → 4 fix commits on `dev`. Notable: `from __future__ import annotations` fixed a latent `JSONField[dict]` PEP-649 crash; env-derived CSRF + fail-loud `HW_RADAR_ALLOWED_HOSTS`.
- **2026-07-05a — MS-0 Tasks 1–7 implemented** on `dev` (Django foundation → identity ladder → market/evidence + hypertable → poller stub → deploy artifacts → traceability).
- **2026-07-04q — MS-0 plan authored** (`docs/superpowers/plans/2026-07-04-ms0-foundation.md`) + Codex review loop converged.
- **2026-07-04p — repo went branched/PR-gated** (standing `dev`; `main` strict-protected; merge-commit model; auto-delete OFF); whole-repo cleanup → PR #3/v0.7.
- **2026-07-04n–o — matching layer** → ADR-0019 (proposed) + spec Appendix C.3; spec-hygiene audit → v0.4; template conformance → v0.5 (`MS-#` milestone IDs).
- **2026-07-04d–m — spec consolidation → v0.2**, ADRs 0015–0018, OQ3/OQ15/OQ16–OQ20 resolved (open-questions → EMPTY), freshness-SLO + heartbeat grain.

## Next steps (suggested order)

1. **DONE: MS-1a PR #8 merged** (`c1af1a2`; lxml license exemption + 3 Copilot threads adjudicated en route). **Remaining: approve the `production` deploy gate** (run 28736309450) — the merge deploys as a behavioral no-op. Post-merge operator step: `HW_RADAR_KUMA_PUSH_URL` into the bao-agent template + Kuma monitor (TODO `## Claude`).
2. **MS-1b (matching layer):** next sub-milestone per the design doc — `superpowers:writing-plans` from `docs/superpowers/specs/2026-07-05-ms1-ingestion-design.md` §MS-1b (pure extraction library N1–N4, ladder rungs 0–2, `ListingResolution` migration + resolver, backfill view). Carry the MS-1d must-dos already queued in TODO.
3. **Infra follow-up (out-of-repo, when next touching `homelab`):** bao-services `terraform import` of the hw-radar AppRole + policy — canonical state on **sys76**; run before the next `terraform apply`. Pointer in `homelab` `06233d0`.

## Watch-outs

- Repo is **public** — no secrets/internal hostnames/IPs in committed files (OpenBao paths OK). Live infra specifics stay in the private `homelab` repo.
- **Local-only / git-ignored (never commit):** `docs/handoff.md`, `TODO.md`, `CLAUDE.md`, `.claude/`, `.vscode/`, `docs/codex-delegate/`, `docs/codex-reviews/`. Carry between machines with `scripts/transfer-ignored.sh --up`/`--down`. (**`AGENTS.md` is tracked** — not in this list.)
- **`store.seagate.com` is robots-disallowed** — use the category-page bootstrap JSON, not the cheap Seagate GraphQL signal (documented in the spike report so nobody wires it in later).
- **OQ17 retention numbers and OQ20 allowlist are tunables**, not ratified constants — recorded in DR-008/§16 with values marked adjustable.
- **CI gating:** `check.yml` runs on pushes to `dev`/`main` + all PRs; `dependency-review` is **PR-only** and **required** on `main` — so a dev-only commit gets the full gate but no license scan until the `dev→main` PR (nothing reaches `main` unchecked).
- **OQ / RQ rules:** open in `open-questions.md` (empty; next = OQ21), settled in `resolved-questions.md`; when an item moves, update every referring link that names the file.
- Declines Markdown Frontmatter Standard (ADR-0001); research `index.md` is generated — never hand-edit (regen: `uv run "$SCRIPTS/build_research_index.py" docs/research`).
- Toolchain: **always `uv add`/`uv remove`**; run the gate before claiming "done"; strict BasedPyright on `src/` + `tests/`.
- **Deployment is a CT (ADR-0003):** backups are **not** auto — TimescaleDB needs **TimescaleDB-aware logical dumps** (OQ3). When raw scrape payloads get a disk path (MS-1+), add the CT-116 subvol to restic `BACKUP_PATHS`. Requirements: `homelab/docs/plans/2026-07-04-hw-radar-backup-requirements.md` §6.
