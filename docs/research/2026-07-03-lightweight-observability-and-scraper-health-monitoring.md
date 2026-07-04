---
schema_version: '1.0'
id: 2026-07-03-lightweight-observability-and-scraper-health-monitoring
title: Lightweight Self-Hosted Observability, Uptime Monitoring, and Scraper-Rot Detection at Single-VM Scale (2026)
description: Research on minimal self-hosted monitoring, error tracking, metrics, scraper-health checks, and scraper testing for a single-maintainer Python app + scraper stack on one Debian VM.
doc_type: research
status: active
created: '2026-07-03'
updated: '2026-07-03'
reviewed: '2026-07-03'
owner: chris
tags:
- monitoring
- observability
- self-hosted
- web-scraping
- testing
- uptime-kuma
- glitchtip
- sentry
aliases:
- scraper health monitoring
- dead man's switch monitoring
- uptime kuma vs gatus
- glitchtip vs sentry
related: []
source:
- https://healthchecks.io/docs/monitoring_cron_jobs
- https://gatus.io/docs/monitoring-push-based
- https://glitchtip.com/documentation/install/
- https://docs.sentry.io/product/monitors-and-alerts/monitors/crons
- https://docs.victoriametrics.com/victoriametrics/faq
confidence: high
visibility: private
license: null
---

# Lightweight Self-Hosted Observability, Uptime Monitoring, and Scraper-Rot Detection at Single-VM Scale (2026)

## Context

Single Debian 13 VM, single maintainer, FastAPI/Django app + ~20 e-commerce scraper sources on a scheduler, PostgreSQL, behind NGINX. Two needs: (A) operator self-monitoring (app/VM/DB/queue/job/email health) and (B) scraper-rot detection (silent breakage of a scraping source). Goal: avoid a full Prometheus+Grafana+Alertmanager stack unless clearly justified.

## Recommended minimal stack

| Layer | Recommendation | Why |
| --- | --- | --- |
| Uptime/health (A) | **Uptime Kuma** (self-hosted) for HTTP/TCP/DB checks + its **Push monitor** type for dead-man's-switch on scheduled jobs, *plus* **healthchecks.io free hosted tier** (20 checks) as an offsite second heartbeat | Kuma gives a friendly single-maintainer UI; a hosted heartbeat survives the case where the whole VM (including Kuma itself) is down |
| Error tracking (B/A) | **GlitchTip**, self-hosted (Docker Compose, Postgres+Redis, 256 MB-1 GB RAM) | Sentry-SDK-compatible, orders of magnitude lighter than self-hosted Sentry; or use Sentry SaaS free Developer tier (5k events/mo, 1 user) if zero ops burden matters more than self-hosting |
| Metrics | **None as a new service** — track scraper/job health as rows in existing Postgres (`scraper_runs` table: source, run_at, item_count, success bool). Add VictoriaMetrics single-node only if you later need cross-metric historical trend graphs | Prometheus+Grafana+Alertmanager is 3-4 extra always-on services to operate for one maintainer; VictoriaMetrics single-node is the lightest fallback if metrics become genuinely necessary |
| Scraper-rot detection | Pydantic v2 schema validation per record + per-source `last_success_at`/consecutive-failure counters + count-vs-rolling-average assertion + canary "known-value" pages + prefer JSON-LD over CSS selectors where available | Catches both "0 results" (anti-bot/outage) and "wrong value in a technically-valid field" (selector drift) — the two failure modes tools alone won't distinguish |
| Scraper testing | **vcrpy** cassettes per source + **syrupy** snapshot assertions on parsed output + a scheduled (not just CI) live contract test against JSON-LD endpoints | vcrpy replays real recorded HTML/JSON so tests catch parser regressions without live requests; the scheduled live JSON-LD check is a canary for site-side schema drift that CI alone cannot see |
| Netdata | Optional, run ad hoc rather than always-on | Real-time deep-dive tool; RAM footprint (100MB-2GB+ depending on plugins) is disproportionate to "is disk full" for a single VM |

## Why the heavier stack is overkill here

Prometheus + Grafana + Alertmanager means running and keeping alive 3+ additional long-lived services (Prometheus server, an exporter, Alertmanager, Grafana) plus writing and maintaining PromQL alert rules — for a workload whose actual monitoring surface is small: one app process, one Postgres instance, ~20 scheduled jobs, and disk usage. Every question this research was asked to answer ("is the app up," "did the job run," "is disk full," "did a source go silent") is answerable with a boolean/counter/timestamp per check, not a general-purpose time-series query engine. VictoriaMetrics single-node is the correct *lighter* substitute *if and when* metrics become genuinely necessary (10x+ lower RAM/storage than Prometheus, single static binary, Prometheus-scrape-compatible) [community] — but for this workload, storing run outcomes as Postgres rows next to the data they already write is simpler and requires zero new operational surface.

## Summary

| Angle | Sources | Strongest finding |
| --- | --- | --- |
| Official Docs | 5 | healthchecks.io, GlitchTip, Sentry Crons, Gatus, and VictoriaMetrics docs all confirm the dead-man's-switch/ping model and resource-footprint claims used below |
| Best Practices | 6+ | Push/heartbeat monitor pattern (Kuma, Gatus, healthchecks.io) is the consistent, cross-tool idiom for "did the job run" |
| Footguns | 5 | Self-hosted Sentry needs ~16 GB RAM and 40+ containers (Kafka/ClickHouse/Snuba) — GlitchTip needs 256 MB-1 GB for the same SDK protocol |
| Existing Tools | 12 | GlitchTip is Sentry-SDK-compatible and purpose-built to be the lightweight self-hosted alternative |
| Security | 3 | GlitchTip 5.2 (Nov 2025) fixed a brotli-decompression DOS; Sentry's event-based billing can spike unpredictably without rate limits |
| Recent Changes | 5 | GlitchTip 5.2 added a Postgres-only mode dropping the Redis/Valkey dependency; Uptime Kuma v2 adds MySQL/MariaDB to escape SQLite scaling limits |

**Queries:** 22 · **Results parsed:** ~140 · **Deep reads:** 4 (1 extract failure, covered via search snippets) · **Follow-up pass:** no

## Official Documentation

- healthchecks.io's cron-monitoring model: your job pings a unique URL after each successful run; if the ping doesn't arrive within Period+Grace, the check is marked down and notifications fire — this is the canonical dead-man's-switch contract used by every tool below [official] (https://healthchecks.io/docs/monitoring_cron_jobs)
- Gatus supports the same pattern natively via "external endpoints" with heartbeat/push semantics, so a single tool can cover both active HTTP checks and passive cron heartbeats [official] (https://gatus.io/docs/monitoring-push-based)
- GlitchTip's own install docs state minimum system requirements of 256 MB RAM (all-in-one, no Valkey/Redis) and recommended 512 MB-1 GB, versus self-hosted Sentry's documented multi-service Kafka/ClickHouse/Snuba architecture [official] (https://glitchtip.com/documentation/install/)
- Sentry ships a first-party Cron Monitoring ("Crons") feature that layers dead-man's-switch job monitoring directly onto the same account used for error tracking, via CLI/HTTP/SDK check-ins [official] (https://docs.sentry.io/product/monitors-and-alerts/monitors/crons)
- VictoriaMetrics is explicitly Prometheus-scrape-config-compatible and positions itself as a drop-in, lower-resource single-node replacement for a Prometheus server [official] (https://docs.victoriametrics.com/victoriametrics/faq)

## Best Practices

- Use **Push/heartbeat monitors**, not just active HTTP checks, for anything scheduled: your job calls a ping URL on success; absence of the ping (not presence of an error) is the signal, which also catches "cron itself stopped running" and "process was OOM-killed mid-run" — consistent across Uptime Kuma, Gatus, healthchecks.io, and third-party dead-man's-switch tools [official]+[community] (multiple sources corroborate the identical pattern: https://sipamungkas.com/blog/passive-push-monitoring-with-uptime-kuma/, https://healthchecks.io/docs/monitoring_cron_jobs, https://gatus.io/docs/monitoring-push-based)
- Tune heartbeat/retry thresholds conservatively (e.g., 60s interval + 2-3 retries before declaring "down") to avoid false-positive alerts from transient network blips — this is standard operational advice repeated across Uptime Kuma deployment guides [blog] (https://www.tencentcloud.com/techpedia/144018)
- For "did the alert email actually arrive," add a **round-trip email check**: a scheduled job sends a test email to a mailbox you also poll (via IMAP) or use a canary inbox service, rather than trusting that "SMTP accepted the message" equals "the message was delivered" — SMTP acceptance and final delivery are different guarantees [blog] (https://mailflowmonitoring.com, https://web-alert.io/blog/email-smtp-monitoring-delivery-uptime)

## Footguns and Gotchas

- **Uptime Kuma's SQLite backend degrades at scale** — dashboard load times of 15-30+ seconds and multi-GB database files have been reported once monitor counts reach the low hundreds or heartbeat history accumulates without retention limits — corroborated by the project's own issue tracker (#6181, #5187, #5412) plus independent write-ups — corroborated by GitHub issue #6181, GitHub issue #5187, and an independent Medium case study reducing a 5 GB database to 2.7 MB (https://github.com/louislam/uptime-kuma/issues/6181, https://github.com/louislam/uptime-kuma/issues/5187, https://medium.com/@sn.osmanalp/how-i-reduced-uptime-kuma-database-from-5gb-to-2-7mb-and-made-it-1-850x-faster-b3de8ab8879a). At ~20-30 monitors with capped history retention (30-90 days) this workload stays well clear of the reported failure zone, but set a history-retention cap from day one.
- **Uptime Kuma can raise false "down" alerts under SQLite write contention** (`SQLITE_BUSY: database is locked`) — reported directly on the project's issue tracker and independently corroborated by deployment-guide advice to tune retry/threshold settings specifically to absorb this class of transient failure — corroborated by GitHub issue #7338 and independent operational guidance (https://github.com/louislam/uptime-kuma/issues/7338, https://www.tencentcloud.com/techpedia/144018).
- **Self-hosted Sentry is not lightweight** — documented requirements run to 16+ GB RAM and 40+ containers (Kafka, ClickHouse, Snuba) — corroborated across three independent write-ups citing consistent figures — corroborated across three independent sources (https://earezki.com/ai-news/2026-03-14-glitchtip-vs-sentry/, https://europeanpurpose.com/tool/glitchtip, https://www.pistack.xyz/posts/2026-04-23-glitchtip-vs-exceptionless-vs-sentry-self-hosted-error-tracking-2026/). Do not self-host Sentry on this VM; use GlitchTip or Sentry SaaS instead.
- **Anti-bot detection has shifted to layered ML/behavioral+TLS fingerprinting in 2026**, meaning "0 results returned" is an increasingly common and *sudden* scraper-rot mode (a source that worked yesterday can be silently blocked today), not just gradual HTML/schema drift — corroborated across multiple independent 2026 write-ups on the anti-bot landscape (https://apiclaw.io/en/blog/anti-bot-detection-2026-what-changed, https://scrappey.com/qa/anti-bot/what-is-anti-bot-detection). This strengthens the case for consecutive-failure/zero-result alerting over schema-validation alone.
- **Schema/type validation alone does not catch "plausible but wrong" selector drift** — a field can pass Pydantic type validation (e.g., a price is still a valid float) while actually being pulled from the wrong DOM element after a layout change. Repeatedly raised as an unresolved gap across independent commenters in a practitioner discussion, with structured-data (JSON-LD) extraction and canary/known-value pages proposed as the mitigation [unverified as a single Reddit thread, but the same gap is independently corroborated by ScrapFly's own data-quality guidance recommending JSON-LD/keyed access over positional selectors] (https://www.reddit.com/r/webscraping/comments/1ser5eo/how_do_you_monitor_your_scrapers, https://scrapfly.io/blog/posts/how-to-ensure-web-scrapped-data-quality).

## Existing Tools

| Tool | Maintenance | Link | Fit for use case |
| --- | --- | --- | --- |
| Uptime Kuma | Active | https://github.com/louislam/uptime-kuma | Good — HTTP/TCP/DB/push monitors, best UI for a single maintainer; cap history retention |
| Gatus | Active | https://github.com/TwiN/gatus | Good alternative — YAML/git-friendly config, native external-endpoint heartbeats, lighter persistence than Kuma's SQLite |
| healthchecks.io | Active (hosted + self-hostable) | https://healthchecks.io | Good — offsite second heartbeat; free tier is 20 checks, watch the limit against ~20 scraper sources + app/backup checks |
| Netdata | Active | https://www.netdata.cloud | Optional — heavier RAM (100 MB-2 GB+ depending on plugins); best used ad hoc, not as an always-on service here |
| GlitchTip | Active (small team) | https://glitchtip.com | Recommended — Sentry-SDK-compatible, 256 MB-1 GB RAM, single Docker Compose stack |
| Sentry (SaaS free tier) | Active, well-funded | https://sentry.io/pricing | Zero-ops alternative to GlitchTip; free Developer tier is 1 user / 5,000 events/month and also includes Crons for job monitoring |
| Sentry (self-hosted) | Active but heavy | https://github.com/getsentry/self-hosted | Not recommended for this VM — 16+ GB RAM, 40+ containers |
| VictoriaMetrics | Active | https://victoriametrics.com | Only if a metrics stack becomes genuinely necessary later; lighter single-node fallback vs. full Prometheus+Grafana |
| vcrpy | Active | https://github.com/kevin1024/vcrpy | Recommended — cassette-based HTTP recording/replay for scraper tests, supports requests/httpx/urllib3 |
| pytest-recording | Active (kiwicom) | https://github.com/kiwicom/pytest-recording | vcrpy/pytest integration with `none`-by-default recording mode to block accidental live requests in CI |
| responses | Active (getsentry) | https://github.com/getsentry/responses | Lighter alternative for pure `requests`-only mocking without cassette replay |
| syrupy | Active | https://github.com/tophat/syrupy | Snapshot/golden-file assertions on parsed scraper output |
| Cerberus | Maintained | https://github.com/pyeve/cerberus | Lighter schema-validation alternative to Pydantic if full type coercion isn't needed |

## Security and Compatibility

- GlitchTip 5.2 (2025-11-13) shipped a fix for a denial-of-service vulnerability in its brotli-decompression handling, and the release notes describe the memory-consumption mitigation directly — check that any self-hosted GlitchTip instance is on 5.2+ [official] (https://glitchtip.com/blog/2025-11-13-glitchtip-5-2-released/)
- Sentry's event-based billing model means a single bad deploy or logging loop can generate a large, unplanned overage; Sentry's own inbound filters, per-key rate limits, and spike protection are the documented mitigations if using the SaaS free tier long-term [official-adjacent, corroborated across multiple 2026 pricing trackers] (https://last9.io/blog/sentry-pricing/, https://sentrypricing.com/)
- Uptime Kuma has no built-in API for programmatic monitor configuration and no HA/failover — the monitoring system itself is a single point of failure, which is exactly why an offsite heartbeat (healthchecks.io free tier) is recommended as a second, independent check for the "is the whole VM dead" case [blog] (https://betterstack.com/community/guides/monitoring/uptime-kuma-guide/)

## Recent Changes

- **[version-sensitive]** GlitchTip 5.2 (Nov 2025) added an all-Postgres mode that removes the Valkey/Redis dependency, dropping the minimum footprint to 256 MB RAM — relevant only on 5.2+ (https://glitchtip.com/blog/2025-11-13-glitchtip-5-2-released/)
- **[version-sensitive]** Uptime Kuma v2 adds MySQL/MariaDB as an alternative database backend specifically to address the SQLite scaling problems documented above; v1 remains SQLite-only (https://raw.githubusercontent.com/wiki/louislam/uptime-kuma/Migration-From-v1-To-v2.md)
- **[pricing, verify before relying on it]** Sentry's 2026 pricing keeps the Developer tier free at 5,000 errors/month/1 user, with Team at $26/mo (50k events) and Business at $80/mo (100k events); multiple independent trackers agree on these figures as of April 2026, but Sentry pricing has changed before and should be re-checked at sentry.io/pricing before commitment (https://sentrypricing.com/, https://last9.io/blog/sentry-pricing/)
- The anti-bot landscape shifted materially through 2025-2026 toward layered ML/behavioral/TLS-fingerprint defenses across major vendors (Cloudflare, DataDome, PerimeterX, Akamai) — treat "a source suddenly returns 0 results" as at least as likely as gradual HTML/schema drift going forward (https://apiclaw.io/en/blog/anti-bot-detection-2026-what-changed)

## Open Questions

| # | Question | Why unresolved |
| --- | --- | --- |
| 1 | Does GlitchTip's Sentry-SDK compatibility cover every Python SDK feature you might rely on (breadcrumbs, release tracking, environment tagging) at parity with real Sentry? | Sources assert "drop-in compatible" but none of the reviewed sources report a feature-by-feature parity test; worth a smoke test with your actual SDK usage before fully committing |
| 2 | Does the current free healthchecks.io tier (20 checks) comfortably cover ~20 scraper sources plus the app/backup/DB checks you'd also want, or does it require trimming/consolidating checks? | Depends on your exact final check count, which is implementation-specific and outside the scope of this research pass |
| 3 | Do any of the ~20 e-commerce sources currently expose JSON-LD/schema.org product data, making the "prefer structured data over CSS selectors" recommendation immediately actionable? | Requires inspecting the actual target sites, which this research pass did not do |

## Handoff

Persisted at `/home/chris/projects/hw-radar/docs/research/2026-07-03-lightweight-observability-and-scraper-health-monitoring.md`. Downstream skills that may consume it:

- `superpowers:brainstorming` — feed Open Questions into a design conversation about GlitchTip SDK parity and check-count budgeting
- `feature-dev:feature-dev` — start implementation of the `scraper_runs` health table, Uptime Kuma push monitors, and vcrpy test fixtures

## Sources

| URL | Title | Date | Authority |
| --- | --- | --- | --- |
| https://healthchecks.io/docs/monitoring_cron_jobs | How to Monitor Cron Jobs with Healthchecks.io | 2026 | official |
| https://healthchecks.io/docs/self_hosted_docker | Running with Docker — Healthchecks.io | 2026 | official |
| https://healthchecks.io/faq/ | Frequently Asked Questions — Healthchecks.io | 2026 | official |
| https://healthchecks.io/pricing/ | Plans and Pricing — Healthchecks.io | 2026 | official |
| https://gatus.io/docs/monitoring-push-based | Push-based (external) — Gatus | 2026 | official |
| https://glitchtip.com/documentation/install/ | Install — GlitchTip Documentation | 2026 | official |
| https://glitchtip.com/blog/2025-11-13-glitchtip-5-2-released/ | GlitchTip 5.2 Released | 2025-11-13 | official |
| https://gitlab.com/glitchtip/glitchtip-backend/-/blob/master/README.md | GlitchTip Backend README | 2026 | official |
| https://docs.sentry.io/product/monitors-and-alerts/monitors/crons | Cron Monitoring — Sentry Docs | 2026 | official |
| https://sentry.io/pricing/ | Pricing — Sentry | 2026 | official |
| https://docs.victoriametrics.com/victoriametrics/faq | VictoriaMetrics: FAQ | 2026 | official |
| https://raw.githubusercontent.com/wiki/louislam/uptime-kuma/Migration-From-v1-To-v2.md | Migration From v1 To v2 — Uptime Kuma Wiki | 2026 | official |
| https://github.com/louislam/uptime-kuma/issues/6181 | Main dashboard slow when adding too many monitors | 2026 | official (issue tracker) |
| https://github.com/louislam/uptime-kuma/issues/5187 | DB size · Issue #5187 | 2026 | official (issue tracker) |
| https://github.com/louislam/uptime-kuma/issues/5412 | how to choose db for monitor 2000+ or more | 2026 | official (issue tracker) |
| https://github.com/louislam/uptime-kuma/issues/7338 | SQLITE_BUSY Messages | 2026 | official (issue tracker) |
| https://medium.com/@sn.osmanalp/how-i-reduced-uptime-kuma-database-from-5gb-to-2-7mb-and-made-it-1-850x-faster-b3de8ab8879a | How I Reduced Uptime Kuma Database from 5GB to 2.7MB | 2026 | blog |
| https://www.tencentcloud.com/techpedia/144018 | How to Set Up Uptime Kuma | 2026 | blog |
| https://betterstack.com/community/guides/monitoring/uptime-kuma-guide/ | A Complete Guide to Monitoring With Uptime Kuma | 2026 | blog |
| https://sipamungkas.com/blog/passive-push-monitoring-with-uptime-kuma/ | Passive Push Monitoring With Uptime Kuma | 2026 | blog |
| https://symfolidity.com/en/articles/monitoring-sites-and-backups-with-uptime-kuma/ | Monitoring sites and backups with Uptime Kuma | 2026 | blog |
| https://earezki.com/ai-news/2026-03-14-glitchtip-vs-sentry/ | GlitchTip vs Sentry: Choosing the Right Self-Hosted Platform | 2026-03-14 | blog |
| https://europeanpurpose.com/tool/glitchtip | GlitchTip Review 2026 | 2026 | blog |
| https://www.pistack.xyz/posts/2026-04-23-glitchtip-vs-exceptionless-vs-sentry-self-hosted-error-tracking-2026/ | GlitchTip vs Exceptionless vs Sentry | 2026-04-23 | blog |
| https://www.bugsink.com/blog/glitchtip-vs-sentry-vs-bugsink | GlitchTip vs. Sentry vs. Bugsink | 2025 | blog |
| https://sentrypricing.com/ | Sentry Pricing 2026 | 2026 | blog |
| https://last9.io/blog/sentry-pricing/ | Sentry Pricing 2026: Plans, Costs & How to Reduce Your Bill | 2026 | blog |
| https://apiclaw.io/en/blog/anti-bot-detection-2026-what-changed | Anti-Bot Detection in 2026: What Changed | 2026 | blog |
| https://scrappey.com/qa/anti-bot/what-is-anti-bot-detection | What Is Anti-Bot Detection? How It Works in 2026 | 2026 | blog |
| https://scrapfly.io/blog/posts/how-to-ensure-web-scrapped-data-quality | How to Ensure Web Scrapped Data Quality | 2026 | blog |
| https://datawookie.dev/blog/2025-01-28-test-a-web-scraper-using-vcr | Test a Web Scraper using VCR | 2025-01-28 | blog |
| https://www.reddit.com/r/webscraping/comments/1ser5eo/how_do_you_monitor_your_scrapers | How do you monitor your scrapers? | 2026 | community |
| https://www.reddit.com/r/selfhosted/comments/1oxfsxs/does_it_exist_deadman_switch_notifications/ | Does it exist, deadman switch notifications? | 2026 | community |
| https://github.com/kiwicom/pytest-recording | pytest-recording — GitHub | 2026 | official (project repo) |
| https://github.com/getsentry/responses | responses — GitHub | 2026 | official (project repo) |
| https://mailflowmonitoring.com | MailFlowMonitoring — Free Round-trip Email Infrastructure Monitoring | 2026 | community |
| https://web-alert.io/blog/email-smtp-monitoring-delivery-uptime | Email and SMTP Monitoring: Ensure Delivery | 2026 | blog |
