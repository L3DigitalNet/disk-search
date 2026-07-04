# Further Research — Deep Research Prompts & Completed Reports

> **Status (2026-07-04): all 15 prompts have now been run and reconciled** — the original 12, plus follow-ups **[#13](#13-scraper-testing-finalization--per-tier-canaries--cassette-strategy)** (scraper-testing finalization, reconciled into [`resolved-questions.md` OQ8](resolved-questions.md#oq8--scraper-testing-finalization)), **[#14](#14-agentmail-deliverability--sending-domain-model)**, and **[#15](#15-per-source-inventory-volatility--fast-lane-polling-affordance)** (the latter two added _and answered_ 2026-07-04). For the 12 original prompts, this document is a **completion tracker**: the original prompt text is kept verbatim (provenance + re-runnable), and a status banner above each links its report, states the headline finding, and flags any residual gap. #13–#15 now all carry **✅ Answered** banners (#13 reconciled into OQ8; #14 reconciled into [OQ13](resolved-questions.md#oq13--notification-transport--deliverability-agentmail-vs-transactional-provider); #15 folded into FR-001/FR-002 + the reconciliation report). No `_TBD_` markers remain in the spec — the 12 findings are fully reconciled into [`hw-radar-master-spec.md`](specs/hw-radar-master-spec.md).

These prompts were written for ChatGPT **Deep Research**. Each is self-contained (Deep Research can't see this repo), states the gap it fills, and dictates an output shape to fold back into the spec.

**Scope note:** Research in [`docs/research/tavily-brave-serper.md`](research/tavily-brave-serper.md) covers the Tavily/Brave/Serper search APIs and the **official** eBay Browse/Feed, Amazon SP-API, and Newegg Marketplace APIs. The 12 prompts below deliberately targeted the untouched areas: the other 17 marketplaces, the scoring math, drive-grading domain knowledge, legal footing, and the undecided stack (`_TBD_` markers) — all now answered. Additional operational reports (auth, CD, backups, observability, currency/landed-cost) also landed under `docs/research/` and are tracked in [`open-questions.md`](open-questions.md), not here.

**Residual open items** (none require a new research prompt): confirm JSON-LD presence live per-merchant at implementation (#1); no rigorous recert-vs-new reliability study exists — inherent domain gap (#3); Amazon SP-API fit for a public price monitor and the Serper data-rights chain are take-to-counsel questions (#7).

## Table of Contents

- [Further Research — Deep Research Prompts \& Completed Reports](#further-research--deep-research-prompts--completed-reports)
  - [Table of Contents](#table-of-contents)
  - [Completion status](#completion-status)
  - [1. Data acquisition for the 17 non-API marketplaces](#1-data-acquisition-for-the-17-non-api-marketplaces)
  - [2. HDD/SSD grading \& "applicability" taxonomy](#2-hddssd-grading--applicability-taxonomy)
  - [3. Recertified / refurbished enterprise-drive risk \& warranty landscape](#3-recertified--refurbished-enterprise-drive-risk--warranty-landscape)
  - [4. Quantitative multi-factor scoring model design](#4-quantitative-multi-factor-scoring-model-design)
  - [5. Price benchmarking, $/TB baselines \& existing reference tools](#5-price-benchmarking-tb-baselines--existing-reference-tools)
  - [6. Cross-marketplace product entity resolution](#6-cross-marketplace-product-entity-resolution)
  - [7. Legal \& Terms-of-Service footing for scraping and price monitoring](#7-legal--terms-of-service-footing-for-scraping-and-price-monitoring)
  - [8. Anti-bot-resilient scraping architecture for e-commerce](#8-anti-bot-resilient-scraping-architecture-for-e-commerce)
  - [9. Scheduling, orchestration \& pipeline architecture (Python)](#9-scheduling-orchestration--pipeline-architecture-python)
  - [10. Web framework, database \& environment-management stack decision](#10-web-framework-database--environment-management-stack-decision)
  - [11. Notification \& alerting design, deliverability, and dedup](#11-notification--alerting-design-deliverability-and-dedup)
  - [12. Manufacturer \& specialty-reseller warranty/serial-verification data sources](#12-manufacturer--specialty-reseller-warrantyserial-verification-data-sources)
  - [13. Scraper-testing finalization — per-tier canaries \& cassette strategy](#13-scraper-testing-finalization--per-tier-canaries--cassette-strategy)
  - [14. AgentMail deliverability \& sending-domain model](#14-agentmail-deliverability--sending-domain-model)
  - [15. Per-source inventory volatility \& fast-lane polling affordance](#15-per-source-inventory-volatility--fast-lane-polling-affordance)
  - [Reconciliation order (research → spec)](#reconciliation-order-research--spec)

---

## Completion status

The 12 original topics, the gap each filled, and the report that now answers it. **All 12 are complete (✅).** "Residual" flags the honestly-scoped open questions the reports surfaced. **Rows 13–15 are follow-up prompts:** #13 (added 2026-07-03, **✅ reconciled 2026-07-04**) took [OQ8](resolved-questions.md#oq8--scraper-testing-finalization) (scraper-testing finalization) through ChatGPT Deep Research and has been reconciled into OQ8 (research: [`automated-test-policy-for-a-low-volume-scrapy-price-monitor.md`](research/automated-test-policy-for-a-low-volume-scrapy-price-monitor.md)); #14 (added 2026-07-04, **✅ landed 2026-07-04**) took the AgentMail-deliverability slice of [OQ13](resolved-questions.md#oq13--notification-transport--deliverability-agentmail-vs-transactional-provider) there and has been reconciled back into OQ13. #15 (added 2026-07-04, **✅ answered 2026-07-04** via two parallel research paths + reconciliation) adds the per-source inventory-volatility / fast-lane polling axis surfaced in the "real-time monitoring" scoping brainstorm — the second scheduling axis orthogonal to the T0–T4 acquisition tier; folded into FR-001/FR-002 + the `availability_heartbeat_observation` grain.

| # | Topic (gap it filled) | Status | Report | Residual |
| --: | --- | :-: | --- | --- |
| 1 | Data acquisition, 17 non-API merchants | ✅ | [acquisition](research/programmatic-acquisition-research-for-enterprise-and-nas-drive-merchants.md) | JSON-LD unconfirmed for most merchants — verify live |
| 2 | HDD/SSD grading & applicability taxonomy | ✅ | [taxonomy](research/machine-usable-drive-suitability-taxonomy-for-24-7-nas-and-server-scoring.md) | none |
| 3 | Recertified-drive risk & warranty | ✅ | [recert](research/recertified-enterprise-hard-drives-for-homelab-and-small-business-buyers.md) | no rigorous recert-vs-new study exists (domain gap) |
| 4 | Quantitative multi-factor scoring model | ✅ | [scoring](research/principled-deal-score-for-hard-drive-listings.md) | none |
| 5 | Price baselines ($/TB) & prior art | ✅ | [baselines](research/drive-deal-tracker-research-baselines-tools-shucking-and-timing.md) | none |
| 6 | Cross-marketplace entity resolution | ✅ | [entity-res](research/entity-resolution-for-cross-marketplace-hard-drive-and-ssd-price-tracking.md) + [db](research/database-architecture.md) | none |
| 7 | Legal/ToS footing for scraping + storage | ✅ | [legal](research/us-scraping-and-data-retention-landscape-for-a-retail-hdd-price-monitor.md) | SP-API fit & Serper rights → counsel |
| 8 | Anti-bot scraping architecture | ✅ | [scraping](research/pragmatic-architecture-for-low-volume-python-e-commerce-scraping.md) | none |
| 9 | Scheduling / orchestration | ✅ | [orchestration](research/orchestration-choice-for-a-single-vm-price-polling-service.md) | none |
| 10 | Framework/DB/env stack (`_TBD_` ×3) | ✅ | [stack](research/opinionated-core-stack-recommendations-for-a-python-drive-price-monitor.md) | none |
| 11 | Notification/alerting design | ✅ | [alerting](research/designing-a-low-noise-alerting-layer-for-a-hard-drive-deal-monitor.md) | none |
| 12 | Warranty/serial verification sources | ✅ | [verify](research/programmatic-identity-and-warranty-verification-for-used-enterprise-hdd-listings.md) | no public warranty API exists (answered negative) |
| 13 | Scraper-testing finalization ([OQ8](resolved-questions.md#oq8--scraper-testing-finalization)) | ✅ | [test-policy](research/automated-test-policy-for-a-low-volume-scrapy-price-monitor.md) | none |
| 14 | AgentMail deliverability ([OQ13](resolved-questions.md#oq13--notification-transport--deliverability-agentmail-vs-transactional-provider)) | ✅ | [email-path](research/choosing-an-outbound-email-path-for-a-low-volume-alerting-system.md) | **Postmark primary / SES fallback / AgentMail secondary**; AgentMail is _not_ disqualified on DKIM — the factor is its thinner transactional-deliverability track record; branded custom-domain sending needs its $20/mo tier (free tier is `@agentmail.to` only) |
| 15 | Inventory volatility & fast-lane polling axis ([OQ9](resolved-questions.md#oq9--acquisition-cadence-throttle--skip-policy) follow-up) | ✅ | [reconciliation](research/2026-07-04-polling-cadence-reconciliation.md) (+ [qdev](research/2026-07-04-per-source-inventory-volatility-and-fast-lane-polling.md), [ChatGPT](research/hardware-radar-polling-cadence.md)) | anti-correlation (fast-lane = drop-prone ∩ cheap signal); folded into FR-001 (freshness SLO) + FR-002 (volatility axis) + heartbeat grain; PA-API deprecation → [OQ15](resolved-questions.md#oq15--amazon-acquisition-path-after-pa-api-deprecation) |

---

## 1. Data acquisition for the 17 non-API marketplaces

> **✅ Answered** — [`programmatic-acquisition-…`](research/programmatic-acquisition-research-for-enterprise-and-nas-drive-merchants.md). No broadly usable public retail product API exists across the 17 merchants; best next integrations are **ServerPartDeals** (clean Shopify), **goHardDrive** (crawlable legacy HTML), **WD/Seagate Recertified** (first-party but JS-heavy), and **B&H** (crawlable + affiliate). Full per-merchant matrix delivered (all 17 covered, all five dimensions). **Residual:** JSON-LD/schema.org presence is only inferred ("likely") for most merchants — confirm live during implementation.

**Gap it fills:** The spec lists 20 marketplaces but only eBay/Amazon/Newegg have documented acquisition paths. The manufacturer stores and specialty resellers have zero research — no answer on whether feeds, structured data, or clean scraping exist.

```text
I'm building a personal price-and-availability monitor for enterprise/NAS hard drives (HDDs) and SSDs. I already have acquisition strategies for eBay (Browse/Feed API), Amazon (SP-API), and Newegg (Marketplace API). I need to know how to programmatically obtain current product listings, prices, and stock status from the following 17 merchants, none of which I've researched yet:

Western Digital Store / WD Recertified, Seagate Store / Seagate Recertified, ServerPartDeals, B&H Photo Video, CDW, Insight, PCNation, Wiredzone, goHardDrive, TechMikeNY, ETB Technologies, Bargain Hardware, HardDrivesDirect, ServerMonkey, SaveMyServer, The Server Store, Memory4Less.

For EACH merchant, report: (1) whether any public/partner API, product feed, affiliate feed (e.g. via CJ, Impact, Rakuten, Sovrn), or Google Merchant/structured data exists; (2) whether product pages expose machine-readable structured data (JSON-LD, schema.org Product/Offer, microdata) I could parse; (3) presence and strength of anti-bot protection (Cloudflare, PerimeterX/HUMAN, Akamai, DataDome, CAPTCHAs, rate limiting) based on observable evidence; (4) the platform the storefront runs on (Shopify, Magento/Adobe Commerce, BigCommerce, WooCommerce, custom) since that dictates predictable URL/JSON patterns; (5) a recommended acquisition approach (feed > structured-data parse > headless scrape > skip) with a difficulty rating.

Prioritize the recertified-drive specialists (WD/Seagate recertified stores, ServerPartDeals, goHardDrive) since those are my primary value targets. Cite official docs, affiliate-network catalogs, and platform fingerprints. Present as a per-merchant table plus a short prose recommendation for the top 5.
```

---

## 2. HDD/SSD grading & "applicability" taxonomy

> **✅ Answered** — [`machine-usable-drive-suitability-taxonomy`](research/machine-usable-drive-suitability-taxonomy-for-24-7-nas-and-server-scoring.md). Establishes the tier ladder (desktop < NAS < NAS Pro < enterprise/datacenter for HDDs; client < NAS < enterprise for SSDs), treats **device-managed SMR as a hard reject** for NAS/RAID and **missing PLP as a major SSD penalty**, and delivers a scoring-oriented attribute schema (universal/HDD/SSD field tables) + model-family→tier reference table + explicit parse-vs-lookup split. **Residual:** none.

**Gap it fills:** The scoring system has an "Applicability for Intended Use" factor favoring "server Enterprise/NAS grade" drives, but the spec never defines the machine-readable attributes that classify a drive. Without this taxonomy the scorer can't be built.

```text
I'm building a scoring engine that ranks hard-drive and SSD listings for a homelab/small-business buyer who prefers enterprise- and NAS-grade drives. I need a rigorous, machine-usable taxonomy of the drive specifications that determine whether a drive is suitable for 24/7 NAS/server use, so I can extract these fields from listings and score them.

Cover, for both HDDs and SSDs: (1) the tier ladder — desktop vs NAS vs enterprise/datacenter — and the concrete spec differences (workload rating in TB/year, MTBF/AFR, warranty length, vibration tolerance, rotational-vibration sensors, error recovery control / TLER/ERC, power-loss protection); (2) HDD recording tech — CMR vs SMR (and PMR terminology confusion), why SMR is disqualifying for NAS/RAID rebuilds, and how to reliably detect SMR from model numbers since vendors hide it; (3) helium vs air-filled, and any reliability implications; (4) SSD-specific: DWPD/TBW endurance, SLC/MLC/TLC/QLC, DRAM vs DRAM-less, power-loss protection, U.2/U.3/M.2/SATA/SAS form factors and interfaces; (5) the current model-family landscape — which product lines map to which tier (e.g. WD Red Plus/Pro, WD Gold, Ultrastar DC; Seagate IronWolf/IronWolf Pro, Exos; Toshiba N300/MG/MN) — as a reference table; (6) which of these attributes can be parsed from a typical retail listing title/description vs which require a model-number lookup table.

Deliver: a scoring-oriented attribute schema (field name, data type, how to source it, why it matters), plus the model-family-to-tier reference table. Cite manufacturer spec sheets and datasheets.
```

---

## 3. Recertified / refurbished enterprise-drive risk & warranty landscape

> **✅ Answered** — [`recertified-enterprise-hard-drives`](research/recertified-enterprise-hard-drives-for-homelab-and-small-business-buyers.md). The label alone is weak evidence — **provenance, warranty backing, serial verification, and arrival SMART/FARM data are the strong signals**. Delivers a term taxonomy (recert/refurb/renewed/pull/NOS), per-vendor warranty comparison table, SMART attribute + power-on-hour thresholds, red flags, and an encodable scoring penalty/bonus table with hard-stop rules. **Residual:** no rigorous public study isolates factory-recertified vs new enterprise reliability (the report honestly substitutes Backblaze/community data); WD/Toshiba recert-process detail is thinner than Seagate's.

**Gap it fills:** The tool's entire value thesis is buying recertified enterprise HDDs, but there's no research on what "recertified" actually means, how the risk compares to new, or how warranty terms differ by vendor — all of which should feed the score and buyer guidance.

```text
I'm building a tool to hunt deals on RECERTIFIED and REFURBISHED enterprise hard drives (WD, Seagate, Toshiba, HGST) for a homelab/small-business buyer, sourced from manufacturer recert stores and specialty resellers (ServerPartDeals, goHardDrive, TechMikeNY, serverpart resellers, eBay sellers).

Research and report: (1) precise definitions and differences between "factory recertified", "recertified", "refurbished", "renewed", "used", and "new pulls / new old stock" as used in the enterprise-drive market, and how trustworthy each label is; (2) what manufacturers actually do in the recertification process; (3) real-world reliability evidence for recertified enterprise drives vs new — cite Backblaze drive-stats data, community datasets (r/DataHoarder, r/homelab surveys), and any studies, being explicit about what's rigorous vs anecdotal; (4) the warranty landscape: typical warranty length offered by ServerPartDeals, goHardDrive, WD/Seagate recert stores, and typical eBay sellers, plus whether manufacturer warranty transfers and how to check a serial number's warranty status with WD and Seagate; (5) red flags that indicate a bad recert listing (wiped SMART data, high power-on hours, fake labels, grey-market); (6) which SMART attributes and power-on-hours thresholds a buyer should demand or check on arrival.

Deliver actionable buyer heuristics I can encode as scoring penalties/bonuses (e.g. "warranty < 1yr → penalty", "seller discloses power-on hours → bonus"), plus a per-vendor warranty comparison table. Cite sources and flag confidence levels.
```

---

## 4. Quantitative multi-factor scoring model design

> **✅ Answered** — [`principled-deal-score`](research/principled-deal-score-for-hard-drive-listings.md). Recommends a **weighted geometric-mean (weighted product)** model over four normalized subscores — price cheapness-percentile, Bayesian + Wilson seller trust, rubric-based fitness, availability — with explicit **non-compensatory caps** (e.g. SMR/no-return vetoes), default weights **0.50 / 0.25 / 0.15 / 0.10**, a glass-box explanation payload, and a four-listing worked example. Rejects TOPSIS as the primary score with rationale. **Residual:** none.

**Gap it fills:** The spec names five scoring factors (price/$per-TB, availability, seller reputation, applicability, overall) but gives no methodology for normalizing and combining them. This is the core algorithm and is entirely unspecified.

```text
I'm designing the scoring algorithm for a hard-drive deal-monitoring tool. Each listing has heterogeneous signals I want to fuse into one 0–100 "deal score": price expressed as USD-per-TB, in-stock availability, seller reputation (from different marketplaces with different rating scales), and fitness-for-purpose (enterprise/NAS suitability, warranty, condition). I want a principled design, not an ad-hoc weighted sum I made up.

Research and recommend: (1) normalization techniques for combining features on different scales and directions (min-max, z-score, robust/quantile scaling, log transforms for price) and which fits a right-skewed $/TB distribution best; (2) how to make $/TB scoring *relative to a moving baseline* (e.g. percentile rank against recent listings for the same capacity/tier) rather than an absolute threshold, so the score self-adjusts as market prices fall; (3) methods to normalize seller-reputation across marketplaces with incompatible scales (eBay feedback % + count, Amazon seller rating, star ratings, "no rating available") into a comparable 0–1 trust score, including how to handle low-sample-size sellers (Bayesian/Wilson-score shrinkage); (4) approaches to combining factors — weighted geometric mean vs arithmetic, hard gates/vetoes (e.g. SMR or no-return-policy caps the max score) vs soft penalties, and multi-criteria decision methods (TOPSIS, weighted product model) worth considering; (5) how to keep the score explainable so a listing can show *why* it scored what it did.

Deliver a concrete recommended scoring formula with each sub-score's normalization defined, sensible default weights for a value-focused enterprise-drive buyer, and a worked numeric example on 3–4 hypothetical listings. Cite methods literature where relevant.
```

---

## 5. Price benchmarking, $/TB baselines & existing reference tools

> **✅ Answered** — [`drive-deal-tracker-…-baselines-tools-shucking-and-timing`](research/drive-deal-tracker-research-baselines-tools-shucking-and-timing.md). Provides **July 2026 $/TB baseline tables** for HDDs (8–28 TB, new vs recert) and enterprise SSDs (by endurance tier/interface/condition), identifies sweet spots (**new 18–24 TB, recert 20–28 TB**), and surveys the tool/community landscape with API notes (Keepa = paid API; diskprices/camel/PCPartPicker = no public API, parseable HTML/unofficial wrappers) plus shucking and seasonal-timing guidance. **Residual:** none (tool notes are qualitative, not endpoint schemas — as asked).

**Gap it fills:** Scoring on price requires knowing what a _good_ $/TB is per tier/capacity, and whether prior art exists to borrow from or integrate. The spec assumes $/TB but provides no baselines or awareness of competitors.

```text
I'm building a personal hard-drive/SSD deal tracker and need external reference points for "what is a good price" and awareness of existing tools so I don't reinvent them.

Research: (1) current (as of your latest data) street-price baselines in USD-per-TB for enterprise/NAS HDDs across common capacities (8TB, 12TB, 14TB, 16TB, 18TB, 20TB, 22TB, 24TB+) split by new vs recertified, and for enterprise/NAS SSDs by capacity/endurance tier — give ranges and note volatility; (2) the known "sweet spot" capacities where $/TB is lowest and why it shifts over time; (3) existing tools and communities that already track drive prices — diskprices.com, camelcamelcamel, Keepa, PCPartPicker price history, r/DataHoarder price threads, serverpartdeals deal trackers, shucking/external-drive price guides — including for each whether it has an API, data export, or affiliate feed I could integrate or learn from; (4) the "shucking" external-drive market as an alternate value source (which external enclosures contain which internal drives, current risks/caveats); (5) how drive prices move seasonally and around events (Black Friday, Prime Day, capacity transitions) so my tool can flag genuinely-good vs normal prices.

Deliver a $/TB baseline reference table by capacity and tier, a competitor/tool landscape table (name, coverage, API availability, how it could integrate), and a short section on timing signals. Cite sources and date every price figure.
```

---

## 6. Cross-marketplace product entity resolution

> **✅ Answered** — [`entity-resolution-…`](research/entity-resolution-for-cross-marketplace-hard-drive-and-ssd-price-tracking.md) + [`database-architecture`](research/database-architecture.md). Recommends a surrogate `canonical_product_id` anchored on **brand + exact normalized MPN** (GTIN/ASIN/ePID as aliases, not canonical keys), a **dual physical-key vs sellable-variant-key** model that puts condition at the offer layer, a hybrid rules + NER + LLM-fallback title parser, and multi-pass blocking with a conservative match-decision flow; names OSS ER tools (Splink, dedupe, Magellan, Ditto, pyJedAI, …). The DB report supplies the concrete schema (`drive_model`, `drive_alias`, `listing`, `offer_snapshot`, `pg_trgm`). **Residual:** none.

**Gap it fills:** A price-history database is useless if "the same drive" appears as different rows per merchant. The spec's database section never addresses matching listings to a canonical product — the hardest data-engineering problem here.

```text
I'm building a database that tracks the same hard-drive and SSD models across ~20 marketplaces (eBay, Amazon, Newegg, manufacturer stores, specialty resellers) to compare prices over time. The core problem is ENTITY RESOLUTION: recognizing that listings from different merchants — with different titles, SKUs, and identifiers — refer to the same physical product, while distinguishing genuinely different variants (capacity, interface, recording tech, condition, generation).

Research and recommend: (1) the canonical identifiers available for storage drives — manufacturer model/part number (MPN), GTIN/UPC/EAN, Amazon ASIN, eBay EPID, and how reliably each maps to a unique physical product; the pitfalls (same model number across capacities, OEM vs retail part numbers, region variants, revision suffixes); (2) how to parse and normalize noisy retail listing titles into structured attributes (brand, family, capacity, interface, form factor, condition) — techniques from rule-based parsing to NER to LLM extraction, with tradeoffs; (3) a matching/blocking strategy — how to define a canonical product key, when to trust an exact identifier vs fuzzy attribute match, and how to avoid false merges (a 16TB vs 18TB collision); (4) how CONDITION and variant should factor into the canonical key (should "recertified 14TB Exos" and "new 14TB Exos" be one product with two condition facets, or separate keys?); (5) established open-source tools/libraries or datasets for product matching (e.g. entity-resolution libraries, dedupe, record linkage toolkits) worth using.

Deliver a recommended canonical-product-key design, a title-parsing approach, and a matching decision flow. Cite entity-resolution/product-matching literature and any usable tools.
```

---

## 7. Legal & Terms-of-Service footing for scraping and price monitoring

> **✅ Answered** — [`us-scraping-and-data-retention-landscape`](research/us-scraping-and-data-retention-landscape-for-a-retail-hdd-price-monitor.md). Public **factual** price collection is materially lower CFAA risk post-Van Buren/hiQ (adds Sullivan 2025, DOJ policy, Bright Data cases); the decisive work is **source-by-source contract/API-term governance**, avoiding technical circumvention, minimizing expressive-content retention, and enforcing the strictest per-source TTL in code. Delivers the risk-tiered summary, per-source "what I can store / how long" table (Amazon PA/Creators + SP-API, eBay, Google, Serper), and a retention policy. **Residual:** SP-API's fit for a public price monitor and Serper's rights-chain are flagged **for counsel**, not for more research.

**Gap it fills:** The tool scrapes ~20 commercial sites and stores their data in a **public** GitHub-org repo tied to a business. The spec has no legal analysis — a material risk given business use, and it constrains what can be stored/retained.

```text
I'm building a hard-drive price-monitoring tool for a small US business that will scrape or API-pull product listings, prices, and availability from ~20 retail sites (Amazon, eBay, Newegg, B&H, CDW, manufacturer stores, specialty resellers) and STORE that data in a database to track price history over time. I need a grounded, current understanding of the legal and terms-of-service landscape so I can set a compliant retention and acquisition policy. I am not asking for legal advice to rely on, but for a well-cited overview I can take to counsel.

Research: (1) the current US legal landscape for web scraping of publicly available data — the state of CFAA case law post-hiQ v. LinkedIn and Van Buren, and what remains legally risky vs relatively settled; (2) how breach-of-contract / terms-of-service claims differ from CFAA, and whether browsewrap vs clickwrap enforceability matters for a scraper; (3) copyright and database-rights considerations for storing prices, product descriptions, and images; (4) the specific stored-data restrictions in the terms of the major APIs I'll use — Amazon (SP-API and Creators/Product Advertising content caching/retention rules), eBay (data retention and caching), Google/Serper-derived data — and what each permits me to persist; (5) robots.txt's actual legal weight vs its practical role; (6) practical, widely-recommended compliance hygiene for a good-faith monitor (rate limiting, identifying user-agent, honoring robots.txt, not evading anti-bot, PII avoidance).

Deliver a risk-tiered summary (lower-risk vs higher-risk practices), a per-source "what I'm allowed to store and for how long" table for the major APIs, and a short recommended data-retention/acquisition policy. Cite cases, official API terms, and reputable legal analyses; date everything and flag where the law is unsettled.
```

---

## 8. Anti-bot-resilient scraping architecture for e-commerce

> **✅ Answered** — [`pragmatic-architecture-…-scraping`](research/pragmatic-architecture-for-low-volume-python-e-commerce-scraping.md). **HTTP-first, structured-data-first, browser-last:** Scrapy as orchestrator, a structured-data detector (JSON-LD → platform JSON → bootstrap JSON) in front of every parser, Playwright via `scrapy-playwright` for occasional rendering, `curl_cffi` for the narrow TLS-fingerprint gap, and outsource/skip targets needing residential rotation or CAPTCHA solving. Delivers a difficulty→technique decision tree, a managed-API cost table (ScraperAPI/ZenRows/Zyte/Bright Data/Oxylabs/Firecrawl), and a default stack. **Residual:** none.

**Gap it fills:** The spec names Scrapy but nothing about how to actually retrieve pages from sites that fight scrapers (most large retailers). This is a make-or-break infrastructure decision left blank.

```text
I'm building a Python scraper (currently planning to use Scrapy) that periodically fetches product/price/stock data from e-commerce sites ranging from easy (small Shopify/Magento specialty resellers) to heavily protected (Amazon, Newegg, big retailers behind Cloudflare/Akamai/DataDome/PerimeterX). This is low-volume, good-faith monitoring for personal/small-business use — not high-frequency abuse. I want a pragmatic, current architecture recommendation.

Research and recommend: (1) when plain HTTP + HTML parsing suffices vs when I need a headless/real browser (Playwright, Selenium, or scraping-specific browsers) — decision criteria based on JS-rendering and structured-data availability; (2) the current tooling landscape for Python e-commerce scraping — Scrapy, Playwright, curl_cffi/TLS-fingerprint libraries, and managed scraping APIs (ScraperAPI, ZenRows, Bright Data, Zyte API, Oxylabs, Firecrawl) — with a cost/effort/reliability comparison for a low-volume hobby-scale user; (3) how to detect and cheaply consume JSON-LD / schema.org structured data or hidden JSON (Next.js __NEXT_DATA__, Shopify products.json, Magento patterns) to avoid brittle HTML parsing; (4) polite, ban-avoiding practices that stay on the right side of good faith — rate limiting, backoff, caching, realistic headers, honoring robots.txt — versus aggressive evasion (residential-proxy rotation, CAPTCHA-solving) I should avoid or treat as a signal to stop; (5) a recommended tiered architecture: cheap path for easy sites, escalation path for protected ones, and a "not worth it, use the API or skip" cutoff.

Deliver a decision tree (site difficulty → recommended technique), a tool comparison table with rough costs, and a recommended default stack for Python. Cite tool docs and note anything version-sensitive.
```

---

## 9. Scheduling, orchestration & pipeline architecture (Python)

> **✅ Answered** — [`orchestration-choice-…`](research/orchestration-choice-for-a-single-vm-price-polling-service.md). Use **APScheduler 3.11.x** in a dedicated systemd-supervised poller with PostgreSQL for state; cron/systemd-timers is the leaner floor, and Celery/RQ/Dramatiq/Prefect/Dagster/Airflow are explicitly flagged **over-engineered** for ~20 sources on one VM. Covers per-source rate-limit modeling (two-level token buckets, per-domain concurrency caps, phase offset + jitter, adaptive 429/503 cooldown), retry/failure-isolation (Postgres dead-letter + circuit breaker), a pipeline-stage sketch with partial-rerun boundaries, and observation-vs-alert dedup. **Residual:** none.

**Gap it fills:** The spec promises "real-time or near-real-time monitoring" but specifies nothing about _how_ recurring jobs run — the scheduler/orchestration layer that turns scrapers into a monitoring service is absent.

```text
I'm building a Python service that periodically polls ~20 data sources (APIs and scrapers) for hard-drive prices/availability, normalizes and scores the results, writes to PostgreSQL, and fires alerts on matches/price-drops. Different sources need different poll frequencies (some hourly, some daily) and different rate limits. It runs on a single Debian VM (Hetzner, behind NGINX) for personal/small-business scale — not a large distributed system.

Research and recommend the orchestration/scheduling layer: (1) compare the realistic options at THIS scale — plain cron + scripts, APScheduler, Celery + beat + Redis/RabbitMQ, RQ, Dramatiq, Prefect, Dagster, Airflow — on setup complexity, per-source scheduling flexibility, retry/backoff, observability, and operational weight for a single-VM single-maintainer deployment; explicitly flag which are over-engineered here; (2) how to model per-source rate limits and staggering so I don't hammer any site or trip rate limits (token buckets, jittered scheduling, per-domain concurrency caps); (3) retry, backoff, and failure-isolation patterns so one flaky source doesn't stall the pipeline, plus dead-letter/alerting on persistent source failure; (4) how to structure the pipeline stages (fetch → parse → normalize → resolve entity → score → persist → alert) for testability and partial reruns; (5) idempotency and dedup so re-running a source doesn't create duplicate observations or duplicate alerts.

Deliver a recommended default (with a one-line justification for why the heavier options are overkill at this scale), a per-source scheduling model, and a stage/retry architecture sketch. Cite the tools' own docs and note version-sensitive advice.
```

---

## 10. Web framework, database & environment-management stack decision

> **✅ Answered** — [`opinionated-core-stack-recommendations`](research/opinionated-core-stack-recommendations-for-a-python-drive-price-monitor.md). Resolves all three `_TBD_` markers: **Django** (server-rendered templates + HTMX, over FastAPI/Flask) for a CRUD/dashboard/auth/ingestion app, **PostgreSQL 18** (JSONB + full-text; **no** TimescaleDB and no partitioning until the price-history table demands it), and **uv** for env/dependency management. **Residual:** none — but the spec still lists these as undecided; reconcile into [`hw-radar-master-spec.md`](specs/hw-radar-master-spec.md) and update CLAUDE.md's "FastAPI or Django (undecided)" note.

**Gap it fills:** Fills the three explicit `_TBD_` markers in the spec (Web Framework, Database engine, Environment Management) with a reasoned recommendation rather than a coin flip.

```text
I'm choosing the core stack for a Python web app: a personal/small-business hard-drive price monitor with a scraping/API ingestion backend, a scored/filterable listings database with price-history over time, a web UI to search/filter/set alerts, and background jobs. Single maintainer, deployed on one Debian 13 VM behind NGINX with Let's Encrypt, PostgreSQL-or-MySQL, user authentication. I want current, opinionated recommendations for three decisions.

(1) WEB FRAMEWORK: compare FastAPI (+ a frontend or templating), Django (batteries-included, admin, ORM, auth), and Flask for THIS app — a data-heavy CRUD+dashboard app with background ingestion and simple auth. Weigh: built-in admin/ORM/auth/migrations (Django's strengths) vs FastAPI's async/API-first model, and what each implies for the UI layer (server-rendered templates vs SPA vs HTMX). Note: I generally prefer FastAPI for APIs — say whether that preference is right here or whether Django's included admin/auth/ORM materially reduces build effort for a listings/alerts app, and what I'd give up either way.

(2) DATABASE: PostgreSQL vs MySQL for time-series-ish price-history plus relational product/offer data — compare on time-series/partitioning features, JSON support (for storing raw payloads), full-text search, and ecosystem; note whether a time-series extension (TimescaleDB) or just partitioned tables is warranted at hobby scale, or if it's premature.

(3) ENVIRONMENT/DEPENDENCY MANAGEMENT: evaluate uv (Astral) vs Poetry vs pip-tools/venv for a 2026 Python project — lockfiles, reproducibility, speed, CI integration, and maturity — and give a recommendation.

Deliver a clear recommendation for each of the three with the key tradeoff stated, and a one-paragraph "recommended stack" summary. Cite official docs; flag anything version-sensitive.
```

---

## 11. Notification & alerting design, deliverability, and dedup

> **✅ Answered** — [`designing-a-low-noise-alerting-layer`](research/designing-a-low-noise-alerting-layer-for-a-hard-drive-deal-monitor.md). Use a **stateful per-watch/per-listing** model with dual-fingerprint dedup, debounce/cooldown, enter-vs-recover hysteresis, instant-vs-hourly-digest lanes, and per-watch + global rate caps; send email via a **transactional provider (Postmark preferred, SES for cost)** rather than raw SMTP from Hetzner, with **Pushover/Telegram push before SMS**. Delivers a SQL watch/observation/state/notification data model + two-stage matcher, a deliverability checklist (SPF/DKIM/DMARC), and provider/channel comparison tables. **Residual:** none.

**Gap it fills:** The spec wants email/SMS/push alerts (via AgentMail) but says nothing about alert-fatigue control, deliverability, or dedup — the difference between a useful alerter and a spam cannon.

```text
I'm building the alerting layer for a hard-drive deal monitor. It should notify me (email at minimum, maybe SMS/push later) when a watched drive becomes available or drops below a target price/score. I want a design that's genuinely useful and doesn't devolve into noise.

Research and recommend: (1) alert-fatigue control patterns — deduplication (don't re-alert the same listing), debouncing/cooldowns, digest/batching (hourly/daily roundups vs instant), thresholds and hysteresis (avoid flapping when a price hovers at the boundary), and per-watch rate caps; (2) how to model "watches"/alert rules cleanly (criteria: model/capacity/tier, max price or $/TB, min score, marketplace filter) and match incoming observations against them efficiently; (3) email DELIVERABILITY for a self-hosted small sender from a Hetzner VM sending to my own domain — SPF/DKIM/DMARC setup, why sending directly from a datacenter IP often lands in spam, and whether to use a transactional email API (I have an AgentMail API key; also compare Postmark, SES, Resend, Mailgun as alternatives) rather than raw SMTP; (4) SMS and push options at hobby scale (Twilio, Pushover, ntfy, Telegram bot) with cost/effort tradeoffs; (5) how to make alert emails actionable (clear subject with price/$per-TB/score, direct listing link, why-it-matched explanation, one-click snooze/unsubscribe-per-watch).

Deliver an alert-rule data model sketch, a dedup/debounce/digest strategy, a deliverability setup checklist, and a channel comparison table. Cite deliverability best-practices and the relevant service docs.
```

---

## 12. Manufacturer & specialty-reseller warranty/serial-verification data sources

> **✅ Answered** — [`programmatic-identity-and-warranty-verification`](research/programmatic-identity-and-warranty-verification-for-used-enterprise-hdd-listings.md). **No vendor publishes a documented public warranty API** — use official web forms with caching (Toshiba Asia batches up to 150 serials; Seagate `verify.seagate.com` label validation is the strongest anti-counterfeit signal; WD is most legally constrained), paired with per-vendor model decoders (Seagate ST cheat sheet, Toshiba "Meaning of Model Number," WD family pages) and conservative SMART scoring (197/198 ≠ 0 → reject; 5/187/188 → major downgrade; 199 → caution; POH → pricing context). Delivers the verification-sources table, decoders, and end-to-end flow. **Residual:** the "warranty API" expectation is answered **in the negative** (none exists).

**Gap it fills:** Deep-dive companion to prompts 1 and 3: to score used/recert listings and warn about scams, the tool needs programmatic ways to verify drive identity and warranty from a serial or model number — sources the spec never mentions.

```text
I'm building a tool that evaluates used/recertified enterprise hard-drive listings. To score trust and warranty value, and to catch misrepresented listings, I want to know what identity/warranty verification data I can obtain programmatically or semi-automatically from a drive's model number or serial number.

Research: (1) Western Digital, Seagate, and Toshiba warranty-status lookup services — do they have public/undocumented web endpoints or APIs that return warranty status, expiration, and product model from a serial number, and what are the terms/rate realities of using them at low volume; (2) how to decode/validate WD, Seagate, and Toshiba model numbers and part numbers into capacity, tier, interface, and generation (published decoders or community references); (3) whether serial-number format/validation can catch obviously fake or grey-market listings; (4) what SMART data (power-on hours, reallocated sectors, etc.) a listing might disclose and how to interpret it for a buy/no-buy signal; (5) any third-party services or datasets (e.g. drive-info APIs, community model databases) that map model numbers to full specs so I don't hand-maintain a lookup table.

Deliver: a table of verification sources (source, what it returns, input required, access method, rate/terms caveats), model-number decoder references per manufacturer, and a recommended verification flow for a listing. Cite official warranty portals and community decoder references; be explicit about what's official vs reverse-engineered vs unavailable.
```

---

## 13. Scraper-testing finalization — per-tier canaries & cassette strategy

> **✅ Answered (2026-07-04)** — [`automated-test-policy-for-a-low-volume-scrapy-price-monitor.md`](research/automated-test-policy-for-a-low-volume-scrapy-price-monitor.md). Owner-requested follow-up to [`resolved-questions.md` OQ8](resolved-questions.md#oq8--scraper-testing-finalization), reconciled back into OQ8. The scraper-testing _stack_ was already settled (vcrpy + syrupy + per-tier contract canary + Pydantic v2, plus five research-confirmed amendments — see [OQ8](resolved-questions.md#oq8--scraper-testing-finalization) / resolved gap #9); this prompt finalized the **build-time parameters** the stack left as judgment calls: per-tier canary cadence (JSON-LD 24 h / platform-JSON 12 h / bootstrap-JSON 8 h / HTML 4 h), a synthetic-only cassette policy for every named commercial source, PII-scrubbing config, a failure-classification tree (transient / anti-bot / parser-rot / degradation), and three-workflow CI wiring.

**Gap it fills:** OQ8's two open build-time decisions — the concrete **per-extraction-tier canary frequencies** (risk-weighted down the JSON-LD → platform-JSON → hidden-bootstrap → HTML-selector ladder) and the **per-source synthetic-vs-real cassette assignment** (bounded by each source's data-retention/ToS terms) — have no single authoritative source; they need a focused cross-source synthesis before the test suite is built.

```text
I'm finalizing the automated test strategy for a low-volume Python web-scraping service (Scrapy-based) that monitors ~20 e-commerce sources (manufacturer recertified-drive stores, storage-specialist resellers, eBay/Amazon/Newegg, refurbished-server sellers) for hard-drive prices and availability. This is good-faith personal/small-business monitoring, not high-frequency abuse. My testing STACK is already decided: vcrpy cassettes (record-once, replay-in-CI) for deterministic offline parse tests, syrupy snapshot assertions on parsed output, Pydantic v2 per-record runtime validation, and a scheduled production "contract canary" that checks each source's live structured data against an expected shape. Each source is parsed with a tiered extractor: JSON-LD / schema.org first, then platform JSON (Shopify products.json, Next.js __NEXT_DATA__, Magento patterns), then hidden bootstrap JSON, then brittle HTML selectors as a last resort. I need to finalize the BUILD-TIME PARAMETERS this stack leaves open.

Research and recommend, with citations and dates on anything version- or terms-sensitive:

(1) CANARY FREQUENCY PER EXTRACTION TIER. Given that JSON-LD and first-party JSON endpoints break far less often than HTML selectors, what risk-weighted monitoring cadence per tier is defensible for a low-volume monitor? How do I detect a tier silently DEGRADING — e.g. a source dropping its JSON-LD and forcing a fallback down to HTML — as opposed to a hard break? Recommend concrete frequencies (or a formula) per tier and the signal that should trip an alert.

(2) COMMIT-REAL vs SYNTHETIC CASSETTES, PER SOURCE. Which sources' recorded HTTP cassettes can I legally/ethically COMMIT to a PUBLIC git repository, versus which must use synthetic/hand-crafted fixtures? Map this to the data-retention and terms constraints of the major sources — Amazon Product Advertising / Creators API content, Google- or Serper-derived data, stored product images, and general "transient use only" clauses — versus the more permissive recert specialists (ServerPartDeals, goHardDrive, WD/Seagate recert stores). Give a decision rule I can apply per source.

(3) PII / SENSITIVE-DATA SCRUBBING. What exactly must a cassette be scrubbed of before commit (request/response headers, cookies, auth tokens, API keys, seller PII, buyer-location context), and how do I automate that in vcrpy (before_record_request / before_record_response filters, filter_headers, filter_query_parameters)? Provide a config sketch.

(4) FAILURE CLASSIFICATION. How should the test/monitoring layer distinguish recoverable "parser rot" (the site's markup changed) from "now anti-bot protected" (a soft-block that often returns HTTP 200 plus a challenge page or an empty body) — since the latter is a stop/escalate decision, not a code fix? Give concrete, codable signals for each class (status codes, body-shape assertions, challenge fingerprints, rolling-average / zero-result checks).

(5) CI WIRING. How do I wire all of this into GitHub Actions without flakiness: replay-only in CI (never live network calls), a snapshot-update workflow, and how a broken PRODUCTION canary should surface (fail the scheduled job / open an issue / send an alert) WITHOUT blocking unrelated code PRs?

Deliver: a per-tier canary-frequency table with the risk rationale; a per-source "commit real cassette vs synthetic fixture" decision table for the source list above; a vcrpy scrubbing checklist plus a short config sketch; a failure-classification decision tree (parser-rot vs anti-bot vs transient); and a recommended CI wiring. Cite tool docs (vcrpy, syrupy, Scrapy, Pydantic v2) and the relevant API/site terms; date anything that is version- or terms-sensitive.
```

---

## 14. AgentMail deliverability & sending-domain model

> **✅ Answered (2026-07-04)** — [`choosing-an-outbound-email-path…`](research/choosing-an-outbound-email-path-for-a-low-volume-alerting-system.md). **Recommendation: Postmark primary → Amazon SES fallback → AgentMail as a _secondary_ agent-inbox tool, not the primary alert channel.** AgentMail is **not** disqualified on authentication (it supports custom-domain SPF/DKIM/DMARC); the deciding factor is its **thinner public deliverability track record** for must-not-miss transactional mail vs Postmark's/SES's established transactional model. **Cost caveat:** AgentMail's free tier sends from `@agentmail.to` only — branded `chris@l3digital.net` sending needs its **$20/mo Developer plan**, so it is not the free option [OQ7](resolved-questions.md#oq7--running-cost-budget-model-build-time-pricing-pass) assumed. This closed the one narrow research gap that had been blocking the notification ADR (candidate ADR-0013); findings are **reconciled into [`resolved-questions.md` OQ13](resolved-questions.md#oq13--notification-transport--deliverability-agentmail-vs-transactional-provider)**, leaving the owner's provider call as the only open part. [Prompt #11](#11-notification--alerting-design-deliverability-and-dedup) had settled the alerting _design_ (dedup/debounce/digest/hysteresis, watch model) but treated the owner's AgentMail key as an aside; this prompt characterized it. From the 2026-07-04 gap analysis.

**Gap it fills:** OQ13's decision is AgentMail-as-primary vs a switch to Postmark/SES. That call hinges on facts no report covers: whether AgentMail delivers reliably to an owner-controlled inbox at low volume, how it authenticates the sending domain (its own domain vs a required `l3digital.net` DKIM/SPF/DMARC setup), and whether its shared-IP sender reputation is adequate for transactional deal alerts a business must not miss.

```text
I'm choosing the outbound email path for a low-volume transactional alerting system: a self-hosted hard-drive deal monitor running on a private Debian server that must email deal alerts to a single business owner (from an address at my own domain, e.g. alerts@ or chris@mydomain.tld). Missed or spam-foldered alerts are a real failure — a genuinely good deal not seen is the whole cost. I already hold an API key for "AgentMail" (agentmail.to, an email API aimed at AI agents) and want to know whether to rely on it or switch to an established transactional provider (Postmark or Amazon SES). I have already researched the general alerting design and the Postmark/SES/Resend/Mailgun landscape; this prompt is ONLY about AgentMail specifically and email deliverability mechanics.

Research and report, citing official docs and dating anything version- or pricing-sensitive:

(1) AGENTMAIL DELIVERABILITY & MODEL. What is AgentMail (agentmail.to) — its product model, sending infrastructure, and intended use case? Does it send from its own domains/inboxes (e.g. @agentmail.to addresses), or can/should it send as MY custom domain? For transactional alerts TO my own inbox, what deliverability should I expect (shared vs dedicated IP, sender reputation, inbox-placement track record)? Note the free-tier limits (reportedly ~3,000 emails/month, 100/day) and what the paid tier adds for deliverability specifically.

(2) DOMAIN AUTHENTICATION. To send as my own domain with good inbox placement, what DNS records must I configure — SPF, DKIM (selector/key), DMARC — and does AgentMail support custom-domain sending with DKIM signing at all, or only its own inboxes? Compare this to how Postmark and SES require and verify domain authentication. If AgentMail cannot DKIM-sign my domain, say so plainly — it likely disqualifies it for branded alerts.

(3) WHY DATACENTER SMTP FAILS, AND WHETHER AN API AVOIDS IT. Explain concretely why sending directly via SMTP from a datacenter/hosting IP (Hetzner-class) commonly lands in spam or is blocked, and confirm that using a transactional API (AgentMail, Postmark, or SES) actually sidesteps this — i.e. the provider's IPs and authentication do the heavy lifting, not my server's IP.

(4) FIT & RECOMMENDATION. Given: single recipient (my own inbox), <100 emails/day, a custom business domain I want alerts to appear from, and a strong requirement not to miss alerts — is AgentMail an appropriate primary, or is it better treated as a secondary/agent-inbox tool with Postmark or SES as the primary alert sender? Give a clear recommendation with the deciding factor named, and a fallback plan (e.g. AgentMail primary + SES fallback, or vice versa) with the DNS/setup checklist for the recommended path.

Deliver: a short AgentMail capability profile (sending model, custom-domain/DKIM support, free-tier limits, deliverability posture), a domain-authentication (SPF/DKIM/DMARC) setup checklist for the recommended sender, and a one-line recommendation for AgentMail-vs-Postmark/SES as the primary transactional sender. Cite AgentMail's official docs, the relevant provider docs, and reputable deliverability references; date anything pricing- or version-sensitive.
```

---

## 15. Per-source inventory volatility & fast-lane polling affordance

> **✅ Answered (2026-07-04)** — run via **two parallel paths** and consolidated: qdev/Brave+Serper → [`2026-07-04-per-source-inventory-volatility-and-fast-lane-polling.md`](research/2026-07-04-per-source-inventory-volatility-and-fast-lane-polling.md); ChatGPT Deep Research → [`hardware-radar-polling-cadence.md`](research/hardware-radar-polling-cadence.md); reconciliation → [`2026-07-04-polling-cadence-reconciliation.md`](research/2026-07-04-polling-cadence-reconciliation.md). **Headline:** inventory volatility and cheap-signal availability are _anti-correlated_ — a blanket fast-lane tier is unbuildable where it matters most; eBay recert stores are the only natively drop-prone + cheap source. **Folded into the spec:** FR-001 reworded to a per-source **freshness SLO**, FR-002 gained the **volatility axis** (effective cadence = min(tier ceiling, volatility need); fast-lane = drop-prone ∩ verified cheap signal), and the `availability_heartbeat_observation` grain (glossary/DR-008/Appendix C.2 — DR row renumbered from a duplicated "DR-006" in the 2026-07-04 spec consistency pass). Side-finding escalated to [OQ15](resolved-questions.md#oq15--amazon-acquisition-path-after-pa-api-deprecation) (Amazon PA-API 2026-05-15 deprecation). Owner-requested follow-up from the "real-time monitoring" scoping brainstorm; reframes FR-001's "continuous / near-real-time" language and introduces a second scheduling axis orthogonal to the T0–T4 acquisition tier. Distinct from [OQ9](resolved-questions.md#oq9--acquisition-cadence-throttle--skip-policy) (which set cadence _ceilings_ from rate limits / anti-bot posture — "how fast I **can** poll") and from [Prompt #1](#1-data-acquisition-for-the-17-non-api-marketplaces) (which sets each source's acquisition _mechanism/tier_). This prompt answered **"how fast do I _need_ to poll, given how each site's inventory actually behaves?"**

**Gap it fills:** the current model has one scheduling axis — the acquisition tier — which conflates _poll-affordability_ with _poll-necessity_. Whether a source belongs in an aggressive "fast lane" is actually the **intersection** of (a) does it exhibit bursty restock "drops" that clear fast, and (b) does it expose a cheap availability-only signal that can be polled frequently without a full page render. No existing report characterizes the ~20 sources on either dimension; without it, "near-real-time" stays an unquantified adjective and the fast-lane source set can't be chosen.

```text
I'm scoping the polling cadence for a low-volume, good-faith personal/small-business monitor (Scrapy-based, single VM) that watches ~20 online drive marketplaces — manufacturer recertified-drive stores (Western Digital and Seagate recert/outlet), storage-specialist resellers (ServerPartDeals, goHardDrive, and similar), eBay/Amazon/Newegg, business VARs, and refurbished-server sellers — for HDD and SSD price and availability. I have ALREADY decided the cadence ceilings from rate limits and anti-bot posture (a per-tier baseline→ceiling table), and I have ALREADY decided each source's acquisition mechanism (official API vs structured data vs scrape). This prompt is ONLY about two other things: how VOLATILE each source's inventory actually is, and whether each source exposes a CHEAP availability-only signal I can poll frequently. Do not re-derive rate limits or generic scraping architecture.

Research and report, citing sources and dating anything that is time- or terms-sensitive (stock behavior and platform choices change):

(1) INVENTORY VOLATILITY PROFILE, PER SOURCE. Classify each of the named source types into a behavior profile: "drop-prone" (recertified/enterprise stock appears in bursty restocks and can sell out within minutes-to-hours), "churning" (a continuous flow of new independent listings where the value is the aggregate best price, not any single listing — e.g. large marketplaces), or "stable" (prices and stock move on a days timescale). Ground this in observable evidence: r/DataHoarder and r/homelab restock threads, ServerPartDeals / goHardDrive deal-tracker behavior, Western Digital and Seagate recert/outlet restock patterns, and any deal-community reporting on how fast recert drives clear. For the drop-prone sources specifically, give the best available evidence on HOW FAST a desirable restock actually clears (minutes? tens of minutes? hours?), since that sets whether sub-5-minute polling is even worth it.

(2) CHEAP AVAILABILITY SIGNAL, PER SOURCE. For each source, identify whether it exposes a lightweight, availability-only endpoint that reveals an out-of-stock → in-stock or price transition WITHOUT rendering or parsing the full product page — e.g. Shopify `/products.json` or per-variant `available` booleans and `/collections/<x>/products.json`, BigCommerce or Magento stock endpoints, a sitemap or feed with lastmod timestamps, or a JSON search endpoint. Identify each source's e-commerce platform where possible (Shopify / BigCommerce / Magento / WooCommerce / custom), since that largely determines whether a cheap poll exists. This decides whether a source can be watched with a fast, cheap "stock heartbeat" that only triggers the full fetch→parse→normalize→score→alert pipeline on a detected change.

(3) FAST-LANE SET (THE INTERSECTION). Combining (1) and (2), recommend which specific sources justify an aggressive "fast-lane" detection cadence — the sources that are BOTH drop-prone AND cheaply/safely pollable — and which should explicitly NOT be polled aggressively (churning or stable, or drop-prone but only reachable via an expensive/anti-bot-hostile path where fast polling isn't worth the risk). For the fast-lane sources, recommend a detection cadence and note the trade-off of missed drops at slower cadences.

(4) FRESHNESS SLO PER VOLATILITY CLASS. Recommend a defensible "maximum acceptable staleness" target (the max age of the freshest observation) for each volatility class, expressed as a freshness SLO measured transition-to-alert rather than a raw poll interval. Tie each target to how fast that class's inventory actually changes, and state where faster polling stops adding value relative to a human buyer's decision loop (owner reads an alert, then goes to buy).

(5) DETECTION-VS-PIPELINE DECOUPLING. Assess the pattern of running a cheap high-frequency availability heartbeat and firing the full data pipeline only on a detected transition: for which sources is it viable, what is the minimal request that reliably reveals a transition, and what are the failure modes (e.g. a cached CDN response hiding a real stock change, or a variant-level vs product-level availability mismatch)?

Deliver: a per-source table [source | volatility profile | evidence + how fast drops clear | e-commerce platform | cheap availability signal available? (what it is) | recommended detection cadence | fast-lane yes/no]; a freshness-SLO recommendation per volatility class; and a short recommendation on the availability-heartbeat-vs-full-pipeline decoupling pattern. Cite deal-community sources, platform/API docs, and any reference tools (diskprices.com, ServerPartDeals trackers); date anything stock-behavior- or terms-sensitive.
```

---

## Reconciliation order (research → spec)

All 12 prompts are run; the work now is folding their findings into [`hw-radar-master-spec.md`](specs/hw-radar-master-spec.md). This order front-loads the decisions that unblock the most design/scaffolding work — the same priority that once front-loaded the research now front-loads the spec updates.

| Priority | Prompt | What it resolves in the spec |
| --: | --- | --- |
| 🔴 1 | **#10** Stack decision (framework/DB/env) | Resolves the three `_TBD_` markers → **Django + PostgreSQL 18 + uv**; unblocks scaffolding. Also update CLAUDE.md's "FastAPI or Django (undecided)". |
| 🔴 2 | **#1** Data acquisition (17 merchants) | Sets the per-source acquisition tier (feed > structured-data > scrape > skip) for the marketplace table. |
| 🔴 3 | **#7** Legal/ToS footing | Sets the data-retention/acquisition policy; SP-API & Serper items flagged for counsel. |
| 🔴 4 | **#2** Drive grading taxonomy | Supplies the attribute schema the "Applicability" scoring factor needs. |
| 🟡 5 | **#4** Scoring model design | Defines the composite-score formula, weights, and gates. Depends on #2 and #3. |
| 🟡 6 | **#3** Recert risk & warranty | Feeds scoring penalties/bonuses and buyer guidance. |
| 🟡 7 | **#6** Entity resolution | Defines the canonical-product key + persistence schema for price-history. |
| 🟢 8 | **#9** Scheduling/orchestration | Specifies APScheduler + the fetch→…→alert pipeline stages. |
| 🟢 9 | **#8** Anti-bot scraping architecture | Companion to #1 for the scrape-only sources. |
| 🟢 10 | **#5** Price baselines & prior art | Calibrates scoring baselines; confirms no tool to reuse. |
| 🟢 11 | **#11** Notification/alerting design | Alert-rule data model + deliverability setup. |
| 🟢 12 | **#12** Warranty/serial verification | Enhancement to #3; nice-to-have for v1. |
