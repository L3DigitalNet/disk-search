# Disk Search

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
- **Stewardship & Responsibility:** The tool should be designed to minimize the impact on the marketplaces it monitors, avoiding excessive requests or scraping that could be considered abusive or violate terms of service.

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
- **Notification System:** Emails sent to `chris@l3digital.net` at minimum, with potential for SMS or push notifications.
- **Web Scraping Libraries:** Scrapy. Additional options to be considered based on the specific requirements of each marketplace.

## Environment and Deployment

- **GitHub Repository:** `[L3DigitalNet public repo](https://github.com/L3DigitalNet/disk-search)`
  - _Branching Strategy:_ Main branch for stable releases, development branch for ongoing work, and feature branches for new features or bug fixes.
  - _Commit Guidelines:_ Follow conventional commit messages for clarity and consistency. Commit directly to branches, do not use Pull Requests for personal development work unless collaborating with others.
  - _Note_: This project lives in my Organization account on GitHub because I am intending to use this to purchase hard drives for L3Digital. The repository is public; secrets (API keys, credentials) are **never committed, hard-coded, or exposed**. In production the app resolves them from **OpenBao at runtime** via a local OpenBao Agent ([open-questions.md](../open-questions.md) gap #2 / OQ1); a local `.env` is used **for development only**.
- **Local Clone:** `~/projects/disk-search`
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
  - _Address:_ `https://disk-search.l3digital.net`
  - _Security:_ HTTPS via NGINX and Let's Encrypt.
  - _Authentication:_ Single-account session login with Argon2id, internet-facing ([ADR 0005](../adr/adr-0005-single-account-session-auth.md)).

### Special Considerations

- **Public Repository:** The repository is public. Secrets (API keys, credentials) are **never committed, hard-coded, or otherwise exposed** — production resolves them from **OpenBao at runtime**, and a local `.env` is for development only. Public-repo constraints also shape CI: the runner holds **no OpenBao credential** ([ADR 0006](../adr/adr-0006-cd-rsync-over-tailscale-ssh.md)).

## Database Schema

_Full schema is deferred to a data-model ADR (canonical `drive_model` / `listing` / `observation`; see [`docs/research/database-architecture.md`](../research/database-architecture.md))._ **Extensibility constraint (per [General Design Principles](#general-design-principles)):** model the catalog around a generic **product / category** abstraction rather than hard-coding drive-only fields, so additional **hardware types** (RAM, GPUs, …), marketplaces, scoring criteria, and users can be added without a schema rewrite. v1 implements the drive category only.

## Scoring System

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
