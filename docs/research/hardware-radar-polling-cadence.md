---
schema_version: '1.1'
id: hardware-radar-polling-cadence
title: 'Hardware Radar Polling Cadence: Inventory Volatility and Cheap Availability Signals'
description: ChatGPT Deep Research run on per-source inventory volatility and cheap availability-signal affordance for hw-radar's ~20 marketplaces. Classifies each source drop-prone/churning/stable, inventories cheap no-render signals (Shopify Ajax API, WooCommerce Store API, BigCommerce/Magento GraphQL, eBay Browse), and derives a fast-lane set, percentile freshness SLOs, and an availability-heartbeat-vs-full-pipeline pattern with nine failure modes. Run in parallel with an equivalent qdev research pass; consolidated in the reconciliation report.
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
- shopify
source: []
aliases:
- ChatGPT polling cadence research
related:
- 2026-07-04-polling-cadence-reconciliation
- 2026-07-04-per-source-inventory-volatility-and-fast-lane-polling
- per-source-polling-cadence-and-skip-policy
confidence: medium
visibility: private
license: null
---

# Hardware Radar polling cadence: inventory volatility and cheap availability signals

_Date prepared: 2026-07-04._

Scope: this report intentionally covers only two questions: (1) how volatile each source/source type is in practice, and (2) whether the source exposes a cheap availability/price-change signal that can be polled separately from the full fetch-parse-normalize-score-alert pipeline. It does **not** re-derive rate limits, anti-bot posture, generic Scrapy architecture, or the already-chosen acquisition mechanism.

## Bottom line

The defensible fast lane is narrow:

1. **ServerPartDeals manufacturer-recertified / enterprise-drive collection** is the strongest fast-lane candidate **if** its storefront exposes a stable Shopify-compatible product/collection JSON endpoint or another small JSON payload. It is drop-prone enough to justify fast detection, and the likely platform family is cheap enough to poll once verified.
2. **Other storage-specialist recert resellers** such as goHardDrive-like stores are conditional fast-lane candidates only when they have both (a) desirable finite-lot recert/refurbished inventory and (b) a cheap product/variant availability endpoint. Without that endpoint, do not sub-5-minute poll full HTML.
3. **Western Digital recertified/outlet** is drop-prone, but the public page observed in this pass behaves like a custom storefront/front-end rather than a clean Shopify/Woo/BigCommerce surface. It should be fast-lane only if endpoint reconnaissance finds a small SKU JSON or stock API. Otherwise treat it as high-value but not safely cheap-pollable.
4. **eBay, Amazon, Newegg, broad VAR catalogs, and refurbished-server sellers** should not be aggressive fast-lane targets as broad sources. eBay/Amazon/Newegg are mostly **churning**: the value is aggregate best-price discovery, not catching one specific product-page restock. VARs and most refurbished-server sellers are **stable**: days-to-hours freshness is enough unless a specific one-off SKU has a proven cheap signal.

Evidence on exact “how fast does a restock clear?” is the weakest part of the public record. I found good evidence that recertified/enterprise drives are community-watched and deal-sensitive, and that specialist sellers carry manufacturer-recertified/seller-refurbished finite stock, but I did **not** find reliable public, timestamped threads proving a consistent “sells out in X minutes” rule for WD, ServerPartDeals, or goHardDrive. The practical engineering conclusion is therefore conditional: sub-5-minute polling is worth it only when the source is both drop-prone **and** cheap/safe to heartbeat.

## Volatility classes used here

| Class | Meaning | Operational implication |
| --- | --- | --- |
| **Drop-prone** | Finite lots or recertified/refurbished stock arrive in bursts; desirable SKUs can disappear on a minutes-to-hours timescale. | Use a fast availability heartbeat only where the request is small and stable. |
| **Churning** | Continuous stream of independent listings/offers; one listing matters less than aggregate best price and seller trust. | Poll saved searches/API feeds, not individual product pages aggressively. |
| **Stable** | Catalog price/stock usually moves on hours-to-days timescale. | Slow full crawl plus change detection is enough. |

## Per-source recommendation table

| Source / source type | Volatility profile | Evidence and best estimate of drop speed | E-commerce platform / surface | Cheap availability signal available? | Recommended detection cadence | Fast-lane? |
| --- | --- | --- | --- | --- | --- | --- |
| **Western Digital recertified / outlet** | **Drop-prone** for desirable recertified high-capacity HDDs and enterprise models; otherwise stable catalog. | WD’s own recert page positions these as tested/certified recertified products with warranty and savings, which implies finite recertified inventory rather than normal retail replenishment. r/DataHoarder has active, repeated HDD/SSD price discussion pressure; mods explicitly referenced multiple daily HDD/SSD price posts in late June / early July 2026. Precise sellout timing was not publicly verifiable in this pass. Treat desirable drops as **minutes-to-hours**, not days. Sources: [WD recertified store][wd-recert], [r/DataHoarder price-post moderation][dh-price-posts]. | Appears custom / manufacturer storefront. The fetched page showed front-end templates and SKU/price/cart data, not a simple Shopify/Woo/BigCommerce pattern. | **Not confirmed.** Probe for SKU JSON, embedded bootstrap JSON, XHR product APIs, and sitemap `lastmod`. A sitemap alone is not sufficient for fast stock detection. | If a small SKU/stock JSON is found: **2-5 min** for watched SKUs. If only full page/collection scrape exists: **30-60 min** and no sub-5 polling. | **Conditional / usually no until endpoint is verified.** |
| **Seagate direct recert/outlet or official refurb channel** | **Drop-prone** when it is an official finite recert/refurb lot; **churning** if monitored through eBay seller listings. | Public evidence is stronger for Seagate recert/refurb appearing through specialist sellers than for a directly pollable Seagate-owned recert storefront. TechRadar reported 36 TB Seagate Exos units listed at ServerPartDeals in new, manufacturer-recertified, and seller-refurbished forms in July 2025. Drop speed: assume **hours** unless a community-highlighted coupon/drop creates minutes-level pressure. Source: [TechRadar / ServerPartDeals 36 TB Seagate Exos][techradar-36tb]. | Unknown/custom if direct; eBay surface if official eBay refurb/outlet listings are used. | If eBay-based: **yes**, via eBay Browse API seller-scoped search and item summaries. If direct storefront: **not verified**. | Seller-scoped eBay/API: **10-15 min**. Direct storefront without cheap endpoint: **30-60 min**. | **Conditional.** Fast-lane only for seller-scoped official lots with cheap API/search signal. |
| **ServerPartDeals manufacturer-recertified drives** | **Drop-prone**, with some stable-catalog behavior. High-capacity enterprise recert stock is finite and deal-sensitive. | ServerPartDeals has a dedicated manufacturer-recertified-drive collection. Its page describes factory recertified drives as an alternative to brand-new drives and the site also supports procurement quantities that can exceed visible stock, suggesting stock is real but not always fully expressed as simple retail quantity. TechRadar’s 2025 report confirms ServerPartDeals listing new, manufacturer-recertified, and seller-refurbished high-capacity Seagate Exos models. Drop speed: best estimate **minutes-to-hours** for unusually good $/TB or scarce capacity; exact public timestamps not verified. Sources: [ServerPartDeals manufacturer-recertified collection][spd-recert], [TechRadar / ServerPartDeals 36 TB Seagate Exos][techradar-36tb]. | Likely Shopify/headless-Shopify-like commerce surface because Shop Pay appears in checkout/payment affordances, but the basic `/products.json` probes were not confirmed by the browser tool. Treat platform as **probable but must verify**. | **Likely yes if Shopify-compatible.** Minimal candidates: `/products/<handle>.js`, `/collections/<collection>/products.json`, or any first-party collection JSON/XHR returning variant `available` and price. Shopify’s Ajax Product API exposes product and variant `available`, SKU, and price fields. Source: [Shopify Ajax Product API][shopify-product-api]. | Verified JSON heartbeat: **2-5 min** for watched recert SKUs/collections. HTML-only fallback: **10-15 min**, not faster. | **Yes, once cheap endpoint is verified.** |
| **goHardDrive and similar recert/refurb drive specialists** | **Drop-prone-to-stable.** The best lots are finite; normal catalog stock changes more slowly. | goHardDrive-like sellers are watched because warranty/condition/$/TB can be attractive, but this pass did not verify a public endpoint or timestamped sellout evidence. Treat desirable recert/refurb lots as **tens of minutes-to-hours**, not reliably sub-minute. | Platform **not verified** in this pass. May be custom/legacy commerce, marketplace storefronts, or Shopify-like depending on seller. | **Unknown.** Probe Shopify/Woo/BigCommerce signatures first; otherwise rely on structured data/full HTML. WooCommerce’s Store API, when present, can expose public product data including price and `is_in_stock`; Shopify can expose variant `available`; BigCommerce has Storefront GraphQL product/search/inventory surfaces. Sources: [WooCommerce Store API products][woocommerce-products], [Shopify Ajax Product API][shopify-product-api], [BigCommerce Storefront GraphQL site query][bigcommerce-site], [BigCommerce inventory query][bigcommerce-inventory]. | If cheap JSON exists: **5-10 min**. If HTML only: **15-30 min**. | **Conditional; no sub-5 without endpoint proof.** |
| **Other storage-specialist resellers** | **Stable-to-drop-prone** depending on whether the page represents normal catalog stock or finite recert/refurb lots. | Treat finite-lot recert drives as drop-prone; treat normal catalog pages as stable. Community evidence supports high attention to HDD/SSD pricing, but exact clear-times are source-specific. Source: [r/DataHoarder price-post moderation][dh-price-posts]. | Mixed: Shopify, WooCommerce, BigCommerce, Magento/Adobe Commerce, or custom. | **Platform-dependent.** Shopify: product `.js` / collection JSON. WooCommerce: `/wp-json/wc/store/v1/products` with price and stock fields. BigCommerce: Storefront GraphQL product/search/inventory. Magento/Adobe Commerce: inventory APIs exist, but public unauthenticated availability varies by implementation. Sources: [Shopify Ajax Product API][shopify-product-api], [WooCommerce Store API products][woocommerce-products], [BigCommerce inventory query][bigcommerce-inventory], [Adobe Commerce inventory docs][adobe-commerce-inventory]. | Finite-lot cheap endpoint: **5-10 min**. Normal catalog: **1-6 h**. | **Only when both finite-lot and cheap endpoint are true.** |
| **eBay broad HDD/SSD searches** | **Churning.** Continuous independent listings; value is aggregate best price, seller, condition, and listing age. | eBay Browse API exposes item-summary search with filters, seller filters, price filters, sort options, and pagination. This is naturally a saved-search/feed problem, not a “catch one restock page” problem. Source: [eBay Browse item_summary/search][ebay-browse]. | eBay marketplace API. | **Yes**, but it is a marketplace search signal rather than a product-page stock heartbeat. Use seller/category/query/price filters, `sort=newlyListed` or price sort, and dedupe by item ID. | High-value saved queries: **10-15 min**. Broad market census: **30-60 min**. | **No** for broad search; **conditional** for a single official seller/outlet watch. |
| **Amazon** | **Churning-to-stable.** Offers, Buy Box, third-party sellers, and warehouse/refurbished conditions change, but broad value is aggregate. | Amazon PA-API GetItems can return offer availability/price resources, but the PA-API documentation page now carries a May 15, 2026 deprecation notice and points developers toward Creators API migration. That makes Amazon platform choice and terms especially time-sensitive as of 2026-07-04. Source: [Amazon PA-API GetItems / deprecation notice][amazon-paapi]. | Amazon official API / marketplace. Full-page scraping is anti-bot-hostile and not appropriate for fast polling. | **API-dependent.** Availability/price exists in API resources, but PA-API deprecation means this must be revalidated against the current Amazon-approved API path before implementation. | API/feed: **30-60 min** for watched ASINs or saved searches. No fast HTML polling. | **No.** |
| **Newegg** | **Churning-to-stable.** Marketplace listings and promo pricing change, but not usually a finite recert restock page worth sub-5 polling. | Deal pages can move, but broad Newegg monitoring is a catalog/search-feed problem. No cheap public availability-only endpoint was verified in this pass. | Newegg marketplace/custom commerce. | **Not verified.** Prefer any official feed/API already chosen for the project. Otherwise parse structured data / embedded JSON at moderate cadence only. | **30-120 min** depending on watch specificity. | **No.** |
| **Business VARs** (CDW, Insight, SHI, Provantage-like) | **Stable.** Pricing and availability generally move on hours-to-days timescale, often with quote/procurement semantics. | These are procurement catalogs, not deal-drop sources. Fast polling tends to add cost and block risk before it adds actionable value. | Enterprise commerce/custom; sometimes BigCommerce/Magento-like, often custom search. | **Usually weak.** Structured data, sitemaps, and search JSON may reveal price/product changes; stock state may be hidden behind quote/procurement logic. | Active watched SKU: **4-6 h**. Catalog census: **12-24 h**. | **No.** |
| **Refurbished-server sellers** (Bargain Hardware / ETB / TechMikeNY / The Server Store / UnixSurplus-like) | **Stable-to-drop-prone for one-off lots**, but most drive listings move slower than recert manufacturer drops. | Useful for occasional off-market bargains and cross-border listings, but inventory usually behaves like finite refurbished catalog rather than flash-drop retail. Drop speed: **hours-to-days**, except rare one-off lots. | Mixed: Magento/Adobe Commerce, WooCommerce, Shopify, BigCommerce, or custom. UK/EU sellers also introduce VAT/export-price and landed-cost issues outside this report’s scope. | **Platform-dependent.** Use platform JSON when present; otherwise HTML + structured data. Do not fast-poll full pages. | **1-6 h** for watched categories; **12-24 h** for broad catalog. | **No**, except rare SKU + proven cheap endpoint. |
| **DiskPrices / price-reference tools** | **Churning reference layer**, not a merchant inventory source. | DiskPrices is explicitly a price table over Amazon country sources with condition/capacity/form-factor filters and $/TB-style columns. Good for baselines and sanity checks, not for direct stock-heartbeat alerting. Source: [DiskPrices][diskprices]. | Aggregator/reference site. | **No direct merchant stock transition.** Use only as a benchmark/reference feed if acceptable. | **Daily to 6 h** depending on baseline use. | **No.** |

## Fast-lane set

### Put in the fast lane

A source belongs in the fast lane only if both conditions are true:

1. The source is **drop-prone** for the watched SKU/category.
2. The transition can be detected with a **cheap, low-risk request**: a small JSON payload, API result, feed row, or conditional request that avoids rendering/parsing a full product page.

Concrete candidates:

| Candidate | Fast-lane condition | Detection cadence |
| --- | --- | --- |
| **ServerPartDeals recertified enterprise/HDD collection** | Add only after confirming stable product/collection JSON or equivalent XHR exposing variant availability and price. | **2-5 min** heartbeat for watched SKUs/collection; full pipeline only on change. |
| **Shopify-compatible storage-specialist stores** | Add only for finite-lot recert/refurb categories and verified `/products/<handle>.js`, collection JSON, or equivalent. | **2-10 min** depending on value and cache behavior. |
| **WooCommerce/BigCommerce storage-specialist stores** | Add only when Store API / Storefront GraphQL returns stock/price cheaply and the source is finite-lot/drop-prone. | **5-10 min**. |
| **Seller-scoped eBay official outlet / refurb seller watch** | Only for a specific official seller or high-trust seller query, not broad eBay market search. | **10-15 min** via Browse API saved search. |
| **Western Digital recertified/outlet** | Only if reconnaissance finds a small SKU/stock JSON endpoint or reliable lightweight stock XHR. | **2-5 min** if found; otherwise not fast-lane. |

### Keep out of the fast lane

| Source | Why not aggressive? | Cadence posture |
| --- | --- | --- |
| **Broad eBay searches** | Churning market; fast polling increases duplicate/noise/API use more than it catches unique drops. | 10-15 min high-value saved queries; 30-60 min broad. |
| **Amazon** | API/terms are time-sensitive after PA-API deprecation notice; full-page polling is anti-bot-hostile. | 30-60 min through approved API/feed only. |
| **Newegg broad search** | Churning/stable catalog; no cheap public stock-only endpoint verified. | 30-120 min. |
| **Business VARs** | Stable/procurement catalog behavior. | 4-24 h. |
| **Refurbished-server sellers** | Usually stable finite catalog, not minutes-level flash drops. | 1-24 h depending on watch specificity. |
| **Any drop-prone source with only expensive full-page/JS access** | Fast polling the expensive path increases block/fragility risk and defeats the heartbeat pattern. | Moderate full fetch plus daily repair crawl. |

## Freshness SLO by volatility class

These are expressed as **transition-to-alert freshness SLOs**, not raw poll intervals. The poll interval is an implementation detail; the SLO is the maximum age of the freshest observation that could trigger an alert.

| Volatility class | Freshness SLO | Why this target is defensible | Where faster stops adding value |
| --- | --: | --- | --- |
| **Drop-prone + cheap heartbeat** | **p95 <= 3 min, p99 <= 7 min transition-to-alert** | Desirable finite recert/restock events may clear in minutes-to-hours; a 2-5 min heartbeat gives a real chance to catch a short-lived SKU without full-page pressure. | Below ~60-90 seconds, the owner’s human loop dominates: read alert, decide, open checkout, verify warranty/condition, buy. Sub-minute detection rarely improves purchase probability enough to justify more requests. |
| **Drop-prone but no cheap heartbeat** | **p95 <= 15 min, p99 <= 30 min** | Still worth timely detection, but not worth hammering expensive/custom/anti-bot paths. | Faster than ~10-15 min on full pages mainly buys block risk and compute, not reliability. |
| **Churning marketplaces** | **p95 <= 15-30 min for saved high-value queries; p99 <= 60 min for broad market census** | The target is aggregate best-price awareness, not catching one SKU page before it vanishes. API search deltas and dedupe matter more than seconds. | Faster than ~10 min usually increases alert churn and duplicate processing more than buyer value. |
| **Stable catalogs / VARs / refurbished-server sellers** | **p95 <= 4-6 h for watched SKUs; p99 <= 24 h for broad catalog** | Stock and prices usually move on hours-to-days timescale. | Faster than hourly rarely changes a human purchase outcome unless the source has a specific finite-lot history and cheap endpoint. |
| **Reference/baseline tools** | **p95 <= 24 h** | Used for baselines, sanity checks, and market context rather than immediate purchase action. | Intraday updates are nice-to-have, not alert-critical. |

## Availability heartbeat vs. full pipeline

The heartbeat/full-pipeline split is the right pattern, but only for sources whose platform exposes a small, reliable transition signal.

### Viable heartbeat sources

| Platform/surface | Minimal request | What it can reveal | Source |
| --- | --- | --- | --- |
| **Shopify / Shopify-compatible** | `GET /products/<handle>.js` for watched handles; sometimes `/collections/<collection>/products.json?limit=250` for collection watch. | Product/variant `available`, SKU, price, compare-at price; enough to detect in-stock/out-of-stock and price transitions. | [Shopify Ajax Product API][shopify-product-api] |
| **WooCommerce Store API** | `GET /wp-json/wc/store/v1/products?sku=...` or product/slug endpoint. | Public product data including price, `is_purchasable`, and `is_in_stock`. | [WooCommerce Store API products][woocommerce-products] |
| **BigCommerce Storefront GraphQL** | Product/search query for watched SKUs/categories; inventory query where storefront and token model allow it. | Product list/search changes; inventory-location data where exposed. | [BigCommerce Storefront GraphQL site query][bigcommerce-site], [BigCommerce inventory query][bigcommerce-inventory] |
| **Magento / Adobe Commerce** | Storefront-visible product JSON if available; inventory APIs if authorized. | Stock/salable quantity exists in the platform, but public unauthenticated availability depends on implementation. | [Adobe Commerce inventory docs][adobe-commerce-inventory] |
| **eBay Browse API** | `GET /buy/browse/v1/item_summary/search` with query/category/seller/condition/price filters; use sort and small limits. | New listings, price, seller, condition, item ID; good for marketplace deltas. | [eBay Browse item_summary/search][ebay-browse] |
| **Amazon approved API path** | Current Amazon-approved item/offers endpoint for watched ASINs. | Offer availability and price when resource is permitted. PA-API docs are deprecated as of 2026-05-15, so reverify before implementation. | [Amazon PA-API GetItems / deprecation notice][amazon-paapi] |
| **Custom manufacturer storefronts** | Site-specific XHR/bootstrap JSON only after reconnaissance. | Potentially SKU stock/price, but not portable. | [WD recertified store][wd-recert] |

### Failure modes to design around

1. **CDN/cache staleness.** A JSON endpoint can be cached longer than the underlying inventory. Use conditional requests (`ETag`, `Last-Modified`) where useful, but still run a slower full fetch to repair missed transitions.
2. **Variant vs. product mismatch.** Product-level `available=true` can hide the fact that only the wrong capacity/interface/condition variant is available. Always key heartbeats at the variant/SKU grain when possible.
3. **Collection omission.** Collection JSON may exclude hidden, unpublished, out-of-stock, or >250-variant products. Shopify’s Ajax product response has variant limits; collection endpoints can be incomplete for large catalogs.
4. **Price-only changes.** A heartbeat that watches only `available` misses price drops. Include price, compare-at price, shipping flag if exposed, and stock state in the heartbeat fingerprint.
5. **Backorder/preorder semantics.** `available`, `is_in_stock`, or “purchasable” may include backorder/preorder states. Normalize these separately from physically in-stock inventory.
6. **Marketplace result churn.** eBay/Amazon/Newegg search order changes can look like transitions. Dedupe by durable IDs (`itemId`, ASIN, seller SKU) and score only material changes.
7. **Locale/presentment currency.** Shopify and other storefront APIs may return prices in presentment currency. Normalize currency before comparing price transitions.
8. **Endpoint drift.** Platform endpoints and storefront implementations change. Record `platform_detected_at`, `signal_endpoint`, `signal_confidence`, and `last_successful_signal_at` per source.
9. **Anti-bot escalation.** If the cheap heartbeat begins returning soft-blocks, 403s, CAPTCHA pages, or inconsistent payloads, demote the source out of fast lane rather than escalating frequency.

### Implementation shape

Maintain two observation levels:

- `availability_heartbeat_observation`: cheap poll result, raw fingerprint, source timestamp, stock/price fields, endpoint metadata, cache headers, and decision (`unchanged`, `transition_detected`, `ambiguous`, `failed`).
- `offer_snapshot`: full normalized observation produced only after a transition or scheduled repair crawl.

Trigger the full pipeline on:

- out-of-stock -> in-stock,
- in-stock -> out-of-stock,
- material price drop,
- material shipping/warranty/condition change,
- new listing ID / new variant SKU,
- ambiguity after previous in-stock state.

Also run a slow repair crawl for every source, even fast-lane ones. A good default is daily for stable sources, every 6-12 hours for churning marketplaces, and every 1-4 hours for fast-lane drop-prone sources. This catches cache misses, parser drift, and endpoint omissions without turning full scrapes into the detection mechanism.

## Source notes

- **Western Digital recertified store**: official recertified-drive page, accessed 2026-07-04. [Link][wd-recert]
- **ServerPartDeals manufacturer-recertified collection**: source page for manufacturer-recertified drives, accessed 2026-07-04. [Link][spd-recert]
- **TechRadar / ServerPartDeals 36 TB Seagate Exos article**: published 2025-07-13; evidence that ServerPartDeals carried new, manufacturer-recertified, and seller-refurbished high-capacity Seagate enterprise drives. [Link][techradar-36tb]
- **r/DataHoarder moderation update**: late June / early July 2026 context showing heavy community discussion of HDD/SSD pricing; useful for attention level, not precise restock-clear timing. [Link][dh-price-posts]
- **DiskPrices**: Amazon-derived HDD/SSD price-reference table with condition/capacity/form-factor filters; useful as market reference, not direct merchant stock. [Link][diskprices]
- **Shopify Ajax Product API**: official docs for product/variant JSON including price and availability fields. [Link][shopify-product-api]
- **WooCommerce Store API products**: official docs for public product data, including price and stock fields. [Link][woocommerce-products]
- **BigCommerce Storefront GraphQL site/inventory docs**: official docs showing product/search and inventory query surfaces. [Link 1][bigcommerce-site], [Link 2][bigcommerce-inventory]
- **Adobe Commerce inventory docs**: official inventory/salable-stock API concepts; public availability depends on implementation. [Link][adobe-commerce-inventory]
- **eBay Browse API**: official item-summary search docs. [Link][ebay-browse]
- **Amazon PA-API GetItems docs**: official docs carrying the May 15, 2026 PA-API deprecation notice and offer availability resources. [Link][amazon-paapi]

[wd-recert]: https://www.westerndigital.com/products/recertified
[spd-recert]: https://serverpartdeals.com/collections/manufacturer-recertified-drives
[techradar-36tb]: https://www.techradar.com/pro/36tb-seagate-exos-sata-hard-drive-goes-on-preorder-for-usd800-worlds-largest-hdd-is-already-sold-as-refurbished-but-why
[dh-price-posts]: https://www.reddit.com/r/DataHoarder/comments/1u5ljvs/mod_update_regarding_the_flood_of_hddssd_price/
[diskprices]: https://diskprices.com/
[shopify-product-api]: https://shopify.dev/docs/api/ajax/reference/product
[woocommerce-products]: https://developer.woocommerce.com/docs/apis/store-api/resources-endpoints/products/
[bigcommerce-site]: https://docs.bigcommerce.com/developer/api-reference/graphql/storefront/queries/site
[bigcommerce-inventory]: https://docs.bigcommerce.com/developer/api-reference/graphql/storefront/queries/inventory
[adobe-commerce-inventory]: https://developer.adobe.com/commerce/webapi/rest/inventory/
[ebay-browse]: https://developer.ebay.com/api-docs/buy/browse/resources/item_summary/methods/search
[amazon-paapi]: https://webservices.amazon.com/paapi5/documentation/get-items.html
