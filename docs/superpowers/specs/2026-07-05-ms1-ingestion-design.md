# MS-1 — Ingestion (top 5): Design

> Brainstorm output (2026-07-05, owner-ratified section by section). Instantiates master-spec §19 "MS-1 — Core workflow" as five sequenced sub-milestones, each with its own implementation plan (`superpowers:writing-plans`) and its own `dev→main` PR. The master spec and ADRs remain the design source of truth; this document records the MS-1 *decomposition* and the owner scope decisions taken 2026-07-05. It introduces no new architecture — every mechanism below is fixed by an existing ADR or spec section, cited inline.

**Goal:** all 5 primary recert sources (WD Recertified, Seagate Recertified, ServerPartDeals, goHardDrive, eBay Browse) yield normalized, FX-stamped listings **run through the live rung-0–2 resolver** on a scheduled run — with per-grain resolution counts recorded per source and **each source resolving ≥ 1 listing at family grain or better by MS-1 close** (full coverage is MS-2's ≥ 80% expectation, not an MS-1 gate); re-runs append `offer_snapshot` observations, never duplicate listings; the C.3.5 labeled corpus demonstrates ≥ 99.5% rung-0–2 auto-accept precision on a ≥ 100-decision denominator, ratifying ADR-0019.

## 1. Owner scope decisions (2026-07-05)

These settle what spec §19 left open at the MS-1 boundary:

| # | Decision | Consequence |
| --- | --- | --- |
| S-1 | **Heartbeat machinery (ADR-0015) is IN scope for MS-1** — cheap-signal gating for every source with a verified cheap signal; **fast-lane cadence strictly per FR-002** (`drop-prone` ∩ verified signal). Per-source classification: see the §3 MS-1d matrix. | `availability_heartbeat_observation` hypertable + `availability_heartbeat_event` table land in MS-1d with the OQ17 retention machinery. `heartbeat_enabled` and `fast_lane` are **separate registry fields**: WD/Seagate = heartbeat + fast lane; ServerPartDeals = heartbeat at T2 cadence, **not** fast-laned (churning — volatility research); eBay = fast lane whose Browse poll *is* the cheap signal (no separate heartbeat tier); goHardDrive = full pipeline at T2 cadence. _(Corrected 2026-07-05 per Codex audit SA-002: the original "WD/Seagate/SPD fast-lane" framing conflated cheap-signal gating with fast-lane membership, contradicting FR-002 and the volatility research.)_ |
| S-2 | **Full C.2 substrate + ADR-0017 lifecycle now** (not a core subset) | Two-level token buckets, back-off ladder, auto-ramp, soft-block detection, breaker registry with `paused_pending_fix` recovery probes and the SKIP state — all in MS-1a |
| S-3 | **`httpx` approved** as the HTTP client for API/FX/heartbeat paths (OQ21, resolved 2026-07-05; spec §8.6 row added) | eBay Browse, Frankfurter, and heartbeat probes bypass Scrapy; scrape-tier fetching stays Scrapy |
| S-4 | **eBay production Browse API access VERIFIED LIVE 2026-07-05** — the OpenBao PRD keyset (`secret/api-keys/commerce/ebay`) minted a production client-credentials token (HTTP 200, 7200 s expiry) and a production `buy/browse/v1/item_summary/search` call returned HTTP 200 with real recert-drive results. Not just "credentials exist" (Codex SA-001). | eBay connector is built against the production Browse API; sequenced last in MS-1d to harden the adapter contract on simpler sources first. Buy-API access terms are eBay-mutable — **re-run the same two-step smoke (token mint + one search; never print the token) at MS-1d connector-plan time**; if access has regressed, stop and raise an OQ (defer-eBay vs partner-application decision is the owner's). |
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

- **Source registry as rows:** new `SourceConfig` model, 1:1 with `SourceSite`, carrying the C.2 per-source parameters — tier (T0–T4), `cadence_baseline`/`cadence_ceiling`, volatility profile, cheap-signal kind, `heartbeat_enabled` and `fast_lane` (**separate fields** — see the §3 MS-1d matrix; the FR-002 eligibility constraint applies to `fast_lane` only), back-off state, and the ADR-0017 lifecycle state (`active / backing_off / paused_pending_fix / skip`). ADR-0016 settings-row pattern: cadence values are OQ9-provisional tunables, changed by UPDATE not deploy.
- **`ScraperRun` model** (§18.5): one row per scheduled run — start/finish/status/record counts/failure class. The shared substrate for later observability (OQ5/OQ8/OQ10).
- **Admission machinery** (ADR-0012/0016/0017 + C.2): in-process two-level token buckets (per-source + per-domain), the exponential back-off ladder (`random(0,1) × min(24 h, 10 min × 2^failures)`; `Retry-After` honored verbatim clamped 1 s..baseline), auto-ramp (4 clean polls → halve interval, floored at tier ceiling), latency-spike halving, soft-block detection (EC-007 signals), breaker trips on `anti_bot`/sustained `parser_rot` → `paused_pending_fix` with a daily recovery probe, terminal SKIP as registry state. State lives in memory, checkpointed to PostgreSQL for crash recovery.
- **Pipeline runner:** executes the stage chain with per-stage timeouts and §12.1 failure classification; a failed resolve never blocks persist (listing lands at `grain = none`, error recorded in resolution evidence — C.3).
- **Scrapy integration:** Scrapy's asyncio reactor shares the poller's event loop (`AsyncIOScheduler`) per ADR-0012; scrape-tier adapters are Scrapy spiders run via **`AsyncCrawlerRunner`** — the asyncio-native runner the Scrapy docs prescribe for asyncio hosts (`crawl()` awaitable directly on the shared loop). `CrawlerRunner` + explicit `Deferred.asFuture(loop)` bridging is the documented fallback **only** if `AsyncCrawlerRunner` proves unavailable in the pinned Scrapy version — the chosen primitive is asserted by the walking-skeleton test either way (Codex SA-006). Guardrails (C-007) in one shared settings module: `ROBOTSTXT_OBEY=True`, AUTOTHROTTLE, honest UA, hard timeouts.
- **Reactor lifecycle requirements (Codex SA-006 — load-bearing, per Scrapy docs):** the asyncio reactor is installed **exactly once, before anything imports `twisted.internet.reactor`** (first statement of the poller's `run()`; idempotent guard for tests); **no module-level Twisted reactor imports anywhere** (a prematurely imported default reactor cannot be switched); the poller process owns **one long-lived event loop** — a Twisted reactor cannot be restarted, so per-crawl code must never stop it; and the walking skeleton must prove **two consecutive scheduled crawls in one process on one loop** (multi-`asyncio.run()` test patterns create fresh loops against a stale reactor and are forbidden for Scrapy-touching tests).
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

**Per-source classification matrix** (FR-002-faithful — `fast_lane` = `drop-prone` ∩ verified cheap signal; `heartbeat_enabled` is the orthogonal "cheap probe gates the full pipeline" flag; evidence: [volatility research 2026-07-04](../../research/2026-07-04-per-source-inventory-volatility-and-fast-lane-polling.md) + [WD/Seagate recon spike](../../research/2026-07-04-wd-seagate-recert-endpoint-recon.md)):

| Source | Tier | Acquisition path | Volatility | Cheap signal | `heartbeat_enabled` | `fast_lane` | Poll posture |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ServerPartDeals | T2 | Shopify `products.json` + JSON-LD | **churning** | Shopify `variants[].available` (verified class) | ✅ | ❌ (not drop-prone — FR-002) | Heartbeat at T2 cadence gates the full pipeline; no fast-lane cadence |
| goHardDrive | T2 | Structured data / HTML selectors (verify live at plan time) | churning | none confirmed (plain-HTML keyword check is a plan-time option, not assumed) | ❌ | ❌ | Full pipeline at T2 cadence |
| WD Recertified | T1 | Unauthenticated SAP-Commerce OCC JSON (variant-grain SKU, price, stock) | **drop-prone** | OCC JSON (recon-confirmed) | ✅ | ✅ | Heartbeat at fast-lane cadence; full pipeline on transition |
| Seagate Recertified | T1 | Bootstrap JSON in the robots-allowed `www.seagate.com` category page; **crawl-delay 20 honored** | **drop-prone** | bootstrap JSON (recon-confirmed) | ✅ | ✅ | Heartbeat at fast-lane cadence (≥ 20 s floor); full pipeline on transition. `store.seagate.com` (incl. GraphQL) is robots-disallowed — **never fetched** |
| eBay | T0 | Browse API, OAuth2 client-credentials via `httpx` (production access verified live 2026-07-05, S-4) | drop-prone | **the Browse poll itself** — no separate heartbeat tier (volatility research: "natively cheap") | ✅ (Browse poll doubles as the heartbeat observation) | ✅ | Browse API poll at T0 cadence; heartbeat rows written from the same response |

- Every adapter: Pydantic validation, `raw_payload` persistence with the source's retention class, per-source failure isolation (NFR-001), vcrpy cassettes + syrupy snapshots.
- **Heartbeat storage (S-1/OQ17):** new `availability_heartbeat_observation` hypertable (monthly chunks, 30-day raw retention, compression ≈ 7 days, per-source daily continuous aggregate) + plain `availability_heartbeat_event` table (non-`unchanged` rows, 365-day TTL). Probes read the **variant/SKU-grain** availability field, diff price+stock fingerprints against last-seen, and fire the full pipeline only on `transition_detected`/`ambiguous`.
- **Heartbeat schema requirements (Codex SA-005):** the OQ17 TTLs require **new `RetentionClass` values** (`availability_heartbeat` 30 d, `availability_heartbeat_event` 365 d — both bounded) added to `BOUNDED_RETENTION_CLASSES` and the `retention_constraints()` check lists in `catalog/models/base.py`; **eBay carve-out**: eBay-sourced heartbeat rows carry `retention_class = ebay_listing_observation` (≤ 6 h / delete-on-delist), overriding the class TTLs for that source (DR-008). Migration tests must prove the new classes satisfy the constraints and that wrong class/TTL combinations fail.
- **Pre-real-data operational gate (Codex SA-004) — checked before the first enabled production source, not after:** (1) hourly **TimescaleDB-aware** dumps cover the new tables (wired 2026-07-05c per handoff — *verify*, don't assume); (2) CT-116 disk-space alert confirmed active (raw payloads grow); (3) raw payloads are DB-resident in this design, so the dump pipeline covers them — if any stage later writes disk-path payloads, the CT-116 subvol must enter restic `BACKUP_PATHS` **before** that stage ships; (4) restore path documented (runbook §18.6). Recorded as an MS-1d task, gating the first `enabled=True` flip.
- Endpoint shapes are re-verified live immediately before each connector's plan is written (the recon report is a dated point-in-time probe); the eBay production-access smoke (S-4) re-runs at the same time.

**Exit = spec §19 MS-1 acceptance (minus ratification), plus resolution evidence (Codex SA-003):** 5/5 sources yield ≥ 1 normalized listing on a scheduled run; 100% of non-USD listings carry FX stamps + USD price; international listings flagged; re-runs append `offer_snapshot` rows, not duplicate listings (DR-005); **each source's run report records per-grain resolution counts** (`none/family/model/variant`), so MS-1e's gate has real denominators — MS-1d itself may still carry `grain = none` rows (resolution quality is gated at MS-1e, coverage expectation at MS-2 per C.3.5).

### MS-1e — Validation corpus + ADR-0019 ratification

- Harvest ~150–200 real titles across the 5 sources from connector runs into a versioned JSONL fixture (title, source, raw attributes, ground-truth label: expected grain + target).
- Labeling per S-5: Claude drafts, owner audits a random ~20% + every case where label and matcher disagree.
- A pytest-marked evaluation computes rung-0–2 auto-accept precision and model-grain coverage. **≥ 99.5% precision** → ADR-0019 flips `proposed → accepted` (result recorded in its Confirmation section); spec drops the D-019/C.3 "(proposed)" qualifiers and the ADR-index row updates; TODO ratification item closes. A miss → veto-rule fix + `matcher_version` bump + re-run, per C.3.5 — the gate is not loosened.
- **Denominator + resolution evidence (Codex SA-003 — the gate must not be passable on trivially few matches or `grain = none` rows):** the corpus holds **150–200 titles spanning all 5 sources**, and the precision claim requires **≥ 100 rung-0–2 auto-accepted decisions** in its denominator (floor provisional-tunable; a smaller denominator fails the evaluation with "insufficient corpus", never "pass"). MS-1 close additionally requires: (a) the **FR-003 acceptance case green as a resolver-driven test** (a recert and a new listing of the same drive → one `product_model`, two `product_variant`s — upgraded from MS-0's schema-shape version at MS-1b); (b) a **per-source resolution floor: every one of the 5 sources shows ≥ 1 real listing resolved at family grain or better** (a source that only ever produces `grain = none` rows fails MS-1 — it signals a catalog or extraction gap for that source's inventory, which is exactly what MS-1 must surface); and (c) the evaluation report stating **per-source model-grain-or-better coverage** (reported for MS-2's ≥ 80% expectation; not an MS-1 gate).
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
