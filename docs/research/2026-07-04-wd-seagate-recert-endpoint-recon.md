---
schema_version: '1.1'
id: 2026-07-04-wd-seagate-recert-endpoint-recon
title: WD & Seagate Direct-Recert Stores — Cheap-Signal Endpoint Recon (Spike Results)
description: Live endpoint-recon spike (2026-07-04) closing Open Items #1–#2 of the polling-cadence reconciliation — both WD and Seagate direct recert stores have a confirmed cheap machine-readable price/stock signal. WD exposes an unauthenticated SAP-Commerce OCC JSON API (variant-grain SKU, exact price, exact stock counts); Seagate's robots-allowed category page embeds bootstrap JSON with per-SKU final_price + stock_status (its Magento GraphQL endpoint is cheaper still but robots-disallowed). Both sources are now fast-lane eligible.
doc_type: research
status: active
created: '2026-07-04'
updated: '2026-07-04'
reviewed: null
owner: chris
tags:
- web-scraping
- endpoint-recon
- fast-lane
- availability-heartbeat
- western-digital
- seagate
- sap-commerce
- magento
aliases:
- WD Seagate XHR recon spike
- recert store endpoint recon
related:
- 2026-07-04-polling-cadence-reconciliation
- 2026-07-04-per-source-inventory-volatility-and-fast-lane-polling
- ../adr/adr-0015-availability-heartbeat-grain-volatility-scheduling.md
source: []
confidence: high
visibility: private
license: null
---

# WD & Seagate Direct-Recert Stores — Cheap-Signal Endpoint Recon (Spike Results)

**Spike executed 2026-07-04** (headless `curl` probes, ~10 requests total, standard browser UA, no anti-bot circumvention). Closes **Open Items #1 and #2** of the [polling-cadence reconciliation](2026-07-04-polling-cadence-reconciliation.md): the two best-evidenced drop-prone sources previously had *no confirmed cheap signal* and were excluded from the fast lane pending this recon. **Both now have a confirmed cheap signal.** All endpoints below are publicly discoverable in the stores' own page source; nothing here is a secret or a bypass.

## Headline

| Source | Cheap signal | Transport | Fingerprint fields confirmed | robots.txt posture | Fast-lane verdict |
| --- | --- | --- | --- | --- | --- |
| WD direct recert | ✅ confirmed | Unauthenticated **SAP Commerce (hybris) OCC JSON API** | variant SKU, exact price, exact `stockLevel` count, `stockLevelStatus`, `saleable` | `api.westerndigital.com` has **no robots.txt** (404 ⇒ unrestricted); `www.westerndigital.com` allows the recert pages | **Eligible — 2–5 min heartbeat** per the reconciliation's pending row |
| Seagate direct recert | ✅ confirmed (store **exists** — Open Item #2 answered) | **Bootstrap JSON embedded in the robots-allowed category page** (`www.seagate.com`, crawl-delay 20) | SKU (`STxxxxxNMxxxx`), `final_price`, `stock_status`, `is_preorder`, `percent_off` | `store.seagate.com` is **`Disallow: /` for all agents** — its Magento GraphQL endpoint is off-limits under `ROBOTSTXT_OBEY=True`; `www.seagate.com` allows the category pages at crawl-delay 20 | **Eligible — heartbeat = category-page GET**, min interval ≥ 20 s (crawl-delay), so 2–5 min is fine |

## WD — SAP Commerce OCC API (tier: first-party platform JSON)

The recert landing page (`https://www.westerndigital.com/products/recertified`, HTTP 200 to a plain GET) carries an AEM config div exposing the commerce backend: `data-commerce-service="https://api.westerndigital.com/wdwebservices/v2"`, B2C site id `us` (B2B: `usb2b`), plus `data-clpSolrServletUrl="/bin/wd/clpsolrservlet.json"` (Solr category servlet, present but `data-loadClpfromSolr="false"` on this page) and `data-searchDomain="https://search.westerndigital.com/wdcapps"`.

Standard OCC endpoints work **unauthenticated**:

- **Catalog sweep (one call):** `GET /wdwebservices/v2/us/products/search?query=recertified&fields=products(code,name,price(FULL),stock(FULL))&lang=en&curr=USD` → 12 recert base products with `stock.stockLevelStatus` each (verified live, HTTP 200).
- **Variant grain (per product):** `GET /wdwebservices/v2/us/products/{code}?fields=code,name,price(FULL),stock(FULL),variantOptions(code,priceData(FULL),stock(FULL))&lang=en&curr=USD` → per-variant recert SKU (e.g. `RWDBBGB0040HBK-NESN`), exact `priceData.value`, exact `stock.stockLevel` (e.g. 285 units), `stockLevelStatus`, `saleable` (verified live).

**Fingerprint nuance (matters for ADR-0015 fingerprints):** base-product `stock` and variant `stock` disagree (base said `outOfStock` while variants reported `inStock` with hundreds of units), and variants can be `saleable: false` while `inStock`. The heartbeat fingerprint should key on **variant `saleable` ∧ `stockLevelStatus`**, not the base-product roll-up. Base-product `price` is a `FROM` price; variant `priceData` is the real `BUY` price.

**Caveats:** the `query=recertified` sweep surfaced mostly external/consumer recert products (My Book, Elements SE); the enterprise internal recert catalog (Gold/Red/Ultrastar) may sit under different category facets — enumerate categories/facets at connector build time. Endpoint auth posture could tighten at any time; re-verify before M1+ wiring.

## Seagate — direct store exists; bootstrap JSON is the compliant signal (tier: hidden bootstrap JSON)

**Open Item #2 answered: yes, Seagate sells recert direct.** `https://www.seagate.com/products/seagate-recertified/` with an Exos subcategory (`…/exos-recertified/`), plus an active `fy26q4-10-off-recertified-promo` legal page — the store is real and currently promoted. Six recert SKUs visible on the Exos category page: ST16000NM002C · ST20000NM002C · ST22000NM000C · ST24000NM000C · ST26000NM000C · ST28000NM000C (16–28 TB).

- **Compliant cheap signal:** the category page (AEM, ~547 KB HTML, robots-allowed with `Crawl-delay: 20`) embeds bootstrap JSON per SKU: `"ecommerceEnabled":true`, `"stock_status":"IN_STOCK"`, `"final_price":"549.99"`, `"is_preorder"`, `"percent_off"` (verified live for the three DR-datasheet'd SKUs). One GET per poll covers the whole category — heavier than a JSON API but a single request at the DR-008 variant/SKU grain.
- **Cheaper but disallowed:** `store.seagate.com` is Adobe Commerce/Magento; its GraphQL endpoint (`/graphql`) answers unauthenticated single-SKU queries with `stock_status` + `final_price` (verified live). **However `store.seagate.com/robots.txt` is `User-agent: * / Disallow: /`** — under the spec's `ROBOTSTXT_OBEY=True` guardrail (NG-002/C-007 posture) this endpoint must **not** be polled. Recorded here so nobody "rediscovers" it later and wires it in without noticing the robots posture.

**Caveats:** `www.seagate.com` crawl-delay is 20 s — irrelevant at heartbeat cadence but binding for any burst crawling. The category page's JSON shape is front-end hydration data (bootstrap tier in the OQ8 taxonomy): canary it at the 8 h bootstrap-JSON cadence.

## Consequences for the fast-lane registry (initial values, self-correcting per OQ9)

- The reconciliation's fast-lane candidate table rows "WD direct recert — ⏳ pending" and "Seagate direct recert — ⏳ pending" both flip to ✅ **eligible**: WD at 2–5 min via OCC (`search` sweep for transitions; per-product variant fetch on transition), Seagate at 2–5 min via one category-page GET.
- The reconciliation's organizing anti-correlation ("burstiest sources have no cheap signal") is now **broken in the right direction** — its two counterexamples were exactly the sources this spike probed. The general resolution pattern already ratified ("where the signal is cheap, poll fast by default and let observed data downgrade") now applies to both.
- Both signals ride ADR-0015's heartbeat grain unchanged (fingerprint = price + stock + shipping state at variant/SKU grain); no data-model or spec change needed. The per-source registry entries are build-time config (OQ9 territory), not spec edits.

## Method & limitations

Plain `curl` GETs with a standard desktop-browser User-Agent string, ≤10 requests total across both properties, no cookies, no JS execution, no CAPTCHA/anti-bot interaction encountered or attempted. This was a **point-in-time** probe (2026-07-04): auth posture, robots files, and endpoint shapes churn — re-verify both endpoints during connector build (M1+), and re-check `store.seagate.com`'s robots file in case the Disallow is ever relaxed. WD's Bazaarvoice/loyalty page keys observed in page source are third-party embed keys and deliberately not recorded here.

## Sources

| URL | Title | Date | Authority |
| --- | --- | --- | --- |
| https://www.westerndigital.com/products/recertified | WD recertified store (AEM config div = endpoint discovery) | fetched live 2026-07-04 | official |
| https://api.westerndigital.com/wdwebservices/v2/us/products/search?query=recertified | WD OCC product search (verified response) | fetched live 2026-07-04 | official |
| https://www.westerndigital.com/robots.txt | WD robots (recert pages allowed) | fetched live 2026-07-04 | official |
| https://www.seagate.com/products/seagate-recertified/exos-recertified/ | Seagate Exos recert category page (embedded SKU JSON) | fetched live 2026-07-04 | official |
| https://www.seagate.com/sitemap.xml | Seagate sitemap (recert section discovery) | fetched live 2026-07-04 | official |
| https://www.seagate.com/robots.txt | Seagate main-site robots (crawl-delay 20) | fetched live 2026-07-04 | official |
| https://store.seagate.com/robots.txt | Seagate store robots (`Disallow: /` — GraphQL off-limits) | fetched live 2026-07-04 | official |
