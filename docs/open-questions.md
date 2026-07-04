# Open Questions — `disk-search.md`

**Date:** 2026-07-03 **Subject:** The **unsettled** engineering/design decisions for [`disk-search.md`](specs/disk-search.md), front-loaded — plus the resolved decisions and gap analysis they came out of, kept below for provenance.

> This file began as a **gap analysis** of the spec (12 operational/product-engineering gaps not covered by research). Most of those gaps are now decided. What remains open is distilled into the **[Open questions](#open-questions)** section; the full gap write-ups and every settled decision have moved to **[Resolved](#resolved)**.

## How to maintain this document

Read **[Open questions](#open-questions)** for anything that still needs a call. Everything under **[Resolved](#resolved)** is settled and kept only for provenance — you should not have to read it to know what's outstanding.

**Rules:**

1. **Open questions first, distilled.** Each open question states _only_ the unresolved decision — not the history behind it. The history lives in Resolved and in the research reports.
2. **When a question is settled, move it down.** Relocate its substance to Resolved (record the decision + any ADR) and remove it from Open questions. Never leave a settled item up top.
3. **Split partially-settled items.** If a gap is half-decided, move the decided half to Resolved and leave a focused open question covering _only_ the remaining fork. (This is how the eight OQs below were produced from the twelve gaps.)
4. **Two comment layers per open question, kept separate:**
   - `#### Agent notes` — research/reconciliation context, maintained by the assistant.
   - `#### My Comments` — the owner's notes and decisions; **the assistant does not edit this block.**
5. **Cross-reference by stable ID.** `OQ#` = open question, `RQ#` = resolved question, `gap #` = original gap. ADRs, the spec, and TODO link here by those IDs — keep them stable. If you must renumber, update the referencing ADRs/TODO/spec **in the same change**.

## Table of Contents

- [Open Questions — `disk-search.md`](#open-questions--disk-searchmd)
  - [How to maintain this document](#how-to-maintain-this-document)
  - [Table of Contents](#table-of-contents)
  - [Open questions](#open-questions)
    - [At a glance](#at-a-glance)
    - [OQ1 — `secret_id` out-of-band delivery to the CT](#oq1--secret_id-out-of-band-delivery-to-the-ct)
      - [Agent notes](#agent-notes)
      - [My Comments](#my-comments)
    - [OQ2 — Ephemeral-runner tailnet auth](#oq2--ephemeral-runner-tailnet-auth)
      - [Agent notes](#agent-notes-1)
      - [My Comments](#my-comments-1)
    - [OQ3 — DB RPO acceptance (+ TimescaleDB dump handling)](#oq3--db-rpo-acceptance--timescaledb-dump-handling)
      - [Agent notes](#agent-notes-2)
      - [My Comments](#my-comments-2)
    - [OQ4 — DB placement: own CT vs shared datastores CT](#oq4--db-placement-own-ct-vs-shared-datastores-ct)
      - [Agent notes](#agent-notes-3)
      - [My Comments](#my-comments-3)
    - [OQ5 — Off-box heartbeat](#oq5--off-box-heartbeat)
      - [Agent notes](#agent-notes-4)
      - [My Comments](#my-comments-4)
    - [OQ6 — Final UI page inventory + dismiss→suppress feedback + purchase tracking](#oq6--final-ui-page-inventory--dismisssuppress-feedback--purchase-tracking)
      - [Agent notes](#agent-notes-5)
      - [My Comments](#my-comments-5)
    - [OQ7 — Running-cost budget model (build-time pricing pass)](#oq7--running-cost-budget-model-build-time-pricing-pass)
      - [Agent notes](#agent-notes-6)
      - [My Comments](#my-comments-6)
    - [OQ8 — Scraper testing finalization](#oq8--scraper-testing-finalization)
      - [Agent notes](#agent-notes-7)
      - [My Comments](#my-comments-7)
    - [OQ9 — Acquisition cadence, throttle \& skip policy](#oq9--acquisition-cadence-throttle--skip-policy)
      - [Agent notes](#agent-notes-8)
      - [My Comments](#my-comments-8)
    - [OQ10 — Reliability / resilient acquisition](#oq10--reliability--resilient-acquisition)
      - [Agent notes](#agent-notes-9)
      - [My Comments](#my-comments-9)
  - [Resolved](#resolved)
    - [Resolved questions](#resolved-questions)
    - [Gap summary (all 12, for reference)](#gap-summary-all-12-for-reference)
    - [Resolved gaps \& decisions](#resolved-gaps--decisions)
      - [Gap 1 — Web-app authentication (settled, ADR 0005)](#gap-1--web-app-authentication-settled-adr-0005)
      - [Gap 2 — `.env` secrets model → OpenBao (settled except `secret_id` delivery)](#gap-2--env-secrets-model--openbao-settled-except-secret_id-delivery)
      - [Gap 3 — Currency / landed-cost normalization (settled)](#gap-3--currency--landed-cost-normalization-settled)
      - [Gap 4 — Deployment \& service topology (settled, ADR 0006)](#gap-4--deployment--service-topology-settled-adr-0006)
      - [Gap 5 — Backup / disaster recovery (settled CT path, ADR 0003)](#gap-5--backup--disaster-recovery-settled-ct-path-adr-0003)
      - [Gap 6 — Application self-observability (settled CT path except off-box heartbeat)](#gap-6--application-self-observability-settled-ct-path-except-off-box-heartbeat)
      - [Gap 7 — UI/UX (settled: Django + HTMX + post-alert model; inventory open)](#gap-7--uiux-settled-django--htmx--post-alert-model-inventory-open)
      - [Gap 8 — v1 scope / phasing / acceptance criteria (settled)](#gap-8--v1-scope--phasing--acceptance-criteria-settled)
      - [Gap 9 — Scraper testing strategy (settled stack + amendments; build-time params open)](#gap-9--scraper-testing-strategy-settled-stack--amendments-build-time-params-open)
      - [Gap 10 — Running-cost / budget model (settled approach; pricing pass open)](#gap-10--running-cost--budget-model-settled-approach-pricing-pass-open)
      - [Gap 11 — Shipping (and tax) in the `$/TB` score (settled)](#gap-11--shipping-and-tax-in-the-tb-score-settled)
      - [Gap 12 — Cold-start scoring (settled)](#gap-12--cold-start-scoring-settled)
    - [Scope \& research provenance](#scope--research-provenance)

---

## Open questions

Ten decisions remain. **OQ1–OQ8** are the still-open parts of the original gaps (linked; the settled part of each is in [Resolved](#resolved)). **OQ9–OQ10** surfaced from the spec's General Design Principles consistency audit.

### At a glance

| # | Open question | From | The fork |
| --- | --- | :-: | --- |
| **OQ1** | `secret_id` out-of-band delivery to the CT | gap #2 | pick the provisioning/renewal path now that public-repo CI can't be the courier |
| **OQ2** | Ephemeral-runner tailnet auth | gap #4 | Tailscale OAuth client vs pre-generated ephemeral key |
| **OQ3** | DB RPO (+ TimescaleDB dumps) | gap #5 | accept ≤1 h / no-PITR vs layer pgBackRest + WAL inside the CT |
| **OQ4** | DB placement | gap #5 | own Postgres in the disk-search CT vs the shared datastores CT |
| **OQ5** | Off-box heartbeat | gap #6 | add to off-site GMK Uptime Kuma vs a free healthchecks.io monitor |
| **OQ6** | Final UI inventory + dismiss→suppress | gap #7 | confirm pages; decide if a user _dismiss_ silences re-alerts; purchase-tracking scope |
| **OQ7** | Running-cost budget model | gap #10 | pricing pass ✅ (2026-07-03 → ~$8–15/mo search-API envelope; AgentMail free); residual = encode per-source poll budgets at build |
| **OQ8** | Scraper testing finalization | gap #9 | per-tier canary frequencies; synthetic vs real cassettes per source |
| **OQ9** | Acquisition cadence, throttle & skip | principles §1+5 | per-source cadence numbers + adaptive back-off thresholds + tier-ladder skip cutoff (no spec reword — real-time-where-tolerated is in scope) |
| **OQ10** | Reliability / resilient acquisition | principle §4 | per-source isolation, retry/backoff, circuit-break, health alerts |

---

### OQ1 — `secret_id` out-of-band delivery to the CT

**From:** gap #2 (resolved). **Decision needed:** how the OpenBao AppRole `secret_id` is provisioned and renewed on the disk-search CT, now that public-repo CI (GitHub-hosted) **cannot** be the courier and must hold **no** OpenBao credential.

The secrets _path_ is settled (local OpenBao Agent, AppRole auto-auth, templates to tmpfs `/run/disk-search/secrets.env` — see resolved gap #2). The `role_id` ships in the CT image / config-management. Only the `secret_id` delivery is open.

#### Agent notes

- Candidate paths: an **Ansible run against the CT over Tailscale**, an existing infra automation, or a **local renewal process** on the CT. Pick the provisioning **and** renewal mechanism together.
- The vTPM / `systemd-creds --with-key=tpm2` shortcut is **out** — a CT has no per-container TPM (it shares the host kernel), so that path would reduce to host-key-only encryption (see [RQ3](#resolved-questions), [RQ5](#resolved-questions)). The local OpenBao Agent is therefore the only secrets path.
- Research: [`github-actions-cd-private-debian-vm.md`](research/2026-07-03-github-actions-cd-private-debian-vm.md) §3.

#### My Comments

SSH into Hetzner and look at the existing infra automation, particularly the CT with OpenBao. I believe that bao-agent will be able to resolve this issue.

---

### OQ2 — Ephemeral-runner tailnet auth

**From:** gap #4 (resolved, [ADR 0006](adr/adr-0006-cd-rsync-over-tailscale-ssh.md)). **Decision needed:** which mechanism authenticates the ephemeral GitHub-hosted runner onto the tailnet for the `rsync`/SSH deploy — a **Tailscale OAuth client** (scoped, auto-rotating; preferred) or a **pre-generated ephemeral auth key**.

Not resolvable server-side — it depends on what the existing tailnet ACL setup supports (an admin-console / ACL decision). ADR 0006's CD decision holds regardless of which is chosen.

#### Agent notes

- OAuth client is preferred (scoped, auto-rotating) but must be checked against the existing tailnet ACLs.
- Research: [`github-actions-cd-private-debian-vm.md`](research/2026-07-03-github-actions-cd-private-debian-vm.md).

#### My Comments

Use the Tailscale API key from OpenBao to access the tailnet and check the ACLs. If the ACLs allow for OAuth client auth, then use that. Otherwise, provide additional options/alternatives.

---

### OQ3 — DB RPO acceptance (+ TimescaleDB dump handling)

**From:** gap #5 (resolved CT path, [ADR 0003](adr/adr-0003-deploy-as-lxc-container.md)). **Decision needed:** is the inherited **≤1 h RPO / no PITR** (hourly logical dumps) acceptable for the accumulating price-history moat, or must **pgBackRest + WAL archiving** be layered **inside the CT**?

A second driver is coupled to this: TimescaleDB ([ADR 0007](adr/adr-0007-datastore-postgresql-timescaledb.md)) means the inherited logical `pg_dump` needs **TimescaleDB-aware** dump/restore (`timescaledb_pre_restore()` / `post_restore()`, compression state not preserved), so **physical** backup may be preferable for _correctness_, not only for RPO. Decide both together.

#### Agent notes

- **Fallback design if tighter RPO/PITR is wanted:** pgBackRest physical backup + continuous WAL archiving on-CT (`repo1`) with a second repo (`repo2`) on S3-compatible storage (Backblaze B2 or Hetzner Storage Box), pgBackRest AES-256 encryption → PITR + offsite 3-2-1. Supplement with a weekly `pg_dumpall`.
- TimescaleDB: **physical** backups (pgBackRest / `pg_basebackup`) need no special handling; only logical (`pg_dump`) backups carry hypertable caveats — prefer physical.
- Keep the **monthly restore-test** discipline regardless — an untested backup is a hope. **Patch PostgreSQL/tooling** (recent `pg_dump`/`pg_basebackup`/`pg_rewind` CVEs live in the tools).
- Independent of the CT decision. Research: [`postgresql-backup-disaster-recovery-single-vm.md`](research/2026-07-03-postgresql-backup-disaster-recovery-single-vm.md).

#### My Comments

Create a document of all backup requirements and constraints, including RPO, PITR, and TimescaleDB considerations. Evaluate the current backup strategy against these requirements and determine if the current ≤1 h RPO is acceptable or if a more robust solution is needed. Go into the `homelab` repo and create appropriate documentation for disk-search and document it's backup needs there. The backup strategy will have to be coordinated with the existing Hetzner backup strategy and any other relevant infrastructure. We can expand/improve as necessary, but the first step is to document the requirements and constraints. This is not a blocker, it can be completed in parallel or after the project is deployed, but it should be done before the first backup is taken.

---

### OQ4 — DB placement: own CT vs shared datastores CT

**From:** gap #5 (resolved CT path, [ADR 0003](adr/adr-0003-deploy-as-lxc-container.md)). **Decision needed:** own Postgres **inside the disk-search CT** (self-contained, matches the spec's "same container" intent) vs the **shared datastores CT** (centralized, already in the dump pipeline).

Either way the DB must be added to `backup-dumps.sh`. Both are compatible with ADR 0003.

#### Agent notes

- Trade-off is self-containment vs centralization; the backup-wiring obligation is the same for both (coverage is a hardcoded allowlist, not auto-discovery).

#### My Comments

The app/project and it's associated database should be self-contained in the disk-search CT. This is consistent with the spec's intent and simplifies deployment and management.

---

### OQ5 — Off-box heartbeat

**From:** gap #6 (resolved CT path). **Decision needed:** the one real observability gap after the CT decision — there is **no off-box watchdog**, so a total-box outage would be caught by no external observer. Choose the fix: add a disk-search liveness monitor to the **off-site GMK Uptime Kuma** (already alerts by email) vs a free **healthchecks.io** heartbeat.

#### Agent notes

- Either satisfies the "one heartbeat must live off-box" requirement the research insists on. GMK Uptime Kuma reuses existing infra; healthchecks.io is a zero-infra external.
- **Settled and kept regardless** (generic infra monitoring can't see these): the in-app **`scraper_runs` table** (shared with [OQ8](#oq8--scraper-testing-finalization) / gap #9), a **dead-man's-switch heartbeat**, and **email-delivery confirmation**. Infra health (up/disk/CPU/RAM) is auto-covered — the fleet-digest health check auto-discovers the CT from `pct list`; confirm a **disk-space threshold** alert applies since raw scrape payloads grow. Error tracking (GlitchTip/Sentry) is **not** in the existing stack — add it only if wanted.
- Research: [`lightweight-observability-and-scraper-health-monitoring.md`](research/2026-07-03-lightweight-observability-and-scraper-health-monitoring.md).

#### My Comments

We will use the existing GMK Uptime Kuma instance to monitor the disk-search CT. This is consistent with the existing infrastructure and will provide the necessary off-box heartbeat monitoring. This will also be monitored periodically by the `Hetzner EX130-R · Fleet Digest` (see the `homelab` repo) for details. This is not a blocker, it can be completed in parallel or after the project is deployed, but should be done before entering production.

---

### OQ6 — Final UI page inventory + dismiss→suppress feedback + purchase tracking

**From:** gap #7 (resolved: Django + HTMX + post-alert model). **Decision needed:** the rendering approach (Django + server-rendered templates + HTMX, [ADR 0004](adr/adr-0004-web-framework-django-htmx.md)) and the post-alert **state machine** are settled. Still open:

1. **Confirm the final MVP page inventory / flows** (proposed below).
2. **Dismiss→suppress:** should a user _dismiss_ actually silence future re-alerts? The alerting research dedups on listing + alert fingerprints but **does not** model "user marked dismissed → suppress." Wiring dismiss into alert-suppression is an **addition beyond the research** and must be designed.
3. **Purchase tracking / realized-savings:** no research backing — treat as **genuinely optional for v1**.

#### Agent notes

- **Proposed MVP page inventory (to confirm):** Dashboard (filterable ranked deals) · Listing detail (score breakdown + "why it matched") · Watches / alert-rules manager · Price-history view · Listing-state controls (`interested`/`purchased`/`dismissed`/`snoozed`).
- Use the **Django admin as the internal back-office** (inspect offers, fix bad entity matches, triage ingestion) — but the admin is _not_ the user-facing front end, so the pages above are still needed.
- **Post-alert model (settled):** per-watch, per-listing state machine (`none / pending / firing / cooling / digested`); snooze at two granularities (watch `snoozed_until`; listing 24 h / 7 d); one-click actions as HMAC-signed single-purpose links; the **watch is the unit of opt-out**.
- **Score-breakdown UI** has a ready pattern: the alerting report's "why it matched" block (current facts + per-threshold pass-margin line) is directly reusable as the listing-detail explainability view.
- **Watch-rule UI shape:** keep **hard filters separate from thresholds**; **no free-text title matching** — watches target normalized fields only.
- Research: [`opinionated-core-stack-recommendations-for-a-python-drive-price-monitor.md`](research/opinionated-core-stack-recommendations-for-a-python-drive-price-monitor.md), [`designing-a-low-noise-alerting-layer-for-a-hard-drive-deal-monitor.md`](research/designing-a-low-noise-alerting-layer-for-a-hard-drive-deal-monitor.md).

#### My Comments

_(none yet)_

---

### OQ7 — Running-cost budget model (build-time pricing pass)

**From:** gap #10 (resolved approach). **Decision needed:** set per-source poll budgets against a monthly ceiling. The approach is settled (free-feed-first); what's open is a **build-time pricing pass** not covered by any research — **current Serper/Brave/Tavily per-call pricing, AgentMail email pricing, and backup object-storage costs** — plus verifying **Brave's storage-rights plan requirement** (a licensing constraint on caching, not just call cost).

#### Agent notes

- **Free-feed-first is confirmed viable:** no target merchant exposes a paid-only retail API; nearly all expose free structured/HTML data a self-hosted Scrapy parser reads at zero per-call cost. **eBay Browse + Feed** and **Amazon SP-API** (if seller-authorized) are **free official feeds** — do not re-poll them via paid search APIs. Scraping itself is free compute on the CT. The only unavoidable recurring paid costs are occasional search-API discovery calls, AgentMail, and backup object storage.
- **Search APIs are discovery/spot-check only** — never promote a search hit to a trusted offer without validating against the official API or merchant page.
- **Pricing pass — verified 2026-07-03 (Claude web research against vendor pricing pages).** Marginal per-call cost, assuming monthly free tiers exhausted:

  | Service | Marginal cost | Free tier | Storage / caching rights |
  | --- | --- | --- | --- |
  | **Serper** | **$0.001**/query (one-time $50 / 50k-credit pack; credits expire 6 mo) | 2,500 credits, one-time | No vendor restriction found |
  | **Brave Search** | **$5.00/1k** ($0.005/query); $5/mo auto-credit ≈ 1k free | ≈ 1k/mo via the $5 credit | **Standard plan does _not_ grant storage rights** — persisting Brave's own result JSON needs an **Enterprise "contact us"** plan (historically ~$45/1k, a **stale 2025** figure — get a quote) |
  | **Tavily** | **$0.008**/basic search ($0.016 advanced) — dearest of the three | 1,000 credits/mo (recurring) | Marketed for RAG; no explicit persist clause found |
  | **AgentMail** | **$0** at this volume | 3,000 emails/mo, 100/day cap | — |

  **Bottom line:** ≈ **$8–15/mo** for the three search APIs combined **if traffic is weighted toward Serper** (~5× cheaper than Brave, ~8× than Tavily) — inside the **$10–20 target**. An even 1k/1k/1k split ≈ $14/mo; leaning on Brave/Tavily for the bulk breaches $20. **AgentMail is effectively free** — alert volume sits far under both caps; the $20 Developer tier is only forced by >100 emails/day or by needing a custom sending domain (deliverability).

- **Brave storage-rights is an _architecture_ constraint, not just a cost:** use Brave — and, to be safe, Serper/Tavily too — **purely as a discovery/URL source; do not persist the search provider's own snippets/JSON.** The scraper then fetches and stores the _listing page's_ own content, which is outside the provider's licensing scope. This keeps the cheap $5/1k Brave tier sufficient and dovetails with the discovery-only rule above. Confirm Serper/Tavily ToS before persisting their raw results.
- **Watch items:** Brave's storage-rights price is now Enterprise-only (no public number; the ~$45/1k is a stale 2025 indicative figure) — get a live quote before relying on it. **Tavily** was announced as acquired by Nebius (2026-02-10) — re-verify its pricing before build. **This pricing pass answers OQ7's build-time-pricing fork;** the residual is a build-time config task (encode per-source poll budgets within the ~$8–15/mo envelope), not an open research question.
- **Managed-scraping APIs avoided for this merchant set** (free structured data covers it); reference list prices are date-sensitive — re-verify at build.
- **The per-source budget record already has a home:** the orchestration research's **two-level token buckets** (per-source + per-domain, `cadence`/`jitter`/`rate`/`burst`) _are_ the poll-budget mechanism — reuse them. Recommended cadence: single-digit daily checks per SKU; circuit-break chronically failing sources.
- Research: [`programmatic-acquisition-research-for-enterprise-and-nas-drive-merchants.md`](research/programmatic-acquisition-research-for-enterprise-and-nas-drive-merchants.md), [`tavily-brave-serper.md`](research/tavily-brave-serper.md), [`pragmatic-architecture-for-low-volume-python-e-commerce-scraping.md`](research/pragmatic-architecture-for-low-volume-python-e-commerce-scraping.md), [`orchestration-choice-for-a-single-vm-price-polling-service.md`](research/orchestration-choice-for-a-single-vm-price-polling-service.md).

#### My Comments

**Search:** I have active accounts for each search service and I keep them topped up with funds. This question will require additional research to find the current per-call pricing for each service and to verify Brave's storage-rights plan requirement. Since I use these services elsewhere we will assume that any monthly free tier limits have already been exceeded and that we will be paying for any calls made. I feel that I will be comfortable with $10 to $20 per month total for all three services combined, but will reconsider after additional research (to be performed by Claude).

**AgentMail:** AgentMail is free; research the free tier limits, but it is unlikely to be a problem.

**Backup Costs:** The backup object storage costs are already budgeted as part of my general server costs, but I will verify that the current plan is sufficient for the expected data volume. No further action is needed for this, but I will keep an eye on it.

---

### OQ8 — Scraper testing finalization

**From:** gap #9 (resolved stack + amendments). **Decision needed:** the **vcrpy + syrupy + contract-canary + Pydantic-v2** stack and its five amendments are settled/confirmed by research. What remains is **build-time finalization**: concrete **per-tier canary frequencies** (risk-weighted down the extraction ladder) and **per-source assignment of synthetic vs real cassettes**.

#### Agent notes

- **Canary must be per-extraction-tier** (JSON-LD → platform JSON → hidden bootstrap → HTML selectors); tiers break independently, so assert the shape of whichever payload each source actually uses. **Risk-weight frequency by tier** — brittle HTML selectors warrant tighter coverage than a first-party JSON endpoint.
- **Do not commit real cassettes for retention-restricted sources** (Amazon PA/Creators 24 h TTL, Google/Serper "transient only", stored images) — use **synthetic/hand-crafted fixtures**; real recorded cassettes are fine for the recert specialists. **Scrub cassettes of PII before commit** (a compliance requirement).
- **Classify failure type** in the counter layer — recoverable **parser rot** vs **now-anti-bot-protected** (a soft-block often returns HTTP 200 + challenge/empty body). The latter is a _stop/escalate_ decision, not a fix.
- Shares the `scraper_runs` table with [OQ5](#oq5--off-box-heartbeat) / gap #6.
- **Queued for ChatGPT Deep Research** (owner, 2026-07-03): prompt **#13** in [`further-research-needed-prompts.md`](further-research-needed-prompts.md) covers exactly this build-time finalization (risk-weighted per-tier canary frequencies; synthetic-vs-real cassette assignment per source). OQ8 stays **open** pending that report.
- Research: [`lightweight-observability-and-scraper-health-monitoring.md`](research/2026-07-03-lightweight-observability-and-scraper-health-monitoring.md), [`pragmatic-architecture-for-low-volume-python-e-commerce-scraping.md`](research/pragmatic-architecture-for-low-volume-python-e-commerce-scraping.md), [`us-scraping-and-data-retention-landscape-for-a-retail-hdd-price-monitor.md`](research/us-scraping-and-data-retention-landscape-for-a-retail-hdd-price-monitor.md).

#### My Comments

Agent comments look good, but I want to conduct a full deep research with ChatGPT looking into this. Add an entry and prompt to `docs/further-research-needed-prompts.md`.

---

### OQ9 — Acquisition cadence, throttle & skip policy

**From:** General Design Principles audit (folds findings #1 + #5). **Principles-level wording settled:** the old "Stewardship & Responsibility" principle was replaced in the spec with **"Moderate Aggressive Usage"** ([`disk-search.md:21`](specs/disk-search.md)). **Owner posture (2026-07-03):** poll as aggressively — up to real-time/continuous — as each source _tolerates_, and moderate **only** when a service-side protection or red-line would be crossed. The spec's "real-time (or near real-time)" Features framing is therefore **consistent and stays as-is — no reword** (the earlier "reword the real-time framing" task is **withdrawn**). **Decision needed:** the concrete numbers that operationalize "aggressive but self-moderating":

- **per-source cadence** — target poll frequency per source/tier (research floor: single-digit daily checks per SKU; go faster where the source tolerates it);
- **adaptive throttle / back-off** — which signals mark an approaching red-line (HTTP 429/503, soft-block challenge, latency spikes) and the cooldown they trigger, so aggressiveness self-limits _before_ tripping a protection;
- **skip policy** — the tier-ladder cutoff (official API → structured data → headless scrape → **skip**) for a source that cannot be polled without crossing a red-line.

#### Agent notes

- **No spec reword needed** (owner, 2026-07-03): real-time/continuous polling _where the source tolerates it_ is within "Moderate Aggressive Usage" — be aggressive, moderate only when a service protection/red-line would be crossed. This supersedes the earlier note that Features L25/L35 must be reworded; that task is **withdrawn**.
- The cadence + throttle mechanism is already designed: the orchestration research's **two-level token buckets** (per-source + per-domain; `cadence`/`jitter`/`rate`/`burst`) set **aggressively**, plus an **adaptive 429/503 cooldown** that pulls them back as a protection is approached — shared with [OQ7](#oq7--running-cost-budget-model-build-time-pricing-pass) (same budget mechanism) and [OQ10](#oq10--reliability--resilient-acquisition) (same circuit-breaker substrate). Research floor: single-digit daily per SKU; circuit-break chronically failing sources.
- The tier ladder and "**skip** rather than fight anti-bot" is the settled acquisition posture (gap #10 / OQ7 and the scraping research).
- Research: [`orchestration-choice-for-a-single-vm-price-polling-service.md`](research/orchestration-choice-for-a-single-vm-price-polling-service.md), [`pragmatic-architecture-for-low-volume-python-e-commerce-scraping.md`](research/pragmatic-architecture-for-low-volume-python-e-commerce-scraping.md), [`us-scraping-and-data-retention-landscape-for-a-retail-hdd-price-monitor.md`](research/us-scraping-and-data-retention-landscape-for-a-retail-hdd-price-monitor.md).

#### My Comments

I have changed the spec to remove:

```text
- **Stewardship & Responsibility:** The tool should be designed to minimize the impact on the marketplaces it monitors, avoiding excessive requests or scraping that could be considered abusive or violate terms of service.
```

and replaced it with:

```text
- **Moderate Aggressive Usage:** The tool should be designed to avoid excessive requests or scraping that could be considered abusive or violate terms of service or result in rate limiting.
```

Update the open question to reflect that the spec has been updated to remove the Stewardship & Responsibility language and replace it with Moderate Aggressive Usage. The open question is now focused on confirming the per-source cadence/politeness numbers and confirming the skip policy.

---

### OQ10 — Reliability / resilient acquisition

**From:** General Design Principles audit (finding #4). **Decision needed:** the **Reliability** principle requires graceful degradation, but the spec defines no failure model. Decide the acquisition failure model, then add a Features note:

- **per-source failure isolation** — one marketplace being down, rate-limited, or changing its markup must not halt the others;
- **retry/backoff** policy and **circuit-breaking** thresholds (a source that fails repeatedly is paused → `paused_pending_fix`) instead of silently returning stale/empty data;
- **health alerting** on repeated failure, wired to the `scraper_runs` table.

#### Agent notes

- **Status (2026-07-03):** both dependencies are moving — [OQ5](#oq5--off-box-heartbeat) is **settled** (off-box heartbeat = the off-site GMK Uptime Kuma) and [OQ8](#oq8--scraper-testing-finalization) is **queued for Deep Research** (prompt #13; parser-rot-vs-anti-bot failure classification). OQ10 stays **open** until OQ8 lands that failure model; the resilience substrate itself — per-source failure isolation, retry/backoff, circuit-break (`paused_pending_fix`), and the `scraper_runs` table (gap #6 / gap #9) — is already settled and only needs wiring.
- Circuit-break state (`paused_pending_fix`) is from the orchestration research; the count-vs-rolling-average + empty-result assertion (gap #9) is the silent-failure detector.
- Research: [`orchestration-choice-for-a-single-vm-price-polling-service.md`](research/orchestration-choice-for-a-single-vm-price-polling-service.md), [`lightweight-observability-and-scraper-health-monitoring.md`](research/2026-07-03-lightweight-observability-and-scraper-health-monitoring.md).

#### My Comments

See [OQ5](#oq5--off-box-heartbeat) and [OQ8](#oq8--scraper-testing-finalization) for the shared substrate. Then update or close this question based on the decisions made in those two questions.

---

## Resolved

Everything below is **settled**. It is retained for provenance and to keep ADR/spec cross-references resolvable. New readers do not need to read this to know what is outstanding — that is entirely in [Open questions](#open-questions).

### Resolved questions

Cross-cutting questions the research surfaced, now closed. Referenced by ADRs/spec as `RQ#`.

| # | Question | Resolution |
| --- | --- | --- |
| **RQ1** | Framework: Django or FastAPI? | **Django** + server-rendered templates + HTMX — the app's center of gravity is an authenticated listings DB + dashboards + CRUD + alerts, not an API platform. **[ADR 0004](adr/adr-0004-web-framework-django-htmx.md).** Locks in `manage.py migrate`, `contrib.auth`, and the Django admin as back-office. |
| **RQ2** | Public URL required, or Tailscale-only acceptable? | **Public URL required**, with a single strong-password account; Tailscale-only rejected. Drives the auth model (resolved gap #1, [ADR 0005](adr/adr-0005-single-account-session-auth.md)). |
| **RQ3** | Does the Proxmox host give a per-service vTPM? | The host has `swtpm` installed, so a full **VM** could get a vTPM — but disk-search deploys as a **CT** (RQ5), which has **no per-container TPM** (shared host kernel). So `systemd-creds --with-key=tpm2` is **not** available → secrets go via the local OpenBao Agent (resolved gap #2, [OQ1](#oq1--secret_id-out-of-band-delivery-to-the-ct)). |
| **RQ4** | Existing Hetzner backup & monitoring coverage? | **Characterized on 2026-07-03** (specifics in the private `homelab` repo). **Backup:** file-level restic + hourly logical dumps to two offsite repos, but **opt-in per service via a hardcoded allowlist**, **no PITR** (≤1 h RPO), **no VM-image backup**. **Monitoring:** rich but **on-box only**, **no off-site watchdog**; a CT is auto-discovered by the health check, a VM is not. Net: a CT maximizes infra reuse; an off-box heartbeat ([OQ5](#oq5--off-box-heartbeat)) and a DB-RPO decision ([OQ3](#oq3--db-rpo-acceptance--timescaledb-dump-handling)) are the two things to add. |
| **RQ5** | Deployment model — CT vs VM? | **Dedicated LXC container**, superseding the spec's "VM". Aligns with the "every service in a dedicated LXC" standard and maximizes infra reuse (fleet-digest auto-discovers the CT; its data is reachable by the host's file-level restic). **[ADR 0003](adr/adr-0003-deploy-as-lxc-container.md).** Consequences: vTPM off the table (RQ3) → local OpenBao Agent; backup is **not** automatic (wire the CT into `backup-restic.sh`/`backup-dumps.sh`); DB on a container Postgres ([OQ4](#oq4--db-placement-own-ct-vs-shared-datastores-ct)). |
| **RQ6** | Datastore: PostgreSQL or MySQL? | **PostgreSQL (system-of-record) + TimescaleDB** for the price-history/observation side. **[ADR 0007](adr/adr-0007-datastore-postgresql-timescaledb.md).** Adds the TimescaleDB-aware-dump driver to [OQ3](#oq3--db-rpo-acceptance--timescaledb-dump-handling). |

### Gap summary (all 12, for reference)

The original gap analysis and where each landed. 🔴/🟡/🟢 = original priority.

| # | Gap | Pri | Outcome |
| --: | --- | :-: | --- |
| 1 | Web-app authentication undefined | 🔴 | **Settled** — single-account Argon2id session login ([ADR 0005](adr/adr-0005-single-account-session-auth.md)). |
| 2 | `.env` secrets contradict OpenBao standard | 🔴 | **Settled** (path) — local OpenBao Agent on the CT, decoupled from CI. Open part → [OQ1](#oq1--secret_id-out-of-band-delivery-to-the-ct). |
| 3 | No currency / landed-cost normalization | 🔴 | **Settled** — Frankfurter FX → USD; flag international listings (no fixed haircut). |
| 4 | Deployment & service topology a black box | 🔴 | **Settled** — `rsync` over Tailscale SSH + systemd ([ADR 0006](adr/adr-0006-cd-rsync-over-tailscale-ssh.md)). Open part → [OQ2](#oq2--ephemeral-runner-tailnet-auth). |
| 5 | No backup / disaster recovery | 🟡 | **Settled** (CT path) — inherit restic + hourly dumps ([ADR 0003](adr/adr-0003-deploy-as-lxc-container.md)). Open parts → [OQ3](#oq3--db-rpo-acceptance--timescaledb-dump-handling), [OQ4](#oq4--db-placement-own-ct-vs-shared-datastores-ct). |
| 6 | No application self-observability | 🟡 | **Settled** (CT path) — infra health auto-covers the CT; in-app `scraper_runs`/dead-man's-switch. Open part → [OQ5](#oq5--off-box-heartbeat). |
| 7 | UI/UX specified as one line | 🟡 | **Settled** — Django + HTMX rendering + post-alert state machine. Open part → [OQ6](#oq6--final-ui-page-inventory--dismisssuppress-feedback--purchase-tracking). |
| 8 | No v1 scope / phasing / acceptance criteria | 🟡 | **Settled** — six-milestone MVP plan (M0–M5) accepted; authoritative phasing to be authored via `spec-pipeline`. |
| 9 | No scraper testing strategy | 🟡 | **Settled** — vcrpy + syrupy + contract canary + Pydantic v2 (+5 amendments). Open part → [OQ8](#oq8--scraper-testing-finalization). |
| 10 | No running-cost / budget model | 🟢 | **Settled** (approach) — free-feed-first, config-driven per-source poll budget. Open part → [OQ7](#oq7--running-cost-budget-model-build-time-pricing-pass). |
| 11 | Shipping/tax not in the `$/TB` score | 🟢 | **Settled** — score on price + shipping (+ tax where known); missing-shipping = penalty/flag. |
| 12 | Cold-start: no history for relative scoring | 🟢 | **Settled** — continuous-shrinkage warm-up (`λ = min(1, n_eff/50)`); graded seed sources. |

### Resolved gaps & decisions

Full write-ups of the twelve gaps. For split gaps, only the **settled** part is here; the open part is the linked OQ.

#### Gap 1 — Web-app authentication (settled, ADR 0005)

**Was:** the spec asserted "user authentication for secure access" and anticipated future multi-user, but defined no auth model, mechanism, or user schema. Evidence: [`disk-search.md:7`](specs/disk-search.md), [`:79`](specs/disk-search.md).

**Decision → [ADR 0005](adr/adr-0005-single-account-session-auth.md):** a single strong-password account with **Argon2id** session login (Django `contrib.auth`), internet-facing; the load-bearing constraint is that the app holds **no in-app secrets**. Stub a `users` table now; **Authelia forward-auth** reserved for the multi-user end state. Full context and the forward-auth security rules (localhost bind, header overwrite, CVE-pinned gateway) live in the ADR. Research: [`auth-for-self-hosted-single-maintainer-python-app.md`](research/2026-07-03-auth-for-self-hosted-single-maintainer-python-app.md).

#### Gap 2 — `.env` secrets model → OpenBao (settled except `secret_id` delivery)

**Was:** the spec repeatedly said secrets live in a committed-excluded `.env`, but the org standard is **OpenBao as the credential store**, and it never answered **how the deployed app obtains secrets at runtime** — a real contradiction, sharpened by the repo being public. Evidence: [`disk-search.md:62`](specs/disk-search.md), [`:82`](specs/disk-search.md), [`:95`](specs/disk-search.md), [`:107`](specs/disk-search.md), [`:111`](specs/disk-search.md).

**Decision:**

- **Runtime injection via OpenBao Agent** (`bao agent`, its own hardened systemd unit) using **AppRole auto-auth**. The agent templates secrets to a root-owned, `0640`, app-group-readable file on **tmpfs** (`/run/disk-search/secrets.env`, gone on reboot); app services depend on it via `After=`. No plaintext `.env` at rest, no secrets baked into unit files.
- **The Agent runs locally on the CT, fully decoupled from CI.** Because CD is `rsync` over Tailscale SSH from a **GitHub-hosted** runner (gap #4), the public-repo CI job holds **no OpenBao credential at all** — it only rsyncs code and triggers `systemctl restart`; the running services pick up secrets the Agent has already templated. The `role_id` lives in the CT image/config-management.
- **Reconcile the spec's language:** `.env` is acceptable **for local development only**; production resolves secrets from OpenBao at runtime.
- **Still open:** the `secret_id` out-of-band delivery/renewal path → **[OQ1](#oq1--secret_id-out-of-band-delivery-to-the-ct)**. (The earlier "CD job fetches a response-wrapped `secret_id`" mechanism is withdrawn — CI is no longer on the box and, being public, must hold no OpenBao credential.)

Research: [`github-actions-cd-private-debian-vm.md`](research/2026-07-03-github-actions-cd-private-debian-vm.md) §3.

#### Gap 3 — Currency / landed-cost normalization (settled)

**Was:** the score is `USD` per `TB`, but several ranked merchants (ETB Technologies, Bargain Hardware) are UK/EU resellers pricing in GBP/EUR, and the buyer is US-based — cross-border listings scored on a false basis. Evidence: [`disk-search.md:13`](specs/disk-search.md), merchants at [`:40`–`:41`](specs/disk-search.md).

**Decision (owner, 2026-07-03 — accepted with changes):**

- **FX:** use **Frankfurter** (ECB-anchored, free, no API key, MIT, self-hostable), refreshed once/day. Store `fx_rate`, `fx_pair`, `fx_rate_date`, `fx_source` **on each observation** so historical scores are auditable and reproducible.
- **Normalize all prices to USD, but do NOT apply a fixed "international overhead" haircut.** Instead **flag** international listings (e.g. `"international — extra shipping/duty likely; verify before buying"`) and let the owner decide. Rationale: a cross-border purchase is unlikely to be worthwhile (shipping + potential customs), and a hardcoded percentage would be false precision — surface the risk rather than bake in a number. HDDs classify under **HTS 8471.70 at a 0% base (MFN) rate**, so the volatile cost is the surcharge the flag defers to the user.
- **Do NOT compute exact duty.** As of 2026-07-03 the US **de-minimis exemption is suspended indefinitely** and the add-on tariff rate for UK/EU goods is in active legal flux — a precise duty figure would be false precision that goes stale.
- **VAT footgun:** UK/EU VAT should be **zero-rated on export**, but many storefronts display VAT-inclusive prices pre-checkout — the scraper must not treat a VAT-inclusive shelf price as the export price.

Research: [`currency-conversion-and-landed-cost-estimation…md`](research/2026-07-03-currency-conversion-and-landed-cost-estimation-for-cross-border-drive-price-scoring.md).

#### Gap 4 — Deployment & service topology (settled, ADR 0006)

**Was:** "GitHub Actions → automatic deployment to Hetzner on merge to main" stated the _what_, never the _how_: transport, how the app runs as a service, how CI reaches a non-public target. Evidence: [`disk-search.md:72`–`:75`](specs/disk-search.md).

**Decision → [ADR 0006](adr/adr-0006-cd-rsync-over-tailscale-ssh.md):** a **GitHub-hosted `ubuntu-latest`** runner builds/tests, joins the tailnet **ephemerally**, then `rsync`s to the CT and restarts over `tailscale ssh` (self-hosted runner rejected on a public repo). Systemd web + worker units under a dedicated non-root user; **timers** for scrapes; venv built on the CT (`uv sync --frozen`); expand/contract migrations before restart. Full trigger/secret discipline lives in the ADR. **Still open:** the ephemeral-runner tailnet auth mechanism → **[OQ2](#oq2--ephemeral-runner-tailnet-auth)**. Research: [`github-actions-cd-private-debian-vm.md`](research/2026-07-03-github-actions-cd-private-debian-vm.md); per-source scheduling refined in [`orchestration-choice…md`](research/orchestration-choice-for-a-single-vm-price-polling-service.md).

#### Gap 5 — Backup / disaster recovery (settled CT path, ADR 0003)

**Was:** the accumulated historical price data _is_ the tool's compounding value; a single box with no backup means one disk failure erases the moat. Evidence: [`disk-search.md:19`](specs/disk-search.md), [`:22`](specs/disk-search.md); DB co-located per [`:69`](specs/disk-search.md).

**Decision (CT path) — [ADR 0003](adr/adr-0003-deploy-as-lxc-container.md):** add the disk-search **CT** to the existing Hetzner restic + hourly-dump pipeline; keep the monthly restore-test discipline. **Still open:** DB-RPO acceptance → **[OQ3](#oq3--db-rpo-acceptance--timescaledb-dump-handling)**; DB placement → **[OQ4](#oq4--db-placement-own-ct-vs-shared-datastores-ct)**.

**Live-state findings (2026-07-03 — verified on the server; specifics in the private `homelab` repo):**

- **The existing backup is file-level restic + logical DB dumps — there is _no_ VM-image backup.** No scheduled `vzdump`/PBS runs. restic backs up the host + each **LXC container's** app data via ZFS-subvolume paths → local ZFS repo, an **hourly offsite copy** (Hetzner Storage Box), and a **weekly offsite copy of a tier-1 subset** (Backblaze B2). Retention: 48 hourly / 14 daily / 8 weekly / 6 monthly.
- **Databases are dumped _logically, hourly_.** `pg_dump --format=custom` per DB + `pg_dumpall --globals-only`, captured by restic. **No WAL archiving, no PITR** → **RPO up to ~1 hour**.
- **Coverage is a hardcoded allowlist, _not_ auto-discovery.** `backup-restic.sh` and `backup-dumps.sh` name each path/DB by hand; a fail-loud guard aborts on a vanished path, but a **new service is never picked up automatically.**

**Implications:** had it stayed a standalone VM with an in-VM DB, it would have fallen **entirely outside** existing backup coverage — a primary reason the deployment model was decided as a CT (RQ5). **Decided path (CT):** deploy as a dedicated LXC container with its DB on a container Postgres, **and at provisioning add its data paths to `backup-restic.sh` + its DB to `backup-dumps.sh`** — this wiring is mandatory, not automatic. **Caveat (TimescaleDB, ADR 0007):** the inherited logical `pg_dump` needs TimescaleDB-aware dump/restore — a plain allowlist entry is insufficient; otherwise add in-CT physical backup (see OQ3).

**Fallback design if tighter RPO/PITR is wanted:** **pgBackRest** physical backup + continuous **WAL archiving** on the box (`repo1`) with a **second repo (`repo2`) on S3-compatible storage** (Backblaze B2 or Hetzner Storage Box) using pgBackRest **AES-256** — PITR + 3-2-1 offsite. Supplement with a weekly `pg_dumpall`. **TimescaleDB:** physical backups need no special handling; prefer them over logical. **Patch PostgreSQL/tooling** (recent `pg_dump`/`pg_basebackup`/`pg_rewind` CVEs). Research: [`postgresql-backup-disaster-recovery-single-vm.md`](research/2026-07-03-postgresql-backup-disaster-recovery-single-vm.md).

#### Gap 6 — Application self-observability (settled CT path except off-box heartbeat)

**Was:** deal alerts tell the _user_ about drives; nothing tells the _operator_ that the app is down, out of disk, a scrape stopped, or alert emails aren't delivered. Evidence: [`disk-search.md:11`](specs/disk-search.md).

**Decision (CT path):** split the concern — **infrastructure health** (up/disk/CPU/RAM) rides the existing Hetzner monitoring, which **auto-discovers the CT**; **application-level health** stays in-app via the **`scraper_runs` table** (shared with gap #9 / OQ8), a **dead-man's-switch heartbeat**, and **email-delivery confirmation**. **Still open:** the off-box heartbeat → **[OQ5](#oq5--off-box-heartbeat)**.

**Live-state findings (2026-07-03 — verified on the server):**

- **Monitoring is rich but _on-box_.** A twice-daily "fleet-digest" runs a ~57-probe health check across every container + the host, an on-box Uptime Kuma, plus CVE scans, AIDE, Lynis. The health check **auto-discovers containers from `pct list`** — so a new **CT** _is_ monitored automatically (a VM would only get a coarse up/down probe).
- **Alert _delivery_ is off-box** (email via MS Graph → M365), so a degraded-but-reachable box can still page out.
- **But there is no off-box _watchdog_.** Every heartbeat is a push monitor to the **on-box** Uptime Kuma; the off-site GMK Uptime Kuma does not monitor Hetzner. **A total-box outage would be caught by no automated off-box observer** — exactly the failure mode the research flagged.

**Implications:** the fleet-digest health check auto-covers a new container; confirm a **disk-space threshold** alert applies (raw payloads grow). **The one real gap is an off-box heartbeat** (OQ5). Keep the in-app pieces regardless; error tracking (GlitchTip/Sentry) is not in the existing stack — add if wanted. Research: [`lightweight-observability-and-scraper-health-monitoring.md`](research/2026-07-03-lightweight-observability-and-scraper-health-monitoring.md).

#### Gap 7 — UI/UX (settled: Django + HTMX + post-alert model; inventory open)

**Was:** "Provides a user-friendly web-based interface" with no page inventory, flows, or post-alert action model. Evidence: [`disk-search.md:20`](specs/disk-search.md).

**Decision (settled parts):** **rendering — [ADR 0004](adr/adr-0004-web-framework-django-htmx.md):** Django + server-rendered templates + HTMX, matching a single-maintainer, data-heavy CRUD+dashboard app without an SPA build chain; use the **Django admin as internal back-office**. **Post-alert model:** a per-watch, per-listing **state machine** (`none / pending / firing / cooling / digested`), first-class snooze at two granularities, one-click HMAC-signed action links, watch-as-unit-of-opt-out; dedup on listing + alert fingerprints. **Watch-rule UI:** hard filters separate from thresholds, no free-text title matching. **Still open:** the final page inventory, the dismiss→suppress feedback path, and purchase-tracking scope → **[OQ6](#oq6--final-ui-page-inventory--dismisssuppress-feedback--purchase-tracking)**. Research: [`opinionated-core-stack-recommendations…md`](research/opinionated-core-stack-recommendations-for-a-python-drive-price-monitor.md), [`designing-a-low-noise-alerting-layer…md`](research/designing-a-low-noise-alerting-layer-for-a-hard-drive-deal-monitor.md).

#### Gap 8 — v1 scope / phasing / acceptance criteria (settled)

**Was:** the spec said v1 "will not" optimize for other users, but never stated what v1 **does** include vs defers across 20 marketplaces + scoring + entity resolution + a web UI. Evidence: [`disk-search.md:7`](specs/disk-search.md).

**Decision — phased milestones accepted as planning input;** the authoritative phased spec will be authored with the **`spec-pipeline`** plugin (these milestones map onto its phases, and the acceptance criteria are the raw material for each phase's exit gate).

| Milestone | Deliverable | Done when… |
| --- | --- | --- |
| **M0 Foundation** | Django stack, DB schema, single-account auth (gap #1), CD via rsync/Tailscale (gap #4) + systemd + OpenBao Agent (gap #2) | A trivial page deploys on merge and the service reads a secret from OpenBao at runtime |
| **M1 Ingestion (top 5)** | Acquisition for the 5 primary recert sources → normalized `listing` rows, USD-normalized | Listings from all 5 land in Postgres with FX-normalized (USD) price and an international flag where applicable |
| **M2 Scoring** | Scoring engine + `$/TB` baseline w/ warm-up (gap #12) + explainable sub-scores | Every listing has a reproducible 0–100 score with a visible breakdown |
| **M3 Web UI** | Dashboard, listing detail, watches manager (gap #7) | Owner can filter deals and create/edit a watch |
| **M4 Alerts** | Email alerts via AgentMail with dedup/debounce | A matching drop fires exactly one actionable email |
| **M5 Hardening & breadth** | Remaining marketplaces, entity resolution, backups (#5), observability (#6), scraper tests (#9) | Backups restore-tested; scraper-rot alerts fire; ≥15 sources live |

**Detailed per-milestone tasks + measurable acceptance criteria:**

- **M0 — Foundation.**
  - _Tasks:_ scaffold the Django project (uv-managed, BasedPyright-strict); define the canonical `drive_model` / `listing` / `observation` schema (from [`database-architecture.md`](research/database-architecture.md)) as initial migrations; stub the `users` table + single-account session login (Argon2id); stand up the CD workflow (GitHub-hosted `ubuntu-latest` → `rsync` over Tailscale SSH); install systemd web + worker units and the local OpenBao Agent unit.
  - _Acceptance:_ merge to `main` deploys automatically with **zero manual steps**; the running web service serves an authenticated "hello" page and **reads at least one secret sourced from OpenBao** (no plaintext `.env` on the CT); `uv sync --frozen` reproduces the locked env; migrations apply cleanly from empty; a **rollback to the previous SHA** is demonstrated.
- **M1 — Ingestion (top 5).**
  - _Tasks:_ implement acquisition for the 5 primary recert sources (WD Recertified, Seagate Recertified, ServerPartDeals, goHardDrive, eBay Browse/Feed) using the structured-data-first tier ladder; normalize into `listing` rows; wire **Frankfurter FX → USD** with `fx_rate`/`fx_pair`/`fx_rate_date`/`fx_source` stamped **on each observation** (gap #3); set the international flag.
  - _Acceptance:_ all **5/5 sources** yield ≥1 normalized `listing` on a scheduled run; **100%** of non-USD listings carry a stored FX rate + date and a normalized USD price; international listings are flagged; a re-run produces new `observation` rows, not duplicate `listing`s.
- **M2 — Scoring.**
  - _Tasks:_ implement the scoring engine — log(`$/TB`) cohort percentile with 90-day window + 30-day half-life decay, cohort key = capacity · tier · interface · condition, and the **continuous warm-up** `λ = min(1, n_eff/50)` shrinkage toward 0.5 (gap #12); persist per-sub-score explanation payloads.
  - _Acceptance:_ **every** listing has a 0–100 score that is **reproducible** from stored inputs; the score exposes a **per-factor breakdown**; thin-cohort listings (n_eff < 50) visibly shrink toward neutral and are marked **provisional**; a documented cohort-relaxation fallback fires when a cohort is too small.
- **M3 — Web UI.**
  - _Tasks:_ build Dashboard, Listing detail (score breakdown + "why it matched"), Watches manager (hard filters vs thresholds, no free-text), Price-history view, listing-state controls (gap #7); expose the Django admin as back-office.
  - _Acceptance:_ owner can filter the dashboard by brand/capacity/tier/interface/condition and **create, edit, and delete a watch**; a listing detail renders the **pass-margin** explanation for each crossed threshold; state changes persist and re-render.
- **M4 — Alerts.**
  - _Tasks:_ email alerts via AgentMail with the dedup/debounce design — listing + alert fingerprints, cooldown/hysteresis, signed one-click action links, **email-delivery confirmation**.
  - _Acceptance:_ a single qualifying price drop fires **exactly one** email (verified against the alert-fingerprint ledger); one-click snooze/stop links work and are HMAC-verified; a simulated repost under a new URL is **de-duplicated**; a delivery failure is **detectably surfaced**.
- **M5 — Hardening & breadth.**
  - _Tasks:_ add the remaining marketplaces, entity resolution, backups (#5), application self-observability (#6), and the scraper test suite (#9 — vcrpy + syrupy + per-tier contract canary).
  - _Acceptance:_ **≥15 sources** live; a backup is **restore-tested into a scratch instance** at least once; a deliberately broken parser trips a **scraper-rot alert within one scheduled cycle**; CI runs the cassette/snapshot suite green.

#### Gap 9 — Scraper testing strategy (settled stack + amendments; build-time params open)

**Was:** CI names "testing workflows" but the spec never said **how** to test scrapers against sites that change and fight bots. Evidence: [`disk-search.md:73`](specs/disk-search.md).

**Decision (settled):**

- **Recorded fixtures:** **vcrpy cassettes** per source (record once, replay in CI) — deterministic, offline parse tests.
- **Snapshot tests:** **syrupy** golden-file assertions on parsed output.
- **Production canary:** a **scheduled** live **structured-data contract check** per source + a **known-value canary page**.
- **Runtime validation:** **Pydantic v2** per-record validation + `last_success_at` / consecutive-failure counters + a count-vs-rolling-average assertion; alert when a source returns 0/malformed N runs in a row. Shares the `scraper_runs` table from gap #6.

**Five research-confirmed amendments (2026-07-03):** (1) canary must be **per-extraction-tier**, not JSON-LD-only — tiers break independently; (2) **risk-weight canary frequency by tier** — fragility increases down the ladder; (3) **scrub cassettes of PII before commit** (compliance, not hygiene); (4) **do not commit real cassettes for retention-restricted sources** — use synthetic fixtures; real cassettes fine for recert specialists; (5) **classify failure type** — parser rot vs now-anti-bot-protected (a soft-block often returns HTTP 200 + empty body). **Still open:** the concrete build-time parameters (per-tier frequencies; synthetic-vs-real cassette assignment) → **[OQ8](#oq8--scraper-testing-finalization)**. Research: [`lightweight-observability…md`](research/2026-07-03-lightweight-observability-and-scraper-health-monitoring.md), [`pragmatic-architecture…md`](research/pragmatic-architecture-for-low-volume-python-e-commerce-scraping.md), [`us-scraping-and-data-retention-landscape…md`](research/us-scraping-and-data-retention-landscape-for-a-retail-hdd-price-monitor.md).

#### Gap 10 — Running-cost / budget model (settled approach; pricing pass open)

**Was:** paid search APIs, AgentMail, object storage, and possible managed-scraping APIs had no aggregate budget or ceiling to design polling frequency against. Evidence: [`disk-search.md:55`](specs/disk-search.md), [`:109`–`:111`](specs/disk-search.md).

**Decision (approach):** **prefer free official feeds** (eBay Browse/Feed, structured-data parsing) over paid search calls — search APIs are for _discovery_, not per-poll refresh. **Config-driven per-source poll budget** held under a stated **monthly ceiling**, reusing the orchestration research's **two-level token buckets** (per-source + per-domain). Track actuals via the `scraper_runs` table. Managed-scraping APIs avoided for this merchant set (free structured data covers it; reserve them for a hostile tail — or skip the source). **Still open:** the build-time pricing pass (current Serper/Brave/Tavily per-call pricing, AgentMail, backup object-storage costs; Brave storage-rights plan) → **[OQ7](#oq7--running-cost-budget-model-build-time-pricing-pass)**. Research: [`programmatic-acquisition…md`](research/programmatic-acquisition-research-for-enterprise-and-nas-drive-merchants.md), [`tavily-brave-serper.md`](research/tavily-brave-serper.md), [`pragmatic-architecture…md`](research/pragmatic-architecture-for-low-volume-python-e-commerce-scraping.md), [`orchestration-choice…md`](research/orchestration-choice-for-a-single-vm-price-polling-service.md).

#### Gap 11 — Shipping (and tax) in the `$/TB` score (settled)

**Was:** `$/TB` on item price alone misranks a cheap drive with high shipping — even domestically. Evidence: [`disk-search.md:13`](specs/disk-search.md).

**Decision (accepted):**

- Score on **price + shipping (+ tax where known)**, not item price alone. Marketplace shipping fields (eBay Browse `shippingOptions`, Serper `delivery`) are reliable **only when the request supplies correct buyer-location context** — pin the buyer location on every query.
- When shipping is unknown, **apply a penalty or flag** rather than silently scoring as if free.
- Composes with the **international flag** from gap #3 (which dropped the fixed overhead haircut): domestic known shipping is folded into `$/TB`; cross-border extra cost stays a flag, not a number.

Research: [`currency-conversion-and-landed-cost-estimation…md`](research/2026-07-03-currency-conversion-and-landed-cost-estimation-for-cross-border-drive-price-scoring.md).

#### Gap 12 — Cold-start scoring (settled)

**Was:** the moving-baseline / percentile scoring needs accumulated history that doesn't exist at launch. Evidence: [`disk-search.md:19`](specs/disk-search.md), [`:22`](specs/disk-search.md).

**Decision (resolved via research):**

1. **Replace the hard "switch at N observations" with continuous shrinkage:** `s_price = λ·(1 − q) + (1 − λ)·0.5` with **`λ = min(1, n_eff/50)`**, so a thin cohort is pulled toward neutral **0.5** and reaches full confidence at **≈50 effective observations**. This _is_ the built-in provisional-confidence mechanism (surface `n_eff`/`λ` as the "provisional" indicator).
2. **Threshold on _effective_ sample size:** `n_eff = (Σw)²/Σ(w²)` under a 90-day window with **30-day half-life** decay (`w = 2^(−age_days/30)`).
3. **Fallback shrinks toward 0.5, not toward an absolute `$/TB` verdict** — prefer documented **cohort-relaxation** (relax condition → adjacent capacity → parent tier) over an absolute table; keep dated `$/TB` bands only as a UI reference / sanity floor.
4. **Expand the cohort key** to **capacity · tier · interface/form-factor · condition bucket**; for SSDs add **endurance class (DWPD)** — SSDs must never be compared on capacity alone.

**Seed sources, graded:** **Keepa** is the only sanctioned machine-readable seed (paid API); **ServerPartDeals** is the key recert benchmark (no API — parse its catalog); **diskprices.com / CamelCamelCamel / PCPartPicker** are UI/sanity references only; **r/DataHoarder** is qualitative. Every seed is **market-dated** (the 2026 bands reflect an abnormal ~46% supply-constrained run-up) — timestamp and age out any seeded baseline as real observations accrue. Research: [`principled-deal-score…md`](research/principled-deal-score-for-hard-drive-listings.md), [`drive-deal-tracker…baselines…md`](research/drive-deal-tracker-research-baselines-tools-shucking-and-timing.md).

### Scope & research provenance

This document deliberately **excludes** anything already covered elsewhere:

- **Covered by research docs** — search APIs, official eBay/Amazon/Newegg APIs, storage/caching-compliance ([`research/tavily-brave-serper.md`](research/tavily-brave-serper.md)); DB engine, schema, entity resolution, price-history modelling ([`research/database-architecture.md`](research/database-architecture.md)).
- **Covered by domain research** — the 17 non-API merchants, drive-grading taxonomy, recert risk/warranty, scoring math, `$/TB` baselines, entity resolution, legal/ToS, anti-bot scraping, job scheduling, framework/DB/env `_TBD_`s, notification/dedup design, serial/warranty verification — queued in [`further-research-needed-prompts.md`](further-research-needed-prompts.md); **all landed** under [`research/`](research/) and folded into the gaps above.

Everything above is the **operational / product-engineering** layer a research-first spec tends to leave blank.

**How the solutions were researched:** five parallel sweeps (Tavily-first, Context7-gated, cross-corroborated) on 2026-07-03, each persisted under `docs/research/`:

| Report | Informs |
| --- | --- |
| [`2026-07-03-github-actions-cd-private-debian-vm.md`](research/2026-07-03-github-actions-cd-private-debian-vm.md) | gap #2, #4 · OQ1, OQ2 |
| [`2026-07-03-auth-for-self-hosted-single-maintainer-python-app.md`](research/2026-07-03-auth-for-self-hosted-single-maintainer-python-app.md) | gap #1 |
| [`2026-07-03-currency-conversion-and-landed-cost-estimation-…md`](research/2026-07-03-currency-conversion-and-landed-cost-estimation-for-cross-border-drive-price-scoring.md) | gap #3, #11 |
| [`2026-07-03-postgresql-backup-disaster-recovery-single-vm.md`](research/2026-07-03-postgresql-backup-disaster-recovery-single-vm.md) | gap #5 · OQ3 |
| [`2026-07-03-lightweight-observability-and-scraper-health-monitoring.md`](research/2026-07-03-lightweight-observability-and-scraper-health-monitoring.md) | gap #6, #9 · OQ5, OQ8 |
