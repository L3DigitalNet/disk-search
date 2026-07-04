---
schema_version: '1.1'
id: orchestration-engine-reconfirmation-2026
title: Orchestration Engine Reconfirmation (2026) — APScheduler vs Systemd Timers vs Task Queues
description: Reconfirms APScheduler 3.11.x in a single supervised long-running poller as the right scheduler for a ~20-source single-VM price-polling service given a shared token-bucket/circuit-breaker requirement, addresses APScheduler 4.0's alpha status, surveys 2025-2026 task-queue churn (RQ cron, Taskiq/Repid/FastStream), and reconciles the ADR 0006 "systemd timers for scrapes" contradiction.
doc_type: research
status: active
created: '2026-07-04'
updated: '2026-07-04'
reviewed: null
owner: chris
tags:
- orchestration
- scheduling
- apscheduler
- systemd
- rate-limiting
- circuit-breaker
- single-vm
- reconfirmation
aliases: []
related:
- orchestration-choice-for-a-single-vm-price-polling-service
- ../resolved-questions.md
- ../adr/adr-0006-cd-rsync-over-tailscale-ssh.md
source: []
confidence: high
visibility: public
license: null
---

# Orchestration engine reconfirmation (2026)

## Scope and relationship to the prior report

This report re-confirms, rather than replaces, [`orchestration-choice-for-a-single-vm-price-polling-service.md`](orchestration-choice-for-a-single-vm-price-polling-service.md) (2026-07-03). That report is still the primary reference for the *design* — token-bucket fields, retry/backoff policy, pipeline-stage sketch, and idempotency rules all stand unchanged. This report answers four narrower questions raised in [OQ12](../resolved-questions.md#oq12--orchestration-engine-apscheduler-vs-systemd-timers): whether the tool choice itself still holds a day later, what changed in the ecosystem, whether an in-process model is consistent with the project's design principles, and how to resolve the live wording contradiction against ADR 0006.

## Recommendation, restated with more force

**Use APScheduler 3.11.x inside one long-running, systemd-supervised poller process.** Nothing found in this pass weakens that call — if anything, two independent facts *reinforce* it that the original report didn't have to lean on: APScheduler 3.x's own documentation confirms it does not safely support multiple scheduler processes sharing one job store (so "one process" isn't just the simplest option, it's closer to the only correct one), and Scrapy's default reactor is now the asyncio-backed one, which means the scraper and an `AsyncIOScheduler` can share a single event loop without a Twisted/asyncio bridge.

The systemd-timers-only alternative remains the wrong fit for exactly the reason OQ12 identifies: your requirement is not "run this on a schedule," it's "run ~20 independently-cadenced things against a *shared*, live-updated admission budget (two-level token buckets) and a *shared* circuit-breaker registry, with jitter that itself depends on that shared state." Independent `systemd` timer units are independent processes with no memory between invocations; the moment you need cross-source, in-memory-fast admission decisions, you are re-inventing a scheduler's job queue and state store on top of the OS scheduler, badly. That was true on 2026-07-03 and nothing this pass found changes it.

## 1. Does APScheduler remain the best fit as of mid-2026?

Yes, and the field hasn't moved. Checked against systemd timers, RQ, Dramatiq, and Huey specifically (per OQ12's fork), plus the newer entrants that surfaced in 2025-2026 discourse (Taskiq, Repid, FastStream — covered in §2):

- **Systemd timers** — still the leaner floor for genuinely independent, stateless jobs, and still the wrong primitive once you need shared admission-control state across sources. Nothing changed here; this is a structural limitation of the primitive (each timer fires an independent unit/process with no shared memory), not a maturity gap that a new systemd release could close.
- **RQ** — gained real scheduling ergonomics since the prior report: RQ now ships a first-party `rq.cron` module (`cron.register(...)`, interval-based periodic jobs registered declaratively) alongside the `rq cron` CLI, which narrows the "RQ has no native scheduler" gap the 2026-07-03 report noted. It still requires a Redis (or Valkey) broker and a separate worker process — infrastructure this project doesn't otherwise need — and cron-registered jobs still execute as independent enqueued jobs rather than as a single process holding your live token-bucket/circuit-breaker registry in memory. The verdict is unchanged: viable if you later want queue/process isolation, not a reason to prefer it as the primary scheduler now.
- **Dramatiq** — unchanged posture. Current docs still explicitly defer scheduling to something else (APScheduler is still the documented pairing); Dramatiq 2.x continues to add retry/rate-limit middleware, not scheduling.
- **Huey** — no material change; still a lightweight Redis/SQLite-backed queue with its own periodic-task decorator, still adds a broker dependency for a capability APScheduler already provides in-process.

**New information not in the prior report:** APScheduler's own tracking issue and `django-apscheduler`'s docs both state that **safely sharing a persistent job store across multiple scheduler instances is a 4.0 feature, not something 3.x supports today.** The 2026-07-03 report already recommended "keep one scheduler process" as a caution; this pass found the harder fact behind that caution — in 3.x it is not a best practice you can optionally relax, it is close to a hard constraint. This matters directly for OQ12's shared-state requirement: whatever holds the shared token buckets and circuit-breaker registry, it must live in **one process's memory** (optionally checkpointed to PostgreSQL for restart survival), not be sharded across independently-scheduled units. That is exactly the architecture the prior report already specified; this pass just found a firmer citation for why it's not optional.

## 2. Material 2025-2026 ecosystem changes

| Tool | Change since 2026-07-03 | Effect on recommendation |
|---|---|---|
| **APScheduler** | 3.11.3 released 2026-06-28 (six days before this report) — active maintenance continues on the 3.x branch even while 4.0 development proceeds. 4.0 is at pre-release `4.0.0a6` (per the Debian package tracker); GitHub/PyPI still label the entire 4.0 line "do NOT use this release in production." | Confirms **3.11.x, not 4.x**, exactly as the prior report concluded. See §3 for what to watch for when 4.0 eventually stabilizes. |
| **RQ** | Gained `rq.cron` (declarative periodic-job registration) since the prior report's citation of RQ 2.8 (unique jobs) / 2.10 (webhooks). | Narrows RQ's scheduling gap vs. Celery/APScheduler, but doesn't remove the broker dependency or solve in-process shared state. Still a "future upgrade if you want queue semantics," not a scheduler swap. |
| **Celery** | 5.6.3 (early 2026) adds Pydantic task-argument support; unrelated to scheduling fitness here. | No change — still over-engineered at this scale; the project doesn't need a broker/worker/beat stack for ~20 periodic fetches. |
| **New asyncio-native task-queue entrants (Taskiq, Repid, FastStream)** | Genuinely new since the prior report — 2025-2026 blog/benchmark activity (e.g. a widely-shared 2026-07 comparison) positions these as Celery/Dramatiq alternatives optimized for **high-concurrency, I/O-bound distributed workloads** with async-native workers. | **Do not adopt.** They solve a different problem (maximizing throughput across many concurrent async workers behind a broker — NATS/Redis/RabbitMQ) than this project has (politely-paced polling of ~20 sources with per-domain concurrency caps of 1-2). Bringing in a broker to run fewer than 20 jobs a day per source is disproportionate regardless of how fast the broker is. Noted here only so the OQ record shows they were considered and explicitly ruled out, not overlooked. |
| **Scrapy / asyncio reactor** | Current Scrapy docs specify `TWISTED_REACTOR = 'twisted.internet.asyncioreactor.AsyncioSelectorReactor'` as the **default** value (a change consolidated in recent Scrapy releases). | Directly relevant and new: it means Scrapy's crawl I/O and an `AsyncIOScheduler`-driven admission/circuit-breaker layer can run on the **same asyncio event loop in the same process**, rather than needing a Twisted-reactor-to-asyncio bridge or a separate thread. This makes the "one long-running process" model cheaper to implement than it would have been under Scrapy's historical Twisted-only reactor. |
| **Redis CVEs (2025)** | Two high-severity 2025 Redis CVEs are worth flagging precisely because Redis is the dependency every queue-based alternative (RQ, Dramatiq, Celery, Huey, Taskiq, Repid) would add: **CVE-2025-49844** ("RediShell," critical RCE, patched) and **CVE-2025-21605** (unauthenticated DoS via unbounded output buffers). Both are patched in current Redis releases and require either public exposure or authenticated access to exploit — not a reason to panic if you already run patched Redis elsewhere — but they are a concrete illustration of the "each additional piece of infrastructure is additional attack surface and patch burden" argument the prior report made in the abstract. | Reinforces, doesn't newly establish, the "don't add a broker you don't need" conclusion. If a future phase adds Redis for caching or another purpose, track its CVE feed; don't add it *just* to get scheduling you already have via APScheduler. |
| **No CVEs found against APScheduler itself.** | — | In-process, no-network-listener scheduler continues to carry a smaller security surface than any broker-based alternative. |

## 3. Is an in-process APScheduler model consistent with "Moderate Aggressive Usage" + Reliability?

Yes — more so than the alternatives, not despite them. Re-reading the spec's [General Design Principles](../specs/hw-radar-master-spec.md#1-purpose--background-light) against the architecture:

- **Moderate Aggressive Usage** ("poll as aggressively as each source tolerates, moderate only near a red-line," per the OQ9 owner posture) requires a mechanism that can **raise and lower admission rates continuously and cheaply**, per source and per domain, in response to live signals (429/503, latency, soft-block challenges). That is inherently a **shared, fast, in-memory state** problem — the whole point is that a `Retry-After` on one source's request should immediately affect the *next* admission check for that source, not wait for a separately-scheduled unit to next wake up and re-read state from disk. An in-process scheduler holding the token buckets and circuit-breaker registry in memory (checkpointed to PostgreSQL for crash recovery, per the prior report's design) is the natural fit; independent systemd-timer units re-reading and re-writing shared state from Postgres on every tick is a slower, lock-contended emulation of the same thing.
- **Reliability** (graceful degradation, per-source failure isolation, circuit-breaking) is likewise a shared-registry problem: the circuit breaker's `paused_pending_fix` state, per OQ10, has to be visible to whatever decides "is this source eligible right now," which is the same admission layer. Splitting eligibility (scheduling) from admission (rate/circuit state) across process boundaries — which is what independent timer units would force — reintroduces exactly the coordination problem APScheduler-in-process avoids.
- **Engineered to Needs** (no speculative complexity) argues *against* a broker-based queue: none of RQ/Dramatiq/Celery/Taskiq/Repid solve a problem this project actually has (distributed workers, multi-machine scale-out, high-throughput concurrent execution). They would be justified if the project needed to fan work out across multiple machines or workers; a single Debian LXC container polling ~20 sources does not.

The one legitimate tension is that an in-process model puts scheduling logic, admission control, and the executing coroutine/thread pool in the same failure domain: a bug in the scheduler can, in principle, affect job execution. The prior report already designed around this with `max_instances=1`, `coalesce=True`, per-source `misfire_grace_time`, and hard fetch-stage timeouts, which bound the blast radius without requiring a second process. That mitigation stands.

## 4. Reconciling the ADR 0006 "systemd timers for scrapes" contradiction

**The contradiction is real and is a wording problem, not a design problem.** [ADR 0006](../adr/adr-0006-cd-rsync-over-tailscale-ssh.md) states: *"periodic scrapes run under **systemd timers**, not an in-process scheduler,"* citing independent journal logging, independent `Restart=`/resource limits per run, and fault isolation (a timer-triggered oneshot unit can't silently die inside a long-running worker the way an in-process scheduler/thread can). Those are legitimate operational advantages of timers — for **stateless, independent** jobs. They were written (2026-07-03, in the CD/deployment research) before the orchestration research had established that this project's scrape jobs are **not** stateless or independent of each other: they share admission budgets and circuit-breaker state by design.

**Recommended reconciliation, to fold into ADR 0006 (or a superseding ADR-0012):**

- **Systemd still supervises** — but it supervises **one long-running poller service** (`Type=simple` or similar, `Restart=on-failure`, resource limits, `ProtectSystem=strict`, the same hardening ADR 0006 already specifies for the worker unit), not one timer per scrape. This preserves ADR 0006's actual goals — process isolation from the web unit, independent resource limits, `Restart=` semantics, systemd-native logging via the journal — while giving up only the *per-run* process boundary, which was never load-bearing for this project (a single flaky fetch failing inside the poller is exactly what the prior report's fetch-stage timeouts + `max_instances=1` + circuit-breaker already isolate, without needing a fresh OS process per attempt).
- **Amend the specific sentence.** Change ADR 0006's "periodic scrapes run under systemd timers, not an in-process scheduler" to something like: *"the poller runs as a single long-running systemd-supervised service using an in-process scheduler (APScheduler 3.11.x, `AsyncIOScheduler`) that owns per-source cadence, jitter, two-level token-bucket admission, and shared circuit-breaker state; systemd supervises the **process** (restart-on-failure, resource limits, journal logging), it does not schedule individual scrapes."* Keep systemd timers as the primitive for anything that genuinely *is* independent and stateless — e.g., a nightly VACUUM/maintenance job, a backup-verification check — where ADR 0006's original reasoning (isolated failure domain, independent `Restart=`) still applies cleanly.
- **This does not reopen ADR 0006's actual decision** (rsync-over-Tailscale-SSH deployment mechanics, OpenBao secret injection, unit hardening). Only the one scheduling-mechanism sentence needs to change; everything else in that ADR is orthogonal to the scheduler question.

## Sources

- APScheduler PyPI project page and release files (3.11.3, uploaded 2026-06-28): https://pypi.org/project/APScheduler/
- APScheduler 4.0.0a1 pre-release page (production-use warning): https://pypi.org/project/APScheduler/4.0.0a1/
- APScheduler 4.0 progress-tracking issue (persistent-store-sharing-across-schedulers listed as a v4 goal): https://github.com/agronholm/apscheduler/issues/465
- `django-apscheduler` PyPI description (confirms shared job store across schedulers is a planned 4.0 feature, not present in 3.x): https://pypi.org/project/django-apscheduler/
- Debian package tracker, `apscheduler` (current upstream pre-release version 4.0.0a6): https://tracker.debian.org/apscheduler
- APScheduler master migration docs (4.0 is "a partial rewrite... since the 3.x series"): https://apscheduler.readthedocs.io/en/master/migration.html
- RQ GitHub repository and CHANGES.md (native `rq.cron` module, `rq cron` CLI): https://github.com/rq/rq, https://github.com/rq/rq/blob/master/CHANGES.md
- RQ documentation (webhooks, worker `--maintenance-interval`): https://python-rq.org/docs/
- "Choosing a Python task queue library in 2026" (Celery vs Dramatiq vs FastStream vs Taskiq vs Repid), r/Python, and the underlying benchmark writeup: https://www.reddit.com/r/Python/comments/1u775lo/, https://aleksul.space/posts/choosing-python-task-queue-library/
- Taskiq project (asyncio-native Celery-alternative, broker-based): https://taskiq-python.github.io/, https://github.com/taskiq-python/taskiq
- Scrapy asyncio documentation (`AsyncioSelectorReactor` as the default `TWISTED_REACTOR`): https://docs.scrapy.org/en/latest/topics/asyncio.html
- Redis security advisories: CVE-2025-49844 ("RediShell") https://redis.io/blog/security-advisory-cve-2025-49844/ ; CVE-2025-21605 https://redis.io/blog/security-advisory-cve-2025-21605/
- Prior report: [`orchestration-choice-for-a-single-vm-price-polling-service.md`](orchestration-choice-for-a-single-vm-price-polling-service.md)
- [`ADR 0006`](../adr/adr-0006-cd-rsync-over-tailscale-ssh.md) (the "systemd timers for scrapes" line under reconciliation)
- [`OQ12`](../resolved-questions.md#oq12--orchestration-engine-apscheduler-vs-systemd-timers)
