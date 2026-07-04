---
schema_version: '1.1'
id: 'adr-0007-hw-radar-datastore-postgresql-timescaledb'
title: 'ADR 0007: Datastore — PostgreSQL as system-of-record + TimescaleDB'
description: 'Use PostgreSQL as the system-of-record with the TimescaleDB extension for the price-history observation workload, rather than MySQL, a plain-PostgreSQL-only build, or ClickHouse-as-primary — the data splits into stable relational dimensions and high-volume mutable time-series.'
doc_type: 'adr'
status: 'active'
created: '2026-07-03'
updated: '2026-07-03'
reviewed: null
owner: ''
consumer: 'mix'
tags:
  - 'adr'
  - 'datastore'
  - 'postgresql'
  - 'timescaledb'
  - 'database'
aliases: []
related:
  - 'docs/adr/README.md'
  - 'docs/specs/hw-radar-master-spec.md'
  - 'docs/open-questions.md'
  - 'docs/resolved-questions.md'
  - 'docs/research/database-architecture.md'
supersedes: []
superseded_by: null
source: []
confidence: 'high'
visibility: 'public'
license: null
project:
  decision_makers:
    - 'chris'
  consulted: []
  informed: []
---

# ADR 0007: Datastore — PostgreSQL as system-of-record + TimescaleDB

MADR status: **accepted**.

## Context and Problem Statement

The spec left the datastore undecided (`_TBD_` — "PostgreSQL or MySQL"). The choice is foundational: it fixes the ORM backing Django (ADR 0004), the schema for the canonical-entity model, and — because the **accumulating price history is the tool's compounding value** — the shape of the workload that backups (ADR 0003) exist to protect.

The data splits cleanly in two, and the datastore has to serve both well:

- **Stable relational dimensions** — manufacturers, canonical drive models, source sites, sellers, cross-marketplace trust rules, ranking weights. These need joins, mutation, deduplication, and per-listing lifecycle management.
- **High-volume, append-mostly, mutable observations** — repeated price / shipping / stock snapshots over time (a genuine time-series), plus messy raw API/scrape payloads that want flexible storage.

The research report [`database-architecture.md`](../research/database-architecture.md) analyzes this directly.

## Considered Options

- **Option 1 — PostgreSQL (system-of-record) + TimescaleDB** for the observation side. (chosen)
- **Option 2 — Plain PostgreSQL only** ("Timescale later if needed").
- **Option 3 — MySQL / MariaDB** (the spec's alternative).
- **Option 4 — ClickHouse as the primary store.**

## Decision Outcome

Chosen option: **Option 1 — PostgreSQL as the system-of-record, with the TimescaleDB extension handling the price-history workload.**

PostgreSQL matches the mixed relational + document shape better than any single-purpose engine: relational joins for the dimensions, `jsonb` for unpredictable provider payloads, **stored generated columns** for row-local economics (`dollars_per_tb`, `total_landed_price`, normalized capacity/warranty), **`pg_trgm`** for fuzzy manufacturer/model matching during entity resolution, and expression/partial/GIN/BRIN indexes for the hot subsets. TimescaleDB — a PostgreSQL _extension_, not a fork — adds hypertables, continuous aggregates, compression, and retention for the repeated-snapshot side, which is exactly what continuously-accruing observation data wants. Cross-row/cross-table rankings ("lowest price in the last 30 days," "best price per model from trusted sellers") live in materialized views or continuous aggregates; row-local math lives in generated columns.

Option 2 is the explicit **fallback**, not a rejection: core PostgreSQL already has declarative partitioning, materialized views, `jsonb`, BRIN, and `pg_trgm`, so a "PostgreSQL-first, Timescale only if needed" build is defensible if minimizing moving parts matters more than the packaged lifecycle features. Option 1 is preferred only because we already _know_ this workload accumulates observation history continuously. Option 3 (MySQL/MariaDB) was rejected: workable (native JSON + full-text) but its mixed relational+document ergonomics are weaker for this exact workload, and there is no incumbent MySQL standardization to preserve. Option 4 (ClickHouse-primary) was rejected for day one: excellent for append-heavy analytics, but it frames updates/deletes as "mutations" and favors batched inserts — a poor fit for a source-of-truth catalog with mutable trust rules, joins, dedup, and per-listing lifecycle. It remains a reasonable _secondary_ analytics warehouse on a later scale-out path.

### Consequences

- **Good** — one always-on database service covers relational, document (`jsonb`), and time-series needs; fewer moving parts on a single CT (ADR 0003).
- **Good** — backs Django's ORM/migrations (ADR 0004) natively; `pg_trgm` gives entity-resolution fuzzy matching without a separate search service.
- **Good** — a clean scale-out path remains (OpenSearch as a companion index if search UX demands it; ClickHouse as an analytics warehouse) without re-platforming the source of truth.
- **Bad** — TimescaleDB is an extension to install, version-track, and keep compatible with the PostgreSQL major; it adds an upgrade dependency the plain-PostgreSQL fallback avoids.
- **Bad (interacts with ADR 0003)** — the backup Hardware Radar *inherits* is **hourly logical `pg_dump`** (ADR 0003 — no physical backup exists; physical is only an optional RPO upgrade in resolved-questions.md OQ3). Logical dumps are precisely the TimescaleDB mode with caveats: restore requires `timescaledb_pre_restore()` / `post_restore()`, and native-compression state is not preserved. **So a TimescaleDB database is *not* correctly protected merely by adding it to the dump allowlist** (as ADR 0003's wiring step implies for an ordinary DB): the dump/restore step must be made **TimescaleDB-aware**, *or* in-CT **physical** backup (`pg_basebackup` / pgBackRest — needs no special handling) must be added (resolved-questions.md OQ3, gap #5). The plain-PostgreSQL fallback (Option 2) sidesteps this caveat entirely — a real, if modest, cost of the extension.
- **Neutral** — the specific PostgreSQL major is not fixed here; it follows what the deployment CT provides. The canonical-entity **schema** (drive-model / listing / observation) is a separate decision (future ADR + `database-architecture.md`), not settled by this engine choice.

### Confirmation

The spec's Database `_TBD_` ("PostgreSQL or MySQL") is resolved to **PostgreSQL + TimescaleDB**. Confirmed when initial migrations create the schema on PostgreSQL with the TimescaleDB extension enabled and observation tables declared as hypertables.

## More Information

- Research: [`database-architecture.md`](../research/database-architecture.md) — executive recommendation, engine comparison, indexing, and single-host operational fit.
- Related: ADR 0004 (Django ORM over this datastore), ADR 0003 (CT deployment + backup — the TimescaleDB physical-vs-logical caveat above), gap #5 (DB backup/RPO), and the pending canonical-entity data-model ADR (schema, distinct from this engine choice).
