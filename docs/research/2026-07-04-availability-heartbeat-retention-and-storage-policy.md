---
schema_version: '1.1'
id: 2026-07-04-availability-heartbeat-retention-and-storage-policy
title: Retention and Storage Policy for a High-Frequency Availability-Heartbeat Observation Table in PostgreSQL + TimescaleDB
description: Resolves hw-radar OQ17 — recommends a class-differentiated retention design for `availability_heartbeat_observation` (short raw retention for bulk `unchanged` rows plus an indefinite per-source daily continuous aggregate, versus long retention for the rare `transition_detected`/`ambiguous`/`failed` classes written to a separate small table), grounded in TimescaleDB's chunk-granular retention model, its continuous-aggregate/retention interaction, its Apache-2-vs-Community license split, and Prometheus/Thanos-style raw-then-downsample conventions. Confirms storage volume is not a constraint at this scale.
doc_type: research
status: active
created: '2026-07-04'
updated: '2026-07-04'
reviewed: null
owner: chris
tags:
- timescaledb
- retention-policy
- compression
- continuous-aggregate
- hypertable
- availability-heartbeat
aliases:
- heartbeat retention policy
- OQ17
related:
- ../adr/adr-0015-availability-heartbeat-grain-volatility-scheduling.md
- database-architecture
- 2026-07-03-postgresql-backup-disaster-recovery-single-vm
- 2026-07-04-per-source-inventory-volatility-and-fast-lane-polling
source: []
confidence: high
visibility: private
license: null
---

# Retention and Storage Policy for a High-Frequency Availability-Heartbeat Observation Table in PostgreSQL + TimescaleDB

## Bottom line

Storage volume is not the constraint here — even at the full 20-source fast-lane scale (~10,000 rows/day, ~3.65M rows/year), this table lands in the tens-of-MB-per-year range once compressed, nowhere near a capacity problem on a single LXC container. The real design problem is that **TimescaleDB's retention policy is chunk-granular** (`drop_chunks`/`add_retention_policy` drop whole time chunks, not rows matching a predicate), so a single hypertable cannot natively keep `unchanged` heartbeats for 2 weeks while keeping `transition_detected`/`ambiguous`/`failed` heartbeats for a year — both classes share the same chunks. The corroborated pattern for this is **not** a per-row retention hack inside one hypertable; it's **writing the rare, diagnostically-valuable classes to a second, separate (and much smaller) table** with its own independent, much longer retention — the same "one hypertable/table per class or purpose" idiom vendor and community guidance converge on. Recommendation: make `availability_heartbeat_observation` a hypertable (for backup/ops consistency with `offer_snapshot`, not because raw volume demands it), give it a short raw-retention window (~30 days) backed by an indefinitely-retained per-source-per-day continuous aggregate for the SLO trend, enable compression on chunks a few days old, and fork every non-`unchanged` decision into a small plain PostgreSQL table (`availability_heartbeat_event`) retained for ~180-365 days — sidestepping the chunk-granularity limitation entirely rather than fighting it.

## Summary

| Angle | Sources | Strongest finding |
| --- | --- | --- |
| Official Docs | 9 | `add_retention_policy`/`drop_chunks`/continuous-aggregate refresh are documented, chunk-granular APIs; the editions table shows exactly which are Community(TSL)-only |
| Best Practices | 4 | Chunk interval and compression segmentby must be sized to the workload's actual row rate, not the "10-100M rows/chunk" high-ingest rule of thumb |
| Footguns | 4 (all corroborated 2+ sources or official) | Retention dropping raw chunks before a continuous aggregate refreshes over them silently zeroes/corrupts the aggregate |
| Existing Tools | 3 | No dedicated tool solves class-differentiated retention; TimescaleDB's own hypertable+cagg+retention stack is the best fit since `offer_snapshot` already pays for it |
| Security | 3 | Compression, automated retention, and continuous aggregates are all TimescaleDB **Community (TSL)** features, not Apache-2 — self-hosted non-DBaaS use is free, but it's the same license class this project already carries via `offer_snapshot` |
| Recent Changes | 3 | TigerData rebrand (2025) + the 2.22/2.23 "hypercore" rename (`add_columnstore_policy` supersedes but doesn't remove `add_compression_policy`) |

**Queries:** 13 · **Results parsed:** ~75 · **Deep reads:** 4 (Tavily extract on TigerData editions, cagg-retention, hypercore-troubleshoot, pg_partman-vs-hypertables docs) · **Follow-up pass:** no (all six angles cleared 2+ distinct sources on the first pass)

## Official Documentation

- `add_retention_policy(hypertable, drop_after => INTERVAL)` schedules a background job that drops chunks whose time range is fully older than `drop_after`; `drop_chunks()` does the same thing immediately/manually. Both operate on whole chunks, never individual rows [official](https://www.tigerdata.com/docs/reference/timescaledb/data-retention/add_retention_policy).
- Continuous aggregates are downsampling materialized views (`CREATE MATERIALIZED VIEW ... WITH (timescaledb.continuous)`) refreshed on a schedule (`add_continuous_aggregate_policy`, `start_offset`/`end_offset`/`schedule_interval`); TimescaleDB's own worked example shows a 24-hour retention policy on the raw table combined with a 7-day-back refresh window **deletes the aggregate's own data** the next time it refreshes, because the refresh only sees "the raw data changed (was deleted)" and propagates that deletion — fixed by setting retention comfortably longer than the refresh window (their example: 30-day retention with a 7-day/1-day refresh window) [official](https://www.tigerdata.com/docs/learn/data-lifecycle/data-retention/data-retention-with-continuous-aggregates).
- The TimescaleDB edition comparison table is unambiguous about which primitives are free (Apache-2) vs. Community(TSL)-licensed: `CREATE TABLE`, `create_hypertable`, `show_chunks`, and **`drop_chunks` are Apache-2**; `add_retention_policy`, all continuous-aggregate DDL/policy functions, and all columnstore/compression functions (`add_columnstore_policy`, legacy `add_compression_policy`, `convert_to_columnstore`, etc.) are **Community-only** [official](https://www.tigerdata.com/docs/get-started/choose-your-path/timescaledb-editions).

## Best Practices

- Default `chunk_time_interval` is 7 days; the commonly cited sizing rule of thumb ("aim for chunks with 10-100M rows" / "25-100 GB per chunk") targets high-ingest IoT/metrics workloads and does not apply at hw-radar's scale — applying it naively would produce absurdly long chunk intervals [blog](https://oneuptime.com/blog/post/2026-02-02-timescaledb-high-ingestion/view), [blog](https://oneuptime.com/blog/post/2026-01-26-timescaledb-hypertables/view). At low volume, the actionable guidance instead is "for lower-volume data, weekly or monthly chunks reduce overhead" [blog](https://oneuptime.com/blog/post/2026-02-08-how-to-run-timescaledb-in-docker-with-hypertables/view).
- Compression `segmentby` should match the columns you actually filter/group by (here: `source_id`, `variant_id`) — get this wrong at low per-segment row counts and compression can **increase** total size rather than shrink it, as a real production case demonstrated (segmenting a modest 28M-row dataset by high-cardinality `ticker` inflated storage because segments/chunks ended up sub-megabyte) [blog](https://mail-dpant.medium.com/my-experience-with-timescaledb-compression-68405425827). This is corroborated as a pattern, not a one-off, by independent guidance that segmentby choice and chunk size need co-tuning [blog](https://oneuptime.com/blog/post/2026-02-02-timescaledb-compression/view).
- The idiomatic fix for "I need different retention for different rows in the same time-series stream" is **not** a per-row retention hack — it's splitting into multiple hypertables/tables by purpose or class. Both a vendor best-practices piece ("a common mistake is putting everything in one hypertable... a typical production setup has 3-5 hypertables, one per data source") [blog](https://www.jusdb.com/blog/timescaledb-hypertables-continuous-aggregates-guide) and TigerData's own schema-design guidance ("one hypertable per customer... for multi-tenancy") [official](https://www.tigerdata.com/learn/designing-your-database-schema-wide-vs-narrow-postgres-tables) converge on splitting by dimension/class as the standard idiom, rather than a single hypertable with row-level retention logic.

## Footguns and Gotchas

- **Retention-vs-continuous-aggregate gap.** Dropping raw chunks before the aggregate's refresh window has covered them silently deletes data from the aggregate too (it materializes "the raw data changed" as "delete", not "no data to see") — demonstrated in TigerData's own worked example [official](https://www.tigerdata.com/docs/learn/data-lifecycle/data-retention/data-retention-with-continuous-aggregates), enforced at the SQL level by a cross-policy validation that errors if a continuous-aggregate refresh window would extend past the retention `drop_after` cutoff (`err_refresh_reten_overlap` in `policies_v2.c`) [official](https://github.com/timescale/timescaledb/blob/main/timescaledb/tsl/src/bgw_policy/policies_v2.c) — but this guard only fires when both policies are declared through the standard API; manual `drop_chunks()` calls or a materialized-view retention policy configured independently of the raw table's policy can still create the gap, which is why TimescaleDB's own issue tracker still treats the UX here as an open usability problem [community](https://github.com/timescale/timescaledb/issues/2198).
- **Compressed chunks cap bulk DML.** INSERT/UPDATE/DELETE against compressed chunks decompresses affected rows into the rowstore first, and TimescaleDB caps how many tuples a single DML statement may decompress (`max_tuples_decompressed_per_dml_transaction` / equivalent hypercore setting) — exceeding it fails the statement rather than silently degrading, confirmed in TigerData's own troubleshooting docs [official](https://www.tigerdata.com/docs/build/tips-and-tricks/troubleshoot-hypercore) and reported directly against the GUC in the project's issue tracker [official](https://github.com/timescale/timescaledb/issues/6804); a third source notes the same limit specifically breaks naive bulk `DELETE`s unless wrapped in `SET LOCAL` to raise it per-transaction [blog](https://mydba.dev/blog/timescaledb-retention-policies). Relevant here because any manual backfill/cleanup while diagnosing a fingerprint bug on already-compressed chunks will hit this.
- **Small chunks/segments inflate compressed size instead of shrinking it** — corroborated above under Best Practices; worth flagging as a footgun specifically because hw-radar's *initial* volume (2-5 sources × 500 rows/day) is exactly the low-row-count regime where a too-fine chunk interval or too-granular `segmentby` produces this failure mode.
- **Logical dump/restore does not preserve compression** and requires `timescaledb_pre_restore()`/`timescaledb_post_restore()` plus a matching extension version on source and target — already established for `offer_snapshot` in this project's own prior backup research and unchanged for this new hypertable [official, per prior in-repo finding](../research/2026-07-03-postgresql-backup-disaster-recovery-single-vm.md).

## Existing Tools

| Tool | Maintenance | Link | Fit for use case |
| --- | --- | --- | --- |
| TimescaleDB hypertable + continuous aggregate + retention/compression policies (built-in) | Active, TigerData-maintained; already adopted for `offer_snapshot` | [tigerdata.com/docs](https://www.tigerdata.com/docs/get-started/choose-your-path/timescaledb-editions) | High — reuses the ops runbook already paid for; retention is chunk-granular so still needs the split-table pattern for class differentiation, not solved out of the box |
| pg_partman | Active community Postgres extension | [pg_partman vs hypertables](https://www.tigerdata.com/learn/pg_partman-vs-hypertables-for-postgres-partitioning) | Low — would mean hand-rolling compression and continuous-aggregate equivalents; only worth it if dropping TimescaleDB entirely, unwarranted while `offer_snapshot` depends on it |
| dbt-timescaledb (community dbt package exposing hypertable/retention config) | Small single-maintainer project | [dbt-timescaledb.debruyn.dev](https://dbt-timescaledb.debruyn.dev/usage/retention-policies/) | Low — only useful inside a dbt-managed pipeline; hw-radar's stack is Django + APScheduler + raw SQL/ORM migrations, no natural integration point |

## Security and Compatibility

- **License class:** compression (`add_columnstore_policy` / legacy `add_compression_policy`), automated retention (`add_retention_policy`), and every continuous-aggregate primitive are **TimescaleDB Community Edition (Tiger Data License / TSL)**, not Apache-2 — only `create_hypertable`, `show_chunks`, and `drop_chunks` are Apache-2 [official](https://www.tigerdata.com/docs/get-started/choose-your-path/timescaledb-editions). Self-hosted, non-DBaaS production use of Community Edition is free per TigerData's own terms, and a real-world support ticket shows exactly what breaks if the "apache" license mode is active instead (`add_compression_policy` errors with "not supported under the current apache license") [community](https://support.zabbix.com/si/jira.issueviews:issue-html/ZBX-20743/ZBX-20743.html), corroborated independently by community discussion of the same Apache-vs-TSL split [community](https://www.reddit.com/r/Database/comments/1r3nw0v/disappointed_in_timescaledb). This doesn't add new licensing exposure — `offer_snapshot` already exercises this same feature/license class (already flagged as a fact-to-record under **OQ20**), so this table's exact license posture should just be folded into that single audit note rather than treated as a new decision.
- **RLS incompatibility:** TimescaleDB explicitly rejects enabling columnstore compression on a table with row-level security policies attached (`ereport(ERROR, ... "columnstore cannot be used on table with row security")`) [official](https://github.com/timescale/timescaledb/blob/main/tsl/src/compression/create.c). Not a current blocker (hw-radar has no per-tenant RLS on this table) but worth recording if a future multi-user visibility layer is added on top of heartbeat data.
- **Backup/restore:** no new risk beyond the already-documented pg_dump/compression caveat above; the heartbeat hypertable's low absolute size (see Storage math) makes the extra recompress-after-restore step negligible next to `offer_snapshot`.

## Recent Changes

- **TigerData rebrand** (June 17, 2025) — the company behind TimescaleDB renamed from Timescale Inc. to TigerData; current docs live at `tigerdata.com` rather than the historical `docs.timescale.com` [community](https://grokipedia.com/page/TimescaleDB), corroborated by the fact that all current official reference/how-to pages collected in this research now resolve under the `tigerdata.com` domain.
- **"Hypercore" rename (TimescaleDB 2.22/2.23).** `add_columnstore_policy()`/`enable_columnstore`/`convert_to_columnstore` supersede the older `add_compression_policy()`/`timescaledb.compress` naming, but the older functions remain supported — no forced migration [official](https://github.com/timescale/docs/blob/latest/api/compression/add_compression_policy.md), [official](https://www.tigerdata.com/docs/reference/timescaledb/hypercore/add_columnstore_policy). The same release line introduced a tech-preview "Direct Compress" path claiming up to 40x faster ingestion into compressed form and continued the >90% compression-ratio positioning [official](https://www.tigerdata.com/blog/introducing-direct-compress-up-to-40x-faster-leaner-data-ingestion-for-developers-tech-preview).
- **`CREATE TABLE ... WITH (timescaledb.hypertable)`** is now available (2.23+) as an alternative to calling `create_hypertable()` on a pre-existing table, with automatic partitioning-column detection when unambiguous [official](https://docs.timescale.com/api/latest/hypertable/create_hypertable/). Either form is fine for this table; `create_hypertable()` matches the existing `offer_snapshot` convention and needs no change.

## Storage-size math (why this isn't a capacity problem)

A narrow heartbeat row (`variant_id` FK, `observed_at`, `decision`, price/stock/shipping fingerprint fields, a short fingerprint hash, latency/HTTP-status metadata) is roughly 150-250 bytes uncompressed including Postgres's per-row tuple overhead. At the **full** fast-lane scale envisioned by ADR-0015 (up to 20 sources × ~500 rows/day) that's ~10,000 rows/day, ~3.65M rows/year, or **roughly 0.7-1.1 GB/year uncompressed including indexes** — at the initial 2-5-source scale it's an order of magnitude smaller. Compression on time-series data this repetitive (a `decision` column that is `unchanged` the overwhelming majority of the time, prices and stock states that repeat across consecutive polls) reliably lands at 90%+ reduction, corroborated across three independent sources spanning a vendor benchmark, a real production case study, and a technical breakdown of the columnar encoding involved [official](https://www.tigerdata.com/blog/introducing-direct-compress-up-to-40x-faster-leaner-data-ingestion-for-developers-tech-preview), [blog](https://dev.to/polliog/timescaledb-compression-from-150gb-to-15gb-90-reduction-real-production-data-bnj), [blog](https://roszigit.com/en/blog/timescaledb-compression-hypercore). Post-compression, even a full year of raw retention across all 20 sources would land in the **tens-of-MB** range — this table will not approach single-digit-GB territory for years even under generous retention. The retention decision here is therefore about controlling backup/restore time, index bloat, and diagnostic-query focus (recent, relevant rows vs. years of noise) — not disk capacity.

## Calibration: how observability systems tier raw-vs-downsampled retention

Prometheus/Thanos/Mimir converge on a **short raw-resolution window plus long-lived downsampled resolutions**, which is the same shape recommended here (short raw `unchanged` retention + an indefinite daily continuous aggregate). Thanos's compactor explicitly warns that raw-retention should be set at least as long as the highest downsample interval you might need to "zoom into," or you lose the ability to inspect recent detail once it's rolled up [official](https://thanos.io/v0.8/components/compact). Mimir/Grafana's own defaults trend toward long total retention (their stated default estimate assumes ~13 months) with downsampling requested as a separate, still-open feature for pruning full-resolution data after a period [official](https://github.com/grafana/mimir/discussions/1834). A third, vendor-neutral write-up frames the general pattern as "hot tier for fast queries, warm tier for long-term/downsampled data, hard disk cap on the hot tier" [blog](https://stackharbor.com/en/knowledge-base/metrics-retention-policies) — directly analogous to the raw-heartbeat-hot / daily-aggregate-warm / rare-class-diagnostic-table split recommended above.

## Recommendation (resolves OQ17)

1. **Make `availability_heartbeat_observation` a hypertable**, consistent with `offer_snapshot`'s existing pattern — not because raw volume forces it (it doesn't, see Storage math), but because it reuses the already-adopted compression/retention/backup runbook instead of introducing a second lifecycle-management mechanism (pg_partman, cron `DELETE`+`VACUUM`) for one small table.
2. **Chunk interval:** start at **monthly** given the initial 2-5-source volume (avoids the small-chunk/segment overhead footgun); revisit down to **weekly** once the fast-lane set approaches 20 sources. This is a judgment call informed by the corroborated "small chunks hurt compression" pattern, not a number found in any single source — re-measure actual chunk/segment sizes once real data lands.
3. **Retention:** `add_retention_policy` on the raw hypertable with `drop_after => INTERVAL '30 days'` — long enough for rolling p95 SLO windows and near-term fingerprint-bug triage, short enough that raw-`unchanged` bulk never grows unbounded.
4. **Continuous aggregate:** `availability_heartbeat_daily` bucketed by `source_id, day, decision, count(*)` with a refresh `start_offset` well inside the 30-day retention window (e.g., 2 days back to 1 hour back), retained indefinitely — its own size is trivial (≈20 sources × 4 classes × 365 days/year ≈ 29K rows/year) and it's exactly what the p95-SLO consumer needs for long-horizon trend without touching raw rows.
5. **Class-differentiated retention:** don't fight chunk granularity — have the poller (which already branches on decision class per ADR-0015) additionally write every non-`unchanged` row (`transition_detected`/`ambiguous`/`failed`) to a second, **plain (non-hypertable) PostgreSQL table** `availability_heartbeat_event`, retained 180-365 days (cheap given its low expected volume) via a simple scheduled `DELETE` — the fingerprint-tuning consumer reads this table exclusively, sidestepping every compression-related footgun above for exactly the rows that matter most for debugging.
6. **Compression:** enable on the raw hypertable only, `compress_segmentby = 'source_id, variant_id'`, `compress_orderby = 'observed_at DESC'`, compressing chunks older than ~3-7 days (well inside the 30-day retention cutoff so the retention-vs-cagg-refresh ordering constraint is trivially satisfied).
7. **License/backup:** no new posture beyond what `offer_snapshot` already carries — fold into the single OQ20 TimescaleDB-Community audit note; no change to the existing hourly logical-dump runbook.

## Open Questions

| # | Question | Why unresolved |
| --- | --- | --- |
| 1 | Are the 30-day (unchanged) / 180-365-day (rare classes) windows numerically right, or just directionally reasonable? | No source addresses hw-radar's specific p95-sample-size requirements; this is a judgment call to validate once eBay (the first fast-lane source) has run for a few weeks — treat as a self-correcting tunable per the OQ9 precedent, not a fixed constant. |
| 2 | Should `availability_heartbeat_event` ever become a hypertable itself? | If the WD/Seagate direct XHR-endpoint recon spike (open in `TODO.md`) succeeds and those two high-volume drop-prone sources join the fast lane, "rare" events may become frequent enough to need compression too — no source covered this hybrid-scale transition point; revisit alongside that spike. |
| 3 | Exact row width / compressed-size numbers for this specific schema | The storage-size math above is a reasoned estimate from column-count assumptions, not a measurement against a live TimescaleDB instance with this exact table — cheap to validate empirically once M1 lands (`hypertable_detailed_size()`). |

## Handoff

Persisted at `docs/research/2026-07-04-availability-heartbeat-retention-and-storage-policy.md`. Downstream skills that may consume it:

- `superpowers:brainstorming` — validate the 30-day/180-365-day windows once real eBay heartbeat data exists
- `feature-dev:feature-dev` — implement the `availability_heartbeat_observation` hypertable + `availability_heartbeat_event` table + continuous aggregate at M1 (first fast-lane source)

## Sources

| URL | Title | Date | Authority |
| --- | --- | --- | --- |
| https://www.tigerdata.com/docs/reference/timescaledb/data-retention/add_retention_policy | add_retention_policy() | Tiger Data Docs | current | official |
| https://www.tigerdata.com/docs/reference/timescaledb/data-retention | Data retention overview | Tiger Data Docs | current | official |
| https://www.tigerdata.com/docs/build/data-management/data-retention/create-a-retention-policy | Add a data retention policy | Tiger Data Docs | current | official |
| https://www.tigerdata.com/docs/learn/data-lifecycle/data-retention/data-retention-with-continuous-aggregates | About data retention with continuous aggregates | Tiger Data Docs | current | official |
| https://github.com/timescale/timescaledb/issues/2198 | Test/improve UX of continuous aggregate refresh + retention | current | official |
| https://www.tigerdata.com/docs/get-started/choose-your-path/timescaledb-editions | Compare TimescaleDB editions | Tiger Data Docs | current | official |
| https://github.com/timescale/docs/blob/latest/api/compression/add_compression_policy.md | add_compression_policy superseded by add_columnstore_policy | current | official |
| https://www.tigerdata.com/docs/reference/timescaledb/hypercore/add_columnstore_policy | add_columnstore_policy() | Tiger Data Docs | current | official |
| https://docs.timescale.com/api/latest/hypertable/create_hypertable/ | Hypertables and chunks | Tiger Data Docs | current | official |
| https://www.tigerdata.com/docs/build/tips-and-tricks/troubleshoot-hypercore | Troubleshoot hypercore | Tiger Data Docs | current | official |
| https://github.com/timescale/timescaledb/issues/6804 | max_tuples_decompressed_per_dml_transaction limit report | current | official |
| https://github.com/timescale/timescaledb/blob/main/src/guc.c | TimescaleDB GUC source (decompression batch limit) | current | official |
| https://github.com/timescale/timescaledb/blob/main/tsl/src/compression/create.c | RLS blocks columnstore compression (source) | current | official |
| https://github.com/timescale/timescaledb/blob/main/timescaledb/tsl/src/bgw_policy/policies_v2.c | Retention/refresh cross-policy validation (source) | current | official |
| https://www.tigerdata.com/blog/timescaledb-2-22-2-23-90x-faster-distinct-queries-postgres-18-support-configurable-columnstore-indexes-uuidv7 | TimescaleDB 2.22 & 2.23 release blog | current | official |
| https://www.tigerdata.com/blog/introducing-direct-compress-up-to-40x-faster-leaner-data-ingestion-for-developers-tech-preview | Introducing Direct Compress | current | official |
| https://www.tigerdata.com/learn/designing-your-database-schema-wide-vs-narrow-postgres-tables | Designing Your Database Schema: Wide vs. Narrow Postgres Tables | current | official |
| https://www.tigerdata.com/learn/pg_partman-vs-hypertables-for-postgres-partitioning | Pg_partman vs. Hypertables for Postgres Partitioning | current | official |
| https://thanos.io/v0.8/components/compact | Thanos Compact — downsampling, resolution, retention | current | official |
| https://github.com/grafana/mimir/discussions/1834 | Downsampling of metric data after a certain period (Mimir) | current | official |
| https://grokipedia.com/page/TimescaleDB | TimescaleDB (TigerData rebrand, editions summary) | current | community |
| https://www.reddit.com/r/Database/comments/1r3nw0v/disappointed_in_timescaledb | Disappointed in TimescaleDB (Apache vs TSL split) | current | community |
| https://support.zabbix.com/si/jira.issueviews:issue-html/ZBX-20743/ZBX-20743.html | Compression with Apache licensed TimescaleDB 2.x | 2022 (historical, license mechanics unchanged) | community |
| https://www.reddit.com/r/PostgreSQL/comments/1cjmuzp/timescaledb_without_hypertables/ | TimescaleDB without Hypertables (small-table overhead) | current | community |
| https://www.reddit.com/r/PostgreSQL/comments/t6pbqa/should_i_use_timescaledb_or_partitioning_is_enough/ | Should I use TimescaleDB or partitioning is enough? | current | community |
| https://mail-dpant.medium.com/my-experience-with-timescaledb-compression-68405425827 | My experience with timescaledb Compression | current | blog |
| https://oneuptime.com/blog/post/2026-02-02-timescaledb-compression/view | How to Compress Data in TimescaleDB | 2026-02-02 | blog |
| https://oneuptime.com/blog/post/2026-01-26-timescaledb-hypertables/view | How to Design TimescaleDB Hypertables | 2026-01-26 | blog |
| https://oneuptime.com/blog/post/2026-02-02-timescaledb-high-ingestion/view | How to Handle High-Ingestion Workloads in TimescaleDB | 2026-02-02 | blog |
| https://oneuptime.com/blog/post/2026-02-08-how-to-run-timescaledb-in-docker-with-hypertables/view | How to Run TimescaleDB in Docker with Hypertables | 2026-02-08 | blog |
| https://www.jusdb.com/blog/timescaledb-hypertables-continuous-aggregates-guide | TimescaleDB Hypertables, Continuous Aggregates & Compression (2026) | current | blog |
| https://mydba.dev/blog/timescaledb-retention-policies | Data Retention Policies: Automating Cleanup in TimescaleDB | current | blog |
| https://dev.to/polliog/timescaledb-compression-from-150gb-to-15gb-90-reduction-real-production-data-bnj | TimescaleDB Compression: From 150GB to 15GB (90% Reduction) | current | blog |
| https://roszigit.com/en/blog/timescaledb-compression-hypercore | TimescaleDB Compression: Hypercore and Columnar Storage | current | blog |
| https://stackharbor.com/en/knowledge-base/metrics-retention-policies | Metrics retention policies knowledge base | current | blog |
| https://dbt-timescaledb.debruyn.dev/usage/retention-policies/ | dbt-timescaledb retention policies | current | community |
