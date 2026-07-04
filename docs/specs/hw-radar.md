# Hardware Radar

**What it is:** A search tool that monitors websites like eBay, ServerPartDeals, Amazon, Newegg, and other online marketplaces for hard disk drives (HDDs) and solid-state drives (SSDs). It alerts users when specific models or brands become available or drop in price. It should locate deals and provide a quantitative score based on price, availability, and seller reputation.

## Audience

This tool is designed for my personal/business use to assist with monitoring and purchasing hard disk drives and solid-state drives for L3Digital assets. It will be featured such that it is convenient for me to use. The first version will not spend development time on making it user-friendly for others, cross-compability, and other considerations that a distributed tool might require; however, it will be designed in a way that it can be easily extended to support other users in the future if the tool proves useful.

## General Design Principles

- **Engineered to Needs:** The tool should be designed to meet the specific needs of the user (myself) and not be over-engineered with unnecessary features or complexity until it is proven necessary.
- **Extensability & Expandability:** The tool should be designed in a way that allows for easy future expansion to support additional:
  - users, user accounts, and user preferences
  - marketplaces
  - scoring criteria
  - alerting mechanisms
  - hardware types (e.g., RAM, GPUs, etc.)
- **Maintainability:** The codebase should be clean, well-documented, and follow best practices to ensure that it can be easily maintained and updated over time.
- **Reliability:** The tool should be robust and handle errors gracefully, ensuring that it continues to function even when encountering issues with marketplace APIs or network connectivity.
- **Security:** The tool should handle sensitive information (e.g., API keys, credentials) securely and follow best practices for authentication and authorization. These should never be committed to the public repository, hard-coded, or otherwise exposed.
- **Moderate Aggressive Usage:** The tool should be designed to avoid excessive requests or scraping that could be considered abusive or violate terms of service or result in rate limiting.

## Features

- **Real-time (or near real-time) Monitoring:** Continuously or frequently scans multiple online marketplaces for hard disk drives and solid-state drives.
- **Score System:** Assigns a score to each listing to help users quickly identify the best deals.
  - _Price:_ Lower prices receive higher scores. Measured in USD per TB.
  - _Availability:_ In-stock items receive higher scores than out-of-stock items.
  - _Seller Reputation:_ Sellers with higher ratings and positive feedback receive higher scores.
  - _Applicability for Intended Use:_ Scores can also consider the drive's specifications (e.g., speed, capacity, warranty) to ensure it meets user needs (server Enterprise/NAS grade drives preferred).
  - _Overall Score:_ Combines the above factors into a single score to rank listings.
- **Alert System:** Sends notifications via email, SMS, or push notifications when a desired hard disk drive or solid-state drive is found or when a price drop occurs.
- **Database of Listings:** Maintains a database of current and past listings to track price trends and availability over time. Also permits sorting and filtering based on user preferences (e.g., brand, capacity, interface type).
- **User Interface:** Provides a user-friendly web-based interface for users to input their desired specifications, set alert preferences, search and filter the database, etc.
- **Integration with Marketplaces:** Directly integrates with popular online marketplaces to fetch listings and updates in real-time where possible. Fallback to periodic scraping if APIs are not available.
- **Historical Data Analysis:** Offers insights into price trends and availability patterns over time, helping users make informed purchasing decisions.

## Marketplaces to Monitor

| Rank | Site | Best use | Source type | Conditions to consider | Trust posture | Ranking rule for tool |
| --: | --- | --- | --- | --- | --- | --- |
| 1 | [Western Digital Store / WD Recertified](https://www.westerndigital.com/) | WD NAS/enterprise HDDs | Manufacturer-direct | New, recertified | Very high | Prefer for WD Red, Gold, Ultrastar, and WD factory recertified drives. |
| 2 | [Seagate Store / Seagate Recertified](https://www.seagate.com/) | Seagate NAS/enterprise HDDs | Manufacturer-direct | New, recertified | Very high | Prefer for IronWolf, Exos, and Seagate factory recertified drives. |
| 3 | [ServerPartDeals](https://serverpartdeals.com/) | Recertified enterprise HDDs | Storage-specialist reseller | Recertified, used, new | High | Best non-manufacturer source for recertified enterprise HDD value. |
| 4 | [B&H Photo Video](https://www.bhphotovideo.com/) | New drives from known brands | Major authorized retailer | New, open-box, used | High | Prefer for new drives when price is competitive and seller is B&H. |
| 5 | [CDW](https://www.cdw.com/) | Business/enterprise purchasing | Business VAR | New | High | Prefer when compatibility, procurement reliability, or business sourcing matters more than lowest price. |
| 6 | [Insight](https://www.insight.com/) | Business/enterprise purchasing | Business VAR | New | High | Similar to CDW; use for business-grade sourcing and supported part numbers. |
| 7 | [Newegg](https://www.newegg.com/) | New drives, deals | Marketplace/retailer | New, open-box, marketplace | Medium-high with filters | Rank high only when sold by Newegg, manufacturer, or trusted specialist seller. |
| 8 | [Amazon](https://www.amazon.com/) | New drives, fast availability | Marketplace/retailer | New, renewed, marketplace | Medium-high with filters | Rank high only when sold by Amazon, manufacturer, or trusted specialist seller; penalize unknown sellers. |
| 9 | [PCNation](https://www.pcnation.com/) | New drives, exact SKU sourcing | VAR / reseller | New | Medium-high | Good for part-number shopping; rank below larger VARs unless price/availability wins. |
| 10 | [Wiredzone](https://www.wiredzone.com/) | Server/storage ecosystem parts | Server-specialist reseller | New, server-compatible parts | Medium-high | Prefer when Supermicro/server compatibility is important. |
| 11 | [goHardDrive](https://www.goharddrive.com/) | Budget recertified HDDs | Storage reseller | Recertified, used | Medium | Good deal source; require clear seller warranty and condition labeling. |
| 12 | [TechMikeNY](https://www.techmikeny.com/) | Refurbished servers and parts | Refurbished server specialist | Used, refurbished | Medium | Better for complete servers or server parts than standalone critical storage. |
| 13 | [ETB Technologies](https://www.etb-tech.com/) | Refurbished enterprise parts | Refurbished enterprise reseller | Used, refurbished | Medium | Stronger option for UK/EU buyers; region-dependent ranking. |
| 14 | [Bargain Hardware](https://www.bargainhardware.co.uk/) | Refurbished enterprise hardware | Refurbished enterprise reseller | Used, refurbished | Medium | Useful UK/EU refurb source; rank higher only for regional availability. |
| 15 | [HardDrivesDirect](https://www.harddrivesdirect.com/) | Exact enterprise/OEM part numbers | Specialty parts reseller | New, refurbished, legacy parts | Medium-low | Use when exact OEM part matching matters; not first choice for bulk NAS builds. |
| 16 | [ServerMonkey](https://www.servermonkey.com/) | Refurbished server parts | Refurbished server reseller | Used, refurbished | Medium-low | Useful for refurb server builds; penalize for standalone drive purchases unless warranty is acceptable. |
| 17 | [SaveMyServer](https://savemyserver.com/) | Refurbished servers/storage | Refurbished server reseller | Used, refurbished | Medium-low | Use as fallback for refurb hardware; rank depends heavily on warranty and geography. |
| 18 | [The Server Store](https://www.theserverstore.com/) | Refurbished servers/storage | Refurbished server reseller | Used, refurbished | Medium-low | Better for systems than drives; fallback source. |
| 19 | [Memory4Less](https://www.memory4less.com/) | Legacy/OEM storage parts | Specialty parts reseller | New old stock, refurbished, hard-to-find parts | Low-medium | Use mainly for hard-to-find parts; not preferred for large storage purchases. |
| 20 | [eBay](https://www.ebay.com/) | Used/recertified deal hunting | Marketplace | Used, recertified, seller-dependent | Variable | Only rank individual listings highly when seller reputation, warranty, condition, and return policy are strong. |

## Software and Tooling Stack

- **Programming Language:** Python (for backend processing, web scraping, and data analysis).
- **Web Framework:** Django with server-rendered templates + HTMX ([ADR 0004](../adr/adr-0004-web-framework-django-htmx.md)).
- **Database:** PostgreSQL (system-of-record) + TimescaleDB for the price-history workload ([ADR 0007](../adr/adr-0007-datastore-postgresql-timescaledb.md)).
- **Notification System:** Email alerts to `chris@l3digital.net`, sent via the existing **Microsoft Graph → M365** path (branded `@l3digital.net` sender, zero marginal cost, creds at OpenBao `secret/apps/microsoft365`), with **AgentMail free** (`@agentmail.to`) as an independent fallback ([ADR 0013](../adr/adr-0013-notification-transport-m365-graph.md)); a paid transactional provider (Postmark/SES) is the documented upgrade path. SMS/push are potential future channels.
- **Orchestration / Scheduler:** a single systemd-supervised **poller** process running **APScheduler 3.11.x** (`AsyncIOScheduler`), owning per-source cadence, jitter, two-level token-bucket admission, and shared circuit-breaker state ([ADR 0012](../adr/adr-0012-orchestration-apscheduler.md)).
- **Web Scraping Libraries:** **Scrapy** orchestrator with a structured-data detector in front of every parser (JSON-LD → platform JSON → bootstrap JSON → HTML selectors), escalating **HTTP-first, browser-last** to **`curl_cffi`** (TLS-fingerprint gap) then **Playwright via `scrapy-playwright`** (genuine JS rendering / reconnaissance), then managed-unblocker-or-skip for the hostile tail ([ADR 0014](../adr/adr-0014-scraping-runtime-escalation-stack.md)). The `curl_cffi`/Playwright tiers are deferred to M5; M1 ships on plain HTTP + structured-data parsing.

## Environment and Deployment

- **GitHub Repository:** `[L3DigitalNet public repo](https://github.com/L3DigitalNet/hw-radar)`
  - _Branching Strategy:_ Main branch for stable releases, development branch for ongoing work, and feature branches for new features or bug fixes.
  - _Commit Guidelines:_ Follow conventional commit messages for clarity and consistency. Commit directly to branches, do not use Pull Requests for personal development work unless collaborating with others.
  - _Note_: This project lives in my Organization account on GitHub because I am intending to use this to purchase hard drives for L3Digital. The repository is public; secrets (API keys, credentials) are **never committed, hard-coded, or exposed**. In production the app resolves them from **OpenBao at runtime** via a local OpenBao Agent ([open-questions.md](../open-questions.md) gap #2 / OQ1); a local `.env` is used **for development only**.
- **Local Clone:** `~/projects/hw-radar`
- **Server Configuration:**
  - _Location:_ Hetzner dedicated server
  - _Containerization:_ **Dedicated LXC container** in Proxmox (not a VM), per the homelab dedicated-LXC standard ([ADR 0003](../adr/adr-0003-deploy-as-lxc-container.md)).
  - _Operating System:_ Debian 13
  - _Web Server:_ NGINX for serving the web application and handling HTTPS.
  - _Database:_ **PostgreSQL (system-of-record) + TimescaleDB** for the price-history observation workload ([ADR 0007](../adr/adr-0007-datastore-postgresql-timescaledb.md)); lives in the same LXC container as the web application for simplicity.
  - _Environment Management:_ uv ([ADR 0002](../adr/adr-0002-python-tooling-standard-local-deviations.md)).
  - _Backup & Monitoring:_ Reuses the existing Hetzner CT infrastructure — file-level restic (local + offsite) + hourly DB dumps, and monitoring auto-discovers the container. Provisioning must add the CT to the backup allowlist, and an off-box heartbeat is still needed. Caveats (≤1 h RPO, no PITR, TimescaleDB dump handling): [ADR 0003](../adr/adr-0003-deploy-as-lxc-container.md) and [open-questions.md](../open-questions.md) gap #5/#6.
- **CI/CD Pipeline:** GitHub Actions for automated testing and deployment.
  - _Runner:_ GitHub-hosted `ubuntu-latest` runner — not self-hosted ([ADR 0006](../adr/adr-0006-cd-rsync-over-tailscale-ssh.md)).
  - _Workflows:_ Separate workflows for testing, building, and deployment.
  - _Live Deployment:_ Automatic deployment to the Hetzner CT on merge to `main`, via `rsync` over Tailscale SSH (ADR 0006).
- **Access:**
  - _Address:_ `https://hw-radar.l3digital.net`
  - _Security:_ HTTPS via NGINX and Let's Encrypt.
  - _Authentication:_ Single-account session login with Argon2id, internet-facing ([ADR 0005](../adr/adr-0005-single-account-session-auth.md)).

### Special Considerations

- **Public Repository:** The repository is public. Secrets (API keys, credentials) are **never committed, hard-coded, or otherwise exposed** — production resolves them from **OpenBao at runtime**, and a local `.env` is for development only. Public-repo constraints also shape CI: the runner holds **no OpenBao credential** ([ADR 0006](../adr/adr-0006-cd-rsync-over-tailscale-ssh.md)).
- **Data Acquisition & Retention Posture:** acquisition is **tiered by legal persistability**, not just by data quality — each source carries a `retention_class` (see [`us-scraping-and-data-retention-landscape`](../research/us-scraping-and-data-retention-landscape-for-a-retail-hdd-price-monitor.md), re-verified 2026-07-03). Tiers:
  - **Persistable (the price-history moat):** **merchant public pages** (recert specialists, resellers, VARs) scraped as **facts, not expression** — the legally cleanest store. **eBay** via the Browse API is storable as current offers (**≤6 h** freshness, **delete-on-delist**, PII-delete; Browse is *not* a Restricted API so the pricing-tool consent bar does not apply — but do **not** build/act on a derived eBay price *model*, §8 gray area). **Tavily**-extracted facts are persistable.
  - **Discovery-only, never persisted (`transient_discovery`, TTL 0):** **Google Programmable Search** (prohibits non-transitory storage; discontinues 2027-01-01), **Serper** (persist only the discovered URL, then re-fetch from the merchant), and **Brave** on the standard plan (storage needs the sales-led "Data with storage rights" plan). Search APIs are **discovery, not authoritative state**.
  - **Amazon = display/discovery only, no price persistence:** official APIs (Creators/PA-API) are affiliate-only + 24 h cache + no image bytes; SP-API is seller-only. Persist **ASIN indefinitely**, nothing else.
  - **Guardrails (encoded in the scraper):** public logged-out pages only; never log in / bypass anti-bot / CAPTCHA; `ROBOTSTXT_OBEY=True`; AUTOTHROTTLE + honor `429`/`Retry-After`; honest User-Agent; prefer official APIs; store facts not expression; no PII; stop on a specific cease-and-desist. These bound the **Moderate Aggressive Usage** principle for scraped (non-API) sources. **No image-byte storage anywhere** (URLs/hashes only). Items tagged for counsel review are noted in the research report.

## Database Schema

_The canonical data model is fixed by **[ADR 0010](../adr/adr-0010-canonical-data-model.md)**: a multi-grain identity ladder — `category → product_family → product_model` (the **physical**, condition-free canonical entity) `→ product_variant` (the **sellable** identity: condition/packaging/warranty-channel) `→ listing → offer_snapshot`, plus an orthogonal `drive_unit` (serial/SMART) grain. External identifiers (GTIN/MPN/ASIN/ePID) are `product_alias` rows, not columns; drive attributes live in a typed `drive_spec` satellite. Full field lists: [`database-architecture.md`](../research/database-architecture.md) + the [suitability taxonomy](../research/machine-usable-drive-suitability-taxonomy-for-24-7-nas-and-server-scoring.md)._ **Extensibility constraint (per [General Design Principles](#general-design-principles)):** the ladder is category-generic — only `drive_spec` is drive-shaped — so additional **hardware types** (RAM, GPUs, …), marketplaces, scoring criteria, and users are added via a new satellite / rows / plugin **without a spine rewrite**. v1 implements the drive category only.

## Scoring System

_Fixed by **[ADR 0011](../adr/adr-0011-composite-deal-score.md)**, validated against mock data ([`drive-deal-scoring-model-test-results`](../research/drive-deal-scoring-model-test-results.md))._

Each listing gets an explainable **0–100** score = a **weighted geometric mean** of four normalized subscores, gated by three non-compensatory veto caps:

- **Price (weight 0.50)** — a **cohort-relative weighted cheapness percentile** on `ln($/TB)`, not an absolute threshold, so the score tracks a moving market. Cohort key = capacity · tier · interface/form · condition; 90-day window with **30-day half-life** decay. Warm-up shrinkage `s_price = λ·(1−q) + (1−λ)·0.5` with **`λ = min(1, n_eff/30)`** pulls thin cohorts toward neutral (marked _provisional_); documented cohort-relaxation (condition → adjacent capacity → parent tier) fills small cohorts. `$/TB` includes shipping (+ tax where known); missing shipping is a penalty/flag; international listings are flagged, not haircut ([ADR 0008](../adr/adr-0008-currency-landed-cost-normalization.md)).
- **Fitness-for-purpose (weight 0.25)** — rubric `0.5·suitability + 0.3·verified-warranty + 0.2·condition`.
- **Seller trust (weight 0.15)** — cross-marketplace positive-equivalent rate with **Beta-Binomial shrinkage** (μ₀ 0.95, κ 20) + **Wilson lower bound** (z 1.2816); no-rating → conservative policy prior (0.60 major / 0.50 other).
- **Availability (weight 0.10)** — bounded rubric (in-stock 1.0 → out-of-stock 0.0).

**Aggregate:** `base = Π_k max(s_k, 0.02)^{w_k}`; **veto caps** (max score regardless of price): device-managed **SMR for enterprise/NAS → 35**, **used/refurb with no returns → 60**, **seller trust < 0.50 → 60**; `deal_score = round(100 · min(base, cap))`. Every listing persists a **per-subscore explanation payload** (percentile + margin, seller evidence, fitness pieces, cap reason) — the glass-box "why it matched" view.

## Accounts, APIs, Credentials, and Services

**Resources:**

- `docs/research/tavily-brave-serper.md` - Research on search APIs and their capabilities.

### AgentMail

**API:**

- _Key Name:_ AGENTMAIL_API_BEARER_TOKEN
- _Key/Value Location:_ **OpenBao** (path below) at runtime; a local `.env` for development only — never committed.
- _OpenBao Path:_ `secret/api-keys/ai/agentmail`
  - Also contains the agent inbox email address; likely not needed for v1 but may be useful for future versions.
- _Usage:_

  ```bash
  curl https://api.agentmail.to/v0/inboxes/l3d%40agentmail.to/messages/%3CPH0PR05MB8240E972D7241D4BB5298116EDF42%40PH0PR05MB8240.namprd05.prod.outlook.com%3E \
  		-H "Authorization: Bearer {{AGENTMAIL_API_BEARER_TOKEN}}"
  ```

### eBay

**API:** See OpenBao path `secret/api-keys/commerce/ebay` for eBay API credentials and usage.

### Brave Search, Serper, Tavily

See OpenBao path `secret/api-keys/search/` ; will need to create new API keys for each search API and store them in OpenBao for Tavily API credentials and usage.

`docs/research/tavily-brave-serper.md` contains research on search APIs and their capabilities.

## Out of Scope

- The tool will not handle payment processing or facilitate transactions between buyers and sellers. It will only collect, store, and provide information and alerts regarding hard disk drives and solid-state drives.
