# Further Research Needed — ChatGPT Deep Research Prompts

Ready-to-paste prompts for ChatGPT **Deep Research** to fill gaps in [`disk-search.md`](specs/disk-search.md). Each prompt is self-contained (Deep Research can't see this repo), states the gap it fills, and dictates an output shape you can fold back into the spec.

**Scope note:** Existing research in [`docs/research/tavily-brave-serper.md`](research/tavily-brave-serper.md) already covers the Tavily/Brave/Serper search APIs and the **official** eBay Browse/Feed, Amazon SP-API, and Newegg Marketplace APIs. These prompts deliberately avoid re-treading that ground and target the untouched areas: the other 17 marketplaces, the scoring math, drive-grading domain knowledge, legal footing, and the undecided stack (`_TBD_` markers).

Paste one prompt at a time. Feed the returned reports back to me and I'll reconcile them into `disk-search.md`.

## Table of Contents

- [Further Research Needed — ChatGPT Deep Research Prompts](#further-research-needed--chatgpt-deep-research-prompts)
  - [Table of Contents](#table-of-contents)
  - [Topic Gap in disk-search.md](#topic-gap-in-disk-searchmd)
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
  - [Suggested priority order](#suggested-priority-order)

---

The 12 topics, mapped to the gaps they fill:

## Topic Gap in disk-search.md

- 🔴 1 Data acquisition for the 17 non-API merchants Only eBay/Amazon/Newegg had acquisition research
- 🔴 2 HDD/SSD grading taxonomy (CMR/SMR, workload, endurance) "Applicability" scoring factor had no defined attributes
- 🔴 3 Recertified-drive risk & warranty landscape The tool's core value thesis, entirely unresearched
- 🟡 4 Quantitative multi-factor scoring model Five factors named, zero methodology
- 🟡 5 Price benchmarks ($/TB baselines) & prior art No idea what a "good deal" is, or what tools exist
- 🟡 6 Cross-marketplace entity resolution Price-history DB has no "same drive" matching
- 🔴 7 Legal/ToS footing for scraping + storage Public business repo scraping 20 sites, no analysis
- 🟢 8 Anti-bot scraping architecture "Scrapy" named; no plan for protected sites
- 🟢 9 Scheduling/orchestration "Near-real-time" promised, no scheduler
- 🟡 10 Framework/DB/env stack decision The three explicit _TBD_ markers
- 🟢 11 Notification/alerting design & deliverability AgentMail named; no dedup/fatigue/deliverability
- 🟢 12 Warranty/serial verification data sources No way to verify used-drive claims

---

## 1. Data acquisition for the 17 non-API marketplaces

**Gap it fills:** The spec lists 20 marketplaces but only eBay/Amazon/Newegg have documented acquisition paths. The manufacturer stores and specialty resellers have zero research — no answer on whether feeds, structured data, or clean scraping exist.

```text
I'm building a personal price-and-availability monitor for enterprise/NAS hard drives (HDDs) and SSDs. I already have acquisition strategies for eBay (Browse/Feed API), Amazon (SP-API), and Newegg (Marketplace API). I need to know how to programmatically obtain current product listings, prices, and stock status from the following 17 merchants, none of which I've researched yet:

Western Digital Store / WD Recertified, Seagate Store / Seagate Recertified, ServerPartDeals, B&H Photo Video, CDW, Insight, PCNation, Wiredzone, goHardDrive, TechMikeNY, ETB Technologies, Bargain Hardware, HardDrivesDirect, ServerMonkey, SaveMyServer, The Server Store, Memory4Less.

For EACH merchant, report: (1) whether any public/partner API, product feed, affiliate feed (e.g. via CJ, Impact, Rakuten, Sovrn), or Google Merchant/structured data exists; (2) whether product pages expose machine-readable structured data (JSON-LD, schema.org Product/Offer, microdata) I could parse; (3) presence and strength of anti-bot protection (Cloudflare, PerimeterX/HUMAN, Akamai, DataDome, CAPTCHAs, rate limiting) based on observable evidence; (4) the platform the storefront runs on (Shopify, Magento/Adobe Commerce, BigCommerce, WooCommerce, custom) since that dictates predictable URL/JSON patterns; (5) a recommended acquisition approach (feed > structured-data parse > headless scrape > skip) with a difficulty rating.

Prioritize the recertified-drive specialists (WD/Seagate recertified stores, ServerPartDeals, goHardDrive) since those are my primary value targets. Cite official docs, affiliate-network catalogs, and platform fingerprints. Present as a per-merchant table plus a short prose recommendation for the top 5.
```

---

## 2. HDD/SSD grading & "applicability" taxonomy

**Gap it fills:** The scoring system has an "Applicability for Intended Use" factor favoring "server Enterprise/NAS grade" drives, but the spec never defines the machine-readable attributes that classify a drive. Without this taxonomy the scorer can't be built.

```text
I'm building a scoring engine that ranks hard-drive and SSD listings for a homelab/small-business buyer who prefers enterprise- and NAS-grade drives. I need a rigorous, machine-usable taxonomy of the drive specifications that determine whether a drive is suitable for 24/7 NAS/server use, so I can extract these fields from listings and score them.

Cover, for both HDDs and SSDs: (1) the tier ladder — desktop vs NAS vs enterprise/datacenter — and the concrete spec differences (workload rating in TB/year, MTBF/AFR, warranty length, vibration tolerance, rotational-vibration sensors, error recovery control / TLER/ERC, power-loss protection); (2) HDD recording tech — CMR vs SMR (and PMR terminology confusion), why SMR is disqualifying for NAS/RAID rebuilds, and how to reliably detect SMR from model numbers since vendors hide it; (3) helium vs air-filled, and any reliability implications; (4) SSD-specific: DWPD/TBW endurance, SLC/MLC/TLC/QLC, DRAM vs DRAM-less, power-loss protection, U.2/U.3/M.2/SATA/SAS form factors and interfaces; (5) the current model-family landscape — which product lines map to which tier (e.g. WD Red Plus/Pro, WD Gold, Ultrastar DC; Seagate IronWolf/IronWolf Pro, Exos; Toshiba N300/MG/MN) — as a reference table; (6) which of these attributes can be parsed from a typical retail listing title/description vs which require a model-number lookup table.

Deliver: a scoring-oriented attribute schema (field name, data type, how to source it, why it matters), plus the model-family-to-tier reference table. Cite manufacturer spec sheets and datasheets.
```

---

## 3. Recertified / refurbished enterprise-drive risk & warranty landscape

**Gap it fills:** The tool's entire value thesis is buying recertified enterprise HDDs, but there's no research on what "recertified" actually means, how the risk compares to new, or how warranty terms differ by vendor — all of which should feed the score and buyer guidance.

```text
I'm building a tool to hunt deals on RECERTIFIED and REFURBISHED enterprise hard drives (WD, Seagate, Toshiba, HGST) for a homelab/small-business buyer, sourced from manufacturer recert stores and specialty resellers (ServerPartDeals, goHardDrive, TechMikeNY, serverpart resellers, eBay sellers).

Research and report: (1) precise definitions and differences between "factory recertified", "recertified", "refurbished", "renewed", "used", and "new pulls / new old stock" as used in the enterprise-drive market, and how trustworthy each label is; (2) what manufacturers actually do in the recertification process; (3) real-world reliability evidence for recertified enterprise drives vs new — cite Backblaze drive-stats data, community datasets (r/DataHoarder, r/homelab surveys), and any studies, being explicit about what's rigorous vs anecdotal; (4) the warranty landscape: typical warranty length offered by ServerPartDeals, goHardDrive, WD/Seagate recert stores, and typical eBay sellers, plus whether manufacturer warranty transfers and how to check a serial number's warranty status with WD and Seagate; (5) red flags that indicate a bad recert listing (wiped SMART data, high power-on hours, fake labels, grey-market); (6) which SMART attributes and power-on-hours thresholds a buyer should demand or check on arrival.

Deliver actionable buyer heuristics I can encode as scoring penalties/bonuses (e.g. "warranty < 1yr → penalty", "seller discloses power-on hours → bonus"), plus a per-vendor warranty comparison table. Cite sources and flag confidence levels.
```

---

## 4. Quantitative multi-factor scoring model design

**Gap it fills:** The spec names five scoring factors (price/$per-TB, availability, seller reputation, applicability, overall) but gives no methodology for normalizing and combining them. This is the core algorithm and is entirely unspecified.

```text
I'm designing the scoring algorithm for a hard-drive deal-monitoring tool. Each listing has heterogeneous signals I want to fuse into one 0–100 "deal score": price expressed as USD-per-TB, in-stock availability, seller reputation (from different marketplaces with different rating scales), and fitness-for-purpose (enterprise/NAS suitability, warranty, condition). I want a principled design, not an ad-hoc weighted sum I made up.

Research and recommend: (1) normalization techniques for combining features on different scales and directions (min-max, z-score, robust/quantile scaling, log transforms for price) and which fits a right-skewed $/TB distribution best; (2) how to make $/TB scoring *relative to a moving baseline* (e.g. percentile rank against recent listings for the same capacity/tier) rather than an absolute threshold, so the score self-adjusts as market prices fall; (3) methods to normalize seller-reputation across marketplaces with incompatible scales (eBay feedback % + count, Amazon seller rating, star ratings, "no rating available") into a comparable 0–1 trust score, including how to handle low-sample-size sellers (Bayesian/Wilson-score shrinkage); (4) approaches to combining factors — weighted geometric mean vs arithmetic, hard gates/vetoes (e.g. SMR or no-return-policy caps the max score) vs soft penalties, and multi-criteria decision methods (TOPSIS, weighted product model) worth considering; (5) how to keep the score explainable so a listing can show *why* it scored what it did.

Deliver a concrete recommended scoring formula with each sub-score's normalization defined, sensible default weights for a value-focused enterprise-drive buyer, and a worked numeric example on 3–4 hypothetical listings. Cite methods literature where relevant.
```

---

## 5. Price benchmarking, $/TB baselines & existing reference tools

**Gap it fills:** Scoring on price requires knowing what a _good_ $/TB is per tier/capacity, and whether prior art exists to borrow from or integrate. The spec assumes $/TB but provides no baselines or awareness of competitors.

```text
I'm building a personal hard-drive/SSD deal tracker and need external reference points for "what is a good price" and awareness of existing tools so I don't reinvent them.

Research: (1) current (as of your latest data) street-price baselines in USD-per-TB for enterprise/NAS HDDs across common capacities (8TB, 12TB, 14TB, 16TB, 18TB, 20TB, 22TB, 24TB+) split by new vs recertified, and for enterprise/NAS SSDs by capacity/endurance tier — give ranges and note volatility; (2) the known "sweet spot" capacities where $/TB is lowest and why it shifts over time; (3) existing tools and communities that already track drive prices — diskprices.com, camelcamelcamel, Keepa, PCPartPicker price history, r/DataHoarder price threads, serverpartdeals deal trackers, shucking/external-drive price guides — including for each whether it has an API, data export, or affiliate feed I could integrate or learn from; (4) the "shucking" external-drive market as an alternate value source (which external enclosures contain which internal drives, current risks/caveats); (5) how drive prices move seasonally and around events (Black Friday, Prime Day, capacity transitions) so my tool can flag genuinely-good vs normal prices.

Deliver a $/TB baseline reference table by capacity and tier, a competitor/tool landscape table (name, coverage, API availability, how it could integrate), and a short section on timing signals. Cite sources and date every price figure.
```

---

## 6. Cross-marketplace product entity resolution

**Gap it fills:** A price-history database is useless if "the same drive" appears as different rows per merchant. The spec's database section never addresses matching listings to a canonical product — the hardest data-engineering problem here.

```text
I'm building a database that tracks the same hard-drive and SSD models across ~20 marketplaces (eBay, Amazon, Newegg, manufacturer stores, specialty resellers) to compare prices over time. The core problem is ENTITY RESOLUTION: recognizing that listings from different merchants — with different titles, SKUs, and identifiers — refer to the same physical product, while distinguishing genuinely different variants (capacity, interface, recording tech, condition, generation).

Research and recommend: (1) the canonical identifiers available for storage drives — manufacturer model/part number (MPN), GTIN/UPC/EAN, Amazon ASIN, eBay EPID, and how reliably each maps to a unique physical product; the pitfalls (same model number across capacities, OEM vs retail part numbers, region variants, revision suffixes); (2) how to parse and normalize noisy retail listing titles into structured attributes (brand, family, capacity, interface, form factor, condition) — techniques from rule-based parsing to NER to LLM extraction, with tradeoffs; (3) a matching/blocking strategy — how to define a canonical product key, when to trust an exact identifier vs fuzzy attribute match, and how to avoid false merges (a 16TB vs 18TB collision); (4) how CONDITION and variant should factor into the canonical key (should "recertified 14TB Exos" and "new 14TB Exos" be one product with two condition facets, or separate keys?); (5) established open-source tools/libraries or datasets for product matching (e.g. entity-resolution libraries, dedupe, record linkage toolkits) worth using.

Deliver a recommended canonical-product-key design, a title-parsing approach, and a matching decision flow. Cite entity-resolution/product-matching literature and any usable tools.
```

---

## 7. Legal & Terms-of-Service footing for scraping and price monitoring

**Gap it fills:** The tool scrapes ~20 commercial sites and stores their data in a **public** GitHub-org repo tied to a business. The spec has no legal analysis — a material risk given business use, and it constrains what can be stored/retained.

```text
I'm building a hard-drive price-monitoring tool for a small US business that will scrape or API-pull product listings, prices, and availability from ~20 retail sites (Amazon, eBay, Newegg, B&H, CDW, manufacturer stores, specialty resellers) and STORE that data in a database to track price history over time. I need a grounded, current understanding of the legal and terms-of-service landscape so I can set a compliant retention and acquisition policy. I am not asking for legal advice to rely on, but for a well-cited overview I can take to counsel.

Research: (1) the current US legal landscape for web scraping of publicly available data — the state of CFAA case law post-hiQ v. LinkedIn and Van Buren, and what remains legally risky vs relatively settled; (2) how breach-of-contract / terms-of-service claims differ from CFAA, and whether browsewrap vs clickwrap enforceability matters for a scraper; (3) copyright and database-rights considerations for storing prices, product descriptions, and images; (4) the specific stored-data restrictions in the terms of the major APIs I'll use — Amazon (SP-API and Creators/Product Advertising content caching/retention rules), eBay (data retention and caching), Google/Serper-derived data — and what each permits me to persist; (5) robots.txt's actual legal weight vs its practical role; (6) practical, widely-recommended compliance hygiene for a good-faith monitor (rate limiting, identifying user-agent, honoring robots.txt, not evading anti-bot, PII avoidance).

Deliver a risk-tiered summary (lower-risk vs higher-risk practices), a per-source "what I'm allowed to store and for how long" table for the major APIs, and a short recommended data-retention/acquisition policy. Cite cases, official API terms, and reputable legal analyses; date everything and flag where the law is unsettled.
```

---

## 8. Anti-bot-resilient scraping architecture for e-commerce

**Gap it fills:** The spec names Scrapy but nothing about how to actually retrieve pages from sites that fight scrapers (most large retailers). This is a make-or-break infrastructure decision left blank.

```text
I'm building a Python scraper (currently planning to use Scrapy) that periodically fetches product/price/stock data from e-commerce sites ranging from easy (small Shopify/Magento specialty resellers) to heavily protected (Amazon, Newegg, big retailers behind Cloudflare/Akamai/DataDome/PerimeterX). This is low-volume, good-faith monitoring for personal/small-business use — not high-frequency abuse. I want a pragmatic, current architecture recommendation.

Research and recommend: (1) when plain HTTP + HTML parsing suffices vs when I need a headless/real browser (Playwright, Selenium, or scraping-specific browsers) — decision criteria based on JS-rendering and structured-data availability; (2) the current tooling landscape for Python e-commerce scraping — Scrapy, Playwright, curl_cffi/TLS-fingerprint libraries, and managed scraping APIs (ScraperAPI, ZenRows, Bright Data, Zyte API, Oxylabs, Firecrawl) — with a cost/effort/reliability comparison for a low-volume hobby-scale user; (3) how to detect and cheaply consume JSON-LD / schema.org structured data or hidden JSON (Next.js __NEXT_DATA__, Shopify products.json, Magento patterns) to avoid brittle HTML parsing; (4) polite, ban-avoiding practices that stay on the right side of good faith — rate limiting, backoff, caching, realistic headers, honoring robots.txt — versus aggressive evasion (residential-proxy rotation, CAPTCHA-solving) I should avoid or treat as a signal to stop; (5) a recommended tiered architecture: cheap path for easy sites, escalation path for protected ones, and a "not worth it, use the API or skip" cutoff.

Deliver a decision tree (site difficulty → recommended technique), a tool comparison table with rough costs, and a recommended default stack for Python. Cite tool docs and note anything version-sensitive.
```

---

## 9. Scheduling, orchestration & pipeline architecture (Python)

**Gap it fills:** The spec promises "real-time or near-real-time monitoring" but specifies nothing about _how_ recurring jobs run — the scheduler/orchestration layer that turns scrapers into a monitoring service is absent.

```text
I'm building a Python service that periodically polls ~20 data sources (APIs and scrapers) for hard-drive prices/availability, normalizes and scores the results, writes to PostgreSQL, and fires alerts on matches/price-drops. Different sources need different poll frequencies (some hourly, some daily) and different rate limits. It runs on a single Debian VM (Hetzner, behind NGINX) for personal/small-business scale — not a large distributed system.

Research and recommend the orchestration/scheduling layer: (1) compare the realistic options at THIS scale — plain cron + scripts, APScheduler, Celery + beat + Redis/RabbitMQ, RQ, Dramatiq, Prefect, Dagster, Airflow — on setup complexity, per-source scheduling flexibility, retry/backoff, observability, and operational weight for a single-VM single-maintainer deployment; explicitly flag which are over-engineered here; (2) how to model per-source rate limits and staggering so I don't hammer any site or trip rate limits (token buckets, jittered scheduling, per-domain concurrency caps); (3) retry, backoff, and failure-isolation patterns so one flaky source doesn't stall the pipeline, plus dead-letter/alerting on persistent source failure; (4) how to structure the pipeline stages (fetch → parse → normalize → resolve entity → score → persist → alert) for testability and partial reruns; (5) idempotency and dedup so re-running a source doesn't create duplicate observations or duplicate alerts.

Deliver a recommended default (with a one-line justification for why the heavier options are overkill at this scale), a per-source scheduling model, and a stage/retry architecture sketch. Cite the tools' own docs and note version-sensitive advice.
```

---

## 10. Web framework, database & environment-management stack decision

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

**Gap it fills:** The spec wants email/SMS/push alerts (via AgentMail) but says nothing about alert-fatigue control, deliverability, or dedup — the difference between a useful alerter and a spam cannon.

```text
I'm building the alerting layer for a hard-drive deal monitor. It should notify me (email at minimum, maybe SMS/push later) when a watched drive becomes available or drops below a target price/score. I want a design that's genuinely useful and doesn't devolve into noise.

Research and recommend: (1) alert-fatigue control patterns — deduplication (don't re-alert the same listing), debouncing/cooldowns, digest/batching (hourly/daily roundups vs instant), thresholds and hysteresis (avoid flapping when a price hovers at the boundary), and per-watch rate caps; (2) how to model "watches"/alert rules cleanly (criteria: model/capacity/tier, max price or $/TB, min score, marketplace filter) and match incoming observations against them efficiently; (3) email DELIVERABILITY for a self-hosted small sender from a Hetzner VM sending to my own domain — SPF/DKIM/DMARC setup, why sending directly from a datacenter IP often lands in spam, and whether to use a transactional email API (I have an AgentMail API key; also compare Postmark, SES, Resend, Mailgun as alternatives) rather than raw SMTP; (4) SMS and push options at hobby scale (Twilio, Pushover, ntfy, Telegram bot) with cost/effort tradeoffs; (5) how to make alert emails actionable (clear subject with price/$per-TB/score, direct listing link, why-it-matched explanation, one-click snooze/unsubscribe-per-watch).

Deliver an alert-rule data model sketch, a dedup/debounce/digest strategy, a deliverability setup checklist, and a channel comparison table. Cite deliverability best-practices and the relevant service docs.
```

---

## 12. Manufacturer & specialty-reseller warranty/serial-verification data sources

**Gap it fills:** Deep-dive companion to prompts 1 and 3: to score used/recert listings and warn about scams, the tool needs programmatic ways to verify drive identity and warranty from a serial or model number — sources the spec never mentions.

```text
I'm building a tool that evaluates used/recertified enterprise hard-drive listings. To score trust and warranty value, and to catch misrepresented listings, I want to know what identity/warranty verification data I can obtain programmatically or semi-automatically from a drive's model number or serial number.

Research: (1) Western Digital, Seagate, and Toshiba warranty-status lookup services — do they have public/undocumented web endpoints or APIs that return warranty status, expiration, and product model from a serial number, and what are the terms/rate realities of using them at low volume; (2) how to decode/validate WD, Seagate, and Toshiba model numbers and part numbers into capacity, tier, interface, and generation (published decoders or community references); (3) whether serial-number format/validation can catch obviously fake or grey-market listings; (4) what SMART data (power-on hours, reallocated sectors, etc.) a listing might disclose and how to interpret it for a buy/no-buy signal; (5) any third-party services or datasets (e.g. drive-info APIs, community model databases) that map model numbers to full specs so I don't hand-maintain a lookup table.

Deliver: a table of verification sources (source, what it returns, input required, access method, rate/terms caveats), model-number decoder references per manufacturer, and a recommended verification flow for a listing. Cite official warranty portals and community decoder references; be explicit about what's official vs reverse-engineered vs unavailable.
```

---

## Suggested priority order

If running these sequentially, this order front-loads the decisions that unblock the most design work:

| Priority | Prompt | Why first |
| --: | --- | --- |
| 🔴 1 | **#1** Data acquisition (17 merchants) | Determines what's even buildable per source. |
| 🔴 2 | **#7** Legal/ToS footing | Gates what you may store/retain; business + public repo raises stakes. |
| 🔴 3 | **#2** Drive grading taxonomy | The scorer can't exist without the attribute schema. |
| 🟡 4 | **#4** Scoring model design | Core algorithm; depends on #2 and #3. |
| 🟡 5 | **#3** Recert risk & warranty | Feeds scoring penalties/bonuses and buyer guidance. |
| 🟡 6 | **#10** Stack decision (framework/DB/env) | Resolves the three `_TBD_` markers; unblocks scaffolding. |
| 🟡 7 | **#6** Entity resolution | Hardest data-engineering problem; needed before price-history is meaningful. |
| 🟢 8 | **#9** Scheduling/orchestration | Turns scrapers into a service. |
| 🟢 9 | **#8** Anti-bot scraping architecture | Companion to #1 for the scrape-only sources. |
| 🟢 10 | **#5** Price baselines & prior art | Calibrates scoring and checks for reusable tools. |
| 🟢 11 | **#11** Notification/alerting design | Independent; can come late. |
| 🟢 12 | **#12** Warranty/serial verification | Enhancement to #3; nice-to-have for v1. |
