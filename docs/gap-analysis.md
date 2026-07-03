# Gap Analysis — `disk-search.md`

**Date:** 2026-07-03 **Subject:** Design/spec gaps in [`disk-search.md`](specs/disk-search.md) **not** covered by existing research or pending research prompts, with research-informed proposed solutions.

## Scope

This analysis deliberately **excludes** anything already covered or planned elsewhere, to avoid false positives:

- **Covered by research docs** — search APIs, official eBay/Amazon/Newegg APIs, and storage/caching-compliance ([`research/tavily-brave-serper.md`](research/tavily-brave-serper.md)); DB engine choice, schema, entity resolution, price-history modelling, trust-rules-as-data ([`research/database-architecture.md`](research/database-architecture.md)).
- **Covered by pending research** — the 17 non-API merchants, drive-grading taxonomy, recert risk/warranty, scoring math, `$/TB` baselines, entity resolution, legal/ToS, anti-bot scraping, job scheduling, framework/DB/env `_TBD_`s, notification/dedup design, and serial/warranty verification — all queued in [`further-research-needed-prompts.md`](further-research-needed-prompts.md).

Everything below falls **outside** all of that: it is the **operational / product-engineering** layer that a research-first spec tends to leave blank.

### How the proposed solutions were researched

Five parallel research sweeps (Tavily-first, Context7-gated, cross-corroborated) were run on 2026-07-03 to ground the solutions. Each persisted a full report under `docs/research/`:

| Report | Informs gaps |
| --- | --- |
| [`2026-07-03-github-actions-cd-private-debian-vm.md`](research/2026-07-03-github-actions-cd-private-debian-vm.md) | #2, #4 |
| [`2026-07-03-auth-for-self-hosted-single-maintainer-python-app.md`](research/2026-07-03-auth-for-self-hosted-single-maintainer-python-app.md) | #1 |
| [`2026-07-03-currency-conversion-and-landed-cost-estimation-for-cross-border-drive-price-scoring.md`](research/2026-07-03-currency-conversion-and-landed-cost-estimation-for-cross-border-drive-price-scoring.md) | #3, #11 |
| [`2026-07-03-postgresql-backup-disaster-recovery-single-vm.md`](research/2026-07-03-postgresql-backup-disaster-recovery-single-vm.md) | #5 |
| [`2026-07-03-lightweight-observability-and-scraper-health-monitoring.md`](research/2026-07-03-lightweight-observability-and-scraper-health-monitoring.md) | #6, #9 |

Gaps #7, #8, #10, #12 are product/scoping decisions rather than research questions; their solutions are reasoned proposals, cross-referencing research facts where relevant.

## Priority summary

| # | Gap | Pri | Proposed solution (one-line) |
| --: | --- | :-: | --- |
| 1 | Web-app authentication undefined | 🔴 | Tailscale-only for v1; clean upgrade path to Authelia forward-auth for multi-user |
| 2 | `.env` secrets contradict OpenBao standard | 🔴 | OpenBao Agent + AppRole response-wrapped `secret_id` at runtime; `.env` for local dev only |
| 3 | No currency / landed-cost normalization | 🔴 | Frankfurter FX daily; convert precisely + editable overhead haircut + "verify duty" flag |
| 4 | Deployment & service topology a black box | 🔴 | Push-only self-hosted runner + local deploy script + systemd units/timers |
| 5 | No backup / disaster recovery | 🟡 | pgBackRest physical+WAL, offsite S3 repo, weekly `pg_dumpall`, monthly restore test |
| 6 | No application self-observability | 🟡 | Uptime Kuma + offsite healthchecks.io heartbeat + GlitchTip + `scraper_runs` table |
| 7 | UI/UX specified as one line | 🟡 | Defined page inventory + post-alert action model; server-rendered + HTMX |
| 8 | No v1 scope / phasing / acceptance criteria | 🟡 | Six-milestone MVP plan (M0–M5) with per-milestone acceptance criteria |
| 9 | No scraper testing strategy | 🟡 | vcrpy cassettes + syrupy snapshots + scheduled live JSON-LD contract canary |
| 10 | No running-cost / budget model | 🟢 | Config-driven per-source poll budget against a monthly ceiling; prefer free feeds |
| 11 | Shipping/tax not in the `$/TB` score | 🟢 | Score on price+shipping(+tax); missing-shipping = penalty/flag |
| 12 | Cold-start: no history for relative scoring | 🟢 | Seed baselines from external references; mark scores "provisional" during warm-up |

---

## 🔴 High-impact gaps

### 1. Web-app authentication is asserted but never designed

**Gap:** The spec says "User authentication for secure access" and is built for one user now but "extended to support other users in the future" — yet no auth model, mechanism, or user-storage schema exists. The [`database-architecture.md`](research/database-architecture.md) schema has no users/sessions tables.

**Evidence:** [`disk-search.md:7`](specs/disk-search.md), [`:78`](specs/disk-search.md).

**Proposed solution — tiered, ship the minimum and keep the upgrade path open:**

- **v1 (recommended): Tailscale-only access.** The owner already runs Tailscale; serve the app on the tailnet with **no public vhost and no auth code at all**. This removes the entire public attack surface for the personal-use phase. Trade-off: unreachable from off-tailnet devices.
- **v1 alternative (only if a public URL is genuinely required):** a single-account **session login** in-app — Django `contrib.auth` or a FastAPI session cookie — with **Argon2id** password hashing (OWASP 2026 default) and `Secure`+`HttpOnly`+`SameSite=Lax` cookies. Gives up MFA/self-service registration.
- **Multi-user end state: Authelia forward-auth** at NGINX (`auth_request`), ~50 MB RAM single Go binary, far lighter than Authentik (~2 GB). Adds MFA + multi-user without hand-rolling it.
- **Security-critical rule for the forward-auth path:** bind the app to **localhost only** so it can never be reached bypassing the proxy, and have NGINX **overwrite (not append)** the trusted identity header. Two live 2025–2026 CVEs (`CVE-2025-54576`, `CVE-2026-34457` in oauth2-proxy) are real instances of header-trust/`auth_request` bypass — pin whatever gateway is chosen to a patched release.
- **Schema now, even at Tier 0:** stub a `users` table so multi-user isn't a later migration crisis.

**Research:** [`auth-for-self-hosted-single-maintainer-python-app.md`](research/2026-07-03-auth-for-self-hosted-single-maintainer-python-app.md).

### 2. `.env` secrets model contradicts the OpenBao standard, with no runtime-injection story

**Gap:** The spec repeatedly says secrets live in a committed-excluded `.env`, but the org standard is **OpenBao as the credential store** (the spec even names OpenBao paths). It never answers **how the deployed app obtains secrets at runtime** — a real contradiction, sharpened by the repo being public.

**Evidence:** [`disk-search.md:62`](specs/disk-search.md), [`:82`](specs/disk-search.md), [`:95`](specs/disk-search.md), [`:107`](specs/disk-search.md), [`:111`](specs/disk-search.md).

**Proposed solution:**

- **Runtime injection via OpenBao Agent** (`bao agent`, run as its own hardened systemd unit) using **AppRole auto-auth**. The agent templates secrets to a root-owned, `0640`, app-group-readable file on **tmpfs** (`/run/disk-search/secrets.env`, gone on reboot); the app services depend on it via `After=`. No plaintext `.env` at rest, no secrets baked into unit files.
- **Solve "Secret Zero" with response wrapping.** The non-secret `role_id` lives in config-management/the VM image. The CD job (which already authenticates to OpenBao with its own narrowly-scoped CI AppRole) requests a **response-wrapped, single-use, short-TTL `secret_id`** and drops only the wrapping token onto the VM; the agent unwraps it once at startup and deletes it. A replay attempt fails and becomes a detectable canary.
- **Reconcile the spec's language:** `.env` is acceptable **for local development only**; production resolves secrets from OpenBao at runtime. This matches the global "never `bao://` in settings, resolve via a wrapper/agent" rule.
- **Confirm:** whether the Proxmox VM has a **vTPM** — it determines whether `systemd-creds --with-key=tpm2` is available as a fallback for rarely-rotated static secrets, or whether that reduces to host-key-only encryption.

**Research:** [`github-actions-cd-private-debian-vm.md`](research/2026-07-03-github-actions-cd-private-debian-vm.md) §3.

### 3. No currency or international landed-cost normalization, yet the scoring unit is `USD/TB`

**Gap:** The score is `USD` per `TB`, but several ranked merchants (ETB Technologies, Bargain Hardware) are UK/EU resellers pricing in GBP/EUR, and the buyer is US-based. Cross-border listings currently score on a false basis — no FX, no shipping, no duty.

**Evidence:** [`disk-search.md:13`](specs/disk-search.md), merchants at [`:40`–`:41`](specs/disk-search.md).

**Proposed solution:**

- **FX:** use **Frankfurter** (ECB-anchored, free, no API key, MIT, self-hostable) refreshed once/day. Store `fx_rate`, `fx_pair`, `fx_rate_date`, `fx_source` **on each observation** so historical scores are auditable and reproducible.
- **Do NOT compute exact duty.** As of 2026-07-03 the US **de-minimis exemption is suspended indefinitely** (CBP interim final rule, 2026-06-24) and the add-on tariff rate for UK/EU goods is in active legal flux (SCOTUS struck down the IEEPA reciprocal tariffs 2026-02-20; a Section 122 stopgap on its own renewal clock replaced them). Presenting a precise duty figure would be false precision that goes stale.
- **Pragmatic model:** convert currency precisely, then apply a single **editable "international overhead" haircut** (start ~15–25%) and **flag** international listings `"international — verify shipping/duty"` rather than ranking them as if landed-equivalent. HDDs classify under **HTS 8471.70 with a 0% base (MFN) rate** — the volatile cost is the surcharge on top, not the base duty.
- **VAT footgun:** UK/EU VAT should be **zero-rated on export** (UK VAT Notice 703), but many storefronts display VAT-inclusive prices pre-checkout — the scraper must not treat a VAT-inclusive shelf price as the export price.

**Research:** [`currency-conversion-and-landed-cost-estimation…md`](research/2026-07-03-currency-conversion-and-landed-cost-estimation-for-cross-border-drive-price-scoring.md).

### 4. Deployment & process/service-management mechanics are a black box

**Gap:** "GitHub Actions → automatic deployment to Hetzner on merge to main" states the _what_, never the _how_: transport, how the web app + workers run as services, how CI reaches a non-public VM.

**Evidence:** [`disk-search.md:71`–`:74`](specs/disk-search.md).

**Proposed solution:**

- **Runner topology:** keep the existing **self-hosted runner on the target VM**, but scope it to **this repo only**, register it **`--ephemeral`/JIT**, and trigger the deploy workflow **only on `push`/`workflow_dispatch` to `main` — never `pull_request`/`pull_request_target`**. The public-repo self-hosted-runner risk is a function of **trigger type, not runner location**; a push-triggered deploy cannot be reached by a fork PR. **Audit every workflow file** for `self-hosted` + PR-triggering events, not just the deploy one. Put the deploy job behind a GitHub **Environment with a required reviewer** as a free extra gate. Keep the runner binary current (GitHub is enforcing a minimum runner version through 2026).
- **Transport:** because the runner is on the VM, "deploy" collapses to a **local script** — `git checkout <sha>` → `uv sync --frozen` → run migrations → `systemctl restart`. No SSH hop, no public port. (If the runner ever moves off-box, fall back to `rsync`/`tailscale ssh` over the tailnet — never a public SSH port.)
- **Packaging:** `uv sync --frozen` into a persistent venv under `/opt/disk-search`. Docker's registry/build overhead buys nothing for a single-VM fleet.
- **Service topology (systemd):** one unit per process — **web** (socket-activated, `Type=simple`, gunicorn + uvicorn workers, `ExecReload=kill -HUP $MAINPID` for graceful reload), **worker(s)** (`Restart=on-failure`), under a **dedicated non-root user** with `ProtectSystem=strict`/`NoNewPrivileges`. Use **systemd timers** (not an in-process scheduler) for periodic scrapes — independent journal logging, resource limits, and restart semantics, and a timer can't silently die inside a long-running worker. Note: plain gunicorn never calls `sd_notify()`, so **avoid `Type=notify`** (it times out).
- **Migrations:** run **before** restart, **expand/contract** (backward-compatible with the still-running old code) — a process discipline the migration tool won't enforce.

**Research:** [`github-actions-cd-private-debian-vm.md`](research/2026-07-03-github-actions-cd-private-debian-vm.md) §1–4.

---

## 🟡 Medium gaps

### 5. No backup / disaster-recovery plan for the price-history database

**Gap:** The accumulated historical price data _is_ the tool's compounding value; a single VM with no backup means one disk failure erases the entire moat. [`database-architecture.md`](research/database-architecture.md) covers retention/compression but not backups.

**Evidence:** [`disk-search.md:19`](specs/disk-search.md), [`:22`](specs/disk-search.md); DB co-located on one VM per [`:69`](specs/disk-search.md).

**Proposed solution:**

- **Define RPO/RTO first**, then: **pgBackRest** for physical backup + continuous **WAL archiving** on-VM (`repo1`), with a **second repo (`repo2`) on S3-compatible object storage** (Backblaze B2 or Hetzner Storage Box) using pgBackRest's built-in **AES-256** encryption. This delivers PITR and 3-2-1 with an offsite copy. Barman/wal-g are viable but heavier/thinner without added benefit at this scale.
- **Supplement** with a weekly `pg_dumpall` as a portable, version-independent export.
- **TimescaleDB:** physical backups (pgBackRest/`pg_basebackup`) need **no special handling**; only logical (`pg_dump`) backups have hypertable caveats and require `timescaledb_pre_restore()`/`post_restore()` and lose compression state — prefer physical.
- **Proxmox `vzdump`/PBS** is a **complement, not a substitute**: VM snapshots of a running DB are crash-consistent **only with the QEMU Guest Agent** doing filesystem freeze/thaw — enable it.
- **Restore-test cadence:** monthly test-restore into a scratch instance; a backup you've never restored is a hope, not a backup.
- **Patch PostgreSQL itself** — recent CVEs (`CVE-2025-8714` in pg_dump/restore; 2026 pg_basebackup/pg_rewind symlink CVEs) live in the tools, not just the DB. (Note: pgBackRest had a ~3-week maintenance gap in 2026 that is now resolved under a multi-sponsor coalition — re-check sponsor durability periodically.)

**Research:** [`postgresql-backup-disaster-recovery-single-vm.md`](research/2026-07-03-postgresql-backup-disaster-recovery-single-vm.md).

### 6. No application self-observability (distinct from deal alerts)

**Gap:** Deal alerts tell the _user_ about drives; nothing tells the _operator_ that the app is down, the VM is out of disk (raw payloads grow), a scheduled scrape stopped running, or alert emails aren't actually being delivered. Pending prompt #9 covers per-source pipeline retries — not fleet health.

**Evidence:** [`disk-search.md:11`](specs/disk-search.md) ("near real-time monitoring") implies always-on jobs with no health story.

**Proposed solution — deliberately lighter than Prometheus/Grafana:**

- **Uptime/health:** **Uptime Kuma** self-hosted (HTTP/TCP/DB checks + **Push monitors** as a cron **dead-man's-switch**) **plus healthchecks.io free tier (20 checks) as an _offsite_ second heartbeat**. The key insight: a monitor on the same VM **cannot alert if that VM is what died** — one heartbeat must live off-box.
- **Error tracking:** **GlitchTip** self-hosted (256 MB–1 GB RAM, Sentry-SDK-compatible) as default, or **Sentry SaaS free tier** (5k events/mo) for zero ops. **Self-hosted Sentry is out** — it needs ~16 GB RAM + Kafka/ClickHouse/Snuba.
- **Metrics:** **skip Prometheus/Grafana/Alertmanager.** Record each scraper run as a **`scraper_runs` Postgres row** (source, started/finished, count, status) right next to the data you already write. VictoriaMetrics single-node is the fallback _only if_ trend graphs later become genuinely necessary.
- **Must-have alerts:** disk-space threshold on the VM; email-delivery confirmation (bounce/deferral) so a silent SMTP failure surfaces.

**Research:** [`lightweight-observability-and-scraper-health-monitoring.md`](research/2026-07-03-lightweight-observability-and-scraper-health-monitoring.md).

### 7. UI/UX is specified only as a one-line feature

**Gap:** "Provides a user-friendly web-based interface" with no page inventory, flows, or — critically — a **post-alert action model** (mark purchased/dismissed, compare, manage watches). Pending prompt #10 only picks the templating _technology_.

**Evidence:** [`disk-search.md:20`](specs/disk-search.md).

**Proposed solution (reasoned; confirm before building):**

- **Rendering approach:** **server-rendered templates + HTMX** — matches a single-maintainer, data-heavy CRUD+dashboard app without an SPA build chain (consistent with prompt #10's framework research).
- **MVP page inventory:**
  1. **Dashboard** — current ranked deals (score, `$/TB`, condition, source), filterable by brand/capacity/tier/interface/condition.
  2. **Listing detail** — the **score breakdown** (why it scored what it did — the explainability the scoring prompt #4 demands) + "why it matched a watch."
  3. **Watches / alert-rules manager** — CRUD over watch criteria (model/capacity/tier, max `$/TB` or score, marketplace filter). Overlaps the alert-rule model in prompt #11.
  4. **Price-history view** — per canonical product, over time.
  5. **Listing state controls** — `interested` / `purchased` / `dismissed` / `snoozed`, so acted-on and rejected listings stop cluttering the dashboard and feed back into alert dedup.
- **Purchase tracking** (lightweight): record what was bought at what price to measure the tool's realized value.

### 8. No v1 scope boundary, phasing, or success criteria

**Gap:** The spec says v1 "will not" optimize for other users, but never states what v1 **does** include vs defers across 20 marketplaces + scoring + entity resolution + a web UI. No milestones, no acceptance criteria.

**Evidence:** [`disk-search.md:7`](specs/disk-search.md); research-priority table exists at [`further-research-needed-prompts.md:225`](further-research-needed-prompts.md) but is a _research_ order, not a _build_ plan.

**Proposed solution — phased milestones with acceptance criteria:**

| Milestone | Deliverable | Done when… |
| --- | --- | --- |
| **M0 Foundation** | Stack chosen (prompt #10), DB schema, minimal auth (Tier 0), CD pipeline + systemd + OpenBao Agent | A trivial page deploys on merge and reads secrets from OpenBao at runtime |
| **M1 Ingestion (top 5)** | Acquisition for the 5 primary recert sources (WD/Seagate recert, ServerPartDeals, goHardDrive, eBay) → normalized `listing` rows | Listings from all 5 land in Postgres with FX-normalized price |
| **M2 Scoring** | Scoring engine (prompt #4) + `$/TB` baseline (prompt #5) + explainable sub-scores | Every listing has a reproducible 0–100 score with a visible breakdown |
| **M3 Web UI** | Dashboard, listing detail, watches manager (gap #7) | Owner can filter deals and create/edit a watch |
| **M4 Alerts** | Email alerts via AgentMail with dedup/debounce (prompt #11) | A matching drop fires exactly one actionable email |
| **M5 Hardening & breadth** | Remaining marketplaces, entity resolution (prompt #6), backups (#5), observability (#6), scraper tests (#9) | Backups restore-tested; scraper-rot alerts fire; ≥15 sources live |

Each milestone gets a written acceptance check before it's "done."

### 9. No testing strategy for scrapers

**Gap:** CI names "testing workflows" but the spec never says **how** to test scrapers against sites that change and fight bots. Untested scrapers rot silently.

**Evidence:** [`disk-search.md:73`](specs/disk-search.md).

**Proposed solution:**

- **Recorded fixtures:** **vcrpy cassettes** per source (record the real HTTP response once, replay in CI) so parsing is tested deterministically and offline.
- **Snapshot tests:** **syrupy** golden-file assertions on the parsed structured output — a parser regression shows as a snapshot diff.
- **Production canary:** a **scheduled (not just CI)** live **JSON-LD / structured-data contract check** per source, plus a **known-value canary page**, to catch the "technically valid but wrong element" failure that offline tests can't see.
- **Runtime validation:** **Pydantic v2** per-record validation + per-source `last_success_at` / consecutive-failure counters + a count-vs-rolling-average assertion; alert when a source returns 0 or malformed results N runs in a row. (Shares the `scraper_runs` table from gap #6.)

**Research:** [`lightweight-observability-and-scraper-health-monitoring.md`](research/2026-07-03-lightweight-observability-and-scraper-health-monitoring.md).

---

## 🟢 Lower-priority gaps

### 10. No running-cost / budget model

**Gap:** Paid search APIs (Serper/Brave/Tavily), AgentMail, object storage for backups, and possible managed-scraping APIs (prompt #8 compares tool costs but not _projected spend_) have no aggregate budget or ceiling to design polling frequency against.

**Evidence:** [`disk-search.md:55`](specs/disk-search.md), [`:109`–`:111`](specs/disk-search.md).

**Proposed solution (design decision):**

- **Prefer free official feeds** (eBay Browse/Feed, structured-data parsing) over paid search calls wherever a source exposes them — search APIs are for _discovery_, not per-poll refresh.
- **Config-driven per-source poll budget:** each source declares a poll frequency; compute projected monthly API-call volume and hold it under a stated **monthly ceiling**. Recert specialists (the value targets) poll more often; long-tail sources daily.
- **Track actuals:** the `scraper_runs` table (gap #6) already captures per-source call counts — surface monthly spend against budget.
- **Confirm current pricing** of Serper/Brave/Tavily/AgentMail tiers before fixing the ceiling (not researched here; a quick lookup at build time).

### 11. Shipping (and tax) not folded into the `$/TB` score

**Gap:** `$/TB` on item price alone misranks a cheap drive with high shipping — even domestically.

**Evidence:** [`disk-search.md:13`](specs/disk-search.md).

**Proposed solution:**

- Score on **price + shipping (+ tax where known)**, not item price alone. Marketplace shipping fields (e.g. eBay Browse `shippingOptions`, Serper `delivery`) are reliable **only when the request supplies correct buyer-location context** — so pin the buyer location on every query.
- When shipping is unknown/unavailable, **apply a penalty or flag** rather than silently scoring as if free — otherwise free-shipping and unknown-shipping listings rank identically.
- This composes with the international-overhead haircut from gap #3.

**Research:** [`currency-conversion-and-landed-cost-estimation…md`](research/2026-07-03-currency-conversion-and-landed-cost-estimation-for-cross-border-drive-price-scoring.md).

### 12. Cold-start: relative scoring has no history on day one

**Gap:** The moving-baseline / percentile scoring that pending prompt #4 will design needs accumulated history that doesn't exist at launch.

**Evidence:** Implied by the price-trend features at [`disk-search.md:19`](specs/disk-search.md), [`:22`](specs/disk-search.md).

**Proposed solution (design decision):**

- **Seed baselines** from the external reference tools that pending prompt #5 will catalogue (diskprices.com, camelcamelcamel/Keepa, r/DataHoarder threads) to provide an initial `$/TB` reference per capacity/tier until enough internal history accrues.
- **Absolute-threshold fallback** during the warm-up window, switching to the self-adjusting percentile baseline once a source has ≥ N observations per (capacity, tier).
- **Mark scores "provisional"** in the UI until the baseline is data-backed, so early scores aren't over-trusted.

---

## Open questions surfaced by the research (decide before building)

1. **Framework: Django or FastAPI?** Changes migration tooling (`manage.py migrate` vs Alembic), the ASGI worker class, and the app-native auth library path. (Resolved by pending prompt #10.)
2. **Does the Proxmox VM have a vTPM?** Determines whether `systemd-creds --with-key=tpm2` is a real hardware-bound fallback for static secrets (gap #2).
3. **Is a public URL actually required**, or is Tailscale-only acceptable for the personal-use phase? Collapses gap #1 to "no auth code" if Tailscale-only (gap #1).
4. **Does the healthchecks.io 20-check free tier** cover ~20 sources + app + backup heartbeats, or is a paid tier / self-hosted instance needed? (gap #6).
