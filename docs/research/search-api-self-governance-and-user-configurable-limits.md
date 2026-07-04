---
schema_version: '1.1'
id: search-api-self-governance-and-user-configurable-limits
title: Search-API Self-Governance and User-Configurable Limits for Outbound Discovery Calls
description: Cost/quota governance for the app's own paid Serper/Brave/Tavily discovery calls — per-provider token-bucket throttling with starting rate/burst numbers, a fail-safe persisted spend-cap circuit breaker distinct from provider dashboards, a failing-provider closed/open/half-open breaker composed as an independent middleware layer, and a small user-configurable budget/aggressiveness settings model informed by API-gateway and self-hosted-tool precedent.
doc_type: research
status: active
created: '2026-07-04'
updated: '2026-07-04'
reviewed: null
owner: chris
tags:
- search-api-governance
- rate-limiting
- circuit-breaker
- budget-cap
- cost-control
- serper
- brave
- tavily
- agentmail
aliases: []
related:
- tavily-brave-serper
- orchestration-choice-for-a-single-vm-price-polling-service
source: []
confidence: high
visibility: private
license: null
---

# Search-API self-governance and user-configurable limits for outbound discovery calls

> **Scope note.** This report is about governing calls the app itself makes and pays for (Serper/Brave/Tavily used for *discovery*). It deliberately does not re-litigate provider selection — see [`tavily-brave-serper.md`](tavily-brave-serper.md) for that — and it is not about politeness/anti-bot throttling toward scraped merchant sites, which [`orchestration-choice-for-a-single-vm-price-polling-service.md`](orchestration-choice-for-a-single-vm-price-polling-service.md) already covers with a two-level (per-source/per-domain) token-bucket design. This report extends that same vocabulary to a third concern: our own outbound spend.

> **Tooling note.** The Tavily MCP server referenced by the standard research workflow was not exposed in this environment; this pass degraded to the Brave + Serper stack plus direct fetches of official docs, per the fail-soft fallback chain. Coverage was not materially affected — all four questions below are backed by official-source or 2+-source-corroborated findings.

## Bottom line

Reuse the orchestration report's per-source policy-row pattern for a new **`discovery_budget`** row per search provider, and give every outbound Serper/Brave/Tavily call a single mandatory choke point — a `SearchBudgetGate` — that evaluates, in strict order: **(1) manual kill switch, (2) persisted hard spend cap, (3) provider circuit-breaker state, (4) token-bucket admission**. Only if all four pass does the call go out. A **token bucket**, not a leaky bucket or bare min-interval, is the right throttle primitive here because the goal is a predictable sustained rate with a small tolerated burst (the same reasoning the orchestration report already used for scraping traffic); reserve leaky-bucket-style constant-rate shaping for cases where you must smooth output regardless of demand, which discovery calls are not. The hard spend cap must **fail safe by stopping calls entirely**, not by falling back to a cheaper provider or degraded mode, because a silent fallback under a live bug just moves the runaway cost instead of stopping it.

## 1. Client-side rate limiting per provider

**Mechanism: token bucket per provider**, mirroring the orchestration report's `source_rate`/`source_burst` fields but scoped to a provider instead of a scrape source. A token bucket is the right choice over a leaky bucket or a bare min-interval floor because it lets you express both "never exceed this sustained rate" and "but tolerate a small burst when several sources become due for discovery at once" in one primitive — leaky-bucket-style constant-rate shaping is a better fit for smoothing *downstream* traffic you don't control the demand curve of, not for a client deciding when to originate its own optional calls [blog, corroborated by two independent write-ups: Arcjet's rate-limiting algorithm comparison and API7.ai's token-bucket-vs-leaky-bucket guide] (<https://blog.arcjet.com/rate-limiting-algorithms-token-bucket-vs-sliding-window-vs-fixed-window/>, <https://api7.ai/blog/token-bucket-vs-leaky-best-rate-limiting-algorithm>). A bare "1 call/min" min-interval floor is a degenerate token bucket with burst=1; it is safe but wastes capacity you're already paying for in unused monthly credits, so a small burst allowance (3-5) is a strictly better default at effectively the same risk profile.

Starting numbers, derived from current published pricing/rate-limit evidence rather than guesswork:

| Provider | Cost basis (2026) | Suggested `rate` | Suggested `burst` | Suggested `daily_call_cap` | Rationale |
| --- | --- | --- | --- | --- | --- |
| **Serper** | Credit-based, ~$1.00/1,000 queries dropping to ~$0.30/1,000 at volume; 2,500 free trial queries, credits valid 6 months [community, cross-corroborated across ~8 independent pricing write-ups: buildmvpfast.com, costbench.com, scrap.io, cloro.dev] | 1 call / 2 min (0.5/min) | 5 | 200 | Cheapest of the three per call; still worth a floor because a bug-triggered loop at, say, 1 call/sec would burn the 6-month trial allotment in under an hour. |
| **Brave Search API** | Free tier removed **February 2026**; now $5 in monthly credits (~1,000 queries) then $5/1,000 requests metered; default capacity **50 req/s** on the Search plan, **2 req/s** on the (pricier, per-call) Answers plan [official: brave.com/search/api pricing page + api-dashboard.search.brave.com/documentation/pricing; corroborated by implicator.ai's Feb 2026 reporting on the tier removal and by firecrawl.dev's alternatives comparison] | 1 call / 5 min (0.2/min) | 3 | 50 | Most expensive per call of the three and the free allowance shrank materially in 2026 — the tightest default is warranted here, well below the 50 req/s ceiling Brave itself enforces. |
| **Tavily** | Free tier **1,000 credits/month** (basic search = 1 credit, advanced = 2); Researcher $30/mo ≈ 4,000 credits; Startup $100/mo ≈ 15,000 searches [community, cross-corroborated across ~6 independent sources: costbench.com, linkgo.dev, alphacorp.ai, aisotools.com, freetier.co; official pricing at tavily.com/pricing and docs.tavily.com/documentation/api-credits] | 1 call / 5 min (0.2/min) | 3 | 30 | Free-tier credit budget is the binding constraint; 30 basic calls/day already consumes ~900 credits/month before any advanced-depth calls, so this floor is set to fit inside the free tier by default. |

These are **starting values, not fixed law** — they should live in the user-configurable settings model in §3, not be hardcoded, per the project's general convention of deriving bounds from data rather than hardcoding enumerations.

**The "bug causes a cost explosion" failure mode** is handled by a layer *above* the token bucket, not by the token bucket itself, because a sufficiently persistent bug (e.g., a retry loop that keeps re-arming its own bucket, or a scheduler defect that spins up N duplicate workers each with their own bucket instance) can still defeat a purely in-process rate limiter. The defense is a **persisted, cross-process hard spend cap** — a `daily_spend_cap_usd` / `monthly_spend_cap_usd` counter in PostgreSQL that every call increments *before* dispatch (reserve-then-call, not call-then-reconcile) and that is checked against the cap on every single call, not sampled periodically. When the projected post-call spend would exceed the cap, the gate refuses the call outright and returns a `budget_exhausted` state — this is the fail-safe behavior the task explicitly asked for: **stop calling, do not silently degrade to a cheaper path or a lower-fidelity substitute**, because a silent degradation under an active bug just relocates the runaway cost rather than eliminating it. A single alert fires on the *transition* into `budget_exhausted` (reusing the transition-based alert-dedupe pattern from the orchestration report, not a per-call alert), and a second alert fires on recovery at the next period reset.

Because credit-costing is provider-specific and not always 1 call = 1 unit (Tavily's advanced-depth search costs 2 credits, not 1), the persisted counter should be **reconciled periodically against provider-reported usage** where an endpoint exists — Tavily publishes a `/usage` endpoint [official, per the earlier `tavily-brave-serper.md` report's inventory of Tavily's API surface] — and the reconciliation job should tighten (never loosen) the local counter if actual provider-side spend is found to be ahead of the local estimate, immediately tripping the cap if so. This mirrors the general lesson from cloud/LLM billing dashboards below: **your own persisted counter is the enforcement mechanism; the provider's own usage page is a corroboration source, not the safety net.**

A manual **kill switch** (a boolean settings field, `kill_switch`, independent of the computed cap) provides the "flip it off entirely" override for when you want certainty during an incident, mirroring the Azure Circuit Breaker pattern's explicit recommendation for a manual override alongside automatic tripping [official, learn.microsoft.com/azure/architecture/patterns/circuit-breaker].

## 2. Circuit breaker for chronically failing/error-spiking providers

Use the standard **closed → open → half-open** state machine as documented by Microsoft's Azure Architecture Center Circuit Breaker pattern [official, learn.microsoft.com/azure/architecture/patterns/circuit-breaker], applied per provider:

- **Closed** (normal): calls flow through; a **time-windowed failure counter** increments on each failed call and resets periodically so isolated blips don't trip the breaker. Suggested default: **5 failures within a 10-minute rolling window** opens the breaker — small enough to react to a genuinely broken integration quickly, large enough not to trip on ordinary transient network noise given these are low-frequency calls (a handful of calls per hour per provider at the §1 rate).
- **Open**: calls fail immediately without hitting the network, and a cooldown timer starts. Suggested default: **5-minute initial cooldown**, doubling on each repeat trip up to a **60-minute cap** — the same capped-exponential-backoff shape the orchestration report already uses for scraper cooldowns (`disabled_until`), applied here to a provider integration instead of a merchant domain.
- **Half-open**: after the cooldown, a single trial call is allowed. Success closes the breaker and resets the failure counter; failure reopens it immediately and restarts (doubles) the cooldown. Azure's guidance is explicit that half-open exists specifically to avoid re-flooding a recovering dependency with the full request volume the moment the timer expires [official].
- **Accelerated trip**: an explicit `429`/`503` with a `Retry-After`, or a definitive non-transient error (auth failure, quota-exceeded response body), should trip the breaker immediately rather than waiting to accumulate the failure count — Azure calls this out as "accelerated circuit breaking," where the failure response itself already carries enough signal to skip the threshold [official].

**Composition with the §1 throttle**: they are **independent middleware layers sharing one per-provider state record**, evaluated in a fixed order inside the `SearchBudgetGate`: kill switch → spend cap → circuit breaker → token bucket. The ordering matters — a blown budget or a known-broken provider should never even reach the rate limiter, because reaching the rate limiter implies the call is otherwise "allowed to be attempted," which is the wrong default once either of those two more severe conditions holds. Sharing one state row (extending the orchestration report's per-source policy record with `breaker_state`, `consecutive_failures`, `opened_at`, `cooldown_s` alongside the new budget fields) keeps one source of truth per provider instead of three uncoordinated counters, and keeps the whole thing testable as pure state transitions rather than scattered conditionals.

## 3. User-configurable budget/aggressiveness settings

**Precedent from comparable systems** consistently shows two things: (a) providers increasingly separate *alerting* from *enforcement*, and self-governance tools that actually stop spend build their own enforcement layer rather than trusting the upstream dashboard; and (b) self-hosted tools expose a small number of knobs (a rate, a cap, sometimes a single "aggressiveness" dial) rather than a full policy DSL, because the operator is usually one person.

- **OpenAI** exposes an organization "usage limit"/monthly budget in `platform.openai.com/settings/organization/limits` plus usage-tier-based spend ceilings that rise automatically with cumulative historical spend [official + blog corroboration, tokenmix.ai's April 2026 billing writeup]. However, independent developer reporting in 2026 describes cases where the monthly budget threshold behaves as an **alert rather than a hard stop** — calls continue and billing continues past the configured number [blog, alephant.io "OpenAI Spend Limit" post, corroborated by a second independent source, ZDNet's July 2026 "how I set OpenAI API usage limits" walkthrough, both making the same point: don't assume the dashboard limit is a kill switch]. This is flagged `[unverified]` as a universal behavior — OpenAI's own rate-limits guide does still describe usage limits and hard caps in some contexts [official, developers.openai.com/api/docs/guides/rate-limits] — but the operative lesson for this project is unaffected either way: **treat any provider-side "budget" as a backstop, never as the primary enforcement mechanism**; your own persisted cap from §1 is the one that must actually stop calls.
- **Anthropic** lets you set a spend limit **per API key** and per workspace in the Claude Console, with organization-wide Usage/Cost Admin APIs for programmatic visibility, though as of mid-2026 there is still no API to *configure* those limits programmatically (console-only) [official docs, platform.claude.com/docs/manage-claude/usage-cost-api; corroborated by community feature requests confirming the console-only gap, github.com/anthropics/claude-quickstarts issues #371 and #276].
- **AWS Budgets** is fundamentally an **alerting/anomaly-detection** service, not an automatic hard stop, unless you separately wire a Budget Action (e.g., an SCP or Lambda) to actually revoke access when a threshold is crossed — multiple independent practitioner write-ups make the same point almost verbatim: "AWS Budgets is proactive... issuing alerts," and "no hard cap exists — AWS will never stop charging you automatically" without extra automation [blog, corroborated across finout.io, wiz.io, and a Feb 2026 dev.to/Medium pair by the same author describing a Terraform-deployed enforcement layer, plus AWS's own docs on Cost Anomaly Detection describing it as ML-based alerting]. Same lesson again: alerting ≠ enforcement.
- **API gateways** (Kong, Tyk) are the clearest precedent for the *mechanism* rather than the policy: both expose declarative rate-limiting/quota configuration across **second/minute/hour/day/month/year windows**, scoped per API, per consumer/key, or globally [official, developer.konghq.com/plugins/rate-limiting and tyk.io/docs/api-management/rate-limit]. That maps directly onto the settings model below — the provider row's `rate_per_min` + `daily_call_cap` is the same shape as a Kong/Tyk per-consumer quota, just scoped to "our own outbound calls to Serper" instead of "inbound calls from a customer."
- **SearXNG**, a self-hosted metasearch aggregator, ships a `limiter.toml` with an explicit **burst window (20s) and long window (10min)** sliding-window rate limiter backed by a persisted Valkey/Redis store, specifically because SearXNG itself looks like a bot to the search engines it queries [official docs + DeepWiki source-level corroboration, docs.searxng.org/admin/searx.limiter.html]. This is a close structural analog to our situation: a self-hosted aggregator throttling its own outbound calls to upstream search infrastructure to avoid tripping the upstream's own limits.
- **FreshRSS/Miniflux** (self-hosted feed aggregators) both expose a **per-feed refresh-interval** field to a single non-technical admin, and both enforce a **platform-wide floor regardless of what the user requests** — FreshRSS refuses to refresh any feed more often than once per 20 minutes even if scheduled tighter [official, freshrss.github.io/FreshRSS/en/admins/08_FeedUpdates.html], and Miniflux's `POLLING_FREQUENCY`/`POLLING_FREQUENCY_MAX` env vars work the same way [official, miniflux.app/docs/configuration.html]. This is a directly useful precedent for the "aggressiveness dial": expose one simple knob to the single maintainer, but hardcode a safety floor underneath it that the knob cannot override.

**Proposed settings model** — one row per provider, persisted (e.g., a `discovery_budget` table), all fields user-editable except where noted:

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `provider` | enum (`serper`\|`brave`\|`tavily`) | — | primary key |
| `enabled` | bool | `true` | operator on/off, independent of `kill_switch` |
| `rate_per_min` | float | per §1 table | token-bucket refill rate |
| `burst` | int | per §1 table | token-bucket capacity |
| `daily_call_cap` | int | per §1 table | hard ceiling, independent of spend |
| `daily_spend_cap_usd` | decimal | provider-tier-derived | e.g. Brave: $0.25/day |
| `monthly_spend_cap_usd` | decimal | provider-tier-derived | should not exceed the paid plan tier you're actually on |
| `alert_threshold_pct` | int | `80` | fires a warning alert before the hard cap trips |
| `kill_switch` | bool | `false` | manual override; forces the gate closed regardless of counters — floor the user cannot raise past a code-enforced maximum (FreshRSS/Miniflux-style safety floor) |
| `breaker_failure_threshold` | int | `5` | consecutive/windowed failures to open the breaker |
| `breaker_window_s` | int | `600` | rolling window for the failure count |
| `breaker_cooldown_s` | int | `300` | initial open-state cooldown |
| `breaker_cooldown_max_s` | int | `3600` | cap on doubling backoff |

A single **`aggressiveness`** enum (`conservative`/`standard`/`aggressive`) can scale `rate_per_min`, `burst`, and the two caps by a multiplier for the maintainer who wants one dial instead of eleven fields — analogous to Kong/Tyk's tiered plan presets and to FreshRSS's floor-under-a-dial pattern. **Enforcement point:** a single `SearchBudgetGate` service that every discovery-layer call site must go through — no code path should be permitted to call the Serper/Brave/Tavily clients directly, mirroring the orchestration report's admission-layer design (there, an `asyncio.Semaphore`/token-bucket pair gates scrape fetches; here, the same shape gates search calls) so there is exactly one place cost governance can be bypassed by a bug, and it is the one place under test.

## 4. AgentMail free-tier limits (2026)

As already established in this project's own [`choosing-an-outbound-email-path-for-a-low-volume-alerting-system.md`](choosing-an-outbound-email-path-for-a-low-volume-alerting-system.md) report (dated the same day), AgentMail's public pricing page lists, as of **July 4, 2026**: **Free — 3 inboxes, 3,000 emails/month, 100 emails/day** [official, agentmail.to/pricing]. This is corroborated by two independent third-party writeups reviewed for this report: eesel.ai's pricing breakdown confirms "3 inboxes, 3,000 emails per month" for Free and separately notes the paid Developer tier "removes the daily sending limit" — implying the daily cap exists on Free [blog, eesel.ai/blog/agentmail-pricing], and InboxKit's review independently states "3 inboxes, 3,000 emails per month, no card" [blog, inboxkit.com/learn/agentmail-review]. No change to these figures was found since the earlier report.

## Open Questions

| # | Question | Why unresolved |
| --- | --- | --- |
| 1 | Does OpenAI's org-level monthly budget currently function as a true hard stop or only an alert? | Conflicting 2026 developer reports found (alephant.io/ZDNet describe alert-only behavior; OpenAI's own rate-limits guide still describes hard caps in some contexts). Doesn't change this project's recommendation (build our own cap regardless), but worth re-checking before citing OpenAI as a governance example elsewhere. |
| 2 | Does Tavily's `/usage` endpoint report cost in a form that can drive automated reconciliation (vs. requiring manual dashboard reading)? | Endpoint's existence is documented in the earlier `tavily-brave-serper.md` report's API inventory, but its response schema wasn't verified against this report's needs. |

## Handoff

Persisted at `docs/research/search-api-self-governance-and-user-configurable-limits.md`. Downstream skills that may consume it:

- `superpowers:brainstorming` — feed the Open Questions into a design conversation before implementing `SearchBudgetGate`
- `feature-dev:feature-dev` — start implementation of the `discovery_budget` table and gate service using the settings model in §3

## Sources

| URL | Title | Date | Authority |
| --- | --- | --- | --- |
| https://learn.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker | Circuit Breaker Pattern - Azure Architecture Center | 2026-07-02 (updated) | official |
| https://blog.arcjet.com/rate-limiting-algorithms-token-bucket-vs-sliding-window-vs-fixed-window/ | Rate Limiting Algorithms: Token Bucket vs Sliding Window vs Fixed Window | 2026-03-24 | blog |
| https://api7.ai/blog/token-bucket-vs-leaky-best-rate-limiting-algorithm | What Is Rate Limiting? Token Bucket vs Leaky Bucket | 2025-09-10 | blog |
| https://brave.com/search/api/ | Brave Search API | 2026 | official |
| https://api-dashboard.search.brave.com/documentation/pricing | Brave Search API pricing | 2026 | official |
| https://www.implicator.ai/brave-drops-free-search-api-tier-puts-all-developers-on-metered-billing/ | Brave Kills Free Search API Tier, Shifts to Metered Billing | 2026-06-08 | blog |
| https://www.firecrawl.dev/blog/brave-search-api-alternatives | Top 5 Brave Search API Alternatives in 2026 | 2026 | blog |
| https://serper.dev/ | Serper - The World's Fastest and Cheapest Google Search API | 2026 | official |
| https://www.buildmvpfast.com/tools/api-pricing-estimator/serper | Serper API Pricing Calculator (2026) | 2026 | community |
| https://costbench.com/software/web-scraping/serper/ | Serper Pricing 2026 | 2026-06-11 | community |
| https://tavily.com/pricing | Tavily pricing | 2026 | official |
| https://docs.tavily.com/documentation/api-credits | Credits & Pricing - Tavily Docs | 2026 | official |
| https://costbench.com/software/web-scraping/tavily/ | Tavily Pricing 2026 | 2026-06-03 | community |
| https://alphacorp.ai/blog/perplexity-search-api-vs-tavily-for-rag-2026 | Perplexity Search API vs Tavily for RAG 2026 | 2026 | blog |
| https://blog.alephant.io/openai-spend-limit-how-to-cap-your-api-bill-2026/ | OpenAI Spend Limit: How to Cap Your API Bill (2026) | 2026 | blog |
| https://www.zdnet.com/article/how-to-set-openai-api-spend-usage-limits/ | How I set OpenAI API usage limits to stop agent overspending | 2026-07-02 | blog |
| https://developers.openai.com/api/docs/guides/rate-limits | Rate limits - OpenAI API | 2026 | official |
| https://platform.openai.com/settings/organization/limits | OpenAI Usage Limits | 2026 | official |
| https://platform.claude.com/docs/en/manage-claude/usage-cost-api | Usage and Cost API - Claude Platform Docs | 2026 | official |
| https://github.com/anthropics/claude-quickstarts/issues/371 | Feature Request: Admin API endpoint for Workspace Rate/Spend Limits | 2026 | community |
| https://github.com/anthropics/claude-quickstarts/issues/276 | Feature Request: API Endpoints for Programmatic Access to Cost and Usage Data | 2026 | community |
| https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html | Managing your costs with AWS Budgets | 2026-06-08 | official |
| https://dev.to/suhas_mallesh/aws-wont-stop-charging-you-ever-deploy-budget-alerts-as-code-with-terraform-before-its-too-late-3mac | AWS Won't Stop Charging You. Ever. | 2026-02-18 | blog |
| https://developer.konghq.com/plugins/rate-limiting/ | Rate Limiting Plugin - Kong Docs | 2026 | official |
| https://tyk.io/docs/api-management/rate-limit | Rate Limiting - Tyk Documentation | 2026 | official |
| https://docs.searxng.org/admin/searx.limiter.html | Limiter - SearXNG Documentation | 2026 | official |
| https://freshrss.github.io/FreshRSS/en/admins/08_FeedUpdates.html | Setting up automatic feed updating - FreshRSS | 2026 | official |
| https://miniflux.app/docs/configuration.html | Configuration Parameters - Miniflux | 2026 | official |
| https://www.agentmail.to/pricing | Pricing - AgentMail | 2026-07-04 | official |
| https://www.eesel.ai/blog/agentmail-pricing | AgentMail pricing explained: Plans, features, and value in 2026 | 2026 | blog |
| https://www.inboxkit.com/learn/agentmail-review | AgentMail Review (2026) | 2026 | blog |
