---
schema_version: '1.1'
id: 'adr-0018-hw-radar-manufacturer-spec-catalog'
title: 'ADR 0018: Manufacturer spec catalog — a first-class reference-data source'
description: 'Promote the ADR-0010 "reference/seed" table group to a first-class acquisition source class — a manufacturer spec catalog ingested from first-party datasheets/structured data on its own slow cadence, populating product_model / drive_spec / product_alias authoritatively (the full family→model→variant MPN matrix), append-only and never-delete, so entity resolution becomes an authoritative lookup rather than inference from noisy listings — and fix that the catalog enriches the observation stream, never gates it.'
doc_type: 'adr'
status: 'active'
created: '2026-07-04'
updated: '2026-07-04'
reviewed: null
owner: ''
consumer: 'mix'
tags:
  - 'adr'
  - 'data-model'
  - 'reference-data'
  - 'acquisition'
  - 'entity-resolution'
  - 'retention'
aliases: []
related:
  - 'docs/adr/README.md'
  - 'docs/adr/adr-0010-canonical-data-model.md'
  - 'docs/adr/adr-0012-orchestration-apscheduler.md'
  - 'docs/adr/adr-0014-scraping-runtime-escalation-stack.md'
  - 'docs/specs/hw-radar-master-spec.md'
  - 'docs/research/entity-resolution-for-cross-marketplace-hard-drive-and-ssd-price-tracking.md'
  - 'docs/research/machine-usable-drive-suitability-taxonomy-for-24-7-nas-and-server-scoring.md'
  - 'docs/research/database-architecture.md'
supersedes: []
superseded_by: null
source: []
confidence: 'high'
visibility: 'public'
project:
  decision_makers:
    - 'chris'
  consulted: []
  informed: []
---

# ADR 0018: Manufacturer spec catalog — a first-class reference-data source

MADR status: **accepted**.

## Context and Problem Statement

[ADR 0010](adr-0010-canonical-data-model.md) fixed the identity spine and delegated the exhaustive attribute columns to a typed `drive_spec` satellite, but it left one question open in its "deferred detail" list: **where do the authoritative `drive_spec` values come from?** It named `reference/seed` tables (`model_family_ref`, `hdd/ssd_price_baseline`) as a downstream group that would "get their own ADRs or milestone implementations." As drawn, the only populated path is **inference from the observation stream** — `drive_spec` filled by whatever attributes the parser can salvage from each listing title/body. ADR-0010 rule flags the cost itself (line 109): "with GTIN/ePID largely unavailable, entity resolution leans on parsed attributes + MPN aliases + `pg_trgm`; the alias table will be sparse for the high-value recert merchants."

Three forces make listing-inferred specs the wrong primary source:

1. **Authority.** Sellers routinely mislabel the scoring-critical attributes — CMR vs SMR (a veto factor, ADR-0011), cache, RPM, 512e vs 4Kn, workload rating, warranty channel. A composite score and a `$/TB` computed on real capacity are only as trustworthy as the attributes behind them. Manufacturer datasheets are ground truth; a listing is a claim.
2. **Match target.** Entity resolution needs something authoritative to resolve _to_. With no seeded alias set, the resolver can only compare noisy listings to each other. The manufacturer catalog is what turns resolution from listing-to-listing fuzzy matching into a **lookup against a known MPN matrix** — the concrete fix for ADR-0010's "sparse alias table" cost.
3. **Different physics.** Reference data is small, slow-changing, authoritative; observation data is huge, fast, noisy. The manufacturer set is finite and small — HDD is ≈3 vendors (Seagate, WD, Toshiba); enterprise/NAS SSD is ≈8–10 (Samsung, Micron/Crucial, Solidigm, SK hynix, Kingston, WD/SanDisk, Kioxia, Seagate). A few thousand SKUs total, changing a handful of times a year. Running that through the listing poller's per-source cadence, tiering, and scoring path is a category error.

A fourth force is specific to this tool's value target: **discontinued models are the core of the recert market.** A drive WD dropped from its site three years ago still sells recertified today — exactly the deals the tool exists to catch — so the catalog cannot be a mirror of the live manufacturer site; it must persist and retain.

This ADR promotes the deferred `reference/seed` group to a **first-class acquisition source class** and fixes its shape, cadence, retention posture, and its relationship to the observation pipeline. It does **not** re-open the identity spine (ADR-0010) — it feeds it.

## Considered Options

- **Option 1 — Infer specs from listings only** (the status quo implied by ADR-0010's population reality). `drive_spec` is filled from parsed listing attributes; no authoritative source; no seeded alias set.
- **Option 2 — A first-class manufacturer spec catalog** ingested from first-party datasheets/structured data on its own slow cadence, populating `product_model` / `drive_spec` / `product_alias` authoritatively, append-only, as reference data distinct from the observation pipeline. (chosen)
- **Option 3 — Buy/import a third-party spec dataset** (a Keepa-style feed, Backblaze drive stats, a commercial spec database) as the sole authority.

## Decision Outcome

Chosen option: **Option 2**, with a bounded **bootstrap** allowance from Option 3 (seed cheaply from an existing dataset where one exists, but manufacturer first-party specs remain the authority and the reconciliation target).

### The load-bearing rules (this is the decision)

1. **The catalog is a reference-data (master-data) source class, distinct from the observation pipeline.** It has its own `fetch → parse → normalize → persist` path that writes `product_model`, `drive_spec`, and `product_alias`, and **stops there** — reference ingest never runs `score` or `alert`, and never writes `offer_snapshot`/heartbeat rows. It is a separate source class in the source registry, not another row on the listing tier ladder.
2. **Sourcing precedence: first-party datasheet/product-manual (usually PDF) + structured data (JSON-LD, product-finder JSON) first; rendered product page last.** Enterprise datasheets are the richest _and_ most stable source (full attribute tables, TBW/DWPD, MTBF, workload rating, warranty terms) and are the manufacturer's own published data — the legally safest posture, consistent with the project's cautious ToS stance and mirroring [ADR 0014](adr-0014-scraping-runtime-escalation-stack.md)'s structured-data-first escalation, applied to reference ingest.
3. **Cadence is slow and is its own axis** — a monthly-order refresh, orthogonal to the listing poller's per-source cadence and the ADR-0015 volatility axis. The catalog is **never** on the fast/heartbeat path. The exact interval is a tunable, not fixed by this ADR; the _separation of the cadence axis_ is the decision.
4. **Append-only / never-delete.** A new `retention_class = manufacturer_reference` is **indefinite**, and a model discontinued upstream is **retained**, not pruned — discontinued drives dominate the recert market the tool targets. This extends ADR-0010 rule 6 with a new retention class; it does not alter any existing class.
5. **Persist the full family→model→variant MPN matrix.** Enterprise/recert matching keys on MPN _variants_ of one family — SATA vs SAS, 512e vs 4Kn, SED/FIPS/SIE, carrier and firmware suffixes (e.g. one Exos family spans dozens of `ST…` part numbers). The catalog stores that fan-out across `product_family → product_model → product_variant` and records **every** MPN/part-number as a `product_alias` row. This seeded alias set is what makes resolution a lookup (rule 2 of the problem).
6. **The catalog enriches the observation stream; it never gates it.** A listing that resolves to a catalog entry inherits authoritative `drive_spec`; a listing that does **not** resolve is still ingested and flagged (`unknown_model` → a catalog-backfill queue). Unmatched listings are the **discovery signal** for catalog gaps — new releases, recert-only SKUs, refurbisher part numbers with no manufacturer page. A gate would throw away exactly the deals the tool exists to find.

**Rejected — Option 1 (infer-only):** it makes the canonical `product_model`/`drive_spec` — the single costliest-to-reverse data in the system (ADR-0010) — only as good as noisy seller copy, and leaves entity resolution with no authoritative match target. It is the population reality ADR-0010 flagged as a cost, not a design we choose to keep.

**Rejected — Option 3 as sole authority:** a purchased/third-party spec feed has unknown coverage of enterprise/recert MPN variants, its own ToS, and no guarantee of retaining discontinued models — and it re-introduces a licensing dependency the project avoids. Retained only as an optional **bootstrap** to avoid a cold start, reconciled against first-party specs.

### Consequences

- **Good** — `drive_spec` becomes authoritative, so scoring (CMR/SMR veto, fitness, `$/TB` on real capacity) rests on manufacturer facts, not seller claims.
- **Good** — entity resolution becomes a lookup against a seeded MPN matrix, directly relieving ADR-0010's "sparse alias table" cost for recert merchants.
- **Good** — reference and observation data are separated by physics (cadence, size, retention, pipeline reach), so neither distorts the other; the price-history moat stays purely observational.
- **Good** — the append-only posture keeps discontinued models — the recert core — permanently matchable.
- **Bad (accepted)** — a second ingestion path to build and maintain, with its own parsers (datasheet PDFs are heterogeneous per vendor) and its own coverage/staleness discipline (new models must be picked up; the backfill queue must be worked).
- **Bad (accepted, and the real risk)** — the value is realized only if listings can be **joined** to catalog entries. The join key — MPN extraction and normalization from noisy recert listings, plus the family↔variant fan-out — is a non-trivial matching layer that this ADR names but does **not** specify; it is now scoped as [ADR 0019](adr-0019-listing-catalog-matching-layer.md) (proposed; see More Information). The catalog without a reliable matcher is inert reference data.

### Confirmation

Implementation confirmation (milestone: catalog seed precedes the entity-resolver hardening, ~MS-1–MS-2): the reference pipeline ingests a vendor's datasheet set and produces `product_model` + `drive_spec` + `product_alias` rows carrying `retention_class = manufacturer_reference` with no `offer_snapshot`/score/alert side effects; a single enterprise family (e.g. an Exos or Ultrastar line) lands as one `product_family` with its full set of per-MPN `product_variant`/alias rows; a listing whose MPN matches an alias inherits the authoritative `drive_spec`; a listing with no match is persisted and enqueued for backfill rather than dropped; a model discontinued upstream on a later refresh is retained, not deleted.

## More Information

- **Extends** [ADR 0010](adr-0010-canonical-data-model.md) — it fills the "reference/seed" deferred-detail slot and adds the `manufacturer_reference` retention class to rule 6, without altering the identity grains. **Relates** [ADR 0014](adr-0014-scraping-runtime-escalation-stack.md) (the structured-data-first escalation ladder, reused for reference ingest) and [ADR 0012](adr-0012-orchestration-apscheduler.md) (the poller schedules the slow reference refresh as its own job, off the fast path). Feeds the entity resolver (spec Appendix C.3).
- **Primary research:** [`entity-resolution-…`](../research/entity-resolution-for-cross-marketplace-hard-drive-and-ssd-price-tracking.md) (dual physical/sellable identity, aliases, blocking — the matcher this catalog seeds), [`machine-usable-drive-suitability-taxonomy-…`](../research/machine-usable-drive-suitability-taxonomy-for-24-7-nas-and-server-scoring.md) (the `drive_spec` field tables the catalog populates), [`database-architecture.md`](../research/database-architecture.md) (base schema).
- **Follow-up (resolved):** the **matching layer** — MPN extraction/normalization from noisy recert listings and the family↔variant fan-out that makes the listing→catalog join reliable. It is the risk that determines whether this catalog pays off, and is scoped as its own design pass before the entity resolver is hardened. _Resolved 2026-07-04: designed as [ADR 0019](adr-0019-listing-catalog-matching-layer.md) (proposed, ratification gated on its validation corpus) + master-spec Appendix C.3._
