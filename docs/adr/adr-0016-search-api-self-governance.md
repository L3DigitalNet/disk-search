---
schema_version: '1.1'
id: 'adr-0016-hw-radar-search-api-self-governance'
title: 'ADR 0016: Search-API self-governance — the ordered SearchBudgetGate'
description: 'Govern all outbound Serper/Brave/Tavily calls through one ordered admission gate — kill switch → persisted spend-cap circuit-breaker (reserve-then-call) → failing-provider breaker → per-provider token bucket — backed by a per-provider settings row, so a software bug or a failing provider fails safe before spending money rather than relying on provider dashboard caps. Ratifies the architecture; starting rate/spend numbers stay tunable.'
doc_type: 'adr'
status: 'active'
created: '2026-07-04'
updated: '2026-07-04'
reviewed: null
owner: ''
consumer: 'mix'
tags:
  - 'adr'
  - 'search-api'
  - 'cost-control'
  - 'rate-limiting'
  - 'circuit-breaker'
aliases: []
related:
  - 'docs/adr/README.md'
  - 'docs/adr/adr-0012-orchestration-apscheduler.md'
  - 'docs/specs/hw-radar-master-spec.md'
  - 'docs/resolved-questions.md'
  - 'docs/research/search-api-self-governance-and-user-configurable-limits.md'
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

# ADR 0016: Search-API self-governance — the ordered SearchBudgetGate

MADR status: **accepted**.

## Context and Problem Statement

The three search providers — Serper, Brave, Tavily — are **metered paid APIs** used for **discovery only** (IR-006). They are called from scheduled code, so a bug (a runaway loop, a mis-scheduled job, a retry storm) could burn real money before a human notices. Research [`search-api-self-governance-and-user-configurable-limits`](../research/search-api-self-governance-and-user-configurable-limits.md) established the load-bearing facts: **provider dashboard caps behave as alert-only in 2026** (they do not reliably hard-stop spend), and **Brave killed its free tier in Feb 2026** ($5/1,000 metered), so cost discipline must live **in our code**, not in the providers' consoles.

The owner (resolved-questions.md OQ7) asked three concrete questions: rate-limit our own calls per provider? add a circuit-breaker for chronically failing providers? expose in-app user settings for limits/aggressiveness? The answer to all three is yes — but the **order** in which those guards run is a real architectural decision (a token bucket that runs before a spend-cap check still lets a runaway loop spend up to the bucket rate all month), and the whole thing depends on **persisted** counters (an in-memory guard resets on every deploy/restart, exactly when a bug is most likely). That combination — an ordered admission architecture over a persisted counter schema — is why this is an ADR and not just a settings table.

## Considered Options

- **Option 1 — Rely on provider dashboard caps + an in-memory rate limiter.** No persisted spend ledger.
- **Option 2 — One ordered, persisted `SearchBudgetGate`: kill switch → spend cap (reserve-then-call) → failing-provider breaker → per-provider token bucket, with a per-provider settings row.** (chosen)
- **Option 3 — A single global monthly spend cap only**, no per-provider buckets or breakers.

## Decision Outcome

Chosen option: **Option 2.** Every outbound search call passes through one **ordered admission gate**; the order is the decision, because each stage is cheaper and more final than the next:

1. **Kill switch** — a manual per-provider (and global) `kill_switch`; if set, refuse immediately. Zero-cost, absolute, human-controlled.
2. **Spend-cap circuit-breaker (reserve-then-call)** — a **persisted PostgreSQL** `daily_spend_cap_usd` / `monthly_spend_cap_usd` counter checked **before** the call; the estimated cost is **reserved** first, the call made second, the actual reconciled third. On exhaustion it fails safe with `budget_exhausted` — the call is never made. This is the runaway-bug guard, and it is persisted precisely so a restart cannot reset it mid-spiral. The local counter is only ever _tightened_ against provider-reported usage, never loosened.
3. **Failing-provider breaker** — per-provider closed → open → half-open: 5 failures / 10 min opens it; a 5-min cooldown doubles to a 60-min cap; a single half-open trial probes recovery; `429` / `Retry-After` / auth-quota errors trip it early. Stops paying for a provider that is down or throttling us.
4. **Per-provider token bucket** — reusing the ADR-0012 poller's `rate`/`burst` vocabulary, the steady-state politeness/spend-rate limiter.

**Per-provider settings row** (one per provider): `enabled`, `rate_per_min`, `burst`, `daily_call_cap`, `daily_spend_cap_usd`, `monthly_spend_cap_usd`, `alert_threshold_pct` (default 80), `kill_switch`, breaker params, and an optional `aggressiveness` enum (conservative/standard/aggressive) that scales the numeric fields. This makes every guard **operator-tunable at runtime** without a deploy.

**Discovery-weighting** flows from the pricing facts, not the architecture: weight traffic toward **Serper** (~5× cheaper than post-free-tier Brave, ~8× than Tavily), keeping the rough envelope ≈ **$8–15/mo** inside the owner's $10–20 band. Search APIs are discovery/URL sources only — **eBay Browse + Feed are free official feeds and must not be re-polled via paid search** (and per OQ15, Amazon has no official feed, so it too is discovery-only, never a paid re-poll target).

Option 1 was rejected on the research's core finding — dashboard caps are alert-only and an in-memory limiter resets on restart, so neither actually hard-stops a runaway. Option 3 was rejected: a single global cap can't stop one misbehaving provider from starving the budget, gives no per-provider failure isolation, and offers no user-facing aggressiveness control.

**Scope of ratification.** This ADR ratifies the **architecture** — the ordered gate, the persisted reserve-then-call spend ledger, the per-provider settings schema, and the fail-safe semantics. The **starting numbers** (bucket rates, daily/monthly caps, the $8–15 envelope) remain **provisional and tunable** (resolved-questions.md OQ7): they are time-sensitive (2026 provider pricing was in flux — Brave storage-rights now Enterprise-only; Tavily acquired by Nebius) and must be re-verified before build. Freezing them in an ADR would be wrong; the settings row exists so they never need to be.

### Consequences

- **Good** — a software bug fails safe **before** spending: the persisted spend cap stops the call, and a restart cannot reset the ledger out from under it.
- **Good** — per-provider isolation: one provider being down or expensive can't drain the others' budget or halt discovery.
- **Good** — the owner's three OQ7 questions are answered by one composable mechanism, runtime-tunable via the settings row (aggressiveness included).
- **Bad (accepted)** — a persisted spend ledger with reserve-then-call reconciliation is more moving parts than an in-memory limiter, and cost estimates must be maintained per provider as pricing changes; wrong estimates skew the reservation. Mitigated by only ever tightening against provider-reported actuals and by the `alert_threshold_pct` early-warning.

### Confirmation

Implementation confirmation: with a daily cap exhausted, the next call returns `budget_exhausted` and **no HTTP request is made**; a provider forced to fail 5×/10 min opens its breaker and is skipped until the half-open probe; the spend ledger survives a process restart (persisted, not in-memory); flipping `kill_switch` halts that provider immediately.

## More Information

- **Consumes** the [ADR 0012](adr-0012-orchestration-apscheduler.md) token-bucket substrate (same `rate`/`burst` vocabulary; the search gate is the outbound-spend analogue of the poller's per-source/per-domain buckets).
- **Ratifies** the previously-_provisional_ spec positions: FR-011 (SearchBudgetGate), AW-008, ERR-006 (breaker), and the §325 stack-table row. Their _no-ADR / provisional_ status markers are repointed here; the **numeric** provisional markers (bucket values, spend envelope, 2026 pricing) intentionally **remain** under OQ7.
- **Record & findings:** resolved-questions.md **OQ7**; research [`search-api-self-governance-and-user-configurable-limits`](../research/search-api-self-governance-and-user-configurable-limits.md), [`tavily-brave-serper`](../research/tavily-brave-serper.md).
