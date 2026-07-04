---
schema_version: '1.1'
id: 2026-07-04-polling-cadence-reconciliation
title: 'Polling Cadence & Inventory Volatility — Reconciliation of Two Parallel Research Runs'
description: Consolidates two independent parallel research runs (qdev/Brave+Serper and ChatGPT Deep Research) on per-source inventory volatility and cheap availability-signal affordance for hw-radar. Records where they converged (settled), the one genuine contradiction (ServerPartDeals volatility) and its dated resolution, each run's unique contributions, and the reconciled design position (per-source freshness-SLO reframing of FR-001, the volatility scheduling axis, the fast-lane starting set, and the availability-heartbeat data grain). Supersedes neither source report; both remain the evidence base.
doc_type: research
status: active
created: '2026-07-04'
updated: '2026-07-04'
reviewed: null
owner: chris
tags:
- inventory-volatility
- polling-cadence
- freshness-slo
- availability-heartbeat
- fast-lane
- reconciliation
aliases:
- polling cadence reconciliation
- volatility research consolidation
related:
- 2026-07-04-per-source-inventory-volatility-and-fast-lane-polling
- per-source-polling-cadence-and-skip-policy
- programmatic-acquisition-research-for-enterprise-and-nas-drive-merchants
source: []
confidence: medium
visibility: private
license: null
---

# Polling Cadence & Inventory Volatility — Reconciliation of Two Parallel Research Runs

## What this is

On 2026-07-04 the same scoping brief (research prompt #15) was run through **two independent paths** to cross-check each other before any of it entered the spec:

- **qdev / `qdev-researcher`** — Sonnet, Brave + Serper recall (Tavily MCP was unavailable that session). Report: [`2026-07-04-per-source-inventory-volatility-and-fast-lane-polling.md`](2026-07-04-per-source-inventory-volatility-and-fast-lane-polling.md).
- **ChatGPT Deep Research** — separate model, separate search corpus. Report: [`hardware-radar-polling-cadence.md`](hardware-radar-polling-cadence.md).

This document is the consolidation. It does **not** supersede either source report — both remain the cited evidence base. It records what is now settled (both agree), the one genuine contradiction and how it was resolved, what each run uniquely contributed, and the reconciled design position to fold into the spec.

The scope boundary from prompt #15 holds throughout: this is only about **(a) how volatile each source is** and **(b) whether it exposes a cheap no-render availability signal**. Rate-limit ceilings and anti-bot posture are already settled in [`per-source-polling-cadence-and-skip-policy.md`](per-source-polling-cadence-and-skip-policy.md) (OQ9) and are not re-derived.

## Bottom line

Two independent research paths — different model, different search corpus — **converged hard**. There was exactly **one** genuine contradiction (ServerPartDeals volatility), now resolved with a dated rationale. The organizing finding both paths reached, one explicitly and one implicitly, is that **inventory volatility and cheap-signal availability are anti-correlated** across hw-radar's source set: the burstiest sources (WD/Seagate direct recert) have no confirmed cheap signal, and the sources with the cleanest cheap signal (Shopify specialists) are the least bursty. The practical consequence: a blanket "fast-lane tier" is mostly unbuildable where it would matter most, so fast-lane membership is a **per-source** question, not a scheduling toggle. The one source that is natively both drop-prone and cheap is **eBay's own manufacturer recert storefronts**, because the Browse API is already the cheap heartbeat.

## 1. Convergence — settled (both runs agree, high confidence)

| Finding | Status |
| --- | --- |
| **Fast-lane = the _intersection_** of drop-prone AND cheap-signal; that set is narrow | ✅ settled |
| **Fast-lane is a per-source question, not a tier** (the anti-correlation) | ✅ settled |
| **eBay Browse API is its own cheap heartbeat**; broad eBay search is _churning_ (saved-search deltas, dedupe by `itemId`); only seller-scoped official recert stores are fast-lane | ✅ settled |
| **Shopify `/products.json` / `/products/<handle>.js` → variant `available` + price** is the canonical cheap mechanism | ✅ settled |
| **Key the heartbeat at the variant/SKU grain**, never a product-level rollup | ✅ settled |
| **CDN cache TTL is a floor** on achievable freshness → conditional requests (`ETag`/`Last-Modified`) + a slow **repair crawl for every source**, fast-lane included | ✅ settled |
| **Amazon / Newegg = churning, no cheap consumer stock signal, do not fast-poll** | ✅ settled |
| **Business VARs (CDW/Insight/SHI/Provantage) = stable** (hours–days; procurement/quote semantics) | ✅ settled |
| **Refurbished-server sellers = stable** (hours–days) except rare one-off lots | ✅ settled |
| **Human decision loop dominates below ~60–90 s** → sub-minute detection is not worth the request cost | ✅ settled |
| **WD direct recert = drop-prone but custom JS, no confirmed cheap signal** → needs an endpoint-recon spike | ✅ settled (spike still owed) |
| **"How fast does a restock clear" is the weakest part of the public record** | ✅ both flagged |

## 2. The one contradiction — ServerPartDeals — and its resolution

| | qdev | ChatGPT Deep Research |
| --- | --- | --- |
| **SPD volatility** | **Churning** — "How often does SPD restock?" thread (2024-12-20) shows gradual days–weeks depletion, no burst | **Drop-prone** — SPD's #1 fast-lane candidate; 2–5 min heartbeat |
| **SPD cheapness** | ✅ Shopify | ✅ Shopify (Shop Pay observed) |

They disagree only on **volatility**, not cost.

**Resolution (owner decision, 2026-07-04): reconciled toward _drop-prone_ → fast-lane at 2–5 min.** The qdev "churning" verdict rests on a **2024-12-20** thread that **predates the 2026 HDD supply/price interruption** visible in the *2026*-dated Seagate threads qdev itself cited (e.g. the ~3-minute 28 TB sellout). Under current market conditions SPD recertified enterprise stock is deal-sensitive and clears quickly, so it is treated as drop-prone. Independently, the cheap Shopify signal makes a 2–5 min heartbeat **low-regret regardless of the classification** — if real transition data later shows churning behaviour, the poller downgrades it with no sunk cost. This is the general resolution pattern for the anti-correlation: **where the signal is cheap, poll fast by default and let observed data downgrade.**

## 3. Complementary contributions (each found what the other missed)

**ChatGPT uniquely added** — fold these in:

- **Amazon PA-API carries a 2026-05-15 deprecation notice → migrate to Creators API.** Fresh, time-sensitive, and it touches an already-"settled" acquisition decision. Escalated in §6 below.
- **Two more cheap-signal platforms:** WooCommerce **Store API** (`GET /wp-json/wc/store/v1/products` → `is_in_stock`, `is_purchasable`, price) and **BigCommerce Storefront GraphQL** inventory. qdev covered only Shopify/Magento.
- **A richer failure-mode list (9 vs 2)** — merged into §5.
- **A concrete two-grain observation model** — `availability_heartbeat_observation` (decision enum `unchanged`/`transition_detected`/`ambiguous`/`failed`) → `offer_snapshot` only on transition. Maps onto ADR-0010. See §4.4.
- **Percentile freshness SLOs (p95/p99)** and a _separate_ tier for **drop-prone-but-no-cheap-signal**.

**qdev uniquely added:**

- **Timestamped sellout evidence** ChatGPT could not find: Seagate $349 28 TB **sold out ~3 min**; "every restock sold out within hours" (both 2026-dated). Partially closes the shared evidence gap — and, importantly, dates the market shift that resolves the SPD contradiction.
- **CDW states a 5-minute internal inventory refresh** — a concrete floor-of-floors for that source; polling any source faster than its own backend refresh buys nothing.
- **Per-source platform fingerprints** (from prior acquisition research): TechMikeNY / SaveMyServer / The Server Store `parts.` = **Shopify**; ETB / ServerMonkey / PCNation = **Magento**; Wiredzone = **Odoo**; goHardDrive = **legacy ASP/HTML**.
- **`changedetection.io`'s restock-detection plugin** as the pattern to imitate for legacy-HTML sources (keyword-based out-of-stock text check on a cheap GET).

## 4. Reconciled design position (to fold into the spec)

### 4.1 Reframe FR-001

Drop the "continuous / near-real-time" wording; state the requirement as a **per-source freshness SLO** (max age of the freshest observation that could trigger an alert, measured transition-to-alert), with four classes below.

### 4.2 Freshness SLO per class

| Class | Freshness SLO (transition→alert) | Note |
| --- | --- | --- |
| **Drop-prone + cheap heartbeat** | **p95 ≤ 3 min, p99 ≤ 7 min** | Matches Seagate's ~3-min real clear time _and_ the T1 cadence ceiling from OQ9 — two independent lines land together |
| **Drop-prone, no cheap signal** | **p95 ≤ 15 min, p99 ≤ 30 min** | Timely but not worth hammering an expensive/anti-bot full-page path |
| **Churning** | **p95 ≤ 15–30 min** (saved queries) / **p99 ≤ 60 min** (broad census) | Aggregate best-price awareness; CDW's 5-min internal refresh is a floor |
| **Stable / VAR / refurb-server** | **p95 ≤ 4–6 h / p99 ≤ 24 h** | Days-timescale movement; hourly rarely changes a purchase outcome |

### 4.3 Second scheduling axis

Add a **volatility profile** (`drop-prone` / `churning` / `stable`) to the per-source registry, orthogonal to the T0–T4 acquisition tier. **Effective cadence = min(tier ceiling, volatility need).** Fast-lane membership = the intersection of `drop-prone` AND a verified cheap signal.

### 4.4 New cheap data grain (candidate ADR)

Introduce `availability_heartbeat_observation` above `offer_snapshot` (extends [ADR-0010](../adr/adr-0010-canonical-data-model.md)): a cheap poll result carrying raw fingerprint, source timestamp, stock/price fields, endpoint metadata, cache headers, and a decision (`unchanged`/`transition_detected`/`ambiguous`/`failed`). The full `fetch → parse → normalize → score → alert` pipeline (producing an `offer_snapshot`) fires only on: OOS→in-stock, in-stock→OOS, material price drop, material warranty/condition/shipping change, new listing/variant ID, or ambiguity after a prior in-stock state. This is a schema-level, hard-to-reverse change → **warrants its own ADR**.

### 4.5 Fast-lane starting set

| Source | Fast-lane | Cadence | Basis |
| --- | --- | --- | --- |
| eBay official recert storefronts | ✅ | 10–15 min (Browse API saved search) | Native cheap heartbeat; already T0 |
| ServerPartDeals (recert collection) | ✅ | 2–5 min heartbeat | Drop-prone (post-2026-interruption) + Shopify; low-regret |
| Other confirmed-Shopify specialists (TechMikeNY, SaveMyServer, The Server Store `parts.`) | ⚠️ conditional | 5–10 min heartbeat | Cheap; add if finite-lot recert behaviour confirmed |
| WD direct recert | ✅ (spike 2026-07-04) | 2–5 min heartbeat | Endpoint **found**: unauthenticated SAP-Commerce OCC JSON (variant SKU + exact price + stock counts) — [recon spike](2026-07-04-wd-seagate-recert-endpoint-recon.md) |
| Seagate direct recert | ✅ (spike 2026-07-04) | 2–5 min heartbeat (one category-page GET; crawl-delay 20 s) | Direct store **exists** (`/products/seagate-recertified/`); robots-allowed category page embeds per-SKU `final_price`+`stock_status` bootstrap JSON. ⚠️ `store.seagate.com` GraphQL is cheaper but robots-**disallowed** — [recon spike](2026-07-04-wd-seagate-recert-endpoint-recon.md) |
| Amazon / Newegg / VARs / refurb-server / DiskPrices | ❌ | per class SLO | Churning/stable or no cheap signal |

## 5. Failure modes to design around (union of both runs)

1. **CDN / cache staleness** — a JSON endpoint can be cached longer than the underlying inventory; check `CF-Cache-Status`/`Age`, use conditional requests, and keep the slow repair crawl as the backstop.
2. **Variant-vs-product mismatch** — product-level `available=true` can hide that only the wrong capacity/interface/condition variant is in stock; key at variant/SKU grain (corroborated across Shopify Community + r/shopify).
3. **Collection omission** — collection JSON may exclude hidden/unpublished/OOS or >250-variant products; don't treat a collection feed as complete.
4. **Price-only changes** — a heartbeat watching only `available` misses price drops; fingerprint must include price + compare-at price + shipping flag + stock state.
5. **Backorder/preorder semantics** — `available`/`is_in_stock`/"purchasable" may include non-physical stock; normalize separately.
6. **Marketplace result churn** — eBay/Amazon/Newegg search-order changes look like transitions; dedupe by durable IDs (`itemId`, ASIN, seller SKU).
7. **Presentment currency** — storefront APIs may return locale/presentment prices; normalize currency before comparing.
8. **Endpoint drift** — record `platform_detected_at`, `signal_endpoint`, `signal_confidence`, `last_successful_signal_at` per source.
9. **Anti-bot escalation** — if the cheap heartbeat starts returning soft-blocks/403/CAPTCHA, **demote out of the fast lane**, do not increase frequency.

## 6. Escalation — not resolved by this task

**Amazon PA-API deprecation (2026-05-15 → Creators API).** Surfaced by the ChatGPT run; it contradicts an assumption in the already-settled Amazon acquisition path (see the acquisition/legal research and resolved-questions). This is a dated, time-sensitive fact and should not live only inside a cadence report. **Recommended follow-up:** open an OQ (or a dated note against the Amazon acquisition decision) and **verify live** before acting — API deprecation timelines shift.

## 7. Open items — resolve empirically or by a targeted spike

| # | Item | How it resolves |
| --- | --- | --- |
| 1 | ~~Do WD.com / Seagate.com expose an internal XHR/bootstrap stock endpoint?~~ | ✅ **Resolved 2026-07-04 by the [endpoint-recon spike](2026-07-04-wd-seagate-recert-endpoint-recon.md):** both do — WD via unauthenticated OCC JSON API, Seagate via bootstrap JSON in the robots-allowed category page (its store GraphQL is robots-disallowed). Both fast-lane eligible. |
| 2 | ~~Does Seagate sell recert **direct** (pollable store) or only via SPD/eBay?~~ | ✅ **Resolved 2026-07-04 (same spike):** yes — `seagate.com/products/seagate-recertified/` (Exos subcategory, 6 SKUs 16–28 TB, active promo). qdev's assumption was right. |
| 3 | Is Magento storefront GraphQL `stock_status`/`only_x_left_in_stock` exposed unauthenticated on ETB / Bargain Hardware / PCNation / ServerMonkey? | Direct probe of each live `/graphql` (version/config-dependent industry-wide) |
| 4 | Real volatility of the ~8 evidence-thin long-tail/B2B sources | hw-radar's own price-history once collecting; or targeted community searches (r/homelabsales) |
| 5 | Actual SPD/WD/Seagate clear-times under 2026 market conditions | hw-radar's own timestamped transition data post-launch (self-correcting registry values) |

## 8. Provenance

Both source reports were run 2026-07-04 on research prompt #15 ([`../further-research-needed-prompts.md`](../further-research-needed-prompts.md#15-per-source-inventory-volatility--fast-lane-polling-affordance)). Treat all stock-behaviour claims as dated — the 2026 HDD supply/price interruption is actively shifting volatility profiles, which is precisely why the SPD contradiction resolved on a _date_ rather than a fixed classification. The freshness SLOs and fast-lane assignments here are **initial** values for a self-correcting per-source registry, not fixed constants.
