# Orchestration choice for a single-VM price-polling service

## Recommended default

For this workload, the best default is **APScheduler 3.11.x running in its own dedicated poller service**, supervised by systemd, with PostgreSQL holding your run state, source state, observations, and alert dedupe keys. APScheduler gives you cron/interval/date triggers, async integration via `AsyncIOScheduler`, per-job concurrency controls, misfire handling, coalescing, persistent job stores, and scheduler events without requiring a broker or a separate orchestration control plane. As of July 2026, the latest stable APScheduler release is 3.11.3; the 4.0 line is still a partial rewrite with migration caveats from 3.x, so the version-sensitive advice here is: **use 3.11.x now, not 4.x alpha/master APIs, for a production single-VM service**.

The reason the heavier options are overkill here is simple: **they add infrastructure to solve problems you do not have yet**. Celery introduces a broker-and-worker stack; Prefect adds a self-hosted server, database-backed control plane, UI, and workers; Dagster adds a daemon and webserver; Airflow adds a metadata DB, scheduler, DAG processor, and webserver. Those are worthwhile when you need team-scale orchestration, lineage, rich UI-driven operations, or distributed execution, but they are disproportionate for “about 20 sources, one Debian VM, one maintainer.”

If you wanted the absolute leanest possible option, **cron + scripts can work**, but only if your schedules are mostly static and you are willing to hand-build dynamic backoff, health state, and observability. On Debian specifically, if you go down the “plain OS scheduler” path, systemd timers are usually a better primitive than classic cron because they support `RandomizedDelaySec=` and `Persistent=` directly.

## What the realistic options look like

At this scale, there are really three tiers: **OS scheduler**, **in-process scheduler**, and **queue/control-plane systems**. The table below compares the options you named against the actual needs of a polite polling service.

| Option | Setup complexity | Per-source scheduling flexibility | Retry and backoff | Observability | Operational weight on one VM | Verdict |
|---|---|---|---|---|---|---|
| **Cron + scripts** | Lowest | Static time expressions only; cron checks jobs on the current minute, so it is coarse and not stateful by itself | Entirely hand-rolled in scripts | Mostly whatever logs, mail output, or custom tables you add | Lowest | Works, but gets awkward fast once schedules, cooldowns, and source health become data-driven. If you stay here, prefer **systemd timers** over plain cron on Debian for jitter and persistence. |
| **APScheduler 3.11.x** | Low | Strong fit: cron, interval, and date triggers; async scheduler support; `CronTrigger` jitter; runtime `pause_job`, `resume_job`, and `reschedule_job` | No opinionated retry framework, but very good execution controls: `max_instances`, `misfire_grace_time`, `coalesce`, listeners, persistent job stores | Logs and scheduler events, but no built-in ops UI | Low | **Best fit.** You get scheduling sophistication without a broker. The main caution is to keep **one scheduler process** in 3.x because job stores must not be shared between schedulers. |
| **Celery + beat + Redis or RabbitMQ** | High | Strong: `celery beat` schedules periodic tasks, and Celery supports task routing and queues | Strong built-ins: `autoretry_for`, `retry_backoff`, `retry_backoff_max`, `retry_jitter`, task `rate_limit`; Flower adds real-time monitoring | Good when paired with Flower | High | Technically capable, but **over-engineered here** because you would be adding a broker, workers, beat, and likely a result backend primarily to schedule ~20 periodic fetches. |
| **RQ** | Medium | Redis only; `enqueue_at`, `enqueue_in`, repeats, and scheduler support via `rq worker --with-scheduler` | Solid light-duty features: retries, exception handlers, registries, job results, webhooks, unique jobs | Simple dashboard available, plus registries and result history | Medium | The lightest “real queue” option. Viable if you decide later that you want queue semantics and process isolation, but still more moving parts than you need for the default design. |
| **Dramatiq** | Medium | Important caveat: Dramatiq does **not** try to be your scheduler; its docs explicitly recommend APScheduler for scheduling | Strong built-ins: retries middleware with exponential backoff, callbacks, result backends, and distributed rate limiters | Better than bare scripts, but no first-party “Flower-like” operations UI in core docs | Medium | A plausible future queue layer, especially if you want strong retry/rate-limit primitives, but **not a scheduler replacement**. Also note its default worker model is aggressive for polite scraping and should be tuned down. |
| **Prefect 3** | High | Strong scheduling and task model; deployments, schedules, retries, and built-in concurrency/rate limits | Strong | Rich UI and state tracking | High | **Over-engineered here.** Prefect brings a real orchestration control plane; useful, but more stack than this service needs on one VM. Also versioning matters in self-hosted mode because client/server compatibility matters. |
| **Dagster** | High | Strong schedules/sensors plus concurrency pools and run retries | Strong | Rich UI, lineage, daemon status, run monitoring | High | **Over-engineered here.** Dagster shines for asset-centric data platforms and team observability, not a single-maintainer polling daemon. |
| **Airflow 3.2.2** | Very high | Very strong DAG scheduler, pools, retries, priorities, UI | Strong | Rich UI and mature ops model | Very high | **Most over-engineered** for this job. Airflow’s architecture is justified when you need a workflow platform; it is a poor fit for a 20-source poller on one box. |

The practical takeaway is that **APScheduler is the only option in your list that is both powerful enough and still proportionate**. Cron is simpler, but too static once per-source backoff and health become first-class. RQ and Dramatiq are the lightest queue-first systems if you later want process isolation. Celery, Prefect, Dagster, and Airflow all solve real problems, but not the ones that dominate this service today.

## Per-source scheduling, staggering, and rate limits

The clean model is to separate **eligibility** from **admission**. Eligibility answers “when should source X be considered for polling again?” Admission answers “even if source X is due, may I actually start a request now without violating per-source or per-domain limits?” That split is what keeps the system polite and predictable under drift, retries, and outages. The scheduling half maps naturally to APScheduler jobs; the admission half is your own lightweight rate-limit layer. APScheduler’s 3.x API lets you reschedule, pause, and resume jobs programmatically, which makes this model straightforward on one VM.

A good per-source policy record should include at least these fields:

| Field | Purpose |
|---|---|
| `source_id` | Stable identifier for the source |
| `cadence` | Base desired poll interval, such as 1 hour or 1 day |
| `stable_offset_s` | Deterministic offset so every hourly source does **not** wake up on the hour |
| `jitter_s` | Small randomization window applied to each next run |
| `domain_key` | Domain- or API-family key for shared limits |
| `source_rate` and `source_burst` | Per-source token bucket rate and burst |
| `domain_rate` and `domain_burst` | Shared token bucket for all sources hitting the same site/API |
| `max_in_flight` | Per-source concurrency cap, usually 1 |
| `domain_max_in_flight` | Per-domain concurrency cap, often 1–2 for scrapers |
| `timeout_s` | Hard timeout per fetch attempt |
| `disabled_until` | Temporary cooldown or circuit-breaker timestamp |
| `retry_profile` | Retryable errors, cap, and backoff parameters |
| `respect_retry_after` | Whether to honor `Retry-After` on 429/503 responses |
| `coalesce` / `misfire_grace_time` | How to behave after downtime or overrun |

The single most important staggering rule is: **never let cadence equal phase**. If ten hourly jobs all use “top of the hour,” you create a self-inflicted thundering herd. Give each source a stable phase offset derived from a hash of the source ID, then add a small per-run jitter window. Jitter is a standard technique for preventing retry and schedule collisions, and systemd exposes essentially the same idea through `RandomizedDelaySec=` for timers.

For rate limits, use **two levels of token bucket**. The first bucket is per source, matching source-specific quotas like “60 calls per hour.” The second bucket is per domain or API family, matching politeness constraints like “never run more than 2 concurrent requests against retailer.example and never average more than 1 request every 5 seconds across all source variants that hit it.” Token bucket is a good fit because it models both sustained rate and allowed burst, and adaptive client-side throttling systems use the same family of ideas when they need to slow down under throttling pressure.

You should also enforce **per-domain concurrency caps** separately from rate. Rate answers “how often may I start”; concurrency answers “how many may run at once.” In practice, that usually means an `asyncio.Semaphore` or equivalent keyed by `domain_key`, with most scraper domains set to 1 and friendlier APIs set to 2 or slightly higher. This is not redundant with token buckets. A site can tolerate one request every few seconds and still dislike two simultaneous browser sessions. That distinction is exactly why systems like Prefect, Dagster, Airflow, Celery, and Dramatiq all expose some notion of concurrency or rate limiting in addition to scheduling.

When a source returns **429**, **503**, or a vendor-specific throttling signal, move from the steady-state cadence to an **adaptive cooldown**. If `Retry-After` is present, honor it. If not, compute the next eligible time with capped exponential backoff plus jitter. For sources that repeatedly throttle, reduce the effective refill rate of the source token bucket for some cooling period instead of only retrying faster and faster into the wall. That is the same basic lesson behind AWS’s distinction between standard retries and adaptive retries with client-side rate limiting.

For APScheduler specifically, most source jobs should run with **`max_instances=1`**, **`coalesce=True`**, and a source-specific **`misfire_grace_time`**. That combination prevents backlogs from turning into replay storms after an outage or a long-running scrape. If the VM is down for six hours, you almost never want six sequential catch-up polls of the same retailer; you want one fresh poll now. APScheduler’s misfire and coalescing behavior exists precisely to control that.

## Retry, backoff, and failure isolation

The scheduler should **not** be the pipeline. It should only decide what becomes runnable and when. Each source run should then execute as an isolated unit with its own timeout, retry budget, and health state, so one broken scraper cannot stall the rest of the service. APScheduler is well-suited to this because it can sit above a small execution layer without forcing you into a broker model.

A good retry policy starts by classifying failures. **Retryable** failures include connect timeouts, read timeouts, transient DNS/network failures, HTTP 5xx, and HTTP 429 when the source says “slow down.” **Non-retryable** failures include authentication problems, permanent authorization blocks, parser breakage due to schema/layout drift, and policy failures where the right behavior is to stop, not push harder. Official guidance from both AWS and Google is broadly consistent here: retry transient failures, use capped exponential backoff with jitter, and do not let retries become an amplifier during outages.

For this service, a strong default is a **two-layer retry design**. Use a very small **in-run retry budget** inside `fetch` itself for obvious transient network issues, then, if the run still fails, let the **next scheduled poll time** absorb the longer recovery curve by moving `next_run_at` out into a cooldown window. That avoids both extremes: no retries at all, and giant retry storms that crowd out other sources. In other words, do a little immediate healing, then fall back to schedule-level healing.

Failure isolation also means **hard time limits**. Fetchers, especially browser-backed scrapers, should run with explicit deadlines so they cannot pin your worker pool forever. For APScheduler jobs, combine job-level concurrency limits with fetch-stage timeouts. For queue-based alternatives, RQ exposes job timeouts and failed-job registries; Dramatiq exposes retries middleware, time limits via middleware, and `on_retry_exhausted`; Celery exposes retries and task rate limits. Those are useful reference points even if you keep the default APScheduler design.

For persistent failures, you do not need a full message-broker DLQ to get the operational benefit of one. On a single VM, a **PostgreSQL dead-letter table** is usually better. When a source exceeds a policy like “five consecutive terminal failures” or “unhealthy for six hours,” write a dead-letter record with the source ID, failure class, last exception, parser or selector version, last successful run, and the frozen input artifact if one exists. Then raise one alert when the source enters unhealthy state and a second when it recovers. This produces the important behavior of a DLQ—durable triage and alerting—without adding broker infrastructure. The same operational concept appears in queue systems through constructs like RQ’s `FailedJobRegistry` or Dramatiq’s `on_retry_exhausted`.

A simple but effective circuit-breaker rule is: if a source is failing with the **same terminal class** repeatedly—say, repeated parser mismatch after a site redesign—stop scheduling it normally and mark it **paused_pending_fix**. That is better than continuing to spend retries and log volume on a source that will not heal until you change code. APScheduler’s runtime pause/resume APIs make that easy.

## Pipeline stages, testability, and partial reruns

The pipeline should be structured so that each stage has **one job, one input contract, and one output contract**. That gives you deterministic tests, replayability, and the ability to rerun downstream stages without touching the source again.

A good sketch looks like this:

```text
schedule source_run
    -> fetch
        -> raw_payload
            -> parse
                -> source_items
                    -> normalize
                        -> canonical_offers
                            -> resolve_entity
                                -> matched_offers
                                    -> score
                                        -> scored_offers
                                            -> persist
                                                -> observation rows
                                                    -> alert_decision
                                                        -> alert_dispatch
```

In practical terms, that means:

- **Fetch** returns raw bytes/text plus metadata such as status code, headers, URL, timing, and content hash.
- **Parse** turns raw payloads into source-native typed records.
- **Normalize** maps source-native records into your canonical offer model.
- **Resolve entity** maps a normalized offer to a tracked drive SKU or canonical item identity.
- **Score** is a pure function that ranks attractiveness and computes match/price-drop eligibility.
- **Persist** is the first durable side-effect boundary.
- **Alert decision** computes the desired alerts from persisted observations and prior alert history.
- **Alert dispatch** is the last, smallest side-effect boundary.

That structure matters because the expensive and flaky parts are not evenly distributed. Sites break in **fetch** and **parse**. Your business rules change in **normalize**, **resolve**, and **score**. Duplicate-alert bugs happen in **persist** and **alert decision**. If you keep those boundaries explicit, your tests stop being giant end-to-end scrapes and become short, sharp unit tests with stored fixtures.

For example, the stage-by-stage testing story becomes straightforward:

| Stage | Best test style | Why it matters |
|---|---|---|
| Fetch | integration tests against controlled endpoints or recorded fixtures | proves timeouts, headers, cookies, proxies, and anti-bot handling |
| Parse | fixture-based unit tests on saved raw payloads | catches site layout drift cheaply |
| Normalize | pure unit tests on source-native records | locks down canonical field mappings |
| Resolve entity | unit tests plus curated alias tables | prevents false joins and missed joins |
| Score | pure unit/property tests | lets you evolve ranking logic safely |
| Persist | DB tests around upserts and constraints | guarantees idempotency under retries |
| Alert decision | fixture-based decision tests with prior-history state | stops duplicate alerts and missed alerts |

The key to **partial reruns** is to persist artifacts or references at meaningful boundaries. At minimum, persist the raw payload content hash and storage pointer, the parsed record set version, the normalized offer set version, and the final persisted observation IDs. Then you can rerun from the right point:

- rerun **parse onward** when a site parser changes,
- rerun **normalize/resolve/score onward** when canonical rules change,
- rerun **alert decision only** when notification rules change.

This is one of the main benefits that heavier orchestrators package into task/flow/op/asset abstractions. You can capture most of that value in a much smaller design by making stage boundaries first-class in your own service. Prefect explicitly models retryable/cacheable tasks and state tracking; Airflow models tasks inside DAGs; Dagster models assets, jobs, schedules, and re-executions. Your service does not need their control planes to benefit from the same underlying decomposition.

## Idempotency and deduplication

Because retries are unavoidable, the service must assume every stage can be run **more than once**. The design target is not “exactly once” execution; it is **idempotent re-execution**. Official guidance on retries is consistent on this point: retries are safe only when the target operation is idempotent or conditionally idempotent.

For this pipeline, there are **two different dedupe problems**, and they should be handled separately:

| Problem | What duplicates look like | Correct defense |
|---|---|---|
| **Observation dedupe** | rerunning the same source poll writes the same offer/price/availability twice | natural keys, content hashes, and `UPSERT` constraints |
| **Alert dedupe** | the same price drop or same match sends multiple notifications | durable alert keys and cooldown / transition logic |

A concrete PostgreSQL design usually looks like this:

| Table | Suggested idempotency key |
|---|---|
| `source_run` | `UNIQUE (source_id, scheduled_for)` |
| `fetch_attempt` | `UNIQUE (source_run_id, attempt_no)` |
| `raw_payload` | `UNIQUE (source_id, content_hash)` or storage pointer keyed by hash |
| `normalized_offer` | deterministic hash of source item identity plus normalized content version |
| `observation` | `UNIQUE (source_id, canonical_item_id, seller_key, observed_at_bucket, price_cents, availability_state)` **or** a content fingerprint if you want exact payload dedupe |
| `alert_event` | `UNIQUE (rule_id, observation_id)` for one-shot alerts, or `UNIQUE (rule_id, canonical_item_id, transition_id)` for transition-based alerts |

The alert side is where many systems get subtly wrong. **Do not dedupe alerts by time alone.** Deduplicate by the **state transition** that justified the alert. A “price dropped below $X” alert should fire when the item crosses from “not below threshold” to “below threshold,” not every time a later rerun observes the already-below-threshold state. Likewise, “in stock” should be keyed to a transition from unavailable to available. That preserves correctness under retries, manual reruns, and parser repairs.

For entity resolution, make the canonical identity stable and explicit. For hard drives, that usually means some combination of manufacturer, model family, capacity, interface, form factor, condition, sometimes spindle speed or NAND class, and a source-specific alias table for SKUs and retailer listing IDs. The output of **resolve entity** should be a canonical item ID plus a confidence or decision record, not a best-effort join that disappears into the next stage. That keeps false merges from poisoning price history.

At the scheduling layer, if you later decide to move to RQ, note that **RQ 2.8 added unique jobs** and **RQ 2.10 added webhooks**, both of which are useful for enqueue dedupe and lightweight heartbeat/terminal-state notifications. Those are version-sensitive features worth knowing about, but they should be seen as optional future upgrades, not reasons to abandon the simpler APScheduler design now.

The simplest durable rule of thumb is this: **every stage that can be retried must either be a pure transform or write through a uniqueness constraint**. If a stage cannot satisfy one of those two conditions, it is the place where duplicate observations or duplicate alerts will eventually appear.