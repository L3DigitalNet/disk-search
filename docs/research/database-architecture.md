# Database Architecture for Tracking SSD and HDD Market Data

## Executive recommendation

The best primary database for your workload is **PostgreSQL with TimescaleDB** on the single VM, with PostgreSQL serving as the system of record and TimescaleDB handling the price-history part of the workload. That combination matches what you described better than a pure document store, a pure search engine, or a pure OLAP engine: you need relational joins across manufacturers, models, sites, sellers, and trust rules; flexible storage for messy API payloads and extracted page content; efficient historical time-series storage for repeated price observations; and support for computed fields, rollups, and indexed filtering. PostgreSQL gives you `jsonb`, generated columns, expression indexes, partial indexes, materialized views, full-text search, and trigram similarity; TimescaleDB adds time-partitioned tables, rollups, compression, retention, and time-series analytics while remaining a PostgreSQL extension rather than a separate fork.

If you want the most conservative operational path, **plain PostgreSQL without TimescaleDB is still viable**. Core PostgreSQL already has declarative partitioning, materialized views, generated columns, `jsonb`, BRIN/B-tree/GIN indexes, full-text search, and `pg_trgm`, so a modest deployment can absolutely work without extensions. The reason I still prefer TimescaleDB is not because core PostgreSQL cannot do the job, but because the extension packages several things you are likely to want anyway for observation-history data: time-oriented partitioning, automated rollups, compression, and retention policies.

I would **not** make ClickHouse the primary store for this project on day one. ClickHouse is excellent when the workload becomes overwhelmingly append-heavy and analytics-dominant; its MergeTree family is explicitly designed for high ingest rates and huge data volumes. But its own docs still frame updates and deletes as “mutations,” and its best-practice guidance emphasizes batched inserts and materialized-view transforms from landing tables. That is a strong fit for a secondary analytics warehouse or a later scale-out path, but less attractive than PostgreSQL for a source-of-truth catalog with mutable seller trust rules, joins, deduplication, and per-listing lifecycle management.

I would treat **OpenSearch as optional, not primary**. It is useful if your interaction layer becomes heavily search-driven—autocomplete, typo tolerance, compound text queries, faceted drilldowns at large scale—but its own mapping and aggregation docs illustrate why it is better thought of as a companion search index than as the canonical database: strings are commonly mapped as both `text` and `keyword`, and aggregations should target keyword-style raw fields rather than analyzed text. That is perfect for search UX, but not a substitute for a relational system of record.

## Gap analysis

The earlier answer was directionally right about the **search layer**: Serper, Tavily, and Brave are best treated as discovery and retrieval tools, not authoritative inventory systems. The big gap was that it stopped before the **storage model**. It did not answer how to preserve raw evidence, normalize messy marketplace data, model repeated observations over time, implement your trust/ranking rules as data rather than code, support fuzzy part-number matching, or compute stable derived metrics such as dollars per TB and in-house composite scores.

That omission matters because storage choices determine whether the rest of the pipeline remains simple or becomes a constant cleanup job. For this domain, the hard part is not just “finding pages.” It is maintaining a canonical model for the same drive across multiple sites, multiple seller conditions, and repeated observations over time, while preserving enough raw evidence to re-parse or audit later. A database that can hold both normalized columns and raw payloads, and can query both effectively, is the real center of gravity.

## Choosing the database type

**PostgreSQL plus TimescaleDB ranks first** because your data is naturally split into stable dimensions and mutable observations. Manufacturers, canonical drive models, source sites, seller trust policies, and ranking weights are relatively stable relational data. Price observations, shipping observations, stock/availability observations, and search/extraction events are quintessential time-series data. PostgreSQL’s `jsonb` is well suited to storing provider payloads and extracted metadata, and PostgreSQL’s generated columns and expression indexes let you project the hot fields you care about into relational columns without losing the original JSON. TimescaleDB then adds hypertables, rollups, compression, retention, and continuous aggregates for the repeated snapshot side of the system.

**Plain PostgreSQL ranks second** because it can still do nearly all of this if the volume stays moderate. Declarative partitioning handles large append-oriented tables; BRIN indexes work well when a column is naturally correlated with physical row order, such as an append-mostly `observed_at` timestamp; materialized views let you persist derived query results; and `pg_trgm` plus full-text search covers a lot of the fuzzy search problem without requiring another service. If you want the fewest moving parts on one VM, “PostgreSQL first, Timescale only if needed” is defensible. I still think it is penny-wise and pound-foolish if you know ahead of time that this will accumulate price history continuously.

**ClickHouse ranks third as a planned expansion path**, not as the first database. Its docs are clear about the strengths: MergeTree engines are designed for high-ingest, huge-volume analytics, and materialized views are meant to shift computation from read time to insert time. Its own JSON landing-table pattern also maps well to noisy API and scraper payloads. The reason it loses as the primary system is that your workload is not just analytics. It also includes record identity, deduplication, policy tables, trust posture, per-source overrides, canonical model matching, and mutable corrections. ClickHouse can do some of that, but it is not where it is happiest.

**MySQL or MariaDB are workable, but not my first choice**. MySQL supports a native JSON data type and full-text indexing, so the basics are present. The problem is ergonomic rather than existential: JSON access is fine, but the community guidance around MySQL JSON indexing still revolves around generated columns or functional indexes on extracted keys, whereas PostgreSQL has a more mature “mixed relational + document” story for this exact kind of workload. If you were already deeply standardized on MySQL, I would not tell you to rip that out. Starting fresh, PostgreSQL is the stronger fit.

**SQLite is useful for local replicas, ad hoc analyst copies, or a desktop cache, not the primary VM database**. SQLite does support generated columns and FTS5, so it is far more capable than many people assume. But that makes it a good sidecar or prototyping store here, not the center of a long-running acquisition and scoring pipeline on a Proxmox-hosted VM.

## Recommended schema

The core modeling mistake to avoid is treating each retail page as “the product.” In this domain, the **canonical entity is the drive model**, and each site page is a **listing or offer representation** of that model. Your schema should therefore separate stable identity from unstable marketplace presentation.

A practical relational core looks like this:

```text
manufacturer
  id, name, normalized_name

drive_model
  id, manufacturer_id, model_family, model_number, normalized_model_number,
  mpn, upc_ean, interface, form_factor, capacity_tb_decimal,
  media_type, rpm, cache_mb, nand_type, pcie_gen, nvme_version,
  workload_rate, tbw, warranty_months, launch_status, spec_json

drive_alias
  id, drive_model_id, alias_text, alias_type, confidence

source_site
  id, name, normalized_name, source_type, trust_tier_default,
  region, base_rank, notes

seller
  id, source_site_id, seller_name, normalized_seller_name,
  seller_trust_tier, trust_score, notes

listing
  id, source_site_id, seller_id, drive_model_id nullable,
  source_listing_key, canonical_url, url_hash,
  title_raw, title_normalized, condition_label_raw,
  condition_enum, warranty_text_raw, page_metadata_json

offer_snapshot
  id, listing_id, observed_at, currency, item_price, shipping_price,
  tax_price nullable, total_landed_price, stock_status,
  quantity_available nullable, sold_by_text, shipped_by_text,
  condition_enum, return_policy_text, warranty_months_effective nullable,
  extraction_method, confidence_score, attrs_json, raw_payload_id

search_observation
  id, provider, endpoint, query_text, query_params_json,
  observed_at, result_rank, result_url, result_title, result_snippet,
  provider_payload_json, matched_listing_id nullable

raw_payload
  id, provider, endpoint, fetched_at, request_json, response_json,
  response_text nullable, content_hash, http_status, parse_version

scoring_policy
  id, active_from, active_to nullable, policy_json

listing_score
  id, snapshot_id, observed_at, dollars_per_tb, trust_adjusted_price_score,
  overall_score, score_breakdown_json
```

That layout is deliberately conservative: it keeps **stable facts** about the drive in `drive_model`, **site/seller policy** in first-class tables, **repeated market observations** in `offer_snapshot`, and **provider evidence** in `search_observation` and `raw_payload`. The important thing is that URLs, page titles, snippets, and scraped attributes remain evidence, not identity. The identity anchor should be normalized model/part data first, with aliases and fallback matching when sites get sloppy.

For your specific ranking table, I would not hardcode those rules in the app. Put them in tables. Your “trust posture,” “ranking rule,” “site preference,” “allowed conditions,” “seller whitelist,” and “regional override” belong in a **policy dimension** so you can change them without schema changes or redeploys. That matters because your own table already contains rules like “prefer only when sold by Newegg/manufacturer/trusted specialist” and “rank higher only for UK/EU regional availability.” Those are data rules, not application constants.

The other critical best practice is to **pull predictable hot fields out of JSON and into real columns**, even when you keep the raw JSON too. PostgreSQL’s `jsonb` is faster to process than `json`, because it stores data in a decomposed binary form and supports indexing, but large JSON documents can still incur substantial overhead; community guidance and performance writeups consistently recommend storing the frequently filtered fields in ordinary columns and using JSONB for the unpredictable remainder. PostgreSQL generated columns are a clean way to keep those extracted values in sync, and expression indexes are the right tool when you need to optimize a particular extracted expression.

For indexing, use **B-tree** for most joins and exact filters on structured fields, **GIN** for containment-style JSONB lookups and full-text vectors, **`pg_trgm`** for fuzzy manufacturer/model matching, **partial indexes** for “hot subset” workloads such as active trusted sellers or live listings only, and **BRIN** for very large append-mostly history tables keyed by time. Official PostgreSQL docs and community guidance line up on the important nuance: GIN is powerful, but it is not a silver bullet; if you repeatedly query a few known JSON keys, expression indexes or columns are often better than a broad GIN index on the entire document.

## Search API compatibility and ingestion

The three search APIs you were already evaluating are compatible with this design because they all emit machine-friendly results, but they should feed the database in **two stages**: first a **raw landing/evidence stage**, then a **normalized catalog stage**. Tavily’s Search API can return cleaned content via `include_raw_content`, and its Research endpoint can be forced into a predictable shape with a caller-provided JSON Schema. Brave’s web search API is JSON by default, supports freshness filters, and can be nudged toward fresher results with `Cache-Control: no-cache` on a best-effort basis. Serper publicly documents a Google SERP-style JSON response shape on its product page, lists Shopping among its supported endpoints, and states that it queries Google in real time without caching. Those are all strong reasons to store each provider response as raw JSON plus normalization metadata before you attempt cross-source matching.

For Tavily specifically, the documentation is unusually aligned with your downstream database goal. Its best-practice docs recommend concise queries under 400 characters, breaking complex tasks into sub-queries, using date/domain filters, choosing search depth deliberately, and using Map before Crawl so you discover structure before doing deeper extraction. Its Extract guidance also recommends query-focused extraction with bounded `chunks_per_source`, and its Research guidance explicitly distinguishes **structured output for pipelines** from prose reports for human reading. That means Tavily is the strongest of the three when you want to flow cleaned, semi-structured research output into a normalization pipeline rather than just store SERP cards.

Brave is especially useful when you want an **independent index** and date filtering, but its docs introduce two database-design implications that are easy to miss. First, since caching is on by default unless you request `no-cache` on a best-effort basis, you should store the exact retrieval timestamp and response headers or provider metadata alongside the result. Second, the docs note that certain local IDs are ephemeral and expire after about eight hours, which means provider-native result IDs should never be your canonical key. Store them as transient evidence, not durable identity.

The right ingestion pattern is therefore:

```text
provider response -> raw_payload
                 -> search_observation
                 -> URL fetch/extract event
                 -> listing upsert
                 -> drive_model match or alias candidate
                 -> offer_snapshot insert
                 -> score/materialized rollup refresh
```

That flow does two things well. It preserves provenance, which matters when site content changes, and it allows you to re-run parsing and matching as your model-improvement logic gets better. It also makes search tools interoperable with official APIs or direct scrapers later: no matter whether an observation came from Tavily, Brave, Serper, a marketplace API, or a direct product-page parser, it lands in the same `offer_snapshot` shape with a pointer back to raw evidence.

Official documentation worth bookmarking for this architecture includes the PostgreSQL manuals on JSON types, generated columns, partitioning, materialized views, `pg_trgm`, BRIN, and backup/restore; Tiger Data’s TimescaleDB docs and self-hosted installation path; ClickHouse docs for MergeTree, materialized views, mutations, bulk inserts, and JSON landing-table patterns; OpenSearch mapping and aggregation docs; Tavily’s API and best-practice docs; Brave Search API documentation; Serper’s official product page; MySQL’s JSON docs; and SQLite’s generated column and FTS5 docs.

## Calculated fields, filtering, and scoring

Use **stored generated columns** for calculations that depend only on values in the same row and that you will sort/filter on often. PostgreSQL explicitly defines generated columns as columns computed from other columns, with stored generated columns computed on write and occupying storage like normal columns. That is a very good fit for things like `total_landed_price`, `dollars_per_tb`, `price_per_gib`, normalized warranty months, or normalized capacity units—provided the formula is row-local and deterministic. SQLite has a similar model if you ever build local analyst replicas, but PostgreSQL is the primary tool here.

Use **views, materialized views, or Timescale continuous aggregates** when the calculation crosses rows or tables. PostgreSQL materialized views persist query output in table-like form, and Timescale continuous aggregates are automatically refreshed rollups over hypertables. Those are the right tools for things like “latest best price per model from trusted sellers,” “lowest price in the last 30 days,” “median recertified price by family,” “seller-trust-adjusted score,” or “price movement by source over time.” Row-local math belongs in generated columns; cross-row or cross-table summaries belong in persisted query layers.

For text filtering and fuzzy model matching, **`pg_trgm` plus structured normalization** is likely enough in the first version. PostgreSQL’s trigram module supports similarity operations and fast searching for similar strings, which is useful for listing-title cleanup and alias resolution when sites append marketing fluff or inconsistent spacing. For exact ranking/filtering facets, keep the fields typed and normalized; fuzzy text should help match candidates, not define the final truth. If the UI later becomes very search-centric, that is when OpenSearch becomes a reasonable companion index.

A simple but important rule: **score inputs should be stored separately from final scores**. Do not just save `overall_score`. Save the score breakdown as structured data as well, either as columns for the hot factors or in `score_breakdown_json` for the long tail. That way you can reweight your trust posture—manufacturer direct vs authorized retailer vs marketplace unknown seller—without destroying auditability. Your own ranking table already implies this need: site preference, seller posture, condition, region, and warranty all influence ranking. Those belong in explainable score components.

## Operational fit for a self-hosted VM

On a single Proxmox VM at Hetzner, I would keep the initial design **single-primary and boring**: PostgreSQL plus TimescaleDB as the only always-on database service, with optional OpenSearch or ClickHouse only if user-facing search UX or large-scale analytics actually demand them. PostgreSQL’s own backup docs emphasize regular backups, continuous archiving for point-in-time recovery, and `pg_basebackup` for base backups of a live cluster. On a single VM, that is the operational baseline I would want before I cared about anything fancier.

For data lifecycle, separate **hot normalized data** from **cold raw evidence** even if they live in the same database. Keep the recent `offer_snapshot` data highly indexed and query-friendly. Keep raw provider responses, extracted markdown/text, and old crawl payloads in append-only tables with simpler indexing and a retention/compression policy. TimescaleDB explicitly adds retention and compression-style lifecycle features on top of PostgreSQL, which is exactly what repeated snapshot data benefits from.

If this later grows into a very large dataset where most queries are no longer “find the best current offer” but instead become “scan huge histories and compute market analytics across everything,” then ClickHouse becomes the obvious secondary warehouse. Its own documentation already suggests the right pattern for that future state: batch inserts, landing tables, JSON extraction, and materialized-view transforms. But that is a scale-path decision, not the best first database for the workload you described.

The short version is this: **use PostgreSQL plus TimescaleDB as the canonical database, model drives separately from listings, store raw evidence as JSON/text beside normalized relational rows, use generated columns for row-local economics, use materialized or continuous aggregates for cross-row rankings, and keep search APIs as evidence/discovery inputs rather than as your source of truth**. That design is the best match for the HDD/SSD tracking problem you described, for the search tools you are already evaluating, and for a self-hosted single-VM deployment that still leaves you a clean path to scale later.
