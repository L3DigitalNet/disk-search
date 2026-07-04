# Open Questions — `hw-radar.md`

**Date:** 2026-07-03 **Subject:** The **unsettled** engineering/design decisions for [`hw-radar.md`](specs/hw-radar.md), front-loaded — plus the resolved decisions and gap analysis they came out of, kept below for provenance.

## How to maintain this document

- Read **[Open questions](#open-questions)** for anything that still needs a call. Everything under **[Resolved](#resolved)** is settled and kept only for provenance — you should not have to read it to know what's outstanding.
- Settled questions are moved to **[Resolved](#resolved)**. If a question is partially settled, move the decided half to Resolved and leave a focused open question covering _only_ the remaining fork.
- Once an ADR is written for a settled question, the resolved decision can be safely removed from this document to control its size. The ADR is the canonical record of the decision.

**Rules:**

1. **Open questions first, distilled.** Each open question states _only_ the unresolved decision — not the history behind it. The history lives in Resolved and in the research reports.
2. **When a question is settled, move it down.** Relocate its substance to Resolved (record the decision + any ADR) and remove it from Open questions. Never leave a settled item up top.
3. **Split partially-settled items.** If a gap is half-decided, move the decided half to Resolved and leave a focused open question covering _only_ the remaining fork. (This is how the eight OQs below were produced from the twelve gaps.)
4. **Two comment layers per open question, kept separate:**
   - `#### Agent notes` — research/reconciliation context, maintained by the assistant.
   - `#### My Comments` — the owner's notes and decisions; **the assistant does not edit this block.**
5. **Cross-reference by stable ID.** `OQ#` = open question, `RQ#` = resolved question, `gap #` = original gap. ADRs, the spec, and TODO link here by those IDs — keep them stable. If you must renumber, update the referencing ADRs/TODO/spec **in the same change**.

## Table of Contents

- [Open Questions — `hw-radar.md`](#open-questions--hw-radarmd)
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
    - [OQ11 — Composite scoring model (adopt research #4)](#oq11--composite-scoring-model-adopt-research-4)
      - [Agent notes](#agent-notes-10)
      - [My Comments](#my-comments-10)
    - [OQ12 — Orchestration engine (APScheduler vs systemd timers)](#oq12--orchestration-engine-apscheduler-vs-systemd-timers)
      - [Agent notes](#agent-notes-11)
      - [My Comments](#my-comments-11)
    - [OQ13 — Notification transport \& deliverability (AgentMail vs transactional provider)](#oq13--notification-transport--deliverability-agentmail-vs-transactional-provider)
      - [Agent notes](#agent-notes-12)
      - [My Comments](#my-comments-12)
    - [OQ14 — Scraping runtime escalation stack](#oq14--scraping-runtime-escalation-stack)
      - [Agent notes](#agent-notes-13)
      - [My Comments](#my-comments-13)
  - [Resolved](#resolved)
    - [Resolved questions](#resolved-questions)
    - [Gap summary (all 12, for reference)](#gap-summary-all-12-for-reference)
    - [Resolved gaps \& decisions](#resolved-gaps--decisions)
      - [Gap 1 — Web-app authentication (settled, ADR 0005)](#gap-1--web-app-authentication-settled-adr-0005)
      - [Gap 2 — `.env` secrets model → OpenBao (settled except `secret_id` delivery)](#gap-2--env-secrets-model--openbao-settled-except-secret_id-delivery)
      - [Gap 3 — Currency / landed-cost normalization (settled, ADR 0008)](#gap-3--currency--landed-cost-normalization-settled-adr-0008)
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

**Ten decisions remain open** — **OQ3** and **OQ6–OQ14** (OQ9–OQ10 surfaced from the spec's General Design Principles consistency audit; **OQ11–OQ14 surfaced from the 2026-07-04 gap analysis — research-complete, ADR-ready decisions carried by domain-research prompts #4/#9/#11/#8 that had a landed report but no prior OQ or ADR**; the rest are the still-open parts of the original gaps). **OQ1, OQ2, OQ4, and OQ5 are settled** (OQ1/OQ2 on 2026-07-04 by live verification against the Hetzner infra + tailnet during the owner-directed investigation; OQ4/OQ5 on 2026-07-03 by owner decision); they are marked ✅ below and kept in place — rather than physically relocated to Resolved — to preserve their `#oq1`/`#oq2`/`#oq4`/`#oq5` anchors (referenced by ADR 0003/0006, TODO, the research README, and OQ10). Their resolutions are also recorded in [Resolved](#resolved).

### At a glance

| # | Open question | From | The fork |
| --- | --- | :-: | --- |
| **OQ1** ✅ | `secret_id` delivery — **settled** | gap #2 | ✅ 2026-07-04 (verified live): onboard as the next **`bao-services` (CT 115)** consumer via a local **bao-agent**; SecretID via `bao-issue-secret-id.sh` (wrap + `pct push`) → `/etc/bao-agent/secret-id`, persistent + CIDR-bound. See [OQ1](#oq1--secret_id-out-of-band-delivery-to-the-ct). |
| **OQ2** ✅ | Ephemeral-runner tailnet auth — **settled** | gap #4 | ✅ 2026-07-04 (verified live): **Tailscale OAuth client** (`secret/infra/tailscale-oauth`, `tag:ci`) via `tailscale/github-action` v4. ⚠️ add a `tag:ci→CT` grant when the wildcard ACL is scoped. See [OQ2](#oq2--ephemeral-runner-tailnet-auth). |
| **OQ3** | DB RPO (+ TimescaleDB dumps) | gap #5 | accept ≤1 h / no-PITR vs layer pgBackRest + WAL inside the CT |
| **OQ4** ✅ | DB placement — **settled** | gap #5 | ✅ 2026-07-03: own Postgres **inside the hw-radar CT** (self-contained; shared-datastores-CT rejected). See [OQ4](#oq4--db-placement-own-ct-vs-shared-datastores-ct). |
| **OQ5** ✅ | Off-box heartbeat — **settled** | gap #6 | ✅ 2026-07-03: **off-site GMK Uptime Kuma** watches the CT (also swept by the Hetzner Fleet Digest; healthchecks.io rejected). See [OQ5](#oq5--off-box-heartbeat). |
| **OQ6** | Final UI inventory + dismiss→suppress | gap #7 | confirm pages; decide if a user _dismiss_ silences re-alerts; purchase-tracking scope |
| **OQ7** | Running-cost budget model | gap #10 | pricing pass ✅ (2026-07-03 → ~$8–15/mo search-API envelope; AgentMail free); residual = encode per-source poll budgets at build |
| **OQ8** | Scraper testing finalization | gap #9 | per-tier canary frequencies; synthetic vs real cassettes per source (Deep Research #13 ✅ landed — reconcile findings) |
| **OQ9** | Acquisition cadence, throttle & skip | principles §1+5 | per-source cadence numbers + adaptive back-off thresholds + tier-ladder skip cutoff (no spec reword — real-time-where-tolerated is in scope) |
| **OQ10** | Reliability / resilient acquisition | principle §4 | per-source isolation, retry/backoff, circuit-break, health alerts |
| **OQ11** | Composite scoring model | research #4 | ratify weighted-geometric-mean + 4 subscores + weights (0.50/0.25/0.15/0.10) + veto gates → fills empty spec §Scoring System · candidate ADR-0011 |
| **OQ12** | Orchestration engine | research #9 | APScheduler vs systemd timers — resolves the ADR-0006 "timers" contradiction; blocks OQ7/OQ9/OQ10 · candidate ADR-0012 |
| **OQ13** | Notification transport & deliverability | research #11, #14 | prompt #14 **landed** → research recommends **Postmark primary / SES fallback / AgentMail secondary**; now an owner call vs the AgentMail lean · candidate ADR-0013 |
| **OQ14** | Scraping runtime escalation stack | research #8 | ratify Scrapy + scrapy-playwright + curl_cffi tier stack · candidate ADR-0014 / spec fold |

---

### OQ1 — `secret_id` out-of-band delivery to the CT

> **✅ SETTLED (owner hunch confirmed + verified live on Hetzner, 2026-07-04):** hw-radar onboards as the **next `bao-services` consumer** — the exact pattern already live for **LiteLLM on CT 110**. A local **bao-agent** sidecar on the hw-radar CT AppRole-auto-auths against the Hetzner-local **`bao-services` store (CT 115)** and renders secrets to tmpfs. The `secret_id` is delivered **operator→CT** by `bao-issue-secret-id.sh` (300 s response-wrap token + `pct push`) and stored at `/etc/bao-agent/secret-id` (mode 0600, **persistent** — `remove_secret_id_file_after_reading=false`), re-read on every agent restart; the consumer AppRole is **long-lived** (`num_uses=0, ttl=0`) with **CIDR binding** as the active security control (not TTL). No renewal treadmill — re-run the issuer only to rotate. The owner's "bao-agent will resolve this" is confirmed. Kept in place to preserve the `#oq1` anchor; also recorded in [Resolved gap #2](#gap-2--env-secrets-model--openbao-settled-except-secret_id-delivery).

**From:** gap #2 (resolved). **Decided:** how the OpenBao AppRole `secret_id` reaches the hw-radar CT (public-repo CI holds **no** OpenBao credential) → **reuse the live `bao-services`/`bao-agent` consumer pattern** — the `secret_id` is delivered locally on the box, never through CI.

The secrets _path_ is settled (local bao-agent, AppRole auto-auth, renders to tmpfs). The `role_id` ships in the CT config-management. The `secret_id` delivery/renewal is now settled per the banner.

#### Agent notes

- **Verified live (2026-07-04):** CT 115 `bao-services` (OpenBao 2.5.3, auto-unsealed via GMK Transit, Tailscale-only) and CT 110 (the LiteLLM consumer) are both **running**. The consumer fleet is documented in `homelab/infrastructure/servers/hetzner-dedicated/bao-agent/` — `configs/hetzner-litellm/` is the reference (`agent.hcl` + `openbao-agent.service` + a `*-bao-gate.conf` systemd drop-in), onboarding via `bao-agent/runbooks/onboard-consumer.md`; SecretID issued by `bao-services/tools/bao-issue-secret-id.sh`.
- **SecretID model (pilot-amended — supersedes OQ1's original response-wrap-and-delete assumption):** the spec's `remove_secret_id_file_after_reading=true` **breaks restart safety** (wrap token is single-use → any restart fails), so the live pattern uses a **persistent, long-lived, CIDR-bound** SecretID at `/etc/bao-agent/secret-id` instead. Adopt the live pattern, not the withdrawn one.
- **Spec-reconciliation follow-ups (hw-radar side, for the next spec pass):** (1) secrets are consumed from the **Hetzner-local `bao-services` CT 115**, not GMK CT 111 directly; (2) the render-path convention is **`/run/bao-agent/hw-radar.env`**, not `/run/hw-radar/secrets.env`; (3) the consumer AppRole's **CIDR bind must include the hw-radar CT's private IP** (`10.0.100.x`).
- **Onboarding is wave-2** (LiteLLM was wave-1, manual): either follow the manual pattern or populate the intentionally-empty `robertdebock.openbao_agent` ansible scaffold. Implementation choice, not a design decision.
- The vTPM / `systemd-creds --with-key=tpm2` shortcut is **out** — a CT has no per-container TPM (it shares the host kernel), so that path would reduce to host-key-only encryption (see [RQ3](#resolved-questions), [RQ5](#resolved-questions)). The local OpenBao Agent is therefore the only secrets path.
- Research: [`github-actions-cd-private-debian-vm.md`](research/2026-07-03-github-actions-cd-private-debian-vm.md) §3.

#### My Comments

SSH into Hetzner and look at the existing infra automation, particularly the CT with OpenBao. I believe that bao-agent will be able to resolve this issue.

---

### OQ2 — Ephemeral-runner tailnet auth

> **✅ SETTLED (owner criterion met + verified against the live ACL, 2026-07-04): use the Tailscale OAuth client.** The owner's rule was "if the ACLs allow an OAuth client, use it." Verified: the tailnet's `tag:ci` is defined and admin-owned ("added 2026-03-24 for GitHub Actions CI/CD deploy"), and an OAuth client already exists at OpenBao **`secret/infra/tailscale-oauth`** with `purpose: "GitHub Actions CI/CD deploy via Tailscale"` — it completed the client-credentials flow and read the ACL (HTTP 200). So hw-radar's CD uses `tailscale/github-action` **v4** (built for ephemeral GitHub-hosted runners; its post-step auto-`tailscale logout` is a feature here) authenticating via that OAuth client, minting an ephemeral node tagged `tag:ci`. **No pre-generated ephemeral auth key needed.** Kept in place to preserve the `#oq2` anchor; also recorded in [Resolved gap #4](#gap-4--deployment--service-topology-settled-adr-0006).

**From:** gap #4 (resolved, [ADR 0006](adr/adr-0006-cd-rsync-over-tailscale-ssh.md)). **Decided:** which mechanism authenticates the ephemeral GitHub-hosted runner onto the tailnet → the **Tailscale OAuth client** (already provisioned for exactly this purpose), not a pre-generated ephemeral auth key. ADR 0006's CD decision holds.

#### Agent notes

- **Verified live (2026-07-04):** the OAuth client at `secret/infra/tailscale-oauth` (`client_id`/`client_secret`, purpose "GitHub Actions CI/CD deploy via Tailscale") authenticated and GET-ed the tailnet ACL; `tag:ci` is present in `tagOwners` (`["autogroup:admin"]`). `tailscale/github-action` v4 is the correct action for an **ephemeral** GitHub-hosted runner — the opposite of the persistent VM 200 runner, which rejected it (auto-logout would sever a persistent `tag:ci`) per the Tailscale-ACL research.
- **⚠️ Latent dependency — the tailnet ACL grants are still wildcard** (`src:* dst:* ip:*`). Today a `tag:ci` node reaches the hw-radar CT with **no extra grant**; but the pending **wildcard→scoped migration** (`homelab/docs/superpowers/plans/2026-05-14-homelab-tailnet-wildcard-removal.md`) will remove that blanket access — when it lands, add an explicit grant `{src:["tag:ci"], dst:["<hw-radar CT>"], ip:["22"]}` or the deploy silently breaks.
- **Transport nuance:** the live `ssh` block is `action:check` for `autogroup:member → autogroup:self` **only** — it does not cover `tag:ci → CT` for _Tailscale SSH_. Prefer **bare OpenSSH + a deploy key** over the tailnet (the wildcard grant opens port 22; matches the VM 200 precedent), or add a `tag:ci → CT` ssh rule if Tailscale SSH is wanted. ADR 0006 says "restarts over `tailscale ssh`" → reconcile to bare-ssh or add the ssh rule.
- **Operational finding (resolved 2026-07-04):** the stored `secret/infra/tailscale-api` token had **expired 2026-06-22**; owner minted a new one (now valid to 2026-10-01, verified HTTP 200). Independent of CD — the OAuth client is what CD uses.
- Research: [`github-actions-cd-private-debian-vm.md`](research/2026-07-03-github-actions-cd-private-debian-vm.md); tailnet ACL scoping in `homelab/docs/research/2026-05-14-tailscale-acl-wildcard-to-scoped-ci-runner.md`.

#### My Comments

Use the Tailscale API key from OpenBao to access the tailnet and check the ACLs. If the ACLs allow for OAuth client auth, then use that. Otherwise, provide additional options/alternatives.

---

### OQ3 — DB RPO acceptance (+ TimescaleDB dump handling)

**From:** gap #5 (resolved CT path, [ADR 0003](adr/adr-0003-deploy-as-lxc-container.md)). **Decision needed:** is the inherited **≤1 h RPO / no PITR** (hourly logical dumps) acceptable for the accumulating price-history moat, or must **pgBackRest + WAL archiving** be layered **inside the CT**?

A second driver is coupled to this: TimescaleDB ([ADR 0007](adr/adr-0007-datastore-postgresql-timescaledb.md)) means the inherited logical `pg_dump` needs **TimescaleDB-aware** dump/restore (`timescaledb_pre_restore()` / `post_restore()`, compression state not preserved), so **physical** backup may be preferable for _correctness_, not only for RPO. Decide both together.

#### Agent notes

- **Owner direction (2026-07-03):** don't pick an RPO in the abstract — **first author a backup-requirements doc** (RPO, PITR, and the TimescaleDB dump/restore constraints) for hw-radar in the private **`homelab` repo**, coordinated with the existing Hetzner backup strategy; then evaluate the inherited **≤1 h RPO / no-PITR** against those documented requirements and expand only if they demand it. **Non-blocking** — can land in parallel with or after deploy, **but must precede the first backup being taken.**
- **Requirements doc written (2026-07-04):** `homelab/docs/plans/2026-07-04-hw-radar-backup-requirements.md` (verified live against `backup-dumps.sh`/`backup-restic.sh`). **Headline finding:** hw-radar is the fleet's **first TimescaleDB consumer**, but every existing dump is plain `pg_dump --format=custom` with no hypertable awareness → a naïve allowlist entry **restores incorrectly**. So the real work is **TimescaleDB-correct dumps + wiring coverage, not tighter RPO** — the inherited **≤1 h RPO / no-PITR is accepted for v1** (revisit if OQ9 sets sub-hourly polling). Own-CT Postgres (OQ4) matches the CT 109/112/114 pattern. _(OQ3 stays open pending the owner's confirmation of the doc's §7 decisions — RPO, join-B2-tier-1, logical-vs-physical — and the provisioning-time wiring.)_
- **Fallback design if tighter RPO/PITR is wanted:** pgBackRest physical backup + continuous WAL archiving on-CT (`repo1`) with a second repo (`repo2`) on S3-compatible storage (Backblaze B2 or Hetzner Storage Box), pgBackRest AES-256 encryption → PITR + offsite 3-2-1. Supplement with a weekly `pg_dumpall`.
- TimescaleDB: **physical** backups (pgBackRest / `pg_basebackup`) need no special handling; only logical (`pg_dump`) backups carry hypertable caveats — prefer physical.
- Keep the **monthly restore-test** discipline regardless — an untested backup is a hope. **Patch PostgreSQL/tooling** (recent `pg_dump`/`pg_basebackup`/`pg_rewind` CVEs live in the tools).
- Independent of the CT decision. Research: [`postgresql-backup-disaster-recovery-single-vm.md`](research/2026-07-03-postgresql-backup-disaster-recovery-single-vm.md).

#### My Comments

Create a document of all backup requirements and constraints, including RPO, PITR, and TimescaleDB considerations. Evaluate the current backup strategy against these requirements and determine if the current ≤1 h RPO is acceptable or if a more robust solution is needed. Go into the `homelab` repo and create appropriate documentation for hw-radar and document it's backup needs there. The backup strategy will have to be coordinated with the existing Hetzner backup strategy and any other relevant infrastructure. We can expand/improve as necessary, but the first step is to document the requirements and constraints. This is not a blocker, it can be completed in parallel or after the project is deployed, but it should be done before the first backup is taken.

---

### OQ4 — DB placement: own CT vs shared datastores CT

> **✅ SETTLED (owner, 2026-07-03):** own Postgres **inside the hw-radar CT** — the app and its database are **self-contained in one CT** (consistent with the spec's "same container" intent; simpler to deploy and manage). The shared-datastores-CT option is **rejected**. Kept here rather than physically moved to Resolved, to preserve the `#oq4` anchor (ADR 0003, TODO); the resolution is also recorded in [Resolved gap #5](#gap-5--backup--disaster-recovery-settled-ct-path-adr-0003).

**From:** gap #5 (resolved CT path, [ADR 0003](adr/adr-0003-deploy-as-lxc-container.md)). **Decided:** ~~own Postgres inside the hw-radar CT vs the shared datastores CT~~ → **own Postgres inside the hw-radar CT**.

**Residual (implementation, not a decision):** at provisioning, add the CT's DB to `backup-dumps.sh` — with the **TimescaleDB-aware** dump caveat from [OQ3](#oq3--db-rpo-acceptance--timescaledb-dump-handling). Compatible with ADR 0003.

#### Agent notes

- **Resolved** in favor of self-containment. The backup-wiring obligation (coverage is a hardcoded allowlist, not auto-discovery) is now an M0/M5 implementation task, tracked via gap #5.

#### My Comments

The app/project and its associated database should be self-contained in the hw-radar CT. This is consistent with the spec's intent and simplifies deployment and management.

---

### OQ5 — Off-box heartbeat

> **✅ SETTLED (owner, 2026-07-03):** use the **off-site GMK Uptime Kuma** to watch the hw-radar CT (reuses existing infra; already alerts by email), additionally swept periodically by the **Hetzner EX130-R · Fleet Digest** (see the `homelab` repo). The **healthchecks.io** option is **rejected**. **Non-blocking** — land before entering production. Kept in place to preserve the `#oq5` anchor (OQ10, gap #6, the research README, TODO); resolution also recorded in [Resolved gap #6](#gap-6--application-self-observability-settled-ct-path-except-off-box-heartbeat).

**From:** gap #6 (resolved CT path). **Decided:** the one real observability gap after the CT decision was the missing **off-box watchdog** (a total-box outage caught by no external observer) → **off-site GMK Uptime Kuma** (not healthchecks.io).

#### Agent notes

- **Chosen:** the **off-site GMK Uptime Kuma** — reuses existing infra and satisfies the "one heartbeat must live off-box" requirement the research insists on. (The healthchecks.io alternative — zero-infra external — was the runner-up.)
- **Settled and kept regardless** (generic infra monitoring can't see these): the in-app **`scraper_runs` table** (shared with [OQ8](#oq8--scraper-testing-finalization) / gap #9), a **dead-man's-switch heartbeat**, and **email-delivery confirmation**. Infra health (up/disk/CPU/RAM) is auto-covered — the fleet-digest health check auto-discovers the CT from `pct list`; confirm a **disk-space threshold** alert applies since raw scrape payloads grow. Error tracking (GlitchTip/Sentry) is **not** in the existing stack — add it only if wanted.
- Research: [`lightweight-observability-and-scraper-health-monitoring.md`](research/2026-07-03-lightweight-observability-and-scraper-health-monitoring.md).

#### My Comments

We will use the existing GMK Uptime Kuma instance to monitor the hw-radar CT. This is consistent with the existing infrastructure and will provide the necessary off-box heartbeat monitoring. This will also be monitored periodically by the `Hetzner EX130-R · Fleet Digest` (see the `homelab` repo) for details. This is not a blocker, it can be completed in parallel or after the project is deployed, but should be done before entering production.

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

This question has been open for a while. We need to confirm the final MVP page inventory and flows in case new information changes your recommendation. If necessary, conduct research using /qdev:research and update the open question and existing research doc(s) with the findings.

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

**Search:**

_New Comments:_ I am not sure what search rates were assumed for the estimates from agent comments above. Further research should include:

- Should we rate limit our own search calls on a per-source basis to a reasonable time interval (e.g., 1 call per 1 minute per source) to avoid unreasonable usage and to prevent any unexpected costs (i.e. software bug results in excessive calls) or hitting any rate limits?
- Should we implement a circuit breaker for chronically failing sources to prevent unnecessary costs and API abuse?
- User settings in the app to adjust limits, timing, aggressiveness, etc. (e.g., user can set a maximum number of searches per day/week/month, or adjust the aggressiveness of the search frequency)?

Past/resolved comments:

```markdown
I have active accounts for each search service and I keep them topped up with funds. This question will require additional research to find the current per-call pricing for each service and to verify Brave's storage-rights plan requirement. Since I use these services elsewhere we will assume that any monthly free tier limits have already been exceeded and that we will be paying for any calls made. I feel that I will be comfortable with $10 to $20 per month total for all three services combined, but will reconsider after additional research (to be performed by Claude).
```

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
- **Deep Research prompt #13 — report LANDED** (2026-07-03, indexed 2026-07-04): [`automated-test-policy-for-a-low-volume-scrapy-price-monitor.md`](research/automated-test-policy-for-a-low-volume-scrapy-price-monitor.md) answers exactly this build-time finalization (risk-weighted per-tier canary cadence + degradation alerts; per-source real-vs-synthetic cassette commit policy; vcrpy PII-scrubbing; a parser-rot-vs-anti-bot failure-classification tree; CI wiring). OQ8 stays **open** pending **reconciliation of the report's findings** into this OQ + the spec — a distinct, not-yet-done follow-up (the report is the input, not the decision). Prompt #13 itself is in [`further-research-needed-prompts.md`](further-research-needed-prompts.md).
- Research: [`lightweight-observability-and-scraper-health-monitoring.md`](research/2026-07-03-lightweight-observability-and-scraper-health-monitoring.md), [`pragmatic-architecture-for-low-volume-python-e-commerce-scraping.md`](research/pragmatic-architecture-for-low-volume-python-e-commerce-scraping.md), [`us-scraping-and-data-retention-landscape-for-a-retail-hdd-price-monitor.md`](research/us-scraping-and-data-retention-landscape-for-a-retail-hdd-price-monitor.md).

#### My Comments

Agent comments look good, but I want to conduct a full deep research with ChatGPT looking into this. Add an entry and prompt to `docs/further-research-needed-prompts.md`.

I think this was done? Check `docs/research/` and `docs/further-research-needed-prompts.md` to see if this was already done. If it was, then we can close this OQ. If not, then we need to do the research and update the OQ with the findings.

If additional research is needed, we should use the `/qdev:research` command to conduct the research and update the open question and existing research doc(s) as applicable with the findings.

---

### OQ9 — Acquisition cadence, throttle & skip policy

**From:** General Design Principles audit (folds findings #1 + #5). **Principles-level wording settled:** the old "Stewardship & Responsibility" principle was replaced in the spec with **"Moderate Aggressive Usage"** ([`hw-radar.md:21`](specs/hw-radar.md)). **Owner posture (2026-07-03):** poll as aggressively — up to real-time/continuous — as each source _tolerates_, and moderate **only** when a service-side protection or red-line would be crossed. The spec's "real-time (or near real-time)" Features framing is therefore **consistent and stays as-is — no reword** (the earlier "reword the real-time framing" task is **withdrawn**). **Decision needed:** the concrete numbers that operationalize "aggressive but self-moderating":

- **per-source cadence** — target poll frequency per source/tier (research floor: single-digit daily checks per SKU; go faster where the source tolerates it);
- **adaptive throttle / back-off** — which signals mark an approaching red-line (HTTP 429/503, soft-block challenge, latency spikes) and the cooldown they trigger, so aggressiveness self-limits _before_ tripping a protection;
- **skip policy** — the tier-ladder cutoff (official API → structured data → headless scrape → **skip**) for a source that cannot be polled without crossing a red-line.

#### Agent notes

- **No spec reword needed** (owner, 2026-07-03): real-time/continuous polling _where the source tolerates it_ is within "Moderate Aggressive Usage" — be aggressive, moderate only when a service protection/red-line would be crossed. This supersedes the earlier note that Features L25/L35 must be reworded; that task is **withdrawn**.
- The cadence + throttle mechanism is already designed: the orchestration research's **two-level token buckets** (per-source + per-domain; `cadence`/`jitter`/`rate`/`burst`) set **aggressively**, plus an **adaptive 429/503 cooldown** that pulls them back as a protection is approached — shared with [OQ7](#oq7--running-cost-budget-model-build-time-pricing-pass) (same budget mechanism) and [OQ10](#oq10--reliability--resilient-acquisition) (same circuit-breaker substrate). Research floor: single-digit daily per SKU; circuit-break chronically failing sources.
- The tier ladder and "**skip** rather than fight anti-bot" is the settled acquisition posture (gap #10 / OQ7 and the scraping research).
- Research: [`orchestration-choice-for-a-single-vm-price-polling-service.md`](research/orchestration-choice-for-a-single-vm-price-polling-service.md), [`pragmatic-architecture-for-low-volume-python-e-commerce-scraping.md`](research/pragmatic-architecture-for-low-volume-python-e-commerce-scraping.md), [`us-scraping-and-data-retention-landscape-for-a-retail-hdd-price-monitor.md`](research/us-scraping-and-data-retention-landscape-for-a-retail-hdd-price-monitor.md).

#### My Comments

Research any outstanding questions about the per-source cadence/politeness numbers and confirm the skip policy. Do this research using /qdev:research and update the open question and existing research doc(s) as applicable with the findings.

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

- **Status (updated 2026-07-04):** both dependencies have moved — [OQ5](#oq5--off-box-heartbeat) is **settled** (off-box heartbeat = the off-site GMK Uptime Kuma) and [OQ8](#oq8--scraper-testing-finalization)'s Deep Research (prompt #13) **has landed** ([the test-policy report](research/automated-test-policy-for-a-low-volume-scrapy-price-monitor.md) carries the parser-rot-vs-anti-bot failure-classification tree). OQ10 stays **open** until that failure model is **reconciled** into OQ8/the spec and wired; the resilience substrate itself — per-source failure isolation, retry/backoff, circuit-break (`paused_pending_fix`), and the `scraper_runs` table (gap #6 / gap #9) — is already settled and only needs wiring.
- Circuit-break state (`paused_pending_fix`) is from the orchestration research; the count-vs-rolling-average + empty-result assertion (gap #9) is the silent-failure detector.
- Research: [`orchestration-choice-for-a-single-vm-price-polling-service.md`](research/orchestration-choice-for-a-single-vm-price-polling-service.md), [`lightweight-observability-and-scraper-health-monitoring.md`](research/2026-07-03-lightweight-observability-and-scraper-health-monitoring.md).

#### My Comments

See [OQ5](#oq5--off-box-heartbeat) and [OQ8](#oq8--scraper-testing-finalization) for the shared substrate. Then update or close this question based on the decisions made in those two questions.

---

### OQ11 — Composite scoring model (adopt research #4)

**From:** domain-research **prompt #4** (landed: [`principled-deal-score…`](research/principled-deal-score-for-hard-drive-listings.md)) — _not_ one of the twelve operational gaps, which is why it carries no prior OQ or ADR. **Decision needed:** ratify the composite scoring algorithm so the **empty** spec `## Scoring System` section ([`hw-radar.md:108`](specs/hw-radar.md)) can be written and a **candidate ADR-0011** recorded. The research recommendation is concrete; the open forks are owner sign-off calls:

1. **Aggregation:** adopt the **weighted geometric mean (weighted product model)** over four normalized subscores, or override toward an arithmetic sum / TOPSIS? (Research recommends the geometric mean and explicitly rejects TOPSIS as the primary score.)
2. **Subscores + weights:** confirm the four subscores — price cheapness-percentile · seller trust (Bayesian + Wilson) · fitness-for-purpose rubric · availability — at default weights **0.50 / 0.25 / 0.15 / 0.10**, or reweight for a value-focused enterprise/recert buyer.
3. **Non-compensatory caps (vetoes):** confirm the hard gates that cap the max score regardless of price — e.g. **device-managed SMR** and **no-return-policy**. Which conditions are hard vetoes vs soft penalties is the load-bearing product call.
4. **Explainability payload:** confirm the glass-box per-subscore explanation is a first-class **stored** output (already assumed by [OQ6](#oq6--final-ui-page-inventory--dismisssuppress-feedback--purchase-tracking)'s listing-detail "why it matched" view).

#### Agent notes

- **ADR-ready now — no new research.** The blocker is ratification, not information: prompt #4 delivered the formula, default weights, gates, and a four-listing worked example.
- The **price subscore's internals are already settled** by gap #11 (shipping/tax folded into `$/TB`) and gap #12 (cohort percentile + continuous warm-up `λ = min(1, n_eff/50)`). OQ11 is the **outer composite** — how the four subscores combine and where the vetoes sit — which those gaps did not cover.
- The **fitness** subscore consumes the suitability taxonomy (prompt #2: tier ladder, SMR hard-reject, PLP penalty) and recert risk (prompt #3: warranty/SMART penalty-bonus table); the **seller-trust** subscore uses cross-marketplace Bayesian + Wilson shrinkage for low-sample sellers (prompt #4).
- Once ratified, this fills spec `## Scoring System` (blank) and maps onto milestone **M2** (whose acceptance criteria already assume this model — reproducible 0–100 with per-factor breakdown).
- Research: [`principled-deal-score…`](research/principled-deal-score-for-hard-drive-listings.md), [`machine-usable-drive-suitability-taxonomy…`](research/machine-usable-drive-suitability-taxonomy-for-24-7-nas-and-server-scoring.md), [`recertified-enterprise-hard-drives…`](research/recertified-enterprise-hard-drives-for-homelab-and-small-business-buyers.md), [`drive-deal-tracker…baselines…`](research/drive-deal-tracker-research-baselines-tools-shucking-and-timing.md).

#### My Comments

Before writing an ADR on the scoring model, I want to test it against mock data to see if it produces reasonable results. Does it actually rate items that are expected to be high or low correctly? Claude will create a small dataset of hard drive listings with various attributes and run the scoring algorithm to see if the output aligns with expectations. Conduct any additional research necessary: do this research using /qdev:research and update the open question and existing research doc(s) with the findings. Also create a comprehensive report/results document at `docs/research/drive-deal-scoring-model-test-results.md` that includes the dataset, the scoring results, and any analysis or conclusions drawn from the test.

---

### OQ12 — Orchestration engine (APScheduler vs systemd timers)

**From:** domain-research **prompt #9** (landed: [`orchestration-choice…`](research/orchestration-choice-for-a-single-vm-price-polling-service.md)), surfaced against **[ADR 0006](adr/adr-0006-cd-rsync-over-tailscale-ssh.md)**. **Decision needed:** name the scheduler that runs the recurring `fetch → parse → normalize → entity-resolve → score → persist → alert` pipeline, and resolve a **live contradiction** — ADR 0006 says "**timers** for scrapes," but prompt #9 recommends **APScheduler 3.11.x** in a systemd-supervised long-running poller with PostgreSQL job state. **Candidate ADR-0012.**

- **The fork:** **APScheduler in-process** (per-source cadence, jitter, two-level token buckets, adaptive 429/503 cooldown, dead-letter + circuit-breaker — all in one supervised process, sharing state) **vs. systemd timers** (leaner, but per-source rate modeling and _shared_ back-off/circuit-breaker state are awkward across independent one-shot units).
- **This blocks OQ7 / OQ9 / OQ10:** all three assume the **two-level token-bucket** cadence/back-off substrate, which is an in-process (APScheduler-style) model, _not_ independent systemd timers. Deciding the engine is a prerequisite to operationalizing their cadence numbers and circuit-breaker thresholds.

#### Agent notes

- **ADR-ready now — no new research.** Prompt #9 explicitly flags **Celery / RQ / Dramatiq / Prefect / Dagster / Airflow as over-engineered** at ~20 sources on one VM; the real choice is APScheduler vs plain timers, with APScheduler favored for per-source scheduling flexibility, retry/back-off, and _shared_ circuit-breaker state.
- **ADR 0006 reconciliation is mandatory whichever way this goes:** if APScheduler wins, amend ADR 0006's "timers for scrapes" line (systemd still _supervises_ the poller process; it no longer _schedules_ each scrape). If timers win, OQ7/OQ9/OQ10's token-bucket model must be re-specified for stateless one-shot units.
- Shares the `scraper_runs` table (gaps #6/#9) for run state and the `paused_pending_fix` circuit-breaker state ([OQ10](#oq10--reliability--resilient-acquisition)).
- Research: [`orchestration-choice…`](research/orchestration-choice-for-a-single-vm-price-polling-service.md).

#### My Comments

I am leaning toward APScheduler as the orchestration engine. However, the research that labeled the other solutions as over-engineered may have been done prior to the recent changes in the scraping architecture and number of sources. Plus, we need to consider the general design principles of the project and whether APScheduler is consistent with those principles. Further research should be done to confirm that APScheduler is still the best choice given the current architecture and number of sources. Do this research using /qdev:research and update the open question and existing research doc(s) with the findings.

---

### OQ13 — Notification transport & deliverability (AgentMail vs transactional provider)

**From:** domain-research **prompt #11** (landed) + **prompt #14** (landed 2026-07-04: [`choosing-an-outbound-email-path…`](research/choosing-an-outbound-email-path-for-a-low-volume-alerting-system.md)), against the spec's **AgentMail** standardization ([`hw-radar.md:68`](specs/hw-radar.md), OpenBao `secret/api-keys/ai/agentmail`). **Research is now complete — the remaining decision is an owner call.** Confirm the email-send path and its deliverability setup so alerts do not spam-folder. **Candidate ADR-0013.**

- **The tension (now with a research recommendation):** prompt #11 recommended a **transactional provider (Postmark preferred, SES for cost)** over raw datacenter SMTP; prompt #14 characterized the missing piece — **AgentMail specifically** — and recommends **Postmark primary → SES fallback → AgentMail as a _secondary_ agent-inbox tool, not the primary alert channel.** The spec + OpenBao standardize on AgentMail and the owner leans AgentMail (see [OQ7 My Comments](#oq7--running-cost-budget-model-build-time-pricing-pass)), so the open decision is now a **conscious owner call: accept the Postmark-primary recommendation, or override toward AgentMail.**
- **Deciding factor (per #14):** _not_ a capability gap — AgentMail **does** support custom-domain **SPF/DKIM/DMARC**, so it is not disqualified on authentication. The factor is AgentMail's **thinner public deliverability track record** for must-not-miss transactional mail vs Postmark's/SES's long-established transactional-delivery model.
- **Cost caveat — undercuts OQ7's "AgentMail is free":** #14 found AgentMail's **free tier sends from `@agentmail.to` only**; **branded custom-domain sending (`chris@l3digital.net`) requires the $20/mo Developer plan.** "Free" therefore holds only for an _unbranded_ from-address — for a branded business alert the cost is comparable to Postmark/SES, which weakens the main reason to prefer AgentMail.
- **Open forks:** (1) **primary provider** — Postmark (research pick) vs AgentMail (owner lean), now that both cost ~$20/mo for branded sending; (2) **fallback** provider (research: SES cold-standby on the same domain); (3) whether SES's initial **sandbox** (200 msg/day, verified-recipients-only until production access is granted) is acceptable for a one-recipient failover.

#### Agent notes

- **Scope is narrow — transport + deliverability only.** The **alert-rule data model, dedup/debounce/digest, and hysteresis are already settled** (prompt #11 + [OQ6](#oq6--final-ui-page-inventory--dismisssuppress-feedback--purchase-tracking)'s post-alert state machine). OQ13 does not reopen alerting logic.
- Couples to gap #6's **email-delivery confirmation** (the operator-side signal that a send actually left the box).
- **Prompt #14 LANDED (2026-07-04) — the research gap is closed;** what remains is the owner's provider call, not more research. Findings reconciled above: the Postmark-primary recommendation, the DKIM-is-fine / track-record-is-the-real-factor nuance, and the free-tier-is-`@agentmail.to`-only cost caveat.
- **Deliverability mechanics (shared by whichever provider wins):** a **high-quality shared IP pool** is correct at this volume (dedicated IPs need sustained volume to build reputation); direct SMTP from the Hetzner box is **out** (Hetzner blocks ports 25/465, and a datacenter IP lacks the reputation/PTR/auth history receivers demand). `l3digital.net` still needs **SPF + DKIM + DMARC** either way — start `p=none`, tighten to `p=quarantine`/`p=reject` once alignment is confirmed.
- Research: [`designing-a-low-noise-alerting-layer…`](research/designing-a-low-noise-alerting-layer-for-a-hard-drive-deal-monitor.md), [`choosing-an-outbound-email-path…`](research/choosing-an-outbound-email-path-for-a-low-volume-alerting-system.md).

#### My Comments

I am not going to pay for the email service at this time. Whatever gets implemented must be free for the time being. I will revisit this question if we find that email deliverability is a problem and we need to pay for a service to improve it. Research this problem further to resolve this.

---

### OQ14 — Scraping runtime escalation stack

**From:** domain-research **prompt #8** (landed: [`pragmatic-architecture…scraping`](research/pragmatic-architecture-for-low-volume-python-e-commerce-scraping.md)), against the spec's under-specified "Scrapy. Additional options to be considered" ([`hw-radar.md:69`](specs/hw-radar.md)). **Decision needed:** ratify the concrete escalation stack so the spec §Software Stack names it. **Candidate ADR-0014** (or a straight spec fold — lower priority than OQ11–OQ13).

- Prompt #8's default is **HTTP-first, structured-data-first, browser-last:** Scrapy as orchestrator, a structured-data detector (JSON-LD → platform JSON → bootstrap JSON) in front of every parser, **Playwright via `scrapy-playwright`** for occasional rendering, **`curl_cffi`** for the narrow TLS-fingerprint gap, and **skip / outsource** for targets needing residential-proxy rotation or CAPTCHA solving.
- **Open fork:** adopt the full stack in the spec now, or trim — e.g. defer `curl_cffi`/Playwright to **M5** breadth and ship **M1**'s five recert sources on plain HTTP + structured-data parsing (those are the "easy" tier), adding the browser/TLS tiers only when a hostile source demands it.

#### Agent notes

- **ADR-ready now — no new research.** Prompt #8 delivered the difficulty→technique decision tree, a managed-API cost table, and the default stack.
- Dovetails with the spec's **Special Considerations guardrails** (`ROBOTSTXT_OBEY=True`, AUTOTHROTTLE, no anti-bot bypass) and the **acquisition tier ladder** (feed > structured-data > headless > skip) already in the spec — OQ14 only names the _tools_ per tier.
- The **skip cutoff** ("not worth it — use the API or skip") is the same tier-ladder cutoff as [OQ9](#oq9--acquisition-cadence-throttle--skip-policy)'s skip policy — decide them consistently.
- Because it is the lowest-stakes of the four (most of it is already implied by the spec's acquisition posture), a spec fold may be sufficient without a standalone ADR — owner's call.
- Research: [`pragmatic-architecture…scraping`](research/pragmatic-architecture-for-low-volume-python-e-commerce-scraping.md), [`programmatic-acquisition…`](research/programmatic-acquisition-research-for-enterprise-and-nas-drive-merchants.md).

#### My Comments

Would we actually use Playwright? Can that be used programmatically in a headless way to scrape the sites we need without an AI agent/LLM?

---

## Resolved

Everything below is **settled**. It is retained for provenance and to keep ADR/spec cross-references resolvable. New readers do not need to read this to know what is outstanding — that is entirely in [Open questions](#open-questions).

### Resolved questions

Cross-cutting questions the research surfaced, now closed. Referenced by ADRs/spec as `RQ#`.

| # | Question | Resolution |
| --- | --- | --- |
| **RQ1** | Framework: Django or FastAPI? | **Django** + server-rendered templates + HTMX — the app's center of gravity is an authenticated listings DB + dashboards + CRUD + alerts, not an API platform. **[ADR 0004](adr/adr-0004-web-framework-django-htmx.md).** Locks in `manage.py migrate`, `contrib.auth`, and the Django admin as back-office. |
| **RQ2** | Public URL required, or Tailscale-only acceptable? | **Public URL required**, with a single strong-password account; Tailscale-only rejected. Drives the auth model (resolved gap #1, [ADR 0005](adr/adr-0005-single-account-session-auth.md)). |
| **RQ3** | Does the Proxmox host give a per-service vTPM? | The host has `swtpm` installed, so a full **VM** could get a vTPM — but hw-radar deploys as a **CT** (RQ5), which has **no per-container TPM** (shared host kernel). So `systemd-creds --with-key=tpm2` is **not** available → secrets go via the local OpenBao Agent (resolved gap #2, [OQ1](#oq1--secret_id-out-of-band-delivery-to-the-ct)). |
| **RQ4** | Existing Hetzner backup & monitoring coverage? | **Characterized on 2026-07-03** (specifics in the private `homelab` repo). **Backup:** file-level restic + hourly logical dumps to two offsite repos, but **opt-in per service via a hardcoded allowlist**, **no PITR** (≤1 h RPO), **no VM-image backup**. **Monitoring:** rich but **on-box only**, **no off-site watchdog**; a CT is auto-discovered by the health check, a VM is not. Net: a CT maximizes infra reuse; an off-box heartbeat ([OQ5](#oq5--off-box-heartbeat)) and a DB-RPO decision ([OQ3](#oq3--db-rpo-acceptance--timescaledb-dump-handling)) are the two things to add. |
| **RQ5** | Deployment model — CT vs VM? | **Dedicated LXC container**, superseding the spec's "VM". Aligns with the "every service in a dedicated LXC" standard and maximizes infra reuse (fleet-digest auto-discovers the CT; its data is reachable by the host's file-level restic). **[ADR 0003](adr/adr-0003-deploy-as-lxc-container.md).** Consequences: vTPM off the table (RQ3) → local OpenBao Agent; backup is **not** automatic (wire the CT into `backup-restic.sh`/`backup-dumps.sh`); DB on a container Postgres ([OQ4](#oq4--db-placement-own-ct-vs-shared-datastores-ct)). |
| **RQ6** | Datastore: PostgreSQL or MySQL? | **PostgreSQL (system-of-record) + TimescaleDB** for the price-history/observation side. **[ADR 0007](adr/adr-0007-datastore-postgresql-timescaledb.md).** Adds the TimescaleDB-aware-dump driver to [OQ3](#oq3--db-rpo-acceptance--timescaledb-dump-handling). |

### Gap summary (all 12, for reference)

The original gap analysis and where each landed. 🔴/🟡/🟢 = original priority.

| # | Gap | Pri | Outcome |
| --: | --- | :-: | --- |
| 1 | Web-app authentication undefined | 🔴 | **Settled** — single-account Argon2id session login ([ADR 0005](adr/adr-0005-single-account-session-auth.md)). |
| 2 | `.env` secrets contradict OpenBao standard | 🔴 | **Settled** ([ADR 0009](adr/adr-0009-secrets-runtime-openbao-agent.md)) — local bao-agent on the CT consuming the Hetzner **`bao-services` (CT 115)** store; SecretID delivery settled ([OQ1](#oq1--secret_id-out-of-band-delivery-to-the-ct) ✅, verified live 2026-07-04). |
| 3 | No currency / landed-cost normalization | 🔴 | **Settled** ([ADR 0008](adr/adr-0008-currency-landed-cost-normalization.md)) — Frankfurter FX → USD; flag international listings (no fixed haircut). |
| 4 | Deployment & service topology a black box | 🔴 | **Settled** — `rsync` over Tailscale + systemd ([ADR 0006](adr/adr-0006-cd-rsync-over-tailscale-ssh.md)); runner tailnet auth settled → **Tailscale OAuth client** ([OQ2](#oq2--ephemeral-runner-tailnet-auth) ✅, verified live 2026-07-04). |
| 5 | No backup / disaster recovery | 🟡 | **Settled** (CT path) — inherit restic + hourly dumps ([ADR 0003](adr/adr-0003-deploy-as-lxc-container.md)); DB placement settled → **own-CT Postgres** ([OQ4](#oq4--db-placement-own-ct-vs-shared-datastores-ct) ✅). Open part → [OQ3](#oq3--db-rpo-acceptance--timescaledb-dump-handling) (DB-RPO). |
| 6 | No application self-observability | 🟡 | **Settled** (CT path) — infra health auto-covers the CT; in-app `scraper_runs`/dead-man's-switch; off-box heartbeat settled → **GMK Uptime Kuma** ([OQ5](#oq5--off-box-heartbeat) ✅). |
| 7 | UI/UX specified as one line | 🟡 | **Settled** — Django + HTMX rendering + post-alert state machine. Open part → [OQ6](#oq6--final-ui-page-inventory--dismisssuppress-feedback--purchase-tracking). |
| 8 | No v1 scope / phasing / acceptance criteria | 🟡 | **Settled** — six-milestone MVP plan (M0–M5) accepted; authoritative phasing to be authored via `spec-pipeline`. |
| 9 | No scraper testing strategy | 🟡 | **Settled** — vcrpy + syrupy + contract canary + Pydantic v2 (+5 amendments). Open part → [OQ8](#oq8--scraper-testing-finalization). |
| 10 | No running-cost / budget model | 🟢 | **Settled** (approach) — free-feed-first, config-driven per-source poll budget. Open part → [OQ7](#oq7--running-cost-budget-model-build-time-pricing-pass). |
| 11 | Shipping/tax not in the `$/TB` score | 🟢 | **Settled** — score on price + shipping (+ tax where known); missing-shipping = penalty/flag. |
| 12 | Cold-start: no history for relative scoring | 🟢 | **Settled** — continuous-shrinkage warm-up (`λ = min(1, n_eff/50)`); graded seed sources. |

### Resolved gaps & decisions

Full write-ups of the twelve gaps. For split gaps, only the **settled** part is here; the open part is the linked OQ.

#### Gap 1 — Web-app authentication (settled, ADR 0005)

**Was:** the spec asserted "user authentication for secure access" and anticipated future multi-user, but defined no auth model, mechanism, or user schema. Evidence: [`hw-radar.md:7`](specs/hw-radar.md), [`:79`](specs/hw-radar.md).

**Decision → [ADR 0005](adr/adr-0005-single-account-session-auth.md):** a single strong-password account with **Argon2id** session login (Django `contrib.auth`), internet-facing; the load-bearing constraint is that the app holds **no in-app secrets**. Stub a `users` table now; **Authelia forward-auth** reserved for the multi-user end state. Full context and the forward-auth security rules (localhost bind, header overwrite, CVE-pinned gateway) live in the ADR. Research: [`auth-for-self-hosted-single-maintainer-python-app.md`](research/2026-07-03-auth-for-self-hosted-single-maintainer-python-app.md).

#### Gap 2 — `.env` secrets model → OpenBao (settled except `secret_id` delivery)

**Was:** the spec repeatedly said secrets live in a committed-excluded `.env`, but the org standard is **OpenBao as the credential store**, and it never answered **how the deployed app obtains secrets at runtime** — a real contradiction, sharpened by the repo being public. Evidence: [`hw-radar.md:62`](specs/hw-radar.md), [`:82`](specs/hw-radar.md), [`:95`](specs/hw-radar.md), [`:107`](specs/hw-radar.md), [`:111`](specs/hw-radar.md).

**Decision:**

- **Runtime injection via OpenBao Agent** (`bao agent`, its own hardened systemd unit) using **AppRole auto-auth**. The agent templates secrets to a root-owned, `0640`, app-group-readable file on **tmpfs** (`/run/hw-radar/secrets.env`, gone on reboot); app services depend on it via `After=`. No plaintext `.env` at rest, no secrets baked into unit files.
- **The Agent runs locally on the CT, fully decoupled from CI.** Because CD is `rsync` over Tailscale SSH from a **GitHub-hosted** runner (gap #4), the public-repo CI job holds **no OpenBao credential at all** — it only rsyncs code and triggers `systemctl restart`; the running services pick up secrets the Agent has already templated. The `role_id` lives in the CT image/config-management.
- **Reconcile the spec's language:** `.env` is acceptable **for local development only**; production resolves secrets from OpenBao at runtime.
- **Settled 2026-07-04 (verified live) → [ADR 0009](adr/adr-0009-secrets-runtime-openbao-agent.md):** the `secret_id` delivery/renewal path → hw-radar onboards as the next **`bao-services` (CT 115)** consumer via a local **bao-agent**; a persistent, long-lived, **CIDR-bound** SecretID at `/etc/bao-agent/secret-id` delivered operator→CT by `bao-issue-secret-id.sh` (wrap token + `pct push`) → **[OQ1](#oq1--secret_id-out-of-band-delivery-to-the-ct)**. (The earlier "CD job fetches a response-wrapped `secret_id`" mechanism is withdrawn — CI holds no OpenBao credential; the Agent on the CT consumes locally. The spec's `remove_secret_id_file_after_reading=true` is also superseded — it breaks restart safety.)

Research: [`github-actions-cd-private-debian-vm.md`](research/2026-07-03-github-actions-cd-private-debian-vm.md) §3.

#### Gap 3 — Currency / landed-cost normalization (settled, ADR 0008)

**Was:** the score is `USD` per `TB`, but several ranked merchants (ETB Technologies, Bargain Hardware) are UK/EU resellers pricing in GBP/EUR, and the buyer is US-based — cross-border listings scored on a false basis. Evidence: [`hw-radar.md:13`](specs/hw-radar.md), merchants at [`:40`–`:41`](specs/hw-radar.md).

**Decision (owner, 2026-07-03 — accepted with changes) → [ADR 0008](adr/adr-0008-currency-landed-cost-normalization.md):**

- **FX:** use **Frankfurter** (ECB-anchored, free, no API key, MIT, self-hostable), refreshed once/day. Store `fx_rate`, `fx_pair`, `fx_rate_date`, `fx_source` **on each observation** so historical scores are auditable and reproducible.
- **Normalize all prices to USD, but do NOT apply a fixed "international overhead" haircut.** Instead **flag** international listings (e.g. `"international — extra shipping/duty likely; verify before buying"`) and let the owner decide. Rationale: a cross-border purchase is unlikely to be worthwhile (shipping + potential customs), and a hardcoded percentage would be false precision — surface the risk rather than bake in a number. HDDs classify under **HTS 8471.70 at a 0% base (MFN) rate**, so the volatile cost is the surcharge the flag defers to the user.
- **Do NOT compute exact duty.** As of 2026-07-03 the US **de-minimis exemption is suspended indefinitely** and the add-on tariff rate for UK/EU goods is in active legal flux — a precise duty figure would be false precision that goes stale.
- **VAT footgun:** UK/EU VAT should be **zero-rated on export**, but many storefronts display VAT-inclusive prices pre-checkout — the scraper must not treat a VAT-inclusive shelf price as the export price.

Research: [`currency-conversion-and-landed-cost-estimation…md`](research/2026-07-03-currency-conversion-and-landed-cost-estimation-for-cross-border-drive-price-scoring.md).

#### Gap 4 — Deployment & service topology (settled, ADR 0006)

**Was:** "GitHub Actions → automatic deployment to Hetzner on merge to main" stated the _what_, never the _how_: transport, how the app runs as a service, how CI reaches a non-public target. Evidence: [`hw-radar.md:72`–`:75`](specs/hw-radar.md).

**Decision → [ADR 0006](adr/adr-0006-cd-rsync-over-tailscale-ssh.md):** a **GitHub-hosted `ubuntu-latest`** runner builds/tests, joins the tailnet **ephemerally**, then `rsync`s to the CT and restarts over `tailscale ssh` (self-hosted runner rejected on a public repo). Systemd web + worker units under a dedicated non-root user; **timers** for scrapes; venv built on the CT (`uv sync --frozen`); expand/contract migrations before restart. Full trigger/secret discipline lives in the ADR. **Settled 2026-07-04 (verified live):** the ephemeral-runner tailnet auth → the **Tailscale OAuth client** (`secret/infra/tailscale-oauth`, minting a `tag:ci` ephemeral node) via `tailscale/github-action` v4 → **[OQ2](#oq2--ephemeral-runner-tailnet-auth)**. Research: [`github-actions-cd-private-debian-vm.md`](research/2026-07-03-github-actions-cd-private-debian-vm.md); per-source scheduling refined in [`orchestration-choice…md`](research/orchestration-choice-for-a-single-vm-price-polling-service.md).

#### Gap 5 — Backup / disaster recovery (settled CT path, ADR 0003)

**Was:** the accumulated historical price data _is_ the tool's compounding value; a single box with no backup means one disk failure erases the moat. Evidence: [`hw-radar.md:19`](specs/hw-radar.md), [`:22`](specs/hw-radar.md); DB co-located per [`:69`](specs/hw-radar.md).

**Decision (CT path) — [ADR 0003](adr/adr-0003-deploy-as-lxc-container.md):** add the hw-radar **CT** to the existing Hetzner restic + hourly-dump pipeline; keep the monthly restore-test discipline. **Settled 2026-07-03:** DB placement → **own Postgres inside the hw-radar CT** (self-contained; [OQ4](#oq4--db-placement-own-ct-vs-shared-datastores-ct)). **Still open:** DB-RPO acceptance → **[OQ3](#oq3--db-rpo-acceptance--timescaledb-dump-handling)** (owner: document requirements in the `homelab` repo first).

**Live-state findings (2026-07-03 — verified on the server; specifics in the private `homelab` repo):**

- **The existing backup is file-level restic + logical DB dumps — there is _no_ VM-image backup.** No scheduled `vzdump`/PBS runs. restic backs up the host + each **LXC container's** app data via ZFS-subvolume paths → local ZFS repo, an **hourly offsite copy** (Hetzner Storage Box), and a **weekly offsite copy of a tier-1 subset** (Backblaze B2). Retention: 48 hourly / 14 daily / 8 weekly / 6 monthly.
- **Databases are dumped _logically, hourly_.** `pg_dump --format=custom` per DB + `pg_dumpall --globals-only`, captured by restic. **No WAL archiving, no PITR** → **RPO up to ~1 hour**.
- **Coverage is a hardcoded allowlist, _not_ auto-discovery.** `backup-restic.sh` and `backup-dumps.sh` name each path/DB by hand; a fail-loud guard aborts on a vanished path, but a **new service is never picked up automatically.**

**Implications:** had it stayed a standalone VM with an in-VM DB, it would have fallen **entirely outside** existing backup coverage — a primary reason the deployment model was decided as a CT (RQ5). **Decided path (CT):** deploy as a dedicated LXC container with its DB on a container Postgres, **and at provisioning add its data paths to `backup-restic.sh` + its DB to `backup-dumps.sh`** — this wiring is mandatory, not automatic. **Caveat (TimescaleDB, ADR 0007):** the inherited logical `pg_dump` needs TimescaleDB-aware dump/restore — a plain allowlist entry is insufficient; otherwise add in-CT physical backup (see OQ3).

**Fallback design if tighter RPO/PITR is wanted:** **pgBackRest** physical backup + continuous **WAL archiving** on the box (`repo1`) with a **second repo (`repo2`) on S3-compatible storage** (Backblaze B2 or Hetzner Storage Box) using pgBackRest **AES-256** — PITR + 3-2-1 offsite. Supplement with a weekly `pg_dumpall`. **TimescaleDB:** physical backups need no special handling; prefer them over logical. **Patch PostgreSQL/tooling** (recent `pg_dump`/`pg_basebackup`/`pg_rewind` CVEs). Research: [`postgresql-backup-disaster-recovery-single-vm.md`](research/2026-07-03-postgresql-backup-disaster-recovery-single-vm.md).

#### Gap 6 — Application self-observability (settled CT path except off-box heartbeat)

**Was:** deal alerts tell the _user_ about drives; nothing tells the _operator_ that the app is down, out of disk, a scrape stopped, or alert emails aren't delivered. Evidence: [`hw-radar.md:11`](specs/hw-radar.md).

**Decision (CT path):** split the concern — **infrastructure health** (up/disk/CPU/RAM) rides the existing Hetzner monitoring, which **auto-discovers the CT**; **application-level health** stays in-app via the **`scraper_runs` table** (shared with gap #9 / OQ8), a **dead-man's-switch heartbeat**, and **email-delivery confirmation**. **Settled 2026-07-03:** the off-box heartbeat → the **off-site GMK Uptime Kuma** watches the CT (also swept by the Hetzner Fleet Digest) → **[OQ5](#oq5--off-box-heartbeat)**.

**Live-state findings (2026-07-03 — verified on the server):**

- **Monitoring is rich but _on-box_.** A twice-daily "fleet-digest" runs a ~57-probe health check across every container + the host, an on-box Uptime Kuma, plus CVE scans, AIDE, Lynis. The health check **auto-discovers containers from `pct list`** — so a new **CT** _is_ monitored automatically (a VM would only get a coarse up/down probe).
- **Alert _delivery_ is off-box** (email via MS Graph → M365), so a degraded-but-reachable box can still page out.
- **But there is no off-box _watchdog_.** Every heartbeat is a push monitor to the **on-box** Uptime Kuma; the off-site GMK Uptime Kuma does not monitor Hetzner. **A total-box outage would be caught by no automated off-box observer** — exactly the failure mode the research flagged.

**Implications:** the fleet-digest health check auto-covers a new container; confirm a **disk-space threshold** alert applies (raw payloads grow). **The one real gap was an off-box heartbeat — now settled as the off-site GMK Uptime Kuma** (OQ5). Keep the in-app pieces regardless; error tracking (GlitchTip/Sentry) is not in the existing stack — add if wanted. Research: [`lightweight-observability-and-scraper-health-monitoring.md`](research/2026-07-03-lightweight-observability-and-scraper-health-monitoring.md).

#### Gap 7 — UI/UX (settled: Django + HTMX + post-alert model; inventory open)

**Was:** "Provides a user-friendly web-based interface" with no page inventory, flows, or post-alert action model. Evidence: [`hw-radar.md:20`](specs/hw-radar.md).

**Decision (settled parts):** **rendering — [ADR 0004](adr/adr-0004-web-framework-django-htmx.md):** Django + server-rendered templates + HTMX, matching a single-maintainer, data-heavy CRUD+dashboard app without an SPA build chain; use the **Django admin as internal back-office**. **Post-alert model:** a per-watch, per-listing **state machine** (`none / pending / firing / cooling / digested`), first-class snooze at two granularities, one-click HMAC-signed action links, watch-as-unit-of-opt-out; dedup on listing + alert fingerprints. **Watch-rule UI:** hard filters separate from thresholds, no free-text title matching. **Still open:** the final page inventory, the dismiss→suppress feedback path, and purchase-tracking scope → **[OQ6](#oq6--final-ui-page-inventory--dismisssuppress-feedback--purchase-tracking)**. Research: [`opinionated-core-stack-recommendations…md`](research/opinionated-core-stack-recommendations-for-a-python-drive-price-monitor.md), [`designing-a-low-noise-alerting-layer…md`](research/designing-a-low-noise-alerting-layer-for-a-hard-drive-deal-monitor.md).

#### Gap 8 — v1 scope / phasing / acceptance criteria (settled)

**Was:** the spec said v1 "will not" optimize for other users, but never stated what v1 **does** include vs defers across 20 marketplaces + scoring + entity resolution + a web UI. Evidence: [`hw-radar.md:7`](specs/hw-radar.md).

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

**Was:** CI names "testing workflows" but the spec never said **how** to test scrapers against sites that change and fight bots. Evidence: [`hw-radar.md:73`](specs/hw-radar.md).

**Decision (settled):**

- **Recorded fixtures:** **vcrpy cassettes** per source (record once, replay in CI) — deterministic, offline parse tests.
- **Snapshot tests:** **syrupy** golden-file assertions on parsed output.
- **Production canary:** a **scheduled** live **structured-data contract check** per source + a **known-value canary page**.
- **Runtime validation:** **Pydantic v2** per-record validation + `last_success_at` / consecutive-failure counters + a count-vs-rolling-average assertion; alert when a source returns 0/malformed N runs in a row. Shares the `scraper_runs` table from gap #6.

**Five research-confirmed amendments (2026-07-03):** (1) canary must be **per-extraction-tier**, not JSON-LD-only — tiers break independently; (2) **risk-weight canary frequency by tier** — fragility increases down the ladder; (3) **scrub cassettes of PII before commit** (compliance, not hygiene); (4) **do not commit real cassettes for retention-restricted sources** — use synthetic fixtures; real cassettes fine for recert specialists; (5) **classify failure type** — parser rot vs now-anti-bot-protected (a soft-block often returns HTTP 200 + empty body). **Still open:** the concrete build-time parameters (per-tier frequencies; synthetic-vs-real cassette assignment) → **[OQ8](#oq8--scraper-testing-finalization)**. Research: [`lightweight-observability…md`](research/2026-07-03-lightweight-observability-and-scraper-health-monitoring.md), [`pragmatic-architecture…md`](research/pragmatic-architecture-for-low-volume-python-e-commerce-scraping.md), [`us-scraping-and-data-retention-landscape…md`](research/us-scraping-and-data-retention-landscape-for-a-retail-hdd-price-monitor.md).

#### Gap 10 — Running-cost / budget model (settled approach; pricing pass open)

**Was:** paid search APIs, AgentMail, object storage, and possible managed-scraping APIs had no aggregate budget or ceiling to design polling frequency against. Evidence: [`hw-radar.md:55`](specs/hw-radar.md), [`:109`–`:111`](specs/hw-radar.md).

**Decision (approach):** **prefer free official feeds** (eBay Browse/Feed, structured-data parsing) over paid search calls — search APIs are for _discovery_, not per-poll refresh. **Config-driven per-source poll budget** held under a stated **monthly ceiling**, reusing the orchestration research's **two-level token buckets** (per-source + per-domain). Track actuals via the `scraper_runs` table. Managed-scraping APIs avoided for this merchant set (free structured data covers it; reserve them for a hostile tail — or skip the source). **Still open:** the build-time pricing pass (current Serper/Brave/Tavily per-call pricing, AgentMail, backup object-storage costs; Brave storage-rights plan) → **[OQ7](#oq7--running-cost-budget-model-build-time-pricing-pass)**. Research: [`programmatic-acquisition…md`](research/programmatic-acquisition-research-for-enterprise-and-nas-drive-merchants.md), [`tavily-brave-serper.md`](research/tavily-brave-serper.md), [`pragmatic-architecture…md`](research/pragmatic-architecture-for-low-volume-python-e-commerce-scraping.md), [`orchestration-choice…md`](research/orchestration-choice-for-a-single-vm-price-polling-service.md).

#### Gap 11 — Shipping (and tax) in the `$/TB` score (settled)

**Was:** `$/TB` on item price alone misranks a cheap drive with high shipping — even domestically. Evidence: [`hw-radar.md:13`](specs/hw-radar.md).

**Decision (accepted):**

- Score on **price + shipping (+ tax where known)**, not item price alone. Marketplace shipping fields (eBay Browse `shippingOptions`, Serper `delivery`) are reliable **only when the request supplies correct buyer-location context** — pin the buyer location on every query.
- When shipping is unknown, **apply a penalty or flag** rather than silently scoring as if free.
- Composes with the **international flag** from gap #3 (which dropped the fixed overhead haircut): domestic known shipping is folded into `$/TB`; cross-border extra cost stays a flag, not a number.

Research: [`currency-conversion-and-landed-cost-estimation…md`](research/2026-07-03-currency-conversion-and-landed-cost-estimation-for-cross-border-drive-price-scoring.md).

#### Gap 12 — Cold-start scoring (settled)

**Was:** the moving-baseline / percentile scoring needs accumulated history that doesn't exist at launch. Evidence: [`hw-radar.md:19`](specs/hw-radar.md), [`:22`](specs/hw-radar.md).

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
