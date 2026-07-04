---
schema_version: '1.0'
id: 2026-07-03-currency-conversion-and-landed-cost-estimation-for-cross-border-drive-price-scoring
title: Currency Conversion and Landed-Cost Estimation for Cross-Border Drive Price Scoring
description: FX API selection, US de-minimis/duty/VAT landed-cost model, and a pragmatic scoring approach for normalizing GBP/EUR UK/EU refurbished-enterprise-drive listings to comparable landed USD $/TB against US buyers.
doc_type: research
status: active
created: '2026-07-03'
updated: '2026-07-03'
reviewed: '2026-07-03'
owner: hw-radar
tags:
- currency-conversion
- landed-cost
- customs-duty
- de-minimis
- cross-border-ecommerce
aliases:
- landed cost estimation
- FX conversion for drive scoring
- de minimis 2026
related: []
source:
- https://frankfurter.dev
- https://www.cbp.gov/trade/basic-import-export/e-commerce/faqs
- https://www.federalregister.gov/documents/2026/06/24/2026-12670/indefinite-suspension-of-the-de-minimis-exemption-for-merchandise-arriving-through-all-modes-other
- https://www.ecfr.gov/current/title-19/chapter-I/part-159/subpart-C
- https://hts.usitc.gov/search?query=8471
- https://www.gov.uk/guidance/vat-on-goods-exported-from-the-uk-notice-703
confidence: high
visibility: private
license: null
---

# Currency Conversion and Landed-Cost Estimation for Cross-Border Drive Price Scoring

## Bottom line

For a hobby/small-business USD-per-TB scorer, use **Frankfurter** (ECB-sourced, free, no key, open source, self-hostable) for daily GBP/EUR→USD rates, store the rate and its date alongside every scored observation, and refresh once per day (FX for used/refurb hardware does not need intraday precision). Do **not** attempt to compute exact customs duty programmatically. As of **2026**, the US de-minimis exemption that used to let sub-$800 shipments skip duty is **suspended indefinitely for all countries** (CBP interim final rules effective **June 24, 2026**), and the "reciprocal tariff" regime that would set the actual add-on rate for UK/EU goods is **in legal flux** post-Supreme-Court ruling (Feb 20, 2026) and currently running on a temporary Section 122 authority that itself has an expiration/renewal cycle. Given that instability, a scoring engine should (a) convert currency using a defensible, timestamped rate, (b) add a conservative flat "international overhead" haircut to the landed-cost estimate (freight + likely duty/brokerage band), and (c) flag international listings with a "verify shipping/duty — cross-border rules changed in 2025-2026" badge rather than presenting a false-precision duty figure. This is corroborated by CBP's own official guidance, the Federal Register, and multiple independent trade-law trackers (see Sources).

## Summary

| Angle          | Sources | Strongest finding |
| -------------- | ------- | ----------------- |
| Official Docs  | 7       | CBP confirms Aug 29, 2025 global de-minimis suspension; June 24, 2026 interim final rules make it indefinite [official] |
| Best Practices | 4       | Landed-cost = COGS + freight + insurance + duty + tax + brokerage; HS code is the pivot for duty lookup [community] |
| Footguns       | 5       | De-minimis suspension is NOT restored by the Feb 2026 SCOTUS IEEPA ruling — different legal authority [official + community, 3+ sources] |
| Existing Tools | 4       | Zonos/Easyship/Dutify offer landed-cost APIs, but per-order pricing (Zonos: $2 + 10% of duty) is uneconomical at hobby scale [community] |
| Security       | 3       | CBP uses 19 CFR 159 certified quarterly/date-of-exportation rates for actual duty calc — different from any market-rate API a scorer would use [official] |
| Recent Changes | 6       | Reciprocal tariffs (UK 10%, EU up to 15%) invalidated by SCOTUS Feb 20, 2026; replaced by temporary 10% global Section 122 tariff, itself expiring/renewing on a ~150-day clock [official + community] |

**Queries:** 11 · **Results parsed:** ~70 · **Deep reads:** 0 (search snippets were sufficiently authoritative; no extract calls were needed beyond search-result content) · **Follow-up pass:** no (all six angles cleared the 2-source bar on the first pass)

## Official Documentation

- CBP's own e-commerce FAQ confirms: "Effective August 29, 2025, this Executive Order suspends duty-free treatment for low-value shipments (valued at or under $800) from all countries." [official] (https://www.cbp.gov/trade/basic-import-export/e-commerce/faqs)
- Federal Register interim final rule: CBP indefinitely suspended the $800 de-minimis exemption for all non-postal modes effective **June 24, 2026**, and separately built a new postal informal-entry process for mail shipments valued ≤ $2,500 (delayed compliance date **October 22, 2026** for specified shipments). Public comments were due July 24, 2026. [official] (https://www.federalregister.gov/documents/2026/06/24/2026-12670/indefinite-suspension-of-the-de-minimis-exemption-for-merchandise-arriving-through-all-modes-other)
- 19 CFR Part 159 Subpart C (currency conversion for customs purposes): CBP must use a "proclaimed rate" or Federal-Reserve-Bank-of-NY "certified rate," fixed to the **date of exportation**, not a live market rate — this is legally distinct from whatever FX API a price-scoring tool uses, and CBP publishes its own weekly "Foreign Currency Exchange Rate Multipliers." [official] (https://www.ecfr.gov/current/title-19/chapter-I/part-159/subpart-C, https://www.cbp.gov/trade/programs-administration/determining-duty-rates/foreign-currency-exchange-rates)
- HTS classification for hard disk drives sits under heading **8471.70** (e.g., 8471.70.40.65 / 8471.70.50.65 "Hard magnetic disk drive units"), and CBP CROSS binding rulings show these have historically carried a **General (Column 1/MFN) duty rate of "Free" (0%)**. SSDs classify separately under **8523.51** (semiconductor media) per CBP ruling HQ H296912. [official] (https://hts.usitc.gov/search?query=8471, https://rulings.cbp.gov/ruling/R02941, https://www.customsmobile.com/rulings/docview?doc_id=HQ+H296912)
- UK VAT Notice 703 confirms goods can be **zero-rated for VAT when exported outside the UK**, subject to the retailer holding valid proof of export — meaning a compliant UK merchant should not be charging UK VAT on a sale shipped to a US buyer. [official] (https://www.gov.uk/guidance/vat-on-goods-exported-from-the-uk-notice-703)
- Frankfurter's own docs describe it as tracking daily rates from 84 central banks (ECB-anchored), open source (MIT), with a documented self-host path and no API key requirement. [official-adjacent, project's own docs] (https://frankfurter.dev, https://frankfurter.dev/integrations)
- CBP FY2026 customs user fee notice (General Notice, 90 FR 34665, effective Oct 1, 2025): Merchandise Processing Fee (MPF) ad valorem rate stays **0.3464%**, with a minimum of **$33.58** and maximum of **$651.50** per formal entry; Informal Entry/Release fee is **$2.62**. [official] (https://www.buckland.com/news/cbp-announces-adjusted-customs-user-fees-for-fy-2026, corroborated at https://mohawkglobal.com/trade-translation/cbp-adjusts-customs-user-fees-for-inflation-effective-10-1-2025)

## Best Practices

- Standard landed-cost decomposition used across multiple vendor guides: **product cost + international freight + insurance + customs duty + import VAT/GST + brokerage/handling + currency conversion**, keyed off an accurate HS/HTS code — accuracy of the HS code is repeatedly cited as the single biggest lever on correctness. [community] (https://www.customsinfo.com/knowledge-center/landed-cost-calculation-an-integral-part-of-the-ecommerce-customer-experience, https://dutypilot.org/blog/calculate-landed-cost-dtc-2026)
- Multiple vendors (Zonos, Dutify) explicitly support returning an **approximate** landed-cost estimate even without a precise HS code or country of origin, falling back to broader classification tiers — validating that "approximate is acceptable" is an accepted industry pattern, not a shortcut unique to this tool. [community] (https://zonos.com/docs/supply-chain/landed-cost/get-started, https://docs.dutify.com/docs/landed-cost-calculator-api)
- Displaying landed cost (vs. price-only) at checkout is reported to materially change buyer behavior (conversion swings cited up to 100-300% in vendor marketing, treat as directional/vendor-sourced rather than verified) — relevant context for why marketplaces increasingly expose all-in price fields, but not itself load-bearing for a scoring engine. [blog] (https://www.easyship.com/blog/international-checkout-to-show-accurate-rates-taxes-duties-upfront-for-cross-border-shipping-services)
- For customs-law compliance (not just cost estimation), CBP's own valuation guidance fixes the FX conversion date to **date of exportation**, which a scoring tool should not attempt to replicate — a same-day or previous-business-day rate for scoring purposes is a reasonable, clearly-labeled approximation, not a customs-compliant valuation. [official] (19 CFR 159.32, cited above)

## Footguns and Gotchas

- **De-minimis suspension is not the same legal action as the reciprocal-tariff regime, and the Feb 20, 2026 SCOTUS ruling did NOT restore it.** Confirmed independently by CBP's own FAQ, the Federal Register text of EO 14388, and two independent trade-focused blogs explaining the SCOTUS ruling's scope — the $800 statutory threshold under 19 U.S.C. 1321 still exists in name, but duty-free treatment is suspended by a separate presidential/CBP regulatory action. — corroborated by https://www.cbp.gov/trade/basic-import-export/e-commerce/faqs, https://blog.ordoro.com/2026/02/25/de-minimis-exemption-2026, https://carraglobe.com/us-de-minimis-exemption-suspended-2026
- **The actual "extra" tariff rate on top of the base HTS duty for UK/EU goods is currently unstable and cross-referencing sources disagree by date.** Timeline: reciprocal tariffs under IEEPA (UK 10%, EU up to 15%, per EO "Further Modifying the Reciprocal Tariff Rates," July 2025) → SCOTUS ruled IEEPA-based tariffs unlawful Feb 20, 2026, CBP stopped collecting them Feb 24, 2026 → administration imposed a **10% global tariff under Section 122 of the Trade Act of 1974** as a replacement, itself time-limited (a federal appeals court upheld continued collection as of July 1, 2026, with commentary noting the authority's underlying ~150-day clock and a stated expiration near **July 24, 2026**) → separately, Section 232 tariffs on steel/aluminum/copper/pharma/semiconductors continue on their own track and are largely unrelated to plain HDDs. — corroborated by https://www.europarl.europa.eu/RegData/etudes/BRIE/2026/779864/ECTI_BRI(2026)779864_EN.pdf [official-adjacent, EU Parliament research], https://www.wiley.law/trump-administration-tariff-tracker, https://budgetlab.yale.edu/research/state-us-tariffs-scotus-ruling-update, https://ourtake.bakerbotts.com/post/102n7tq/trump-tariff-tracker-july-2-2026 — **treat any specific UK/EU ad-valorem add-on percentage as volatile and re-verify before hardcoding.**
- **UK VAT may or may not already be stripped from a scraped listing price**, depending on whether the merchant's storefront detects a non-UK shipping address before or after price display. Because VAT Notice 703 zero-rates *exports*, a properly compliant retailer's checkout price for a US-shipped order should exclude UK VAT (currently 20% standard rate) — but many storefronts display VAT-inclusive list prices to all visitors and only remove VAT at checkout. If a monitor scrapes the pre-checkout listing price, it likely still includes 20% VAT that the US buyer will never actually pay, which would make UK listings look artificially expensive relative to true landed cost. — corroborated by https://www.gov.uk/guidance/vat-on-goods-exported-from-the-uk-notice-703 [official] and cross-checked against general VAT-refund-mechanics explainers, https://www.expatica.com/uk/finance/taxes/vat-refund-uk-2173739 [blog]
- **Section 232 semiconductor tariffs (25%, effective Jan 15, 2026) are scoped to "advanced computing chips" and specified derivative products meeting defined technical parameters** — plain magnetic HDDs (HTS 8471.70) are very unlikely to be in scope, but SSDs (HTS 8523.51, semiconductor-media storage) are closer to the covered category and warrant a specific check if the tool ever scores SSDs. — corroborated by https://taxnews.ey.com/news/2026-0209-us-section-232-proclamation-imposes-25-percent-tariff-on-certain-semiconductors and CBP's own CSMS #67400472 guidance bulletin [official], https://content.govdelivery.com/accounts/USDHSCBP/bulletins/4047318

## Existing Tools

| Tool | Maintenance | Link | Fit for use case |
| ---- | ----------- | ---- | ----------------- |
| Zonos Landed Cost API | Active, commercial | https://zonos.com/landed-cost | Accurate and guaranteed, but priced **$2 + 10% of duties/taxes per order** — uneconomical for a passive scoring/monitoring tool that isn't processing real transactions |
| Easyship | Active, commercial | https://www.easyship.com | Has a free duty/tax calculator tool and shipping-rate API, oriented at merchants shipping *out*, not buyers estimating landed cost *in* |
| Dutify Landed Cost Calculator API | Active, commercial | https://docs.dutify.com/docs/landed-cost-calculator-api | Auto-classifies HS codes from product titles; per-call pricing model more compatible with low-volume batch scoring than Zonos's per-order model |
| SimplyDuty | Active, commercial | (per-call pricing ~£0.10/call, cited in trade-compliance-pricing roundup) | Cheapest per-call option surfaced in this research if precise duty numbers are ever wanted for a subset of listings |

None of these existing tools is a good fit for **passive, high-volume, low-stakes** listing scoring — they are built for merchants who need guaranteed, remittable duty figures at real checkout, not for a hobby-scale comparison engine. This supports the recommendation below to approximate rather than integrate.

## Security and Compatibility

- No CVEs or security advisories apply to FX-rate consumption specifically; the operationally relevant risk is **data licensing/rate-limit compliance**, not security. exchangerate.host (APILayer) has moved to a metered/paid model (free tier capped, e.g. 1,500 req/month cited for ExchangeRate-API-style competitors) — treat "free forever" claims for that family of APILayer products skeptically as of 2026; Frankfurter remains genuinely free/open-source with no published request cap because it is self-hostable. [community] (https://exchangerate.host/pricing, https://currencyfreaks.com/blog/ExchangeRate-Api-Pricing-Alternative)
- CBP's own currency-conversion rule (19 CFR 159.31) is a **compatibility/authority distinction, not a security issue**: any market-rate API a scorer uses is legally a different rate than what CBP would use to actually liquidate duty, so any "landed cost" the tool shows is necessarily an estimate, never a customs-compliant figure. [official]
- eBay's Browse API `getItem`/`getItems` shipping fields (`shippingOptions`, `shippingCost`, min/max estimated delivery dates) are officially documented and populated when the `X-EBAY-C-ENDUSERCTX` contextualLocation header is supplied — but eBay's own community forum has open questions from developers about getting cost estimates outside that specific flow, implying reliability depends on correctly setting buyer-location context on every call. [official + community] (https://developer.ebay.com/api-docs/buy/browse/types/gct:ShippingOption, https://community.ebay.com/t5/eBay-APIs-Talk-to-your-fellow/API-call-to-get-estimated-shipping-cost-ebay-shipping-calculator/td-p/34033804)

## Recent Changes

- **Aug 29, 2025:** Global suspension of the $800 Section 321 de-minimis duty-free exemption takes effect (EO 14324), following an earlier China/Hong-Kong-specific suspension (EO 14256, May 2, 2025). [official]
- **Feb 20, 2026:** SCOTUS rules IEEPA-based "reciprocal" tariffs unlawful; CBP stops collecting them Feb 24, 2026. Administration immediately imposes a new 10% global tariff under **Section 122 of the Trade Act of 1974** as a stopgap, and separately signs EO 14388 explicitly **continuing** the de-minimis suspension (confirming it survives the SCOTUS ruling because it rests on different legal authority). [official]
- **Jan 14-15, 2026:** Section 232 semiconductor tariff (25%) takes effect on advanced chips and defined derivative products — HDDs are very likely out of scope; SSDs merit a follow-up check if in scope for this tool. [official]
- **June 24, 2026:** CBP issues Interim Final Rules making the de-minimis suspension **indefinite** for all non-postal modes, plus a new postal informal-entry process (≤$2,500) for mail — public comments were open through July 24, 2026, meaning the rule could still be revised, but as of this report's date it is the current binding rule. [official]
- **As of ~July 2026 (report date):** the Section 122 10% global tariff (successor to the invalidated reciprocal tariffs) is reported as still being collected pending further litigation/renewal, with commentary suggesting the administration intends to migrate it to a more durable legal basis (e.g., Section 301) before its own expiration window closes. **This is the most volatile figure in the whole model and should be treated as a placeholder, not a constant.** [community, multiple corroborating trackers]

## Recommended landed-cost model for the scorer

**1. Currency conversion (implement now, cheap, low-risk):**
- Source: **Frankfurter** (`https://api.frankfurter.dev/v2/latest?from=GBP&to=USD` and `from=EUR&to=USD`), no API key, ECB-anchored, MIT-licensed, self-hostable as a fallback if the public instance ever becomes unavailable.
- Refresh cadence: **once per day** (a batch job, e.g. at scrape time or a scheduled cron before the daily scoring run) is more than sufficient — ECB ref rates themselves only update once per business day, and used-hardware pricing does not move at FX-tick granularity.
- Store, per observation: `fx_rate`, `fx_pair` (e.g., `GBPUSD`), `fx_rate_date` (the date the rate was published for, not just the timestamp fetched), and `fx_source` (`"frankfurter/ecb"`). This gives full auditability if a listing's USD/TB score is later questioned, and lets you detect stale-rate bugs (e.g., a weekend/holiday carry-forward) after the fact.
- Do not attempt to replicate CBP's 19 CFR 159 customs-valuation rate — it's a different rate for a different legal purpose (duty liquidation), not price comparison.

**2. Landed cost — approximate, don't compute exact duty:**
Full programmatic duty computation is **not** a good investment for this tool right now, for three independent reasons corroborated above: (a) the underlying US tariff regime for UK/EU goods is in active legal flux (SCOTUS ruling → Section 122 stopgap → pending renewal/replacement) such that any hardcoded percentage will likely be wrong within months; (b) even the base HTS duty for HDDs (0% under Column 1/MFN) can be overridden by whichever surcharge regime is currently active, and that surcharge is exactly the volatile part; (c) all existing commercial landed-cost APIs (Zonos, Easyship, Dutify) are priced/architected for real checkout transactions, not passive listing-comparison at hobby scale.

Recommended pragmatic model:
1. Convert listing price to USD using the daily Frankfurter rate (auditable, cheap, accurate for the actual conversion step).
2. Add a flat, editable **"international overhead" constant** (e.g., a configurable percentage or dollar band, initially set conservatively, e.g. 15-25% of item price, reflecting a plausible blend of international freight + a plausible duty/brokerage range under the current suspended-de-minimis regime) rather than a computed duty figure.
3. Surface an explicit **"International — verify shipping/duty (US de-minimis suspended as of 2026; rates subject to change)"** flag/badge on every non-US-origin listing, with a link or tooltip pointing at the fact that landed cost is an estimate, not a guarantee.
4. Revisit the flat overhead constant periodically (e.g., quarterly) rather than trying to keep pace with the tariff litigation in real time — this is explicitly the trade-off the research surfaced: precision here decays faster than a small tool can reasonably track.

**3. Folding shipping into $/TB generally (domestic and international):**
- Score on **item price + shipping (+ applicable buyer-side tax where knowable)**, not item price alone — domestic listings with "free shipping" folded into a higher item price and listings with a separate shipping charge are not comparable on item price alone, and this generalizes directly to the cross-border case (landed cost is simply "shipping cost, but with a customs/duty component added").
- Marketplace `delivery`/shipping fields (e.g., eBay Browse API's `shippingOptions.shippingCost`) are officially documented and can be reasonably reliable **only when the request correctly supplies the buyer's destination context** (`X-EBAY-C-ENDUSERCTX: contextualLocation=...`); without that, shipping estimates can silently default to seller-location assumptions. For merchants without a shipping API (most of the UK/EU refurb resellers per the companion acquisition research), shipping cost will need to be scraped from the product page or estimated with a merchant-specific flat default, clearly flagged as an estimate rather than presented with false precision equal to a directly-sourced number.
- When shipping cost cannot be determined at all (neither API field nor visible page text), prefer a documented default-and-flag approach over silently scoring on item price alone, to avoid systematically under-scoring the true cost of listings with hidden/high shipping.

## Open Questions

| # | Question | Why unresolved |
| --- | --- | --- |
| 1 | What is the current, binding ad-valorem add-on rate for UK-origin and EU-origin goods once the Section 122 tariff's ~July 24, 2026 window closes? | Actively litigated/renewing as of the report date; no source could give a stable post-expiration answer |
| 2 | Do any of the monitored UK/EU refurb resellers already strip VAT for US-bound checkouts, or do their scraped listing prices still include UK/EU VAT? | Merchant-specific behavior; requires a live checkout test per merchant, out of scope for a desk-research pass |
| 3 | Are SSDs (HTS 8523.51) ever in scope for this tool, and if so, do they fall under the Jan 2026 Section 232 semiconductor tariff's technical parameters? | Only relevant if the tool's scope expands beyond HDDs; not resolved because current scope is HDDs |

## Handoff

Persisted at `/home/chris/projects/hw-radar/docs/research/2026-07-03-currency-conversion-and-landed-cost-estimation-for-cross-border-drive-price-scoring.md`. Downstream skills that may consume it:

- `superpowers:brainstorming` — feed Open Questions (esp. #1, the tariff-volatility question) into a design conversation about how often to revisit the flat overhead constant
- `feature-dev:feature-dev` — implement the Frankfurter-based FX fetch/store pipeline and the international-listing flag described in the recommended model

## Sources

| URL | Title | Date | Authority |
| --- | ----- | ---- | --------- |
| https://www.cbp.gov/trade/basic-import-export/e-commerce/faqs | E-Commerce Frequently Asked Questions | 2026 | official |
| https://www.federalregister.gov/documents/2026/06/24/2026-12670/... | Indefinite Suspension of the De Minimis Exemption... | 2026-06-24 | official |
| https://www.whitehouse.gov/presidential-actions/2026/02/continuing-the-suspension-of-duty-free-de-minimis-treatment-for-all-countries | EO 14388 | 2026-02-20 | official |
| https://www.ecfr.gov/current/title-19/chapter-I/part-159/subpart-C | 19 CFR Part 159 Subpart C — Conversion of Foreign Currency | current | official |
| https://www.cbp.gov/trade/programs-administration/determining-duty-rates/foreign-currency-exchange-rates | CBP Foreign Currency Exchange Rates | 2025-09-30 | official |
| https://hts.usitc.gov/search?query=8471 | Harmonized Tariff Schedule, heading 8471 | current | official |
| https://rulings.cbp.gov/ruling/R02941 | CBP CROSS Ruling R02941 (HDD classification, Free duty) | 2006-01-04 | official |
| https://www.customsmobile.com/rulings/docview?doc_id=HQ+H296912 | CBP Ruling HQ H296912 (SSD classification, 8523.51) | historical | official |
| https://www.gov.uk/guidance/vat-on-goods-exported-from-the-uk-notice-703 | VAT on goods exported from the UK (VAT Notice 703) | current | official |
| https://content.govdelivery.com/accounts/USDHSCBP/bulletins/4047318 | CSMS #67400472 — Section 232 Semiconductor Duties Guidance | 2026-01 | official |
| https://frankfurter.dev | Frankfurter — Free exchange rates API | current | official (project docs) |
| https://frankfurter.dev/integrations | Frankfurter Integrations | current | official (project docs) |
| https://exchangerate.host/pricing | ExchangeRate Host Pricing | 2026 | community |
| https://currencyfreaks.com/blog/ExchangeRate-Api-Pricing-Alternative | ExchangeRate-API Pricing, Free Plan Limits | 2026 | blog |
| https://www.buckland.com/news/cbp-announces-adjusted-customs-user-fees-for-fy-2026 | CBP Adjusted Customs User Fees FY2026 | 2025 | community (citing official Fed Reg 90 FR 34665) |
| https://mohawkglobal.com/trade-translation/cbp-adjusts-customs-user-fees-for-inflation-effective-10-1-2025 | CBP Adjusts Customs User Fees | 2025 | community |
| https://zonos.com/landed-cost | Zonos Landed Cost | current | community |
| https://zonos.com/docs/global-ecommerce/landed-cost/pricing | Zonos Landed Cost Pricing | current | community |
| https://docs.dutify.com/docs/landed-cost-calculator-api | Dutify Landed Cost Calculator API | current | community |
| https://gingercontrol.com/blog/trade-compliance-software-pricing-models-compared | Trade Compliance Software Pricing Models Compared (2026) | 2026 | blog |
| https://developer.ebay.com/api-docs/buy/browse/types/gct:ShippingOption | eBay Browse API ShippingOption | current | official |
| https://community.ebay.com/t5/eBay-APIs-Talk-to-your-fellow/API-call-to-get-estimated-shipping-cost-ebay-shipping-calculator/td-p/34033804 | eBay community: estimated shipping cost API | undated | community |
| https://www.europarl.europa.eu/RegData/etudes/BRIE/2026/779864/ECTI_BRI(2026)779864_EN.pdf | US tariffs: economic, financial and monetary repercussions | 2026-03 | official (EU Parliament research service) |
| https://www.wiley.law/trump-administration-tariff-tracker | Trump Administration Tariff Tracker | 2026 (ongoing) | community |
| https://budgetlab.yale.edu/research/state-us-tariffs-scotus-ruling-update | State of U.S. Tariffs: SCOTUS Ruling Update | 2026-02 | community (Yale Budget Lab) |
| https://ourtake.bakerbotts.com/post/102n7tq/trump-tariff-tracker-july-2-2026 | Trump Tariff Tracker – July 2, 2026 | 2026-07-02 | community (law firm tracker) |
| https://blog.ordoro.com/2026/02/25/de-minimis-exemption-2026 | Is the De Minimis Exemption Back in 2026? | 2026-02-25 | blog |
| https://carraglobe.com/us-de-minimis-exemption-suspended-2026 | US De Minimis Exemption Suspended 2026 | 2026-04 | blog |
| https://taxnews.ey.com/news/2026-0209-us-section-232-proclamation-imposes-25-percent-tariff-on-certain-semiconductors | US Section 232 proclamation imposes 25% tariff on semiconductors | 2026-01-15 | community (EY tax news) |
