# Gap Analysis — `disk-search.md`

**Date:** 2026-07-03 **Subject:** Design/spec gaps in [`disk-search.md`](specs/disk-search.md) **not** covered by existing research or pending research prompts, with research-informed proposed solutions.

## Scope

This analysis deliberately **excludes** anything already covered or planned elsewhere, to avoid false positives:

- **Covered by research docs** — search APIs, official eBay/Amazon/Newegg APIs, and storage/caching-compliance ([`research/tavily-brave-serper.md`](research/tavily-brave-serper.md)); DB engine choice, schema, entity resolution, price-history modelling, trust-rules-as-data ([`research/database-architecture.md`](research/database-architecture.md)).
- **Covered by domain research** — the 17 non-API merchants, drive-grading taxonomy, recert risk/warranty, scoring math, `$/TB` baselines, entity resolution, legal/ToS, anti-bot scraping, job scheduling, framework/DB/env `_TBD_`s, notification/dedup design, and serial/warranty verification. These were *queued* in [`further-research-needed-prompts.md`](further-research-needed-prompts.md); **as of 2026-07-03 the reports have landed** under [`research/`](research/) (14 imported + the 5 operational sweeps below), so this reconciliation pulls their findings directly into the gaps rather than pointing at pending prompts.

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

Gaps #7, #8, #10, #12 began as product/scoping decisions rather than dedicated operational research questions. As of the 2026-07-03 reconciliation, the imported domain reports now materially inform **#7** (UI/post-alert model — stack + alerting reports), **#10** (costs/free-feeds — acquisition + scraping + orchestration reports), and **#12** (cold-start scoring — deal-score + baselines reports); **#8** remains a reasoned build-plan (to be finalized via `spec-pipeline`).

## Priority summary

| # | Gap | Pri | Proposed solution (one-line) |
| --: | --- | :-: | --- |
| 1 | Web-app authentication undefined | 🔴 | **Decided:** single strong-password account (app holds no sensitive data); Argon2id session login; Authelia forward-auth reserved for multi-user |
| 2 | `.env` secrets contradict OpenBao standard | 🔴 | OpenBao Agent (AppRole auto-auth) **local on the VM, decoupled from CI**; `.env` for local dev only *(clarification pending)* |
| 3 | No currency / landed-cost normalization | 🔴 | **Decided:** Frankfurter FX → normalize all to USD; **flag** international listings (no fixed haircut), user decides |
| 4 | Deployment & service topology a black box | 🔴 | **Decided:** GitHub-hosted `ubuntu-latest` build/test → `rsync` over Tailscale SSH to the private VM; systemd units/timers |
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

**Decision (2026-07-03): the app is intentionally internet-facing behind a single strong-password account.** The owner's controlling constraint is that the web app holds **no secrets or sensitive data**, so a single-account login is an acceptable surface. Chosen path:

- **v1 (chosen): single-account session login.** Django `contrib.auth` or a FastAPI session cookie, with **Argon2id** password hashing (OWASP 2026 default) and `Secure`+`HttpOnly`+`SameSite=Lax` cookies. Enforce a strong password; optional TOTP can be added later without a schema change.
- **Considered and rejected: Tailscale-only.** Would remove the public attack surface entirely, but also makes the app unreachable off-tailnet — the owner wants it internet-reachable, so this was declined.
- **Design constraint to carry into the spec (owner's rationale):** keep sensitive data **out of the app entirely**, so that even a single-account compromise cannot leak secrets. This is the load-bearing assumption behind accepting single-user auth — state it explicitly in the spec, not just here.
- **Multi-user end state (unchanged): Authelia forward-auth** at NGINX (`auth_request`), ~50 MB RAM single Go binary, far lighter than Authentik (~2 GB). Adds MFA + multi-user without hand-rolling it.
- **Security-critical rule for the eventual forward-auth path:** bind the app to **localhost only** so it can never be reached bypassing the proxy, and have NGINX **overwrite (not append)** the trusted identity header. Two live 2025–2026 CVEs (`CVE-2025-54576`, `CVE-2026-34457` in oauth2-proxy) are real instances of header-trust/`auth_request` bypass — pin whatever gateway is chosen to a patched release.
- **Schema now:** stub a `users` table so multi-user isn't a later migration crisis.

**Research:** [`auth-for-self-hosted-single-maintainer-python-app.md`](research/2026-07-03-auth-for-self-hosted-single-maintainer-python-app.md).

#### User Comments

**Status:** Rejected *(Tailscale-only recommendation)* → **resolved to single-account session login**

**Reasoning:** The internet-facing web app should have no secret or sensitive data baked into it. There will still be some basic auth to access. I don't see a security risk in using a single user account with a strong password.

### 2. `.env` secrets model contradicts the OpenBao standard, with no runtime-injection story

**Gap:** The spec repeatedly says secrets live in a committed-excluded `.env`, but the org standard is **OpenBao as the credential store** (the spec even names OpenBao paths). It never answers **how the deployed app obtains secrets at runtime** — a real contradiction, sharpened by the repo being public.

**Evidence:** [`disk-search.md:62`](specs/disk-search.md), [`:82`](specs/disk-search.md), [`:95`](specs/disk-search.md), [`:107`](specs/disk-search.md), [`:111`](specs/disk-search.md).

**Proposed solution:**

- **Runtime injection via OpenBao Agent** (`bao agent`, run as its own hardened systemd unit) using **AppRole auto-auth**. The agent templates secrets to a root-owned, `0640`, app-group-readable file on **tmpfs** (`/run/disk-search/secrets.env`, gone on reboot); the app services depend on it via `After=`. No plaintext `.env` at rest, no secrets baked into unit files.
- **Secret Zero is simpler now that CI no longer runs on the VM** (see gap #4's decision — deploy is `rsync` over Tailscale SSH from a **GitHub-hosted** runner, not a self-hosted runner on the box). The OpenBao Agent runs **locally on the VM, fully decoupled from CI**: the `role_id` lives in the VM image/config-management, and the `secret_id` is provisioned **out-of-band to the VM** (at provisioning time, or renewed by a local process), **never handed to the GitHub-hosted CI job.** This is strictly better than the old plan — a public-repo CI runner should hold **no OpenBao credential at all**; it only rsyncs code and triggers `systemctl restart`, and the running services pick up secrets the Agent has already templated.
- **Reconcile the spec's language:** `.env` is acceptable **for local development only**; production resolves secrets from OpenBao at runtime. This matches the global "never `bao://` in settings, resolve via a wrapper/agent" rule.

**Research:** [`github-actions-cd-private-debian-vm.md`](research/2026-07-03-github-actions-cd-private-debian-vm.md) §3.

#### User Comments

**Status:** Further clarification needed → **direction set; two items to confirm**

**Reconciled direction (2026-07-03):** OpenBao Agent local on the VM, decoupled from CI (reconciled against gap #4's rsync-from-GitHub-hosted-runner decision — the earlier "CD job fetches a response-wrapped `secret_id`" mechanism is withdrawn because CI is no longer on the VM and, being a public repo, must hold no OpenBao credential).

**Open clarifications:**
1. **`secret_id` delivery to the VM out-of-band** — decide the provisioning/renewal path (e.g. Ansible run against the VM over Tailscale, or an existing infra automation) now that CI can't be the courier.
2. **vTPM on the Proxmox VM?** — determines whether `systemd-creds --with-key=tpm2` is a real hardware-bound fallback for the handful of rarely-rotated static secrets, or reduces to host-key-only encryption. For a short static-secret set, `systemd-creds` may even be simpler than a full OpenBao Agent — worth weighing once the vTPM answer is known.

### 3. No currency or international landed-cost normalization, yet the scoring unit is `USD/TB`

**Gap:** The score is `USD` per `TB`, but several ranked merchants (ETB Technologies, Bargain Hardware) are UK/EU resellers pricing in GBP/EUR, and the buyer is US-based. Cross-border listings currently score on a false basis — no FX, no shipping, no duty.

**Evidence:** [`disk-search.md:13`](specs/disk-search.md), merchants at [`:40`–`:41`](specs/disk-search.md).

**Proposed solution:**

- **FX:** use **Frankfurter** (ECB-anchored, free, no API key, MIT, self-hostable) refreshed once/day. Store `fx_rate`, `fx_pair`, `fx_rate_date`, `fx_source` **on each observation** so historical scores are auditable and reproducible.
- **Do NOT compute exact duty.** As of 2026-07-03 the US **de-minimis exemption is suspended indefinitely** (CBP interim final rule, 2026-06-24) and the add-on tariff rate for UK/EU goods is in active legal flux (SCOTUS struck down the IEEPA reciprocal tariffs 2026-02-20; a Section 122 stopgap on its own renewal clock replaced them). Presenting a precise duty figure would be false precision that goes stale.
- **Model (owner decision 2026-07-03 — accepted with changes):** convert currency precisely so **all prices normalize to USD**, but do **not** apply any fixed "international overhead" haircut. Instead **flag** international listings — e.g. `"international — extra shipping/duty likely; verify before buying"` — and let the user decide how to weigh them. Rationale: a cross-border purchase is unlikely to be worthwhile (shipping plus potential customs duties), and a hardcoded percentage would be false precision; surface the risk rather than bake in a number. HDDs classify under **HTS 8471.70 with a 0% base (MFN) rate**, so the volatile cost is the surcharge on top — exactly the part the flag defers to the user.
- **VAT footgun:** UK/EU VAT should be **zero-rated on export** (UK VAT Notice 703), but many storefronts display VAT-inclusive prices pre-checkout — the scraper must not treat a VAT-inclusive shelf price as the export price.

**Research:** [`currency-conversion-and-landed-cost-estimation…md`](research/2026-07-03-currency-conversion-and-landed-cost-estimation-for-cross-border-drive-price-scoring.md).

#### User Comments

**Status:** Accepted with changes

**Reasoning:** Normalize all to USD, but do not apply a fixed international overhead. Instead, flag international listings and let the user decide how to treat them. It is unlikely that the user will be able to purchase from international sellers (additional costs from shipping likely to apply and potential customs duties), so they should be aware of the potential for additional costs.

### 4. Deployment & process/service-management mechanics are a black box

**Gap:** "GitHub Actions → automatic deployment to Hetzner on merge to main" states the _what_, never the _how_: transport, how the web app + workers run as services, how CI reaches a non-public VM.

**Evidence:** [`disk-search.md:71`–`:74`](specs/disk-search.md).

**Decision (2026-07-03 — supersedes the self-hosted-runner proposal): GitHub-hosted build/test, then `rsync` over Tailscale SSH.** This is a **public** repo, and GitHub advises against self-hosted runners on public repos (a fork PR can execute untrusted code on your infrastructure — a risk best avoided outright rather than fenced off by trigger discipline). Chosen model:

- **Runner:** a **GitHub-hosted `ubuntu-latest`** runner builds and tests the code (no infrastructure to harden, torn down after each run). The deploy step joins the tailnet **ephemerally** (`tailscale/github-action` with an OAuth client or a short-TTL, pre-authorized, ephemeral auth key), then `rsync`s the artifact to the VM and triggers the remote restart over `tailscale ssh`. No public SSH port; no persistent runner.
- **Trigger discipline (still applies):** deploy only on `push`/`workflow_dispatch` to `main`, never `pull_request`/`pull_request_target`. Put the deploy job behind a GitHub **Environment with a required reviewer**, and store the Tailscale auth key + deploy SSH key as **Environment secrets** so PR-triggered runs can't read them. Scope the tailnet ACL so the ephemeral runner node can reach **only** the disk-search VM's SSH port.
- **Transport & packaging:** `rsync` the checked-out source (or a `uv`-built wheel/sdist) to `/opt/disk-search`, then over `tailscale ssh` run `uv sync --frozen` into a persistent venv → run migrations → `systemctl restart`. Build the venv **on the VM**, not in CI, to avoid arch/path skew. Docker's registry/build overhead buys nothing for a single-VM fleet.
- **Service topology (systemd):** one unit per process — **web** (socket-activated, `Type=simple`, gunicorn + uvicorn workers, `ExecReload=kill -HUP $MAINPID` for graceful reload), **worker(s)** (`Restart=on-failure`), under a **dedicated non-root user** with `ProtectSystem=strict`/`NoNewPrivileges`. Use **systemd timers** (not an in-process scheduler) for periodic scrapes — independent journal logging, resource limits, and restart semantics, and a timer can't silently die inside a long-running worker. Note: plain gunicorn never calls `sd_notify()`, so **avoid `Type=notify`** (it times out). *(The orchestration research ([`orchestration-choice-for-a-single-vm-price-polling-service.md`](research/orchestration-choice-for-a-single-vm-price-polling-service.md)) refines the per-source scheduling that runs under these timers — two-level token buckets, jitter, circuit-breaking.)*
- **Migrations:** run **before** restart, **expand/contract** (backward-compatible with the still-running old code) — a process discipline the migration tool won't enforce.

**Research:** [`github-actions-cd-private-debian-vm.md`](research/2026-07-03-github-actions-cd-private-debian-vm.md) §1–4.

#### User Comments

**Status:** Additional clarification needed → **resolved to GitHub-hosted `ubuntu-latest` + `rsync` over Tailscale SSH**

**Reasoning:** This is a public repo. GitHub recommends not using self-hosted runners for public repos. We will use the `ubuntu-latest` GitHub-hosted runner to build and test the code, then use `rsync` over Tailscale SSH to deploy to the private VM.

**Open clarification:** how the ephemeral runner authenticates to the tailnet — a **Tailscale OAuth client** (preferred; scoped, auto-rotating) vs a pre-generated ephemeral auth key. Confirm which the existing tailnet ACL setup supports.

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

#### User Comments

**Status:** Additional clarification needed → **defer to existing Hetzner backup infra; add the VM; confirm it meets DB-level RPO**

**Reasoning:** There are existing backup processes in place for Hetzner CTs and VMs. We will need to confirm that the existing backup processes are sufficient for our needs. If not, we will implement a backup strategy as described above. The disk-search VM will have to be added to the existing backup processes.

**Reconciled direction (2026-07-03):** first add the disk-search VM to the existing Hetzner CT/VM backup process; then verify it actually protects the **price-history database** at the required granularity — the one caveat the research surfaces is that a VM-level snapshot of a *running* Postgres is crash-consistent **only when the QEMU Guest Agent performs filesystem freeze/thaw**, and it gives no point-in-time recovery (PITR) between snapshots. If the existing process lacks freeze/thaw or the RPO gap between snapshots is too large for the accumulating price history, layer the pgBackRest + WAL-archiving design above **on top of** (not instead of) the VM backup. Either way, keep the monthly restore-test discipline — an untested backup is a hope.

### 6. No application self-observability (distinct from deal alerts)

**Gap:** Deal alerts tell the _user_ about drives; nothing tells the _operator_ that the app is down, the VM is out of disk (raw payloads grow), a scheduled scrape stopped running, or alert emails aren't actually being delivered. Pending prompt #9 covers per-source pipeline retries — not fleet health.

**Evidence:** [`disk-search.md:11`](specs/disk-search.md) ("near real-time monitoring") implies always-on jobs with no health story.

**Proposed solution — deliberately lighter than Prometheus/Grafana:**

- **Uptime/health:** **Uptime Kuma** self-hosted (HTTP/TCP/DB checks + **Push monitors** as a cron **dead-man's-switch**) **plus healthchecks.io free tier (20 checks) as an _offsite_ second heartbeat**. The key insight: a monitor on the same VM **cannot alert if that VM is what died** — one heartbeat must live off-box.
- **Error tracking:** **GlitchTip** self-hosted (256 MB–1 GB RAM, Sentry-SDK-compatible) as default, or **Sentry SaaS free tier** (5k events/mo) for zero ops. **Self-hosted Sentry is out** — it needs ~16 GB RAM + Kafka/ClickHouse/Snuba.
- **Metrics:** **skip Prometheus/Grafana/Alertmanager.** Record each scraper run as a **`scraper_runs` Postgres row** (source, started/finished, count, status) right next to the data you already write. VictoriaMetrics single-node is the fallback _only if_ trend graphs later become genuinely necessary.
- **Must-have alerts:** disk-space threshold on the VM; email-delivery confirmation (bounce/deferral) so a silent SMTP failure surfaces.

**Research:** [`lightweight-observability-and-scraper-health-monitoring.md`](research/2026-07-03-lightweight-observability-and-scraper-health-monitoring.md).

#### User Comments

**Status:** Additional clarification needed → **defer host/VM health to existing Hetzner monitoring; keep app-level scraper-health in-app**

**Reasoning:** There are existing monitoring processes in place for Hetzner CTs and VMs. We will need to confirm that the existing monitoring processes are sufficient for our needs. If not, we will implement a monitoring strategy as described above. The disk-search VM will have to be added to the existing monitoring processes.

**Reconciled direction (2026-07-03):** split this gap in two — **infrastructure health** (VM up, disk space, CPU/RAM) defers to the existing Hetzner monitoring; add the disk-search VM to it. If that monitoring already runs **off-box**, it also satisfies the research's key insight (a monitor on the same VM can't alert when that VM is what died) — confirm it does, and that a **disk-space threshold** alert is in place, since raw scrape payloads grow. **Application-level health** — a scheduled scrape silently stopped, a source returning zero/garbage, alert emails not actually delivered — is *not* something generic VM monitoring sees; keep the lightweight in-app pieces regardless: the **`scraper_runs` table** (shared with gap #9) plus a **dead-man's-switch heartbeat** and **email-delivery confirmation**. Only add Uptime Kuma / GlitchTip if the existing stack doesn't already cover error tracking.

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

**Research-informed refinements (2026-07-03)** — from [`opinionated-core-stack-recommendations…md`](research/opinionated-core-stack-recommendations-for-a-python-drive-price-monitor.md) and [`designing-a-low-noise-alerting-layer…md`](research/designing-a-low-noise-alerting-layer-for-a-hard-drive-deal-monitor.md):

- **Rendering approach is now research-backed, not just reasoned:** the stack report explicitly recommends **Django + server-rendered templates + HTMX** over FastAPI for this app precisely because its center of gravity is "authenticated listings database + dashboards + CRUD + alerts + internal operations," not an API platform — Django's built-in auth/ORM/migrations/admin remove scaffolding. (This also informs the gap #1 auth path and pending prompt #10's framework choice — they converge on Django.)
- **Use the Django admin as the internal back-office** (inspect scraped offers, correct bad entity matches, triage ingestion, review users/alerts/catalog) — but the report cites Django's own warning that the admin is *not* the user-facing front end, so the dashboard/detail/watch pages above are still needed on top of it.
- **The post-alert action model is now concrete.** The alerting report defines a per-watch, per-listing **state machine** (`none / pending / firing / cooling / digested`) and first-class **snooze at two granularities** — snooze a *watch* (`snoozed_until`) and snooze a *listing* (24h/7d). Each alert exposes one-click actions (Open · Snooze watch · Snooze listing · Stop watch) as **signed single-purpose links** (HMAC over `watch_id`/`target`/`action`/`exp`/`nonce`); the **watch is the unit of opt-out**, not the whole sender. Fold these into the "listing state controls" page and reuse the same links in-app.
- **Dedup is observation-driven, with a caveat for the state controls:** the report dedups on a **listing fingerprint** + an **alert fingerprint** (`sha256(watch_id | listing_fingerprint | reason_code | threshold_bucket)`) plus a similarity key for reposts under new URLs — but it does **not** model "user marked dismissed → suppress future alerts." If we want a user *dismiss* to actually silence re-alerts (implied by gap #7's state controls), that feedback path is an **addition beyond the research** and must be designed.
- **Score-breakdown UI has a ready pattern:** the alerting report's "why it matched" block — current facts (Price, $/TB, Score, Availability, Marketplace, Seller, Link) plus a **per-threshold pass-margin** line (e.g. "Max price watch: $190.00 → passed by $10.01") — is designed for email but is directly reusable as the listing-detail explainability view the scoring work (prompt #4) demands.
- **Watch-rule UI shape:** keep **hard filters separate from thresholds**, and **do not expose free-text title matching** — watches target normalized fields only (`model_ids`, `family_ids`, `capacity_tb` min/max, `tier_any`, `marketplaces_any`; thresholds `max_price`, `max_price_per_tb`, `min_score`; plus delivery policy: channels, digest mode, debounce, cooldown, hysteresis).
- **Gap in the research:** neither report covers **purchase tracking / realized-savings** — that bullet remains a reasoned addition with no research backing, so treat it as genuinely optional for v1.

#### User Comments

**Status:** Additional clarification needed → **rendering + post-alert model now research-backed; final page inventory still to confirm**

**Reasoning:** Additional research in `docs/research/` may provide more information on the UI/UX. The proposed solution above is a good starting point, but we will need to confirm the final page inventory and flows before building.

### 8. No v1 scope boundary, phasing, or success criteria

**Gap:** The spec says v1 "will not" optimize for other users, but never states what v1 **does** include vs defers across 20 marketplaces + scoring + entity resolution + a web UI. No milestones, no acceptance criteria.

**Evidence:** [`disk-search.md:7`](specs/disk-search.md); research-priority table exists at [`further-research-needed-prompts.md:225`](further-research-needed-prompts.md) but is a _research_ order, not a _build_ plan.

**Proposed solution — phased milestones.** The summary table is the skeleton; the detailed task/acceptance breakdown follows it. **This is planning input, not the final plan:** the owner will author the authoritative phased spec with the **`spec-pipeline` plugin** (L3DigitalNet Claude-Code-Plugins marketplace), so these milestones should map onto spec-pipeline *phases*, and the acceptance criteria below are the raw material for each phase's exit gate — not a substitute for them.

| Milestone | Deliverable | Done when… |
| --- | --- | --- |
| **M0 Foundation** | Django stack (prompt #10), DB schema, single-account auth (gap #1), CD via rsync/Tailscale (gap #4) + systemd + OpenBao Agent (gap #2) | A trivial page deploys on merge and the service reads a secret from OpenBao at runtime |
| **M1 Ingestion (top 5)** | Acquisition for the 5 primary recert sources → normalized `listing` rows, USD-normalized | Listings from all 5 land in Postgres with FX-normalized (USD) price and an international flag where applicable |
| **M2 Scoring** | Scoring engine (prompt #4) + `$/TB` baseline w/ warm-up (prompt #5, gap #12) + explainable sub-scores | Every listing has a reproducible 0–100 score with a visible breakdown |
| **M3 Web UI** | Dashboard, listing detail, watches manager (gap #7) | Owner can filter deals and create/edit a watch |
| **M4 Alerts** | Email alerts via AgentMail with dedup/debounce (prompt #11) | A matching drop fires exactly one actionable email |
| **M5 Hardening & breadth** | Remaining marketplaces, entity resolution (prompt #6), backups (#5), observability (#6), scraper tests (#9) | Backups restore-tested; scraper-rot alerts fire; ≥15 sources live |

**Detailed per-milestone tasks + measurable acceptance criteria:**

- **M0 — Foundation.**
  - *Tasks:* scaffold the Django project (uv-managed, `pyproject.toml`, BasedPyright-strict per the python-tooling standard); define the canonical `drive_model` / `listing` / `observation` schema (from [`database-architecture.md`](research/database-architecture.md)) as initial migrations; stub the `users` table + single-account session login (Argon2id); stand up the CD workflow (GitHub-hosted `ubuntu-latest` → `rsync` over Tailscale SSH); install systemd web + worker units and the local OpenBao Agent unit.
  - *Acceptance (measurable):* merge to `main` deploys automatically with **zero manual steps**; the running web service serves an authenticated "hello" page and **reads at least one secret sourced from OpenBao** (no plaintext `.env` on the VM); `uv sync --frozen` reproduces the locked env; migrations apply cleanly from empty; a **rollback to the previous SHA** is demonstrated.
- **M1 — Ingestion (top 5).**
  - *Tasks:* implement acquisition for the 5 primary recert sources (WD Recertified, Seagate Recertified, ServerPartDeals, goHardDrive, eBay Browse/Feed) using the structured-data-first tier ladder ([`pragmatic-architecture…md`](research/pragmatic-architecture-for-low-volume-python-e-commerce-scraping.md)); normalize into `listing` rows; wire **Frankfurter FX → USD** with `fx_rate`/`fx_pair`/`fx_rate_date`/`fx_source` stamped **on each observation** (gap #3); set the international flag.
  - *Acceptance:* all **5/5 sources** yield ≥1 normalized `listing` on a scheduled run; **100%** of non-USD listings carry a stored FX rate + date and a normalized USD price; international listings are flagged; a re-run produces new `observation` rows (time-series), not duplicate `listing`s.
- **M2 — Scoring.**
  - *Tasks:* implement the scoring engine (prompt #4 / [`principled-deal-score…md`](research/principled-deal-score-for-hard-drive-listings.md)) — log(`$/TB`) cohort percentile with 90-day window + 30-day half-life decay, cohort key = capacity · tier · interface · condition, and the **continuous warm-up** `λ = min(1, n_eff/50)` shrinkage toward 0.5 (gap #12); persist per-sub-score explanation payloads.
  - *Acceptance:* **every** listing has a 0–100 score that is **reproducible** from stored inputs (re-scoring yields the identical value); the score exposes a **per-factor breakdown**; thin-cohort listings (n_eff < 50) visibly shrink toward neutral and are marked **provisional**; a documented cohort-relaxation fallback (condition → adjacent capacity → parent tier) fires when a cohort is too small.
- **M3 — Web UI.**
  - *Tasks:* build Dashboard (filterable ranked deals), Listing detail (score breakdown + "why it matched"), Watches manager (hard filters vs thresholds, no free-text), Price-history view, and listing-state controls (gap #7); expose the Django admin as back-office.
  - *Acceptance:* owner can filter the dashboard by brand/capacity/tier/interface/condition and **create, edit, and delete a watch** through the UI; a listing detail renders the **pass-margin** explanation for each crossed threshold; state changes (interested/purchased/dismissed/snoozed) persist and re-render.
- **M4 — Alerts.**
  - *Tasks:* email alerts via AgentMail with the dedup/debounce design (prompt #11 / [`designing-a-low-noise-alerting-layer…md`](research/designing-a-low-noise-alerting-layer-for-a-hard-drive-deal-monitor.md)) — listing + alert fingerprints, cooldown/hysteresis, signed one-click action links, **email-delivery confirmation**.
  - *Acceptance:* a single qualifying price drop fires **exactly one** email (verified against the alert-fingerprint ledger — no duplicate for the same watch/listing/reason/threshold bucket); one-click snooze/stop links work and are HMAC-verified; a simulated repost under a new URL is **de-duplicated**; a delivery failure is **detectably surfaced**.
- **M5 — Hardening & breadth.**
  - *Tasks:* add the remaining marketplaces, entity resolution (prompt #6), backups (#5) into the existing Hetzner process, application self-observability (#6), and the scraper test suite (#9 — vcrpy + syrupy + per-tier contract canary).
  - *Acceptance:* **≥15 sources** live; a backup is **restore-tested into a scratch instance** at least once; a deliberately broken parser trips a **scraper-rot alert within one scheduled cycle**; CI runs the cassette/snapshot suite green.

#### User Comments

**Status:** Accepted with changes → **milestones expanded with tasks + measurable acceptance criteria; to be finalized via `spec-pipeline`**

**Reasoning:** I largely agree with the proposed solution. I would like to see a more detailed breakdown of the milestones, including specific tasks and deliverables for each milestone. I would also like to see a more detailed acceptance criteria for each milestone, including specific metrics and thresholds that must be met in order for the milestone to be considered complete. I will likely be using the `spec-pipeline` plugin from the L3DigitalNet Claude-Code-Plugins repo/marketplace for final spec authoring and phased development.

### 9. No testing strategy for scrapers

**Gap:** CI names "testing workflows" but the spec never says **how** to test scrapers against sites that change and fight bots. Untested scrapers rot silently.

**Evidence:** [`disk-search.md:73`](specs/disk-search.md).

**Proposed solution:**

- **Recorded fixtures:** **vcrpy cassettes** per source (record the real HTTP response once, replay in CI) so parsing is tested deterministically and offline.
- **Snapshot tests:** **syrupy** golden-file assertions on the parsed structured output — a parser regression shows as a snapshot diff.
- **Production canary:** a **scheduled (not just CI)** live **JSON-LD / structured-data contract check** per source, plus a **known-value canary page**, to catch the "technically valid but wrong element" failure that offline tests can't see.
- **Runtime validation:** **Pydantic v2** per-record validation + per-source `last_success_at` / consecutive-failure counters + a count-vs-rolling-average assertion; alert when a source returns 0 or malformed results N runs in a row. (Shares the `scraper_runs` table from gap #6.)

**Research:** [`lightweight-observability-and-scraper-health-monitoring.md`](research/2026-07-03-lightweight-observability-and-scraper-health-monitoring.md).

**Research-informed amendments (2026-07-03)** — the vcrpy + syrupy + contract-canary + Pydantic-v2 stack is **confirmed** by [`pragmatic-architecture…md`](research/pragmatic-architecture-for-low-volume-python-e-commerce-scraping.md) and [`us-scraping-and-data-retention-landscape…md`](research/us-scraping-and-data-retention-landscape-for-a-retail-hdd-price-monitor.md); five refinements:

1. **Canary must be per-extraction-tier, not JSON-LD-only.** Each source resolves to a different payload tier (JSON-LD → platform JSON like Shopify `.js` → hidden bootstrap `__NEXT_DATA__` → HTML selectors), and tiers break independently. Assert the **shape** of whichever payload each source actually uses. Concrete rot vector: a target's Next.js **Pages→App Router** upgrade silently removes `__NEXT_DATA__` — a shape assertion catches it, a field-presence check may not.
2. **Risk-weight canary frequency by tier.** Sources on brittle HTML selectors (bottom of the ladder) warrant tighter canary coverage than sources on a first-party JSON endpoint — fragility increases monotonically down the ladder.
3. **Scrub cassettes of PII before commit — a compliance requirement, not hygiene.** Retail payloads embed reviews, Q&A, seller/user blocks; the retention research says do not collect "anything that could plausibly be personal data." A committed vcrpy cassette is durable storage, so strip those blocks before commit.
4. **Do not commit real cassettes for retention-restricted sources.** Amazon PA/Creators content (24h TTL), Google/Serper results ("transient only"), and stored images breach license terms if durably committed — use **synthetic/hand-crafted fixtures** for those; real recorded cassettes are fine for the recert specialists.
5. **Classify failure type in the counter layer.** Distinguish recoverable **parser rot** from **"now anti-bot-protected"** — a soft-block often returns HTTP 200 with a challenge/empty body, so the count-vs-rolling-average + empty-result assertion is the right silent-block detector; the latter is a *stop/escalate* decision (per the research's "if it needs CAPTCHA/residential rotation, stop"), not a fix. Use a truthful production UA in live canaries so they exercise the same access path as production.

#### User Comments

**Status:** Accepted with caveat → **confirmed by research; five amendments folded in**

**Reasoning:** Looks good, but check new research in `docs/research/` for any additional information that may be relevant to the testing strategy. The proposed solution above is a good starting point, but we will need to confirm the final testing strategy before building.

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

**Research-informed refinements (2026-07-03)** — from [`programmatic-acquisition…md`](research/programmatic-acquisition-research-for-enterprise-and-nas-drive-merchants.md), [`tavily-brave-serper.md`](research/tavily-brave-serper.md), [`pragmatic-architecture…md`](research/pragmatic-architecture-for-low-volume-python-e-commerce-scraping.md), and [`orchestration-choice…md`](research/orchestration-choice-for-a-single-vm-price-polling-service.md):

- **The budget is smaller than the gap implies — most acquisition is free.** No target merchant exposes a *paid-only* retail API; nearly all expose **free structured/HTML data** a self-hosted Scrapy parser reads at zero per-call cost (ServerPartDeals/TechMikeNY/others on Shopify; ETB/Bargain Hardware on Magento; goHardDrive/HardDrivesDirect legacy HTML). For marketplaces, **eBay Browse + Feed** and **Amazon SP-API** (if seller-authorized) are **free official feeds** — do **not** re-poll them via paid search APIs. So the only unavoidable recurring paid costs are **occasional search-API discovery calls, AgentMail, and backup object storage**; scraping itself is free compute on the VM.
- **Managed-scraping APIs should be avoided for this merchant set** (free structured data covers it); reserve them for a hostile tail that, per the scraping research, is the point to **skip the source instead**. Public list prices *as of 2026-07-03, all date-sensitive — re-verify at build*: ScraperAPI $49/mo→100k credits; Zyte API $0.13–$1.27/1k HTTP (charges only successes); Bright Data ~$1.5/1k; Firecrawl free 1k pages/mo. These are reference points for a ceiling, not a plan to spend.
- **Search APIs are discovery/spot-check only** ("frequent cheap discovery, less-frequent expensive validation") — never promote a search hit to a trusted offer without validating against the official API or merchant page. Note **Brave requires a plan that grants storage rights** to persist results — a licensing constraint on caching, not just call cost. Serper/Brave/Tavily per-call pricing was **not** quoted in research and must be pulled fresh.
- **The per-source budget record already has a home:** the orchestration research's **two-level token buckets** (per-source + per-domain) with `cadence`/`jitter`/`rate`/`burst` fields *are* the poll-budget mechanism gap #10 wants — reuse them. Recommended cadence is **single-digit daily checks per SKU**; circuit-break (`paused_pending_fix`) chronically failing sources to stop wasting calls.
- **Not covered by any report:** **AgentMail** email pricing and **object-storage/backup** costs — two of the four paid drivers. Look these up separately at build time.

#### User Comments

**Status:** Additional consideration needed → **research confirms free-feed-first is viable; concrete figures + rate-budget record identified (still needs a build-time pricing pass)**

**Reasoning:** We will have to research costs and come up with reasonable daily/weekly/monthly budgets for each source. Also consider strategies to rely on free feeds and structured-data parsing wherever possible to reduce costs (potentially spot check via search APIs). We will need to confirm the final budget model before building.

### 11. Shipping (and tax) not folded into the `$/TB` score

**Gap:** `$/TB` on item price alone misranks a cheap drive with high shipping — even domestically.

**Evidence:** [`disk-search.md:13`](specs/disk-search.md).

**Proposed solution:**

- Score on **price + shipping (+ tax where known)**, not item price alone. Marketplace shipping fields (e.g. eBay Browse `shippingOptions`, Serper `delivery`) are reliable **only when the request supplies correct buyer-location context** — so pin the buyer location on every query.
- When shipping is unknown/unavailable, **apply a penalty or flag** rather than silently scoring as if free — otherwise free-shipping and unknown-shipping listings rank identically.
- This composes with the **international flag** from gap #3 (note: gap #3's decision dropped the fixed overhead haircut, so shipping/tax handling is the domestic counterpart — a real, known shipping cost folded into `$/TB`; cross-border extra cost stays a flag, not a number).

**Research:** [`currency-conversion-and-landed-cost-estimation…md`](research/2026-07-03-currency-conversion-and-landed-cost-estimation-for-cross-border-drive-price-scoring.md).

#### User Comments

**Status:** Accepted

### 12. Cold-start: relative scoring has no history on day one

**Gap:** The moving-baseline / percentile scoring that pending prompt #4 will design needs accumulated history that doesn't exist at launch.

**Evidence:** Implied by the price-trend features at [`disk-search.md:19`](specs/disk-search.md), [`:22`](specs/disk-search.md).

**Proposed solution (design decision):**

- **Seed baselines** from the external reference tools that pending prompt #5 will catalogue (diskprices.com, camelcamelcamel/Keepa, r/DataHoarder threads) to provide an initial `$/TB` reference per capacity/tier until enough internal history accrues.
- **Absolute-threshold fallback** during the warm-up window, switching to the self-adjusting percentile baseline once a source has ≥ N observations per (capacity, tier).
- **Mark scores "provisional"** in the UI until the baseline is data-backed, so early scores aren't over-trusted.

**Research-informed refinements (2026-07-03)** — [`principled-deal-score…md`](research/principled-deal-score-for-hard-drive-listings.md) is the authoritative scoring source and [`drive-deal-tracker…baselines…md`](research/drive-deal-tracker-research-baselines-tools-shucking-and-timing.md) supplies the seed sources; these **change the design in four ways**:

1. **Replace the hard "switch at N observations" with continuous shrinkage.** The scoring report never hard-switches; it blends `s_price = λ·(1 − q) + (1 − λ)·0.5` with **`λ = min(1, n_eff/50)`**, so a thin cohort is automatically pulled toward neutral **0.5** and reaches full confidence at **≈50 effective observations**. Adopt this continuous warm-up — it *is* the built-in provisional-confidence mechanism (surface `n_eff`/`λ` as the "provisional" indicator).
2. **Threshold on *effective* sample size, not a raw count:** `n_eff = (Σw)²/Σ(w²)` under a 90-day window with **30-day half-life** decay (`w = 2^(−age_days/30)`).
3. **The absolute-threshold fallback should shrink toward 0.5, not toward an absolute $/TB verdict.** The report argues absolute thresholds "age badly in a falling market," and prefers a documented **cohort-relaxation** fallback (relax **condition → adjacent capacity → parent tier**) over an absolute table. Keep the dated July-2026 `$/TB` bands only as a **UI reference / sanity floor**, not as an input to the score.
4. **Expand the cohort key** beyond (capacity, tier) to **capacity · tier · interface/form-factor · condition bucket**; for SSDs add **endurance class (DWPD)** — the report is explicit that SSDs must never be compared on capacity alone.

**Seed sources, graded (they are not equally usable):** **Keepa** is the *only* sanctioned machine-readable seed (paid API, Python client) — the strongest programmatic candidate for Amazon-linked pricing. **ServerPartDeals** is the key **recert** benchmark but has no API — parse its highly-parseable catalog. **diskprices.com / CamelCamelCamel / PCPartPicker** are **UI/sanity-check references only** (no usable public API). **r/DataHoarder** is a **qualitative** signal, explicitly *not* a source of truth for current pricing. And every seed is **market-dated** — the 2026 bands reflect an abnormal ~46% supply-constrained run-up, so any seeded baseline must be **timestamped and aged out** as real observations accrue; the seed is a warm-up crutch, not a persistent anchor.

#### User Comments

**Status:** Additional research needed → **resolved: continuous-shrinkage warm-up (n_eff/50) replaces the hard switch; seed sources graded**

**Reasoning:** Research in `docs/research/` may provide more information on the cold-start scoring.

---

## Open questions surfaced by the research (status after 2026-07-03 reconciliation)

**Resolved:**

1. ~~**Framework: Django or FastAPI?**~~ → **Django.** The stack research ([`opinionated-core-stack…md`](research/opinionated-core-stack-recommendations-for-a-python-drive-price-monitor.md)) recommends Django + server-rendered templates + HTMX for this app shape; gaps #1 (auth) and #7 (UI) converge on it. Locks in `manage.py migrate`, Django `contrib.auth`, and the Django admin as back-office. *(Confirm against pending prompt #10's final write-up before scaffolding.)*
2. ~~**Is a public URL required, or is Tailscale-only acceptable?**~~ → **Public URL required** with a single strong-password account; Tailscale-only was rejected (gap #1).

**Still open (carried into build):**

3. **Does the Proxmox VM have a vTPM?** Determines whether `systemd-creds --with-key=tpm2` is a real hardware-bound fallback for static secrets — and, for a small static-secret set, whether it's simpler than a full OpenBao Agent (gap #2).
4. **`secret_id` out-of-band delivery to the VM** now that CI (GitHub-hosted, public repo) cannot be the courier — pick the provisioning/renewal path (gap #2).
5. **Ephemeral-runner tailnet auth:** Tailscale OAuth client vs pre-generated ephemeral auth key, per the existing tailnet ACL setup (gap #4).
6. **Existing Hetzner backup & monitoring coverage:** do they protect the price-history DB at the required RPO (freeze/thaw, PITR) and run **off-box**, or must pgBackRest / an off-box heartbeat be layered on (gaps #5, #6)?
7. **Build-time pricing pass:** current Serper/Brave/Tavily per-call pricing and AgentMail + backup object-storage costs — none quoted in research (gap #10).
