---
schema_version: '1.1'
id: per-source-polling-cadence-and-skip-policy
title: Per-Source Polling Cadence, Adaptive Back-Off, and Skip Policy for a 20-Marketplace Drive Price Monitor
description: Concrete per-tier poll cadence (baseline/ceiling), an adaptive back-off ladder keyed to HTTP 429/503/soft-block/latency signals, and a tier-ladder skip decision tree, grounding "aggressive but self-moderating" acquisition in eBay Browse/Feed and Amazon SP-API published rate limits plus current AWS/RFC retry guidance.
doc_type: research
status: active
created: '2026-07-04'
updated: '2026-07-04'
reviewed: null
owner: chris
tags:
- web-scraping
- rate-limiting
- ebay-api
- amazon-sp-api
- backoff
- circuit-breaker
- polling-cadence
aliases: []
related:
- orchestration-choice-for-a-single-vm-price-polling-service
- pragmatic-architecture-for-low-volume-python-e-commerce-scraping
- us-scraping-and-data-retention-landscape-for-a-retail-hdd-price-monitor
- automated-test-policy-for-a-low-volume-scrapy-price-monitor
source: []
confidence: high
visibility: private
license: null
---

# Per-Source Polling Cadence, Adaptive Back-Off, and Skip Policy for a 20-Marketplace Drive Price Monitor

## Bottom line

"Aggressive but self-moderating" (the spec's **Moderate Aggressive Usage** principle, [`hw-radar.md:21`](../archived/hw-radar.md)) should not be encoded as one fixed number. It should be encoded as **a baseline cadence per source tier, a hard ceiling per tier that the system never exceeds even when a source tolerates more, and an auto-ramp that walks from baseline toward ceiling only while the source stays clean** — with any 429/503/soft-block signal collapsing the interval back down through the same back-off ladder the orchestration research already designed (two-level token buckets, `next_run_at` as the recovery mechanism, not tight retry loops). That structure is what makes "real-time where tolerated, moderate only at the red line" concrete rather than aspirational.

For the ~20 sources in [`hw-radar.md`'s marketplace table](../specs/hw-radar-master-spec.md#c1-external-data-integration), only **eBay's Browse/Feed APIs** carry a published, checkable rate limit; everything else — manufacturer recert stores, storage-specialist resellers, refurb-server sellers, Newegg, and Amazon's own product pages — is unpublished HTML/JSON-LD scraping, where the only legitimate ceiling is self-imposed politeness plus the empirically observed back-off ladder. **Amazon's SP-API is out of scope entirely** (already settled in [OQ7](../resolved-questions.md#oq7--running-cost-budget-model-build-time-pricing-pass)/the retention research: it requires an authorized seller account hw-radar's owner does not have) — its published rate limits are cited below only to close out the research prompt's explicit ask, not because they're usable.

## Per-source / per-tier cadence table

Cadence is expressed as **baseline** (where a new or just-recovered source starts) and **ceiling** (the fastest the auto-ramp is ever allowed to reach, regardless of how tolerant the source appears). The ramp rule and back-off ladder are shared across all tiers and defined in the next two sections.

| Tier | Sources (from the spec's marketplace table) | Baseline | Ceiling | Basis |
| --- | --- | --- | --- | --- |
| **T0 — Official API, published quota** | eBay (Browse API search + `getItems`; Feed API if/when approved) | 10 min per active watch | 2 min per active watch | eBay's own daily quotas (below) comfortably support this without ever approaching the limit; no politeness inference needed — the ceiling is a self-imposed sanity cap, not the API's actual limit |
| **T1 — Manufacturer-direct, low anti-bot posture** | Western Digital Store/Recert, Seagate Store/Recert | 30 min | 5 min | Spec ranks these "Very high" trust; manufacturer storefronts are typically Shopify/Magento-class platforms with JSON-LD/first-party JSON (structured-data-first extraction, see [`pragmatic-architecture…`](pragmatic-architecture-for-low-volume-python-e-commerce-scraping.md)) and no documented anti-bot stack — the best candidates for "as aggressive as tolerated" |
| **T2 — Storage-specialist / VAR resellers, high trust** | ServerPartDeals, B&H Photo Video, CDW, Insight, goHardDrive | 1 h | 15 min | Spec ranks "High"/"Medium-high"; smaller commerce platforms, generally no enterprise anti-bot stack, but unpublished limits — ramp is earned, not assumed |
| **T3 — General marketplace/retailer, known anti-bot exposure** | Newegg, Amazon (product-page scrape path only — API is out of scope), PCNation, Wiredzone | 2 h | 30 min | Newegg's developer API is seller/Marketplace-side only (not a consumer catalog feed) and Amazon pages sit behind the most aggressive commercial anti-bot stacks of any target on the list — floor stays conservative even though these are high-value listings |
| **T4 — Refurb-server / regional / lower-priority resellers** | TechMikeNY, ETB Technologies, Bargain Hardware, HardDrivesDirect, ServerMonkey, SaveMyServer, The Server Store, Memory4Less | 4 h (single-digit daily checks) | 1 h | Spec ranks "Medium" to "Low-medium" trust/priority; this tier is the literal floor the prior research (`pragmatic-architecture…`) recommended as the *only* number for the whole set — kept as the baseline for the least-important sources, not the ceiling for everyone |

**Compliance floor, not a politeness ceiling:** eBay's own retention rule requires **displayed item listing data be refreshed at least every 6 hours** ([`us-scraping-and-data-retention-landscape…`](us-scraping-and-data-retention-landscape-for-a-retail-hdd-price-monitor.md)). That is a *minimum* refresh obligation for anything already displayed to the user, independent of and much looser than T0's 10-minute baseline — it only matters as a safety net if T0 ever falls back to a degraded cadence.

**Auto-ramp rule** (shared, all tiers): after **N consecutive clean polls** (default `N = 4`) with no error, no soft-block signal (below), and fetch latency within 2× the source's rolling median, halve the current interval, floored at the tier ceiling. Any single throttle or soft-block signal resets the interval to the tier baseline and hands control to the back-off ladder below — the ramp does not resume until the ladder's cooldown clears and clean polls accumulate again. This is the concrete form of "poll as aggressively as tolerated, moderate only at the red line": the system spends most of its life either ramped up against a ceiling it has earned, or backed off from one it just tripped, never guessing in between.

## Official API rate limits (grounding for T0, and why Amazon SP-API is excluded)

### eBay Browse and Feed APIs (current, verified against `developer.ebay.com`)

| API / resource | Published default limit | What it means for cadence |
| --- | --- | --- |
| **Browse API** — all methods except `getItems` (i.e., `search`) | **5,000 calls/day** per application | ≈208 calls/hour sustained. A 10-minute baseline sweep per watch uses 144 calls/day per watch — dozens of concurrent watches fit inside the default quota without a growth-check request |
| **Browse API** — `getItems` | **5,000 calls/day** per application (separate bucket from `search`) | `getItems` accepts a batch of item IDs per call, so refreshing many already-discovered listings costs far fewer calls than one-per-listing; use this bucket for price/availability refresh of known listings, keep `search` for discovery |
| **Feed API (Buy, Beta)** — `item`, `item_group`, `item_priority` resources | **10,000 calls/day** | Bulk category/day feed files — a fundamentally different acquisition shape (daily snapshot download, not per-item polling); useful if Feed API access is ever granted (it's a Limited Release API requiring business-unit approval), not assumed for v1 |
| **Feed API (Buy, Beta)** — `item_snapshot` resource | **75,000 calls/day** | Same caveat as above |
| **Feed v1 API** | **75,000 calls/day** | Same caveat |
| OAuth token endpoint | Separate daily cap, tracked via the Analytics API `getRateLimits` | Not a v1 concern at this call volume; worth wiring the `x-amzn`-style eBay rate-limit telemetry (eBay's Analytics API `rate_limit` resource) into the health dashboard so growth-check timing is visible before a limit is ever hit |

Source: [eBay Developers Program — API Call Limits](https://developer.ebay.com/develop/get-started/api-call-limits) (re-verified 2026-07-04); [Feed Beta API Overview](https://developer.ebay.com/api-docs/buy/feed/static/overview.html); [Access token rate limits](https://developer.ebay.com/api-docs/static/oauth-rate-limits.html). If any bucket is ever close to being exhausted, eBay's free **Application Growth Check** process (self-service quota-increase request tied to demonstrating efficient call patterns) is the correct escalation path — not switching to scraping eBay's own site, which the current User Agreement's anti-automation clause forbids without prior written permission ([`us-scraping-and-data-retention-landscape…`](us-scraping-and-data-retention-landscape-for-a-retail-hdd-price-monitor.md)).

### Amazon SP-API (cited for completeness — confirmed out of scope)

Amazon's Catalog Items API uses a token-bucket usage plan with genuinely fast published rates — e.g. Catalog Items API v2022-04-01 `getCatalogItem` is **2 requests/second per account-application pair** (250/sec per application, burst 2), `searchCatalogItems` is **2/sec per account-application pair** (500/sec per application, 50/sec for keyword search, burst 2). Source: [SP-API Catalog Items API Rate Limits](https://developer-docs.amazon.com/sp-api/docs/catalog-items-api-rate-limits), [Usage Plans and Rate Limits](https://developer-docs.amazon.com/sp-api/docs/usage-plans-and-rate-limits) (both re-verified 2026-07-04). Those numbers are **moot for hw-radar**: every SP-API operation's rate limit is scoped **per selling-partner account**, and SP-API requires an authorized seller account to call at all — it is not a public catalog/price feed a buyer-side monitor can use, which is exactly what the retention research already concluded ("SP-API is **not usable** for a cross-retailer public price monitor by a non-seller"). This report doesn't change that; it only confirms the numbers a reader might otherwise wonder about.

Amazon product pages themselves therefore stay in **T3** (scrape path), governed by the general cadence/back-off rules below, not by any Amazon-published rate limit — because there isn't one that applies to this use case.

## Adaptive back-off ladder

The orchestration research already designed the right shape: a **small in-run retry budget** for obvious transients, then let the **next scheduled poll time** absorb the real recovery curve, using capped exponential backoff with jitter — never a tight retry loop against a source that just said "slow down." This section supplies the concrete numbers.

### Signal → action → cooldown

| Signal | What it means | Immediate action | Cooldown before next attempt |
| --- | --- | --- | --- |
| **Connect/read timeout, DNS failure** | Transient network issue, not the source objecting | One in-run retry, short delay | `random(0,1) × min(10 s, 1 s × 2^retry)` — full-jitter, 1 in-run retry only, then fall through to the next scheduled poll if it still fails |
| **HTTP 429 with `Retry-After`** | Explicit, source-specified throttle | Stop polling this source immediately | Honor `Retry-After` verbatim, clamped to a floor of 1 s (guards against a malformed/zero header) and a ceiling of the tier's baseline interval (never let a source dictate a *longer* wait than the tier already assumes) |
| **HTTP 429/503 without `Retry-After`** | Throttle or overload, unspecified duration | Stop polling this source; reset ramp counter | `random(0,1) × min(24 h, 10 min × 2^consecutive_failures)` — same full-jitter exponential shape AWS's current SDK retry standard uses for throttling errors, rescaled from API sub-second retries to a scraper's minutes-to-hours cadence. The **24 h cap is deliberate**: it equals the original conservative "single-digit daily checks" research floor, so the worst-case degraded state for any source is exactly the baseline this whole design started from — never worse |
| **Soft-block (see detection heuristics below)** | Anti-bot system engaged, but didn't say so via status code | Treat identically to a 429 without `Retry-After` — same ladder, same 24 h cap | As above |
| **Latency spike** (fetch time > 3× the source's rolling median for 3 consecutive polls) | Early warning of a struggling or newly-protected origin, before it starts hard-blocking | Halve current cadence (not a full back-off) and flag for review | No cooldown yet — this is a *slow-down*, not a *stop*; if a hard signal (429/503/soft-block) follows, escalate to the full ladder above |

**Reset:** the ramp-up rule (4 consecutive clean polls) applies uniformly whether recovering from a timeout, a 429, or a soft-block — there is one recovery path, not a different one per signal type.

**Escalation past the ladder — `paused_pending_fix` vs. permanent skip:** if a source's cooldown reaches the 24 h cap and the *next* scheduled attempt still fails with the same signal class, that source moves to `paused_pending_fix` (mirrors the orchestration research's circuit-breaker rule: same terminal failure class repeating past retries → stop scheduling normally, alert once). A parser-rot failure (schema/layout drift, not a block) is a `paused_pending_fix` code-fix item; a persistent anti-bot/soft-block failure is instead the trigger for the **skip-policy decision** below, because more waiting will not fix an access-technique mismatch — see [`automated-test-policy-for-a-low-volume-scrapy-price-monitor.md`](automated-test-policy-for-a-low-volume-scrapy-price-monitor.md) for the parser-rot-vs-anti-bot classification tree this reuses.

### Soft-block detection heuristics

A soft block is any response that is technically "successful" (HTTP 200) but is not the page you asked for — the highest-risk failure mode because it can silently poison scored data instead of loudly failing. Treat a fetch as soft-blocked when **any** of the following hold, drawing on current anti-bot documentation (Cloudflare JA3/JA4 TLS fingerprinting, DataDome/HUMAN behavioral+device telemetry) and current scraping-API vendor guidance that explicitly warns against trusting status code alone:

- **Structured-data absence**: the extraction-tier canary (already specified in OQ8's test policy) expects a `Product`/`Offer` JSON-LD block, a platform JSON endpoint, or a specific DOM anchor, and none is present in an otherwise-200 response.
- **Body-size outlier**: response body length is a statistical outlier (e.g., < 20% of the source's rolling median page size) — the classic signature of a challenge/interstitial page replacing real content.
- **Known challenge markers**: presence of vendor-specific challenge indicators (Cloudflare `cf-mitigated`/challenge scripts, reCAPTCHA/Turnstile markup, "Access Denied," "Please verify you are a human," or a redirect to a challenge subdomain).
- **Repeated identical hash**: the same content hash returned across multiple distinct requests where the underlying listing state is known to have changed (price/stock elsewhere confirms movement) — a sign the source is serving a cached/blocked stand-in rather than the live page.

Any one of these reclassifies the fetch as failed for scheduling purposes even though the HTTP layer reported success, and feeds the same signal → action → cooldown table above.

## Skip policy: the tier-ladder cutoff

The acquisition ladder, per source, is: **official API → structured data (JSON-LD / platform JSON endpoint / hidden bootstrap JSON) → HTTP-fingerprint fallback (`curl_cffi`) → headless browser (Playwright, selective) → managed unblocker API (small hard-target tail only) → SKIP.** This is the same ladder [`pragmatic-architecture-for-low-volume-python-e-commerce-scraping.md`](pragmatic-architecture-for-low-volume-python-e-commerce-scraping.md) already recommends; what this report adds is *when* to move a rung, expressed against the back-off signals above.

```text
Is a compliant official API available for this source?
├── Yes (eBay Browse/Feed) → use it. Rate-limit against the published quota (T0 above); never fall back to
│   scraping the source's own site to route around the API — that trades a documented quota for a ToS
│   violation (eBay's anti-automation clause) for no acquisition benefit.
└── No official API, or API is scoped to a role we don't have (Amazon SP-API: seller-only)
    └── Does the raw HTML/first response already contain the needed fields (JSON-LD, platform JSON,
        hidden bootstrap JSON)?
        ├── Yes → this is the default, steady-state path for nearly every recert specialist and reseller
        │   on the spec's list. Poll at the tier cadence above.
        └── No → is the gap a TLS/HTTP-fingerprint mismatch only (plain HTTP blocked, but the underlying
            endpoint is still non-JS)?
            ├── Yes → try `curl_cffi` as a narrow fallback before reaching for a browser.
            └── No, the page is genuinely JS-assembled or interaction-gated
                └── Is the source's protection level still "ordinary JS rendering," not a hardened
                    anti-bot stack?
                    ├── Yes → selective Playwright (via `scrapy-playwright`), scoped to just this source.
                    └── No — the source requires challenge-passing, persistent device telemetry, heavy
                        proxy rotation, or CAPTCHA-solving to work *routinely* (not as a rare one-off)
                        └── Is this one of a small number of very-high-value targets where a managed
                            unblocker API's cost is still justified?
                            ├── Yes → managed API (Zyte/ScraperAPI/ZenRows) for that source only —
                            │   the declared exception, not the default architecture.
                            └── No → SKIP. Mark the source inactive in the registry; do not build routine
                                CAPTCHA-solving, stealth, or proxy-rotation infrastructure for it.
```

**When a currently-working source crosses the line into SKIP territory** (as opposed to a source that was never reachable): this is the escalation trigger from the back-off ladder above — a source whose cooldown has repeatedly maxed out at 24 h with a *soft-block* signal (not a parser-rot signal) is the concrete, measured version of "requires evasion to be routine." At that point, try the **next** rung up the ladder first (e.g., a source that suddenly needs `curl_cffi` where plain HTTP used to work is not yet a SKIP candidate — that's a normal escalation). Only mark **SKIP** once the ladder has been exhausted up to (but not including) the CAPTCHA-solving/stealth/heavy-proxy-rotation rung, consistent with the declared hard-stop: *"if it needs residential rotation/CAPTCHA solving to be routine, stop."*

**Legal/ToS triggers that force SKIP regardless of technical feasibility** (from [`us-scraping-and-data-retention-landscape-for-a-retail-hdd-price-monitor.md`](us-scraping-and-data-retention-landscape-for-a-retail-hdd-price-monitor.md), independent of the back-off ladder): a source sends a cease-and-desist; a source's ToS is amended to expressly prohibit this workflow; a source moves the needed data behind a login wall; a source offers a paid data feed that is a realistic substitute. None of the 20 sources in the current spec table are known to be in this state as of 2026-07-04 — eBay's own site-scraping prohibition is moot because eBay is accessed via its API, not scraped; the recert specialists and resellers carry no known anti-automation clause; Newegg's developer program is seller-side and simply isn't used for buyer discovery.

**Pause vs. skip, restated for the registry:** `paused_pending_fix` is temporary and code-owned (parser broke, will be fixed) — keep a low-frequency recovery probe (e.g., once/day) so the source resumes automatically once fixed. **Permanent skip** is a source-registry state change (technique exhausted short of the hard-stop rung, or a legal/ToS trigger fired) — it stops being polled at all until a human re-reviews it; it is not retried automatically.

## Reconciliation note

This report answers [OQ9](../resolved-questions.md#oq9--acquisition-cadence-throttle--skip-policy)'s three open forks (per-source cadence, adaptive back-off thresholds, skip cutoff) with concrete numbers. It does not itself edit `open-questions.md` — that reconciliation (moving OQ9's substance to Resolved, and updating the Features section if the cadence table changes anything load-bearing there) is left as a follow-up, per the doc's own maintenance rule that only the owner/orchestrating session moves items between Open and Resolved.
