# MS-1 — Ingestion (top 5): Design

> Brainstorm output (2026-07-05, owner-ratified section by section). Instantiates master-spec §19 "MS-1 — Core workflow" as five sequenced sub-milestones, each with its own implementation plan (`superpowers:writing-plans`) and its own `dev→main` PR. The master spec and ADRs remain the design source of truth; this document records the MS-1 *decomposition* and the owner scope decisions taken 2026-07-05. It introduces no new architecture — every mechanism below is fixed by an existing ADR or spec section, cited inline.

**Goal:** all 5 primary recert sources (WD Recertified, Seagate Recertified, ServerPartDeals, goHardDrive, eBay Browse) yield normalized, FX-stamped, entity-resolved listings on a scheduled run; re-runs append `offer_snapshot` observations, never duplicate listings; the C.3.5 labeled corpus demonstrates ≥ 99.5% rung-0–2 auto-accept precision, ratifying ADR-0019.

## 1. Owner scope decisions (2026-07-05)

These settle what spec §19 left open at the MS-1 boundary:

| # | Decision | Consequence |
| --- | --- | --- |
| S-1 | **Heartbeat/fast-lane gating (ADR-0015) is IN scope** for the 3 recon-confirmed fast-lane sources (WD, Seagate, ServerPartDeals) | `availability_heartbeat_observation` hypertable + `availability_heartbeat_event` table land in MS-1d with the OQ17 retention machinery; eBay + goHardDrive run full-pipeline polls at tier cadence |
| S-2 | **Full C.2 substrate + ADR-0017 lifecycle now** (not a core subset) | Two-level token buckets, back-off ladder, auto-ramp, soft-block detection, breaker registry with `paused_pending_fix` recovery probes and the SKIP state — all in MS-1a |
| S-3 | **`httpx` approved** as the HTTP client for API/FX/heartbeat paths (OQ21, resolved 2026-07-05; spec §8.6 row added) | eBay Browse, Frankfurter, and heartbeat probes bypass Scrapy; scrape-tier fetching stays Scrapy |
| S-4 | **eBay credentials exist** (OpenBao `secret/api-keys/commerce/ebay`: client id/secret for the client-credentials grant) | eBay connector is built against the production Browse API; sequenced last in MS-1d to harden the adapter contract on simpler sources first |
| S-5 | **Validation corpus: Claude drafts labels, owner audits** a random ~20% sample + every matcher disagreement | Bounded owner time (~30 min) while keeping the ratification gate meaningfully independent |
| S-6 | **Approach A decomposition + PR per sub-milestone** | Five plans, five `dev→main` PRs; `main` (and prod) advances per increment |

Alert transport note: ADR-0017's operator alerts have no email path until MS-4 (ADR-0013). MS-1 ops posture = lifecycle state + failure classes persisted (`scraper_runs`/source registry), logs, and the §18.5 dead-man's-switch push to the off-box Uptime Kuma. Email-based warning alerts are explicitly deferred to MS-4.

## 2. Module layout

New code under `src/hw_radar/`, split on the pipeline's natural seams:

```
hw_radar/
├── acquisition/                 # MS-1a + MS-1d — observation pipeline
│   ├── contracts.py             # Pydantic v2: RawBatch, NormalizedListing, PersistResult,
│   │                            #   RunReport + the SourceAdapter protocol (spec C.1 contract)
│   ├── pipeline.py              # stage runner: fetch→parse→normalize→resolve→persist;
│   │                            #   per-stage timing; §12.1 failure classification
│   ├── fx.py                    # Frankfurter daily-rate service, DB-cached (ADR-0008)
│   ├── heartbeat.py             # cheap-signal probes + price/stock fingerprint diff (ADR-0015)
│   ├── scheduling/              # admission gate: two-level token buckets, back-off ladder,
│   │                            #   ADR-0017 lifecycle/breaker registry, PG checkpointing
│   └── sources/                 # one adapter module per source (+ demo walking skeleton)
├── matching/                    # MS-1b — ADR-0019 matching layer
│   ├── normalize.py             # N1 text canonicalization (single-normalizer invariant)
│   ├── vocab.py                 # N2 controlled vocabularies → typed attributes
│   ├── mpn.py                   # N3 code-shaped token extraction (MPN, OEM, house SKUs)
│   ├── grammars/                # N4 per-vendor MPN decoders (provenance-tiered)
│   ├── ladder.py                # rungs 0–2 + hard-attribute contradiction veto (pure)
│   └── resolver.py              # DB-facing: runs ladder, writes listing_resolution edges
├── refdata/                     # MS-1c — ADR-0018 reference ingest
│                                #   (fetch→parse→normalize→persist; no score/alert)
└── catalog/models/              # additions: resolution.py (ListingResolution),
                                 #   ops.py (SourceConfig, ScraperRun),
                                 #   evidence.py additions (heartbeat observation + event)
```

`matching/` (except `resolver.py`) is a **pure-function library** — no I/O, no Django imports beyond types — per spec C.3's "pure-function library plus a resolver service" split. That makes rungs and decoders table-testable against golden corpora with no DB.

## 3. Sub-milestones

Dependency order: **1a substrate → 1b matcher → 1c catalog → 1d connectors → 1e validation.** The matcher precedes the catalog because catalog ingest must pass through the same normalizer (the C.3 single-normalizer invariant); the catalog precedes connectors because rung-1 hits need seeded aliases; connectors precede validation because the corpus is harvested from real connector output.

### MS-1a — Substrate (scheduler, adapter contract, FX)

- **Source registry as rows:** new `SourceConfig` model, 1:1 with `SourceSite`, carrying the C.2 per-source parameters — tier (T0–T4), `cadence_baseline`/`cadence_ceiling`, volatility profile, cheap-signal kind, `fast_lane`, back-off state, and the ADR-0017 lifecycle state (`active / backing_off / paused_pending_fix / skip`). ADR-0016 settings-row pattern: cadence values are OQ9-provisional tunables, changed by UPDATE not deploy.
- **`ScraperRun` model** (§18.5): one row per scheduled run — start/finish/status/record counts/failure class. The shared substrate for later observability (OQ5/OQ8/OQ10).
- **Admission machinery** (ADR-0012/0016/0017 + C.2): in-process two-level token buckets (per-source + per-domain), the exponential back-off ladder (`random(0,1) × min(24 h, 10 min × 2^failures)`; `Retry-After` honored verbatim clamped 1 s..baseline), auto-ramp (4 clean polls → halve interval, floored at tier ceiling), latency-spike halving, soft-block detection (EC-007 signals), breaker trips on `anti_bot`/sustained `parser_rot` → `paused_pending_fix` with a daily recovery probe, terminal SKIP as registry state. State lives in memory, checkpointed to PostgreSQL for crash recovery.
- **Pipeline runner:** executes the stage chain with per-stage timeouts and §12.1 failure classification; a failed resolve never blocks persist (listing lands at `grain = none`, error recorded in resolution evidence — C.3).
- **Scrapy integration:** Scrapy's asyncio reactor shares the poller's event loop (`AsyncIOScheduler`) per ADR-0012; scrape-tier adapters are Scrapy spiders run via `CrawlerRunner`. Guardrails (C-007) in one shared settings module: `ROBOTSTXT_OBEY=True`, AUTOTHROTTLE, honest UA, hard timeouts.
- **FX service (ADR-0008):** `fx_rate_daily` cache table (date + pair + rate + source), refreshed by a daily job; persist stage stamps `fx_rate/fx_pair/fx_rate_date/fx_source` (existing `offer_snapshot` columns) and computes the USD-normalized price. USD-native listings stamp identity (rate 1.0) so the FR-004 "100% stamped" acceptance is auditable by query.
- **Dead-man's switch:** a poller job pushes the success heartbeat to the off-box Uptime Kuma (§18.5; push URL rendered via bao-agent env, never committed).
- **Walking skeleton:** a fixture-backed `demo` source adapter exercised in tests through admission→fetch→parse→normalize→resolve(`none`)→persist, proving the substrate end-to-end before real connectors.
- **New deps:** `scrapy`, `pydantic` (already §8.6-allowed), `httpx` (OQ21). Dev: `vcrpy`, `syrupy` (already allowed).

**Exit:** gate green; demo source runs end-to-end under APScheduler in a test; token-bucket/back-off/lifecycle transitions unit-tested; FX job fetches and caches a real daily rate (recorded cassette in CI).

### MS-1b — Matching layer (ADR-0019 rungs 0–2)

- **Extraction stack (C.3.1):** N1 canonicalization (NFKC, case-fold, separator unification, boilerplate strip); N2 controlled vocabularies → typed attributes with per-attribute confidence + producing-layer provenance (capacity→bytes, interface/link speed, form factor, RPM, cache, sector format, CMR/SMR, SED/FIPS/ISE, condition incl. `for-parts`, packaging, warranty-channel cues, quantity/lot, brand normalization incl. WD↔SanDisk "Optimus"); N3 code-shaped token extraction (MPN candidates, refurbisher house SKUs → source-local aliases, OEM part-number patterns per the OEM cross-reference research); N4 per-vendor grammar decoders deriving **family/capacity/generation only**, each rule tagged `vendor_official / corroborated_community / inferred`.
- **Ladder (C.3.2):** rungs 0–2 auto-accept (re-observation → exact alias → grammar decode at family grain); rungs 3–4 emit explicit `review` outcomes into the queue (no UI until MS-3 — Django admin suffices for inspection). Hard-attribute contradiction veto at every rung.
- **Resolution state (C.3.3):** new `ListingResolution` model — append-only edges `(listing, grain, target, method, confidence, matcher_version, evidence jsonb, resolved_at, superseded_by)`; migration adds the denormalized `product_family`/`product_model` FKs + `resolution_grain`/`resolution_confidence` to `listing` (today it carries only the `product_variant` FK). `product_variant` rows created on demand once model grain + normalized condition are both known.
- **Backfill queue (C.3.4):** a DB view over listings below model grain + the rung-2 decoded-but-unknown set, with occurrence counts and first/last seen. The occurrence-triggered targeted-reference-fetch loop is wired in MS-1c; thresholds are settings rows.
- **Testing:** table-driven golden-title corpus; per-vendor decoder vectors from datasheets; normalizer idempotence property test; the **catalog↔listing normalizer parity test** lands here and runs in CI.

**Exit:** gate green; ladder verdicts correct on the golden table (fixture catalog rows); `test_recert_and_new_are_one_model_two_variants` upgraded from schema-shape to resolver-driven (FR-003's MS-1 acceptance).

### MS-1c — Catalog seed (ADR-0018)

- `refdata/` implements the truncated reference pipeline (`fetch → parse → normalize → persist`) writing `product_model` / `drive_spec` / `product_alias` (full family→model→variant MPN matrix, grain-tagged per C.3) with `retention_class = manufacturer_reference`; **no** snapshot/score/alert side effects.
- **Families:** the top-5 recert families as sold by the 5 sources — expected Seagate Exos + IronWolf Pro, WD Ultrastar + Red Pro/Gold; the final list is confirmed from live source inventory during implementation (recorded in the MS-1c plan).
- **Sourcing precedence** per ADR-0018: first-party datasheet/structured data first, rendered page last. Catalog aliases pass through `matching.normalize` (parity invariant).
- **Scheduling:** a monthly-order poller job, off the fast path; a discontinued model on a later refresh is retained, not deleted (acceptance-tested per the ADR Confirmation section).
- The C.3.4 occurrence-triggered discovery loop (decoded-but-unknown MPN crossing a threshold → targeted reference fetch enqueued) is wired here.

**Exit:** gate green; one enterprise family lands as one `product_family` with its full per-MPN variant/alias fan-out; a fixture listing whose MPN matches a seeded alias inherits authoritative `drive_spec`; DR-009 stamping verified.

### MS-1d — Connectors + heartbeat

Build order (hardening the contract on simple sources before the OAuth one): **ServerPartDeals → goHardDrive → WD → Seagate → eBay**.

| Source | Tier/path | Notes |
| --- | --- | --- |
| ServerPartDeals | Shopify: `products.json` + JSON-LD | Confirmed Shopify; also a fast-lane cheap signal (`variant.available`) |
| goHardDrive | Structured data / HTML selectors (verify live at plan time) | Full-pipeline polls at tier cadence (no confirmed cheap signal) |
| WD Recertified | Unauthenticated SAP-Commerce OCC JSON (variant-grain SKU, exact price/stock) | Per the 2026-07-04 endpoint-recon spike; re-verify live before the plan |
| Seagate Recertified | Bootstrap JSON embedded in the robots-allowed `www.seagate.com` category page; **crawl-delay 20 honored** | `store.seagate.com` (incl. its GraphQL) is robots-disallowed — **never fetched** (recon spike; handoff watch-out) |
| eBay | Browse API (T0), OAuth2 client-credentials from OpenBao `secret/api-keys/commerce/ebay` via `httpx` | eBay retention semantics per C.1: ≤ 6 h freshness, delete-on-delist, `retention_class = ebay_listing_observation` incl. heartbeat rows |

- Every adapter: Pydantic validation, `raw_payload` persistence with the source's retention class, per-source failure isolation (NFR-001), vcrpy cassettes + syrupy snapshots.
- **Heartbeat gating (S-1):** new `availability_heartbeat_observation` hypertable (monthly chunks, 30-day raw retention, compression ≈ 7 days, per-source daily continuous aggregate) + plain `availability_heartbeat_event` table (non-`unchanged` rows, 365-day TTL) — the OQ17 dual-write design. Probes read the **variant/SKU-grain** availability field, diff price+stock fingerprints against last-seen, and fire the full pipeline only on `transition_detected`/`ambiguous`. Fast-lane set: WD, Seagate, ServerPartDeals.
- Endpoint shapes are re-verified live immediately before each connector's plan is written (the recon report is a dated point-in-time probe).

**Exit = spec §19 MS-1 acceptance (minus ratification):** 5/5 sources yield ≥ 1 normalized listing on a scheduled run; 100% of non-USD listings carry FX stamps + USD price; international listings flagged; re-runs append `offer_snapshot` rows, not duplicate listings (DR-005).

### MS-1e — Validation corpus + ADR-0019 ratification

- Harvest ~150–200 real titles across the 5 sources from connector runs into a versioned JSONL fixture (title, source, raw attributes, ground-truth label: expected grain + target).
- Labeling per S-5: Claude drafts, owner audits a random ~20% + every case where label and matcher disagree.
- A pytest-marked evaluation computes rung-0–2 auto-accept precision and model-grain coverage. **≥ 99.5% precision** → ADR-0019 flips `proposed → accepted` (result recorded in its Confirmation section); spec drops the D-019/C.3 "(proposed)" qualifiers and the ADR-index row updates; TODO ratification item closes. A miss → veto-rule fix + `matcher_version` bump + re-run, per C.3.5 — the gate is not loosened.
- The **OEM dual-labeling spot-check** (TODO `## Claude`) rides the same harvest: measure how often ServerPartDeals/eBay listings print both an OEM token and an MPN, validating the lazy OEM-alias strategy's assumption.

**Exit:** ratification recorded (or the documented fix loop executed); MS-1 milestone closed in spec §17.3/§19; handoff + TODO updated.

## 4. Error handling & ops (MS-1 posture)

- Failure classification per §12.1 routes each failure to retry / back-off / breaker / review (ADR-0017); one source's failure never halts the others (NFR-001).
- Lifecycle + failure classes persisted on `SourceConfig`/`ScraperRun`; structured logs; Kuma dead-man's switch. **No email alerts until MS-4** — §18.5's warning-alert rows ride DB + logs until the transport exists.
- Raw payloads accumulate on disk/DB from MS-1d onward: the handoff watch-out applies — when raw scrape payloads get a disk path, add the CT-116 subvol to restic `BACKUP_PATHS` (homelab repo, out-of-repo follow-up).

## 5. Testing strategy

- **Unit (no DB):** matching library (golden titles, decoder vectors, property tests), token bucket/back-off/lifecycle math, fingerprint diffing, FX math.
- **DB:** migrations (hypertable DDL, retention constraints), resolver writes, backfill view, catalog ingest idempotence, snapshot-append-not-duplicate.
- **Connector:** vcrpy cassettes (synthetic-only per OQ8 posture) + syrupy snapshots of normalized output; live-endpoint smoke checks are manual/plan-time, never CI.
- Gate (`uv run python -m scripts.check`) green at every commit; each sub-milestone PR runs CI + dependency review.

## 6. Risks / open edges

| Risk | Posture |
| --- | --- |
| Endpoint drift since the 2026-07-04 recon | Re-verify live before each connector plan; adapters isolate per-source breakage (ADR-0017) |
| goHardDrive has no recon spike | Scout its structure at MS-1d plan time; it's tier-2 structured-data/HTML — if it demands browser tiers, that escalation is deferred (ADR-0014) and the source degrades to slower cadence, not SKIP |
| Scrapy `CrawlerRunner` + APScheduler loop-sharing has integration subtleties (reactor install timing, per-run crawler lifecycle) | The MS-1a walking skeleton proves it before any connector work; ADR-0012 fixes the single-process design |
| Corpus precision misses 99.5% | C.3.5's own loop: veto fix + `matcher_version` bump + re-run; never loosen the gate |
| eBay delete-on-delist obligations | `retention_class = ebay_listing_observation` enforced in schema (already present); heartbeat rows carry the same class (OQ17 carve-out) |

## 7. Execution process

Each sub-milestone: `superpowers:writing-plans` plan doc (`docs/superpowers/plans/2026-07-05-ms1<x>-….md`) → execution with the verification gate → `dev→main` PR (merge commit, CI + dependency-review green). Deviations from this design or the spec go to the spec Deviations Log / OQ process, per Appendix B.
