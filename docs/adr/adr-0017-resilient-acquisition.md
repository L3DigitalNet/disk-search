---
schema_version: '1.1'
id: 'adr-0017-hw-radar-resilient-acquisition'
title: 'ADR 0017: Resilient acquisition — per-source isolation + circuit-break lifecycle'
description: 'Run every marketplace source as an independent scheduled unit writing to scraper_runs, with a source-state lifecycle (active ↔ backing-off → paused_pending_fix → active; → SKIP) driven by the failure-classification tree, a silent-degradation detector, and health alerting — so one source failing, being rate-limited, or changing its markup degrades gracefully without halting the others.'
doc_type: 'adr'
status: 'active'
created: '2026-07-04'
updated: '2026-07-04'
reviewed: null
owner: ''
consumer: 'mix'
tags:
  - 'adr'
  - 'reliability'
  - 'acquisition'
  - 'circuit-breaker'
  - 'observability'
aliases: []
related:
  - 'docs/adr/README.md'
  - 'docs/adr/adr-0012-orchestration-apscheduler.md'
  - 'docs/adr/adr-0014-scraping-runtime-escalation-stack.md'
  - 'docs/specs/hw-radar-master-spec.md'
  - 'docs/resolved-questions.md'
  - 'docs/research/2026-07-03-lightweight-observability-and-scraper-health-monitoring.md'
  - 'docs/research/orchestration-choice-for-a-single-vm-price-polling-service.md'
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

# ADR 0017: Resilient acquisition — per-source isolation + circuit-break lifecycle

MADR status: **accepted**.

## Context and Problem Statement

The tool polls ~20 heterogeneous marketplaces of widely varying reliability — some behind anti-bot walls, some prone to markup changes, all outside our control. A naïve poller that treats acquisition as one job has a **single point of failure**: one source timing out, getting rate-limited, or silently returning a challenge page can stall or poison the whole run. NFR-001 requires the opposite — **one marketplace failing must degrade gracefully without stopping the others**.

The pieces to make that true were settled across three other decisions but never tied into one lifecycle: the **failure-classification tree** (resolved-questions.md OQ8 / research #13), the **adaptive back-off ladder** (OQ9), and the **off-box heartbeat + health alerting** (OQ5). What was missing — and what makes this an ADR rather than plumbing — is the **source-state machine** those pieces drive: a persisted per-source lifecycle that decides, from a run's failure class, whether a source retries, backs off, gets circuit-broken for a human, or is permanently skipped. That lifecycle is a registry-schema commitment (a `state` column many subsystems read) and is costly to reverse once sources and history depend on it.

## Considered Options

- **Option 1 — Monolithic acquisition run** with best-effort try/except per source but no persisted per-source state or circuit-breaking.
- **Option 2 — Per-source isolation with a persisted state lifecycle driven by the failure-classification tree, plus silent-degradation detection and health alerting.** (chosen)
- **Option 3 — Per-source isolation but retry-only** (back-off without a `paused_pending_fix` circuit-break or a permanent SKIP terminal state).

## Decision Outcome

Chosen option: **Option 2.**

**Per-source failure isolation.** Each source runs as an independent scheduled unit (ADR-0012 poller) writing a `scraper_runs` record (status, counts, failure class) per run. One source being down, throttled, or markup-changed never halts the others — the blast radius of any failure is one source.

**Source-state lifecycle** (persisted registry state): `active ↔ backing-off → paused_pending_fix → active` (after a code fix + a passing recovery probe), and `→ SKIP` (permanent, human re-review). Transitions are driven by the **failure-classification tree** (evaluated in order): `transient` → `anti_bot` → `parser_rot` → `degradation` → `UNKNOWN`:

- **`transient`** (timeout / 5xx / DNS / TLS / 408) → retry via the OQ9 back-off ladder. A one-off transient causes no lasting state change; a source under **sustained** back-off (repeated transients / honored 429 cooldowns) sits in **`backing-off`** for the duration and returns to **`active`** automatically on the next clean poll — no human involved. This is the only entry into `backing-off`; the harder classes below skip it and go straight to `paused_pending_fix`.
- **`anti_bot`** (401/403/429/503, challenge markers, JSON endpoint returning `text/html`) → **circuit-break to `paused_pending_fix`**; daily recovery probe; operator alert. A soft-block whose cooldown repeatedly maxes the 24 h cap, after exhausting the tier ladder short of CAPTCHA/stealth/heavy-proxy, becomes a permanent **SKIP** (OQ9 skip policy; legal/ToS triggers force SKIP regardless).
- **`parser_rot`** (HTTP 200, authentic page, extractor/Pydantic fails) → **`paused_pending_fix`** (code fix + recovery probe), distinct from anti-bot because the remedy is our code, not back-off.
- **`degradation`** (validates, but the extraction tier worsened, or `required_fields_present_pct` dropped) → a first-class **silent-degradation** signal, alerted, not silently trusted — the failure mode where a source keeps returning 200s but the data is quietly rotting.
- **`UNKNOWN`** (the fall-through — nothing above matched) → treat conservatively: raise an operator alert and hold the source in **`paused_pending_fix`** pending manual classification, rather than silently trusting the run or discarding it. An `UNKNOWN` that a human later reclassifies is retag-and-resumed down the appropriate branch.

**Silent-degradation detection** = count-vs-rolling-average + tier-downgrade + empty-result assertions on every run, so a source returning stale/empty/challenge bodies is caught rather than trusted.

**Health alerting** is wired from `scraper_runs` to the off-box watchdog (off-site Uptime Kuma + Fleet Digest sweep, OQ5), so a stalled poller or a source stuck in `paused_pending_fix` reaches a human off the box.

Option 1 was rejected: try/except without persisted state loses the failure history needed to distinguish a blip from a dead source, and can't circuit-break or auto-recover. Option 3 was rejected: retry-only has no terminal states — a genuinely broken parser retries forever (noise, wasted budget) and a permanently hostile source is never quarantined, so a human is never told "this one needs code" vs "this one is gone."

### Consequences

- **Good** — blast radius of any source failure is exactly one source; the other ~19 keep polling.
- **Good** — the failure _class_ routes to the right remedy automatically: transient retries, anti-bot backs off then quarantines, parser-rot pages a human, degradation is caught before it poisons scores.
- **Good** — `paused_pending_fix` + daily recovery probe means a fixed or recovered source rejoins without manual re-enabling; SKIP quarantines the hopeless tail.
- **Bad (accepted)** — a per-source state machine plus degradation heuristics is real complexity, and the thresholds (what counts as "degraded", when to trip vs retry) are tuning-sensitive; a mis-set threshold either cries wolf or misses rot. Mitigated by sharing the already-tuned OQ8 classification tree and OQ9 back-off ladder rather than inventing new ones, and by treating thresholds as registry-tuned.

### Confirmation

Implementation confirmation (MS-5): a deliberately failed source moves to `paused_pending_fix` while the other sources keep polling; a deliberately broken parser trips a `parser_rot` alert within one scheduled cycle; a source returning empty/challenge bodies trips the silent-degradation detector rather than being trusted; a fixed source clears its recovery probe and returns to `active`.

## More Information

- **Composes** existing decisions rather than adding new mechanisms: the failure-classification tree from resolved-questions.md **OQ8**, the adaptive back-off ladder + skip policy from **OQ9**, the off-box heartbeat from **OQ5**, all scheduled by [ADR 0012](adr-0012-orchestration-apscheduler.md) and escalated through the [ADR 0014](adr-0014-scraping-runtime-escalation-stack.md) tier ladder. This ADR is the **state machine that ties them together**.
- **Ratifies** the previously-_provisional_ spec positions: NFR-001 (reliability), AW-006, and the §Source-lifecycle prose. Their _no-ADR / provisional_ markers are repointed here.
- **Record & findings:** resolved-questions.md **OQ10** (with **OQ5** / **OQ8** for the shared substrate); research [`2026-07-03-lightweight-observability-and-scraper-health-monitoring`](../research/2026-07-03-lightweight-observability-and-scraper-health-monitoring.md), [`orchestration-choice-for-a-single-vm-price-polling-service`](../research/orchestration-choice-for-a-single-vm-price-polling-service.md).
