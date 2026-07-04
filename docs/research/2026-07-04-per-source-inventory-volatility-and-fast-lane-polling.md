---
schema_version: '1.1'
id: 2026-07-04-per-source-inventory-volatility-and-fast-lane-polling
title: Per-Source Inventory Volatility and Fast-Lane Polling Affordance for a 20-Marketplace Drive Monitor
description: Classifies each of hw-radar's ~20 sources as drop-prone/churning/stable by restock behavior (grounded in r/DataHoarder restock threads), inventories which sources expose a cheap no-render availability signal (Shopify/Magento JSON, e-commerce platform survey), and derives a freshness-SLO-per-class plus an availability-heartbeat-vs-full-pipeline decoupling recommendation. Scoping pass run in parallel with an equivalent ChatGPT Deep Research brief for later consolidation.
doc_type: research
status: active
created: '2026-07-04'
updated: '2026-07-04'
reviewed: null
owner: chris
tags:
- inventory-volatility
- restock-behavior
- shopify
- magento
- freshness-slo
- polling-cadence
- availability-heartbeat
aliases:
- fast-lane polling
- availability heartbeat pattern
related:
- per-source-polling-cadence-and-skip-policy
- programmatic-acquisition-research-for-enterprise-and-nas-drive-merchants
source: []
confidence: medium
visibility: private
license: null
---

# Per-Source Inventory Volatility and Fast-Lane Polling Affordance for a 20-Marketplace Drive Monitor

## Bottom line

The two dimensions this report was scoped to measure — **how bursty is a source's inventory** and **how cheaply can that burst be observed** — turn out to be **negatively correlated** across hw-radar's source set, which is the single most useful and least obvious finding here. The sources with the most dramatic drop-prone behavior (Seagate.com and WD.com direct recertified stores — restocks documented selling out in **minutes to a few hours**) are custom, JS-templated storefronts with **no confirmed cheap availability signal**; the sources with the cleanest cheap signal (ServerPartDeals, TechMikeNY, SaveMyServer, and The Server Store's parts subdomain — all Shopify, exposing `/products.json` with a per-variant `available` boolean) are **churning, not drop-prone** — their "sold out" state persists for days to weeks and the value is aggregate best-price tracking, not racing a restock window. The one source that is genuinely both drop-prone *and* natively cheap is **eBay's own manufacturer recert storefronts**, because the Browse API's `getItems`/`estimatedAvailabilities` fields already are the lightweight signal — no separate heartbeat tier is needed there. Practically: build the Shopify-class heartbeat because it's nearly free, but don't expect it to catch the hottest drops; the hottest drops (Seagate/WD direct) need either an accepted freshness gap or a follow-up engineering spike to reverse-engineer their storefront's AJAX stock endpoint (flagged as an open question, not resolved by search research alone).

## Per-source table

| Source | Volatility profile | Evidence + how fast drops clear | E-commerce platform | Cheap availability signal? | Recommended detection cadence | Fast-lane |
| --- | --- | --- | --- | --- | --- | --- |
| **eBay** (Browse API; incl. Seagate/WD official eBay recert stores) | **Mixed**: individual-seller listings are *churning* (continuous new listings); the manufacturers' own eBay recert storefronts mirror the *drop-prone* pattern of their direct sites | eBay opened official Seagate US recert store [community, 1] mirroring direct-site restock cycles | N/A — official API | **Yes, natively.** `getItems`/`getItem` return `estimatedAvailabilities` and a `sellerItemRevision` counter designed exactly for cheap "did anything change" polling [official, 2][official, 3] | Already settled at T0 (10 min baseline / 2 min ceiling per prior cadence research) — no change needed | **Yes** — already the cheapest, fastest lane in the set by design |
| **Western Digital Store / Recert** | **Drop-prone** (moderate evidence — timing less precise than Seagate's) | RedFlagDeals: "restock often... sell out quickly... set up a tracker" [community, 4]; r/DataHoarder asks "how quickly does WD usually restock" with no definitive minute-level answer captured [community, 5] | Custom/headless, JS-templated (prior research: `inventory.stockLevel` var present, no JSON-LD) | **No confirmed cheap signal.** JS-templated pages likely have an internal XHR the storefront calls to render "Notify Me"/stock state, but it was not discovered in this search pass | Existing T1 (30 min / 5 min ceiling) stands; a fast lane is aspirational pending the XHR discovery | **Not yet** — drop-prone but not confirmed cheap; see Open Questions |
| **Seagate Store / Recert** | **Drop-prone**, best-evidenced case in the set | Two independent threads: a $349 28TB "sold out" **3 minutes** after being noticed [community, 6]; a separate restock "sold out within hours," repeatedly, over a month at the same $299 price point [community, 7] | Custom/headless, JS-templated (Rakuten affiliate params, no JSON-LD found) | **No confirmed cheap signal** — same custom-store caveat as WD | Existing T1 stands; highest-priority target for the XHR-discovery follow-up | **Not yet** — highest-value drop-prone target, currently the biggest gap between "worth polling fast" and "can poll cheaply" |
| **ServerPartDeals** | **Churning.** Restocks happen but deplete over days–weeks, not minutes; "cheaper ones just keep selling out" for months on some SKUs [community, 8] | "How often does Serverpartdeals restock?" thread finds no burst pattern, just gradual depletion [community, 8]; "GoHardDrive, ServerPartDeals... deals and stock always fluctuate" [community, 9] | **Shopify**, high confidence (prior research) | **Yes.** `/products.json` and `/products/<handle>.json` expose `variants[].available` (bool) + price with no rendering [official, 10][community, 11] | Existing T2 (1 h / 15 min ceiling) is already adequate — churning value doesn't need sub-15-min resolution | **No** — cheap, but not drop-prone enough to justify a separate fast lane |
| **goHardDrive** | **Churning.** Same ebb-and-flow pattern as ServerPartDeals, no minute-level burst evidence | "Deals and stock always fluctuate" [community, 9]; price/stock described as gradually shifting, not vanishing in minutes [community, 12] | Legacy ASP/HTML (prior research), no JSON endpoint | **Cheap-ish only.** Plain static-feeling HTML, no headless render required, but no JSON — a lightweight GET + text-pattern check ("Currently Unavailable") is the best available signal | Existing T2 stands | **No** — same reasoning as ServerPartDeals |
| **B&H Photo Video** | **Stable/churning** (inferred — no source-specific volatility evidence surfaced this pass) | Not directly evidenced; treated as a "clean retailer baseline" per prior acquisition research, not a recert value target | Custom/proprietary (prior research) | Not confirmed | Existing T2 stands | **No** |
| **CDW** | **Churning**, B2B VAR — official confirmation of a 5-minute internal refresh floor | "CDW updates inventory status every five minutes across most products" [official, 13] — this is also useful as a **polling-value ceiling**: polling CDW's public pages faster than ~5 min cannot reveal fresher data than CDW itself holds | Custom/proprietary B2B (prior research) | Not confirmed as a public JSON endpoint; the 5-minute figure describes CDW's *internal* refresh, not an exposed API | Existing T2 stands; **5 min is a hard floor below which polling adds zero signal**, independent of anti-bot posture | **No** |
| **Insight** | **Churning** (inferred, same B2B class as CDW) | Not directly evidenced this pass | Custom/proprietary B2B (prior research) | Not confirmed | Existing T2 stands | **No** |
| **Newegg** | **Churning**, general marketplace | Third-party scraper vendor copy claims "inventory can change within minutes" [blog, 14] — **low-grade, single-source, vendor-marketing tone; treat as unverified** | Storefront platform not independently confirmed; product pages are React/JS-templated with embedded state | **No** — Marketplace API is seller-side only (already settled); no consumer stock JSON found | Existing T3 stands | **No** |
| **Amazon** | **Churning**, general marketplace; buy-box/3rd-party-seller churn is continuous | Reddit/dev consensus: Amazon pages carry **no embedded LD-JSON** for price/stock, confirmed by a changedetection.io restock-plugin maintainer explicitly building a bespoke Amazon parser because the generic JSON-LD detector doesn't work there [community/vendor, 15][community, 16] | Custom, heavily anti-bot-hardened (out of scope per this report's boundaries) | **No.** No JSON-LD, no public stock API; only a full-HTML fetch-and-parse works, and even that risks anti-bot exposure | Existing T3 stands | **No** |
| **PCNation** | **Stable/churning** (inferred) | Not directly evidenced this pass | Magento/Adobe Commerce likely (prior research) | **Possibly**, with a caveat: Magento's storefront GraphQL (`/graphql`, public/unauthenticated) can expose `stock_status`/`only_x_left_in_stock` on `ProductInterface`, but multiple Magento GitHub issues show this field is inconsistently available depending on version/config — verify per-instance before relying on it [official, 17][community, 18][community, 19] | Existing T2 stands | **No** |
| **Wiredzone** | **Stable/churning** (inferred) | Not directly evidenced this pass | Odoo/Clarico theme (prior research) | Not confirmed — Odoo's `website_sale` module has no standard public stock JSON endpoint found | Existing T2/T3 boundary stands | **No** |
| **TechMikeNY** | **Stable/churning** (inferred — refurb-server-parts class) | Not directly evidenced this pass | **Shopify**, high confidence (prior research) | **Yes** — same `/products.json` mechanism as ServerPartDeals [official, 10] | Existing T4 stands (cheap signal exists but volatility doesn't justify faster) | **No** |
| **ETB Technologies** | **Stable** (inferred) | Not directly evidenced this pass | **Magento 2**, high confidence (prior research) | **Possibly** — same GraphQL `stock_status` caveat as PCNation | Existing T4 stands | **No** |
| **Bargain Hardware** | **Stable** (inferred) — vendor claims "real-time pricing and inventory" (prior research), unverified externally | Not directly evidenced this pass | Magento/Adobe Commerce likely (prior research) | **Possibly** — same GraphQL caveat | Existing T4 stands | **No** |
| **HardDrivesDirect** | **Stable** (inferred) | Not directly evidenced this pass | Legacy PHP storefront (prior research) | No JSON; cheap-ish plain-HTML GET only | Existing T4 stands | **No** |
| **ServerMonkey** | **Stable** (inferred) | Not directly evidenced this pass | Magento/Adobe Commerce likely (prior research) | **Possibly** — same GraphQL caveat | Existing T4 stands | **No** |
| **SaveMyServer** | **Stable** (inferred) | Not directly evidenced this pass | **Shopify**-like, medium confidence (prior research) | **Yes**, if Shopify confirmed — same `/products.json` mechanism | Existing T4 stands | **No** |
| **The Server Store** (`parts.` subdomain) | **Stable** (inferred) | Not directly evidenced this pass | **Shopify** on `parts.theserverstore.com` (prior research, high confidence) | **Yes** — same `/products.json` mechanism | Existing T4 stands | **No** |
| **Memory4Less** | **Stable** (inferred) | Not directly evidenced this pass | Custom/legacy (prior research) | No JSON; cheap-ish plain-HTML GET only | Existing T4 stands | **No** |

**Reading the table's biggest gap honestly:** eight of the twenty rows (B&H, Insight, PCNation, Wiredzone, ETB, Bargain Hardware, ServerMonkey, HardDrivesDirect, Memory4Less, SaveMyServer, The Server Store) carry **no source-specific volatility evidence** — their "stable/churning (inferred)" label rests on their spec-assigned trust tier and general B2B-surplus-market reasoning, not on a restock thread or vendor statement found in this pass. That's an honest limit of a search-only scoping pass against long-tail resellers that don't generate Reddit discussion; see Open Questions.

## Freshness SLO per volatility class

| Class | Recommended max transition-to-alert staleness | Why this number, not faster |
| --- | --- | --- |
| **Drop-prone** (Seagate/WD direct, eBay recert stores) | **2–5 minutes** during an active-restock window | Matches the fastest documented real clearing time (Seagate: ~3 minutes) and matches what restock-tracking SaaS vendors independently converge on as their fastest tier for "high-demand"/"limited-supply" products (Visualping: "every 5 or 10 minutes... ideal for high-demand products" [blog, 20]; PageCrawl.io's paid "Enterprise" tier is 5 min [blog, 21]). Convenient cross-check: this already equals the existing T1 cadence ceiling set by the (separately settled) rate-limit/anti-bot research — the two independent lines of reasoning land on the same number, which is a useful sanity check rather than a coincidence to rely on |
| **Churning** (ServerPartDeals, goHardDrive, CDW, Newegg, Amazon, B&H, Insight, PCNation, Wiredzone) | **15–60 minutes** | The buyer's decision loop here is comparison-shopping across the aggregate best price, not racing a single unit — a listing that's been "sold out for days" doesn't reward minute-level polling. CDW's own **5-minute internal refresh** is a useful floor-of-floors: polling any churning source faster than its own backend refresh interval (5 min, where known) cannot produce fresher data, it only produces more requests |
| **Stable** (T4 refurb-server/regional resellers) | **Hours to a day** | No burst-restock evidence anywhere in this class; matches the existing T4 baseline (4 h) / ceiling (1 h). A human buyer comparing a Server Store vs. Memory4Less quote is not making a purchase decision on minute-level price movement |

## Detection-vs-pipeline decoupling recommendation

**Split cleanly by whether a cheap signal exists, not by volatility class.** The cheap-signal test, not the drop-prone test, determines whether decoupling saves anything:

- **Shopify-class sources** (ServerPartDeals, TechMikeNY, SaveMyServer, The Server Store `parts.`, and goHardDrive/TechMikeNY-adjacent stores once platform is confirmed): run a **heartbeat** against `/products.json` (or the narrower per-product `/products/<handle>.json`) on a short interval (e.g., 5–10 min, well under the existing T2/T4 poll cadence), diff `variants[].available` and `price` against the last-seen value, and fire the full `fetch → parse → normalize → score → alert` pipeline **only** on a detected transition. This is legitimately cheap: a few KB of JSON, no headless render, and Shopify's own docs describe this exact endpoint shape [official, 10]. **Read the variant-level `available` field, not a product-level rollup** — Shopify merchants routinely report product pages showing "Sold Out" while individual variants (or the reverse) are actually available, traced to cache issues and location/variant-tracking mismatches, corroborated across the Shopify Community and r/shopify independently [official/community, 22][community, 23] — this is exactly the "variant-vs-product mismatch" failure mode the brief asked about, and it is real, not hypothetical.
- **Magento-class sources** (ETB, Bargain Hardware, PCNation, ServerMonkey): the same heartbeat pattern is *conditionally* viable via the public storefront GraphQL `stock_status` field, but **verify per-instance first** — Magento's own issue tracker shows this field missing or erroring depending on version/module configuration [official, 17][community, 19]. Where it's absent, fall back to a lightweight category-page HTML GET checked for "In Stock"/"Add to Cart" text, which is still cheaper than a full product-page render.
- **Legacy plain-HTML sources** (goHardDrive, HardDrivesDirect, Memory4Less): no JSON exists, but the pages are server-rendered without a JS framework, so a GET-only heartbeat scanning for out-of-stock keyword text is still meaningfully cheaper than a headless-browser full pipeline run — this is the same technique changedetection.io's built-in "Re-stock detection for single product pages" plugin uses generically across many merchants [official/vendor, 24].
- **Custom JS-heavy storefronts with no confirmed signal** (WD, Seagate, CDW, Insight, B&H, Wiredzone): decoupling **doesn't currently save anything**, because there is no cheaper alternative to whatever the full pipeline already does — poll these at their existing tier cadence as full-pipeline runs; the heartbeat/pipeline split only pays off once a source's own AJAX stock endpoint is reverse-engineered (a dev spike, not a search-research task).
- **eBay**: no split needed — the Browse API's `getItems` call already *is* the cheap heartbeat and the full data, in one request.
- **Amazon/Newegg**: no cheap signal and non-trivial anti-bot risk (out of scope for this report per the settled cadence/anti-bot research); decoupling not recommended — leave these on the existing tier's full-pipeline cadence.

**Known failure modes to guard against, both corroborated:**

1. **CDN-cached responses hiding real changes.** Cloudflare (and similarly configured CDNs) will serve stale HTML during `stale-while-revalidate` windows or whenever `Cache-Control`/`Origin Cache Control` isn't tuned for a fast-changing page — Cloudflare's own docs describe this as expected, not a bug [official, 25], and community threads show operators actively fighting it when origin content changes faster than the cache TTL [community, 26]. Mitigation: check `CF-Cache-Status`/`Age` response headers where present, and treat a source's advertised cache TTL as a floor on achievable freshness regardless of poll interval — polling every 2 minutes against a 10-minute edge cache buys nothing.
2. **Variant-vs-product availability mismatch** (Shopify specifically, likely similar failure classes on Magento). Documented above — always read the most granular field the platform exposes, not a rolled-up summary.

## Open Questions

| # | Question | Why unresolved |
| --- | --- | --- |
| 1 | Do WD.com and Seagate.com expose an internal AJAX/XHR endpoint (used to render "Notify Me When Available"/stock state) that would give the two best-evidenced drop-prone sources a cheap signal? | Requires a browser dev-tools network-tab inspection spike against the live sites, not a search-research task; this is the single highest-value follow-up given these are the two sources where "worth polling fast" and "can poll cheaply" currently diverge most |
| 2 | Is Magento storefront GraphQL's `stock_status`/`only_x_left_in_stock` actually exposed, unauthenticated, on ETB/Bargain Hardware/PCNation/ServerMonkey specifically? | Magento's own issue tracker shows this is version/config-dependent industry-wide; only a direct probe against each live `/graphql` endpoint resolves it per-source |
| 3 | What is the real volatility profile of the eight "inferred, no direct evidence" sources (B&H, Insight, PCNation, Wiredzone, ETB, Bargain Hardware, ServerMonkey, HardDrivesDirect, Memory4Less, SaveMyServer, The Server Store)? | These long-tail/B2B resellers don't generate the Reddit restock-thread discussion that grounded the Seagate/WD/ServerPartDeals/goHardDrive findings; closing this gap would need either direct historical-price-crawl data (once hw-radar is collecting it) or targeted community searches (r/homelabsales, vendor-specific forums) beyond this pass's scope |
| 4 | Is the "Security and Compatibility" angle genuinely out of scope here? | Yes, by explicit orchestrator instruction — rate limits and anti-bot posture are already settled in [`per-source-polling-cadence-and-skip-policy.md`](per-source-polling-cadence-and-skip-policy.md); this report deliberately did not re-derive them, so the angle is intentionally thin rather than a coverage gap |

## Handoff

Persisted at `docs/research/2026-07-04-per-source-inventory-volatility-and-fast-lane-polling.md`. This is a scoping pass run in parallel with an equivalent ChatGPT Deep Research brief on the identical topic — consolidate/reconcile the two before treating either as final. Downstream skills that may consume it:

- `superpowers:brainstorming` — feed Open Questions (esp. #1, the WD/Seagate XHR-discovery spike) into a design conversation about whether that engineering investment is worth it for two sources
- `feature-dev:feature-dev` — the heartbeat-vs-full-pipeline pattern here is directly implementable for the Shopify-class sources once acquisition code exists

## Sources

| URL | Title | Date | Authority |
| --- | ----- | ---- | --------- |
| https://www.reddit.com/r/DataHoarder/comments/1dm45zd/seagate_opens_new_ebay_us_store_for_recertified/ | Seagate opens new eBay US store for recertified drives | undated (2026 thread) | community |
| https://developer.ebay.com/api-docs/buy/browse/resources/item/methods/getItem | getItem: eBay Browse API | current | official |
| https://developer.ebay.com/DevZone/XML/docs/Reference/eBay/GetItem.html | GetItem - Trading API Reference | current | official |
| https://forums.redflagdeals.com/western-digital-recertified-wd-elements-external-desktop-hard-drive-8tb-140-10tb-165-2581411/ | WD Recertified restock/sellout + Distill tracker advice | undated | community |
| https://www.reddit.com/r/DataHoarder/comments/60r16d/how_quickly_does_wd_usually_restock_their_store/ | How quickly does WD usually restock their store? | undated | community |
| https://www.reddit.com/r/DataHoarder/comments/1qy35l1/what_is_going_on_with_seagate_pricing/ | WHAT IS GOING ON WITH SEAGATE PRICING?! (3-min sellout) | 2026 | community |
| https://www.reddit.com/r/DataHoarder/comments/1r8swim/holy_hell_seagate_expansion_drive_prices_have/ | Seagate 28TB "every restock sold out within hours" | 2026 | community |
| https://www.reddit.com/r/DataHoarder/comments/1hiotbl/how_often_does_serverpartdeals_restock/ | How often does Serverpartdeals restock? | 2024-12-20 | community |
| https://www.reddit.com/r/DataHoarder/comments/1ir49gh/enterprise_hdd_price_trends_goharddrive/ | Enterprise HDD price trends (GoHardDrive, ServerPartsDeals) | 2025-02-16 | community |
| https://www.reddit.com/r/unRAID/comments/1nuqlla/where_you_buying_drives/ | "deals and stock always fluctuate" | 2025-09-30 | community |
| https://shopify.dev/docs/api/admin-rest/latest/resources/product-variant | Product Variant — Shopify Admin REST API | current | official |
| https://help.shopify.com/en/manual/shopify-admin/using-json | Accessing detailed data using JSON — Shopify Help Center | current | official |
| https://community.latenode.com/t/getting-keyerror-when-accessing-availability-status-from-shopify-products-json-endpoint/37035 | `/products.json` `available` field usage | 2025-08-17 | community |
| https://www.cdw.com/content/cdw/en/updates/procurement-planning/memory-storage-availability.html | Memory and Storage Availability — CDW (5-min refresh) | current | official |
| https://devdocs.magento.com/guides/v2.4/graphql/interfaces/product-interface.html | GraphQL overview — Adobe Commerce/Magento devdocs | current | official |
| https://magento.stackexchange.com/questions/301684/graphql-product-quantity-in-stock | GraphQL product quantity in stock | undated | community |
| https://github.com/magento/magento2/issues/30048 | GraphQL Error: Cannot query field "stock_status" | undated | community |
| https://github.com/magento/magento2/issues/40187 | Stock Status returned Out of Stock for bundle items | undated | community |
| https://changedetection.io/tutorial/how-get-product-re-stock-or-back-stock-alerts-and-notifications | Restock/back-in-stock alerts — changedetection.io | current | vendor/official (tool docs) |
| https://www.reddit.com/r/changedetectionio/comments/1ecm0yy/does_your_install_of_change_detection_track_price/ | Amazon lacks embedded LD-JSON, custom scraper needed | undated | community + vendor reply |
| https://developers.cloudflare.com/cache/concepts/revalidation/ | Revalidation — Cloudflare Cache docs | current | official |
| https://community.cloudflare.com/t/how-to-disallow-stale-content-being-served-when-origin-is-down/250313 | Disallow stale content when origin is down | 2021 | community |
| https://community.shopify.com/t/products-are-showing-as-sold-out/587486 | Products are showing as sold out — Shopify Community | 2026-02-06 | official (vendor community) |
| https://www.reddit.com/r/shopify/comments/1rpjxuo/products_showing_sold_out_but_stock_is_completely/ | Products showing sold out but stock is completely full | 2026 | community |
| https://distill.io/blog/back-in-stock-alerts/ | Back in Stock Alerts — Distill.io | 2022-11-16 | blog/vendor |
| https://visualping.io/blog/in-stock-alert-track-product-availability | In Stock Alert: How to Track Product Availability — Visualping | 2024-05-16 | blog/vendor |
| https://pagecrawl.io/blog/out-of-stock-monitoring-alerts-guide | Out-of-Stock Alerts & Restock Notifications — PageCrawl.io | 2026-02-11 | blog/vendor |
| https://developer.newegg.com/newegg_marketplace_api/ | Newegg Marketplace API — Newegg Developer Portal (seller-side only) | current | official |
| https://www.reddit.com/r/HomeServer/comments/1hvhsnf/whats_up_with_refurb_hard_drive_prices/ | What's up with refurb hard drive prices? (SPD price stability context) | 2025-01-07 | community |
