---
schema_version: '1.1'
id: 'adr-0015-hw-radar-availability-heartbeat-grain-volatility-scheduling'
title: 'ADR 0015: Availability-heartbeat grain + volatility-aware scheduling'
description: 'Add an availability_heartbeat_observation grain above offer_snapshot in the ADR-0010 identity ladder — a cheap, no-render poll result that gates the full pipeline and fires a snapshot only on a detected transition — and adopt a per-source volatility profile as a second scheduling axis orthogonal to the acquisition tier, so effective cadence = min(tier ceiling, volatility need) and fast-lane membership = drop-prone ∩ a verified cheap availability signal.'
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
  - 'scheduling'
  - 'polling'
  - 'freshness-slo'
  - 'timescaledb'
aliases: []
related:
  - 'docs/adr/README.md'
  - 'docs/adr/adr-0010-canonical-data-model.md'
  - 'docs/adr/adr-0012-orchestration-apscheduler.md'
  - 'docs/adr/adr-0014-scraping-runtime-escalation-stack.md'
  - 'docs/specs/hw-radar-master-spec.md'
  - 'docs/research/2026-07-04-polling-cadence-reconciliation.md'
  - 'docs/research/per-source-polling-cadence-and-skip-policy.md'
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

# ADR 0015: Availability-heartbeat grain + volatility-aware scheduling

MADR status: **accepted**.

## Context and Problem Statement

The original spec framed monitoring as "continuous / near-real-time." Research prompt #15 (per-source inventory volatility & fast-lane polling affordance), run via two independent paths and consolidated in the [polling-cadence reconciliation](../research/2026-07-04-polling-cadence-reconciliation.md), dismantled that framing on two findings:

1. **No source offers a push feed** — everything is poll-based, so "real-time" is a category error; the real target is a per-source **freshness SLO** (max age of the freshest observation, transition-to-alert), bounded below only by the human buyer's ~60–90 s decision loop and above by each source's inventory behaviour.
2. **Inventory volatility and cheap-signal availability are _anti-correlated_.** The burstiest sources (WD/Seagate direct recert, clearing in minutes) expose no cheap availability signal; the sources with a cheap signal (Shopify/WooCommerce specialists) aren't bursty. A blanket "fast-lane tier" is therefore unbuildable — fast-lane membership is an **intersection**, not a tier.

This forces two coupled design questions the acquisition tier (ADR-0014) and orchestration engine (ADR-0012) do **not** answer:

- **Scheduling:** the acquisition tier encodes how fast a source _can_ be polled (trust/anti-bot posture). It says nothing about how fast a source _needs_ polling (inventory churn). Polling a stable source at its tier ceiling wastes budget; polling a drop-prone source at its tier baseline misses the drops the tool exists to catch.
- **Data model:** re-running the full `fetch → parse → normalize → entity-resolve → score → persist` pipeline every poll to notice that nothing changed is wasteful, and worse — writing an `offer_snapshot` per poll would flood the TimescaleDB hypertable with near-duplicate rows and inflate the price-history moat with noise. But a fast source needs frequent cheap checks. This is a **new grain**, not a tuning of the existing one.

Both are **schema-level and hard to reverse** (a new hypertable-adjacent grain in the ADR-0010 identity ladder; a new source-registry dimension the poller reads every cycle), which is why they clear the ADR bar where the other polling parameters — self-correcting tunables — do not.

## Considered Options

- **Option 1 — Keep the two-level model/snapshot shape; poll everything at its tier cadence; write a snapshot per poll.** No new grain, no volatility axis.
- **Option 2 — Add a heartbeat grain above `offer_snapshot` and a per-source volatility profile as a second scheduling axis.** (chosen)
- **Option 3 — Add the volatility axis for scheduling but no separate grain** — schedule by volatility, still run the full pipeline + write a snapshot each poll.

## Decision Outcome

Chosen option: **Option 2.**

### The `availability_heartbeat_observation` grain

A new grain **above** `offer_snapshot` in the ADR-0010 identity ladder (a **supplement to**, not a replacement of, the model → variant → listing → offer_snapshot spine), keyed at the **variant/SKU grain**:

- A **cheap, no-render poll** (Shopify `/products.json` → variant `available`; WooCommerce Store API `is_in_stock`; eBay Browse) captures a **fingerprint of price + stock + shipping state** plus endpoint/cache metadata.
- It records a **decision**: `unchanged` · `transition_detected` · `ambiguous` · `failed`.
- A full `offer_snapshot` (and the pipeline behind it) is produced **only on a detected transition** — OOS↔in-stock, a material price drop, a new variant/listing ID, or post-in-stock ambiguity. `unchanged` heartbeats stay at the heartbeat grain and never touch the offer hypertable.
- Read the **variant-grain** availability field, never a product-level rollup — a product "in stock" because one capacity is available must not mask the target capacity being OOS.

### The volatility scheduling axis

A per-source **volatility profile** — `drop-prone` (bursty recert restocks clearing in minutes–hours) · `churning` (continuous new listings; aggregate-price value) · `stable` (days-timescale) — **orthogonal to the acquisition tier**:

- **Effective cadence = `min(tier ceiling, volatility need)`.** The tier caps how fast we _may_ poll; the volatility profile sets how fast we _should_.
- **Fast lane = `drop-prone` ∩ a verified cheap availability signal** — an intersection. Most drop-prone sources (custom-JS manufacturer recert stores, no cheap signal) are therefore **not** fast-laned; a non-`drop-prone` source is **never** fast-laned regardless of signal.
- Fast-lane sources run the cheap heartbeat above; a slow **repair crawl** still runs for every source, because CDN edge cache is a floor on achievable freshness regardless of poll interval.
- **Per-class freshness SLOs (transition-to-alert p95):** drop-prone + signal ≤ 3 min · drop-prone / no-signal ≤ 15 min · churning ≤ 15–30 min · stable ≤ 4–6 h. This is the concrete replacement for "real-time" in FR-001.

**Starting fast-lane set:** eBay recert stores (Browse API is its own heartbeat — the only natively-both source); ServerPartDeals + confirmed-Shopify specialists; WD/Seagate direct **pending an XHR-endpoint recon spike** (they are the best-evidenced drop-prone sources but have no _confirmed_ cheap signal yet — see `TODO.md`). The volatility profile per source is an **initial value for a self-correcting registry**, tuned from live transition data, not a fixed constant.

Option 1 was rejected: it misses drops on fast sources (defeating the tool's purpose) while flooding the hypertable with duplicate snapshots on slow ones. Option 3 was rejected: scheduling by volatility without a cheap grain still pays the full-pipeline + snapshot-write cost on every fast poll, so the fast lane it enables isn't actually cheap — the grain is what makes frequent polling affordable.

### Consequences

- **Good** — the price-history moat stays clean: one `offer_snapshot` per real transition, not per poll. Heartbeats absorb the "nothing changed" majority cheaply.
- **Good** — budget flows to where inventory actually moves; the anti-correlation finding is encoded structurally (intersection membership) rather than as a hopeful tier assignment.
- **Good** — freshness becomes a measurable, per-source SLO (p95 transition-to-alert), not an unfalsifiable "real-time" claim.
- **Bad (accepted)** — a genuine two-grain schema addition (heartbeat above snapshot) with its own retention and a transition-detection fingerprint to get right; a mis-tuned fingerprint can either miss a transition (too coarse) or thrash the pipeline (too sensitive). Mitigated by the `ambiguous` decision path (escalate to a full fetch when the cheap signal is inconclusive) and by treating profiles/thresholds as registry-tuned, not hard-coded.
- **Bad (accepted)** — two drop-prone flagships (WD/Seagate direct) cannot enter the fast lane until the XHR-recon spike finds a cheap endpoint; until then they run drop-prone/no-signal at the ≤ 15 min SLO.

### Confirmation

Implementation confirmation: a fast-lane source polled via heartbeat produces **no** `offer_snapshot` across a run of `unchanged` polls and **exactly one** on an injected OOS→in-stock transition; a `stable` source is never scheduled below its volatility need even when its tier ceiling is lower; per-source p95 transition-to-alert is observable and within the class SLO.

## More Information

- **Extends** [ADR 0010](adr-0010-canonical-data-model.md) (adds a grain to the identity ladder; does not alter the existing grains) and **feeds** [ADR 0012](adr-0012-orchestration-apscheduler.md) (the poller reads the volatility axis alongside the tier when computing the next-run interval). The acquisition **tier** whose ceiling bounds the effective cadence is the one set by [ADR 0014](adr-0014-scraping-runtime-escalation-stack.md).
- **Ratifies** the previously-_provisional_ spec positions: FR-001 (per-source freshness SLO), FR-002 (volatility axis / effective cadence), the `availability_heartbeat_observation` and "Volatility profile" glossary entries, and DR-008 (the heartbeat data requirement; renumbered from a duplicated "DR-006" in the spec's 2026-07-04 consistency pass — heartbeat retention/TTL itself remains open as OQ17). Their _provisional — candidate ADR_ markers are dropped in the same change and repointed here. FR-002's **tier cadence numbers** remain provisional under OQ9 (self-correcting tunables); only the **volatility axis + heartbeat mechanism** are ratified here.
- **Findings:** [polling-cadence reconciliation](../research/2026-07-04-polling-cadence-reconciliation.md); [per-source-polling-cadence-and-skip-policy](../research/per-source-polling-cadence-and-skip-policy.md).
- **Open follow-up:** the WD/Seagate XHR-endpoint recon spike (`TODO.md`) — turns the two best drop-prone sources fast-lane-able.
