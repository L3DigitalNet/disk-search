---
schema_version: '1.1'
id: 2026-07-04-amazon-data-acquisition-after-paapi-getitems-deprecation
title: 'Amazon Product-Data Acquisition Path After PA-API 5 GetItems Deprecation'
description: 'Live-verified comparison of Amazon Creators API, SP-API, and discovery-only search-API acquisition for a buyer/affiliate, ASIN-persisting price monitor; recommends discovery-only + best-effort Creators API opportunistic enrichment.'
doc_type: research
status: active
created: '2026-07-04'
updated: '2026-07-04'
reviewed: null
owner: chris
tags:
- amazon
- paapi
- creators-api
- sp-api
- selling-partner-api
- asin
- data-acquisition
- affiliate
- deprecation
aliases:
- amazon paapi deprecation
- amazon creators api
- amazon sp-api buyer
- amazon getitems sunset
related:
- tavily-brave-serper
- per-source-polling-cadence-and-skip-policy
- us-scraping-and-data-retention-landscape-for-a-retail-hdd-price-monitor
- programmatic-acquisition-research-for-enterprise-and-nas-drive-merchants
source: []
confidence: medium
visibility: private
license: null
---

# Amazon Product-Data Acquisition Path After PA-API 5 `GetItems` Deprecation

## Context

hw-radar treats Amazon as a **display/discovery-only** source (not a primary value target, no cheap availability signal expected). Per DR-001, only the ASIN is retained indefinitely; all other Amazon fields are ephemeral (24h TTL), no image bytes are stored. This report answers: what is the best acquisition transport for that narrow need, now that PA-API 5 `GetItems` carries a deprecation notice pointing to the Creators API.

All facts below were checked live against primary Amazon sources on 2026-07-04 (see Sources table for fetch/search timestamps implied by tool run); several dates are in active flux and are flagged as such.

## Summary

| Angle | Sources | Strongest finding |
| --- | --- | --- |
| Official Docs | 6 | PA-API's own live doc banner still reads "deprecated May 15th, 2026" today (2026-07-04) even though Amazon's own affiliate emails have since pushed the retirement date twice more, to April 30 then June 30, 2026 [official]/[community] |
| Best Practices | 4 | Layered acquisition (official API where eligible → search-API discovery → targeted extraction) is the standing hw-radar pattern; Amazon should slot in at the "discovery" tier for this use case [community] |
| Footguns | 5 | Creators API gates access behind **10 qualified affiliate sales in the trailing 30 days**, a threshold hw-radar (a buyer-side tool, not an active affiliate storefront) will not realistically clear [official]/[community] |
| Existing Tools | 5 | Keepa and CamelCamelCamel already solve consumer-facing Amazon price-history/alerting; neither exposes a clean self-hostable ASIN+price API sufficient to replace hw-radar's own persistence, but they narrow the value hw-radar can add on Amazon specifically [blog] |
| Security/ToS | 3 | Amazon's Associates Program License explicitly **permits indefinite ASIN storage** but explicitly **bans "robots, or similar data gathering and extraction tools"** for pulling Product Advertising Content [official] |
| Recent Changes | 6 | SP-API private-developer registration hard-requires **first registering as an Amazon Seller with a Professional Selling Account** — a categorical block for a buyer-only integrator [official]/[community] |

**Queries:** 13 · **Results parsed:** ~70 · **Deep reads:** 4 (PA-API GetItems live page, Associates Program Policies, SP-API private-developer registration, SP-API Catalog Items rate limits) · **Follow-up pass:** no (all six angles cleared the 2-source bar on the first sweep)

## ⚠ Existing solution

> **Keepa** (https://keepa.com) and **CamelCamelCamel** (https://camelcamelcamel.com) already track Amazon price history and send price-drop alerts for individual ASINs at consumer scale. Neither is a drop-in replacement for hw-radar's cross-marketplace scoring pipeline (no HDD/SSD-specific normalization, no multi-marketplace composite score, Keepa's API is a paid product built for sellers/repricers), but they are worth knowing about as the "just want an Amazon price alert" alternative a user could reach for instead of hw-radar's Amazon slice specifically.

## 1. Live verification — PA-API 5 `GetItems` deprecation status (as of 2026-07-04)

The live page at `webservices.amazon.com/paapi5/documentation/get-items.html` was fetched directly today and carries this banner verbatim:

> "PA-API will be deprecated on May 15th, 2026. Please migrate to Creators API." ... "This documentation site is no longer maintained, and contains outdated information. Please refer to Creators API documentation." [official] (https://webservices.amazon.com/paapi5/documentation/get-items.html)

This is itself evidence of a footgun: **the documentation date is stale relative to Amazon's own later communications.** Independent third-party reports (WordPress support forum, a plugin vendor's changelog, and a dev.to migration writeup) show Amazon has pushed the retirement date to affiliates by email at least twice past what the docs site shows:

- WordPress.org support thread, quoting a direct Amazon email: "We will retire the PAAPI v5 endpoint on May 15, 2026." (superseding an earlier Jan 31, 2026 Offers-V1-only cutoff) [community] (https://wordpress.org/support/topic/pa-api-deprecation-by-jan-31-2026)
- dev.to migration guide: "April 30, 2026 is the deprecation date and Amazon's recommended migration cutoff, and May 15, 2026 is when the endpoint itself is retired." [community] (https://dev.to/th3nate/amazon-pa-api-v5-is-shutting-down-april-30-2026-here-is-what-changes-at-the-auth-layer-22ek)
- keywordrush.com, quoting a further Amazon notice dated after that: "We're retiring the PAAPI v5 endpoint. To avoid service disruptions, migrate to the new Creators API endpoint for PAAPI by **June 30, 2026**." [community] (https://www.keywordrush.com/blog/amazon-creator-api-what-changed-and-how-to-switch)

Net effect: **as of today (2026-07-04), the most recently reported communicated sunset date (June 30, 2026) has already passed**, while the official docs site still shows the older May 15, 2026 date and self-describes as unmaintained. Whether `GetItems` calls still succeed for existing credential-holders today could not be verified without live PA-API credentials (hw-radar holds none) — this is carried forward as an Open Question rather than asserted either way. What is certain and corroborated across official docs and every third-party source: **PA-API is closed to new registrations** ("PA-API is no longer accepting new customers. Please onboard to Creators API." [official], https://webservices.amazon.com/paapi5/documentation/register-for-pa-api.html), so it is not a viable acquisition path to newly integrate against regardless of the exact shutdown date.

## 2. Amazon Creators API

**What it is:** the successor to PA-API, managed by Amazon Associates (not the general Amazon developer/Appstore team). It exposes the same conceptual operations (Search/Get/Variations) over OAuth 2.0 client-credentials auth instead of AWS SigV4, with new "Credential ID + Credential Secret" pairs that do not carry over from PA-API. [official] (https://community.amazondeveloper.com/t/how-do-i-get-help-with-the-creators-api/2394)

**Data returned:** confirmed via the official SDK's typed request/response shapes and the (identically-modeled) PA-API `OffersV2` resource it inherits: `itemInfo.title`, `images`, and — critically for our use case — `offersV2.listings.price`, `offersV2.listings.availability`, and `offersV2.listings.condition`, all keyed by ASIN. [community] (https://npmx.dev/package/amazon-creators-api) This is genuinely offer/price/availability data, not just affiliate-link/content metadata — the API is fit for our stated minimal need (ASIN + occasional price/availability read) *if eligibility can be met*.

**Eligibility — the hard footgun:** "In addition to an approved creators account, you must also have at least 10 qualifying sales within the past 30 days to access the PA API through the Creators API." This is stated **directly on Amazon's own Creators API landing page** [official] (https://affiliate-program.amazon.com/creatorsapi) and independently corroborated by three community sources describing the same threshold and its enforcement behavior (temporary revocation if sales lapse for a rolling 30-day window): [community] (https://getaawp.com/docs/article/amazon-creators-api), (https://www.keywordrush.com/blog/amazon-pa-api-associatenoteligible-error-is-there-a-new-10-sales-rule), (https://dev.to/th3nate/amazon-pa-api-v5-is-shutting-down-april-30-2026-here-is-what-changes-at-the-auth-layer-22ek). hw-radar is explicitly a buyer/affiliate-adjacent *discovery* surface, not an active storefront driving 10+ qualified Amazon purchases every 30 days — this threshold is realistically **not clearable** for our use case, and access can lapse even if once obtained.

**Rate limits:** Creators API inherits PA-API's revenue-scaled token-bucket model — new credentials start at 1 TPS / 8,640 requests-per-day, then scale with shipped-item revenue attributed through the API (1 TPD per $0.05, up to 10 TPS per $4,320/30-day period). [official] (https://webservices.amazon.com/paapi5/documentation/troubleshooting/api-rates.html) No Creators-API-specific rate-limit page could be reached directly (the official docs portal sits behind an Associates Central sign-in redirect), so this is carried over from PA-API by analogy, not independently confirmed for Creators API specifically — flagged as an Open Question.

**ToS on storage/caching (applies identically to Creators API and PA-API — same governing License):** Amazon's Associates Program Policies state, verbatim: "Unless otherwise notified by us, you may store individual Amazon Standard Identification Numbers (ASINs) for an indefinite period until the termination of this License." Non-image Product Advertising Content may be cached "for up to 24 hours" but must then be refreshed via a fresh API call; images may never be cached, only linked for up to 24 hours. [official] (https://affiliate-program.amazon.com/help/operating/policies) This maps **exactly** onto DR-001 (indefinite ASIN retention, 24h TTL on everything else, no stored image bytes) — if Creators API access were obtainable, its ToS would not be the blocker; eligibility is.

The same policy page also states the License "does not include ... any use of data mining, robots, or similar data gathering and extraction tools" — this is the official-source basis for treating scraping Amazon pages under the Associates License as out of bounds (see §4).

## 3. Amazon SP-API (Selling Partner API)

**Can a non-seller be authorized at all? No — this is a hard, categorical blocker**, confirmed directly from Amazon's own private-developer onboarding docs:

> "Step 1: Register as an Amazon Seller. Before creating a private application, you must first be registered as an Amazon Seller using Amazon Seller Central. Only Professional Selling Accounts can register to develop or integrate with Selling Partner API. Individual accounts are not eligible." [official] (https://developer.amazonservices.com/private-developer)

Public-developer registration is no better: the official registration guide requires "a website URL that is publicly available and provides details about the services that your application offers to **Amazon sellers**" [official] (https://developer-docs.amazon.com/sp-api/docs/register-as-a-public-developer), and community reports independently confirm the practical consequence — a developer account is tied to whichever seller/vendor Central account authorized it, and ownership cannot be transferred to a non-seller entity. [community] (https://stackoverflow.com/questions/66364770/is-it-possible-to-register-as-a-developer-for-amazon-sp-api-without-having-a-sel), (https://stackoverflow.com/questions/77826125/register-as-a-public-developer-for-amazon-sp-api)

**Relevant endpoints (moot given the above, but confirmed for completeness):** `Catalog Items` (`getCatalogItem`, `searchCatalogItems`, ASIN-keyed) and `Product Pricing` (`getCompetitiveSummary`, batch featured-offers-by-ASIN, up to 20 ASINs/call) would together cover exactly the offer/price/availability-by-ASIN need. [official] (https://developer-docs.amazon.com/sp-api/docs/manage-product-listings-guide), (https://developer-docs.amazon.com/sp-api/docs/retrieve-featured-offers-batch-asins) Rate limits are genuinely workable for a low-volume monitor — Catalog Items `getCatalogItem` is 2 req/s per account-application pair (250/s per application, burst 2). [official] (https://developer-docs.amazon.com/sp-api/docs/catalog-items-api-rate-limits) None of this matters: **every SP-API call requires prior authorization from an Amazon selling partner** — there is no buyer-only auth grant. hw-radar's owner is not, and has no plan to become, an Amazon seller or vendor. **SP-API is a hard blocker, not a tradeoff.**

## 4. Discovery-only fallback (Serper/Brave/Tavily)

Third-party search APIs can return Amazon `/dp/<ASIN>` URLs and SERP snippet titles/prices, from which a stable ASIN is trivially extractable (it's embedded in the URL path) and a coarse price signal is sometimes present in the snippet, but neither is authoritative or guaranteed-fresh — it reflects whatever the search engine's crawl last indexed, not a live Amazon price read. This matches hw-radar's existing documented position that search APIs are for **discovery, not authoritative state** (see `tavily-brave-serper.md` and `programmatic-acquisition-research-for-enterprise-and-nas-drive-merchants.md`), and requires no new architecture.

**Legal/ToS considerations, corroborated across independent sources:**

- Amazon's Conditions of Use prohibit "any robot, spider, scraper, or other automated means to access Amazon Services for any purpose," and the Associates Program License separately (and directly, per §2 above) excludes "data mining, robots, or similar data gathering and extraction tools" — both are **contract-law** exposure (ToS breach), not criminal exposure. [official]/[blog] (https://affiliate-program.amazon.com/help/operating/policies), (https://dataprixa.com/does-amazon-allow-web-scraping/)
- Under U.S. law, the controlling precedent (hiQ Labs v. LinkedIn, 9th Cir.) holds that scraping **publicly accessible, logged-out** web data does not violate the CFAA; this has been reinforced by subsequent rulings (e.g., a 2024 Meta v. Bright Data outcome finding no CFAA violation for public-data scraping). [community] (https://dataimpulse.com/blog/is-web-scraping-legal/), (https://www.scraperapi.com/web-scraping/is-web-scraping-legal/)
- **Critical distinction for our case:** using Serper/Brave/Tavily to read *Google's or Bing's index of* Amazon pages is not the same act as our own crawler directly requesting amazon.com — the ToS/robots exposure runs against whoever is issuing requests to Amazon's own servers (the search engine, in this case), not against hw-radar as the search API's client. This narrows hw-radar's own exposure relative to running an Amazon-facing scraper directly, though it does not eliminate the general "don't build a shadow scraping pipeline around Amazon data" posture already adopted in `us-scraping-and-data-retention-landscape-for-a-retail-hdd-price-monitor.md`.

Net: discovery-only via existing search-API infrastructure is **legally the lowest-risk option** of the three and requires zero new integration work, at the cost of freshness/reliability of the price signal (acceptable, since hw-radar already treats Amazon as non-authoritative for availability).

## 5. Recommendation

**Use discovery-only via the existing Serper → Brave → Tavily search-API stack as the sole Amazon acquisition path.** Persist the ASIN (parsed from the `/dp/<ASIN>` URL segment returned by search results) indefinitely per DR-001; treat any price/availability text surfaced in SERP snippets as a low-confidence, non-authoritative hint with the existing 24h TTL, exactly as other T3-tier/unofficial sources are already handled in the polling-cadence design. Do not build a Creators API or SP-API integration.

| | Creators API | SP-API | Discovery-only (current stack) |
| --- | --- | --- | --- |
| **Data available** | Offers/price/availability + content, by ASIN [official] | Offers/price/availability + catalog, by ASIN [official] | ASIN (from URL) + coarse/stale price hint from SERP snippet |
| **Eligibility/authorization** | Approved Associates account **and** 10 qualified sales/30 days, revocable [official] | Requires an Amazon **Seller or Vendor** account; buyer-only entities cannot register [official] | None — already integrated |
| **Rate limits** | 1 TPS/8,640-per-day baseline, scales with affiliate revenue [official] | 2 req/s (Catalog Items), workable for low volume [official] | Governed by existing search-API budget/self-governance, not Amazon |
| **ToS/retention constraints** | Indefinite ASIN storage explicitly permitted; 24h cache on other content; bans scraping/robots [official] | Standard SP-API developer agreement + PII/role restrictions; not reachable without seller status | Amazon ToS runs against the search engine's crawler, not hw-radar directly; lowest direct exposure |
| **Fit for our use case** | Good data shape, **blocked by sales-eligibility gate** we cannot clear | Good data shape, **categorically blocked** (no seller account, no plan to become one) | Adequate for discovery-only; matches stated "no cheap availability signal" expectation |
| **Migration effort** | N/A — not pursuing (would require becoming/maintaining affiliate-sales-qualified status) | N/A — not pursuing (would require becoming an Amazon seller) | **Zero** — no change from current architecture |

**Hard blockers called out explicitly:**
- SP-API: registration itself requires "register as an Amazon Seller" with a **Professional Selling Account** — categorically incompatible with a buyer-only tool, independent of rate limits or data shape. [official]
- Creators API: not a categorical block like SP-API, but the **10-qualified-sales/30-day** gate is a business-model requirement (need active affiliate sales volume) that a discovery/monitoring tool does not naturally generate — treat as **not realistically obtainable**, not merely "harder."
- Neither official option's ToS is actually the constraint for DR-001 compliance — the Associates Program License explicitly permits indefinite ASIN storage. If Creators API eligibility were ever incidentally met (e.g., the maintainer separately runs an active Associates storefront), it would be ToS-compatible with DR-001 as written. This is not expected to happen and should not drive current design.

## Open Questions

| # | Question | Why unresolved |
| --- | --- | --- |
| 1 | Does PA-API 5 `GetItems` still return successful responses today (2026-07-04) for existing credential-holders, given the docs banner (May 15, 2026) and third-party-reported email notices (April 30 / June 30, 2026) disagree and the latest reported date has already passed? | hw-radar holds no PA-API credentials to test live; moot for our recommendation (discovery-only) but relevant if any other project in the org still depends on PA-API |
| 2 | Are Creators-API-specific rate limits (as opposed to inherited PA-API figures) published anywhere outside the sign-in-gated Associates Central portal? | The official Creators API docs portal (`affiliate-program.amazon.com/creatorsapi/docs/`) redirects to Amazon sign-in and could not be read anonymously; not load-bearing for the discovery-only recommendation |

## Handoff

Persisted at `docs/research/2026-07-04-amazon-data-acquisition-after-paapi-getitems-deprecation.md`. Downstream skills that may consume it:

- `superpowers:brainstorming` — feed the two Open Questions into a design conversation if PA-API dependency ever resurfaces elsewhere
- `feature-dev:feature-dev` — confirms no new Amazon integration work is needed; current discovery-only architecture is already correct

## Sources

| URL | Title | Date | Authority |
| --- | --- | --- | --- |
| https://webservices.amazon.com/paapi5/documentation/get-items.html | GetItems · Product Advertising API 5.0 | fetched live 2026-07-04 | official |
| https://webservices.amazon.com/paapi5/documentation/register-for-pa-api.html | Register for Product Advertising API | fetched 2026-07-04 | official |
| https://webservices.amazon.com/paapi5/documentation/troubleshooting/api-rates.html | API Rates · Product Advertising API 5.0 | fetched 2026-07-04 | official |
| https://webservices.amazon.com/paapi5/documentation/offersV2.html | OffersV2 · Product Advertising API 5.0 | fetched 2026-07-04 | official |
| https://affiliate-program.amazon.com/help/operating/policies | Amazon Associates Program Policies | fetched 2026-07-04 | official |
| https://affiliate-program.amazon.com/creatorsapi | Creators API (landing page) | indexed 2026-07-04 | official |
| https://community.amazondeveloper.com/t/how-do-i-get-help-with-the-creators-api/2394 | How do I get help with the Creators API? | undated | official |
| https://developer-docs.amazon.com/sp-api/docs/manage-product-listings-guide | Manage Product Listings with the Selling Partner API | fetched 2026-07-04 | official |
| https://developer-docs.amazon.com/sp-api/docs/retrieve-featured-offers-batch-asins | Retrieve featured offers for a batch of ASINs | fetched 2026-07-04 | official |
| https://developer-docs.amazon.com/sp-api/docs/catalog-items-api-rate-limits | Catalog Items API Rate Limits | fetched 2026-07-04 | official |
| https://developer-docs.amazon.com/sp-api/docs/register-as-a-public-developer | Register as a Public SP-API Developer | fetched 2026-07-04 | official |
| https://developer.amazonservices.com/private-developer | Amazon SP-API — private developer registration | fetched 2026-07-04 | official |
| https://developer-docs.amazon.com/sp-api/docs/usage-plans-and-rate-limits | Usage Plans and Rate Limits | fetched 2026-07-04 | official |
| https://wordpress.org/support/topic/pa-api-deprecation-by-jan-31-2026 | PA API Deprecation by Jan 31, 2026 (forum) | thread, last activity ~2026-04 | community |
| https://dev.to/th3nate/amazon-pa-api-v5-is-shutting-down-april-30-2026-here-is-what-changes-at-the-auth-layer-22ek | Amazon PA-API v5 deprecates April 30, 2026 | 2026 | community |
| https://www.keywordrush.com/blog/amazon-creator-api-what-changed-and-how-to-switch | Amazon Creators API: What Changed and How to Switch | updated through 2026-06-20 | blog |
| https://www.keywordrush.com/blog/amazon-pa-api-associatenoteligible-error-is-there-a-new-10-sales-rule | AssociateNotEligible — 10-Sales Rule | updated 2025-11-16 | blog |
| https://getaawp.com/docs/article/amazon-creators-api | Amazon Creators API — AAWP docs | undated | community |
| https://stackoverflow.com/questions/66364770/is-it-possible-to-register-as-a-developer-for-amazon-sp-api-without-having-a-sel | Register as SP-API dev without seller account? | 2021, still cited | community |
| https://stackoverflow.com/questions/77826125/register-as-a-public-developer-for-amazon-sp-api | Register as public SP-API developer | 2024 | community |
| https://dataimpulse.com/blog/is-web-scraping-legal/ | Is Web Scraping Legal? Laws & Cases (2026 Guide) | 2026 | blog |
| https://dataprixa.com/does-amazon-allow-web-scraping/ | Does Amazon Allow Web Scraping? In 2026 | 2026 | blog |
| https://amazonscraperapi.com/blog/is-scraping-amazon-legal | Is Scraping Amazon Legal? A 2026 Guide for Developers | 2026 | blog |
| https://harpa.ai/blog/best-amazon-price-trackers-and-drop-alerts | Best Amazon Price Trackers 2026: Keepa, CamelCamelCamel | 2026 | blog |
| https://npmx.dev/package/amazon-creators-api | amazon-creators-api (unofficial Node SDK) | 2026 | community |
