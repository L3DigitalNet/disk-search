# MS-1d — Connectors + Heartbeat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the five marketplace connectors (ServerPartDeals → goHardDrive → WD → Seagate → eBay) plus the ADR-0015 availability-heartbeat subsystem, so all five recert sources yield normalized, FX-stamped listings through the live rung-0–2 resolver on scheduled runs, with per-grain resolution counts recorded per source — the spec §19 MS-1 acceptance (minus MS-1e ratification).

**Architecture:** Each connector is a `SourceAdapter` (`fetch()`+`parse()` only) plugged into the existing MS-1a pipeline (`run_source`), which owns normalize→resolve→persist. JSON/API sources (ServerPartDeals, WD, Seagate, eBay) fetch via `httpx` behind a shared robots-preflight guard (httpx bypasses Scrapy's `ROBOTSTXT_OBEY`, so C-007 is enforced explicitly); the plain-HTML source (goHardDrive) fetches via a Scrapy spider like the demo skeleton. The heartbeat subsystem adds a cheap variant/SKU-grain poll that fingerprints price+stock and fires the full pipeline only on a detected transition, backed by a TimescaleDB hypertable + a plain event table with class-differentiated retention.

**Tech Stack:** Django 6 ORM (PostgreSQL + TimescaleDB), httpx (API/JSON/heartbeat), Scrapy (`AsyncCrawlerRunner` on the shared asyncio loop, HTML scrape tier only), Pydantic v2, APScheduler 3.11.x; uv · Ruff · BasedPyright strict · pytest + coverage · pip-audit. Dev: `httpx.MockTransport` for HTTP mocking, `syrupy` for normalized-output snapshots.

## Global Constraints

- Toolchain contract is `AGENTS.md`: fix pass (`uv run ruff format . && uv run ruff check . --fix`) before every commit; full gate (`uv run python -m scripts.check`) green before claiming a task complete. Coverage threshold **85% branch**.
- **BasedPyright strict** on `src/` + `tests/`. Scrapy and APScheduler ship no stubs — reuse the exact per-file `# pyright:` pragma headers already in `sources/demo.py` and `poller/service.py`; add no new blanket ignores.
- Dependencies **only** via `uv add` / `uv add --dev`; never hand-edit `pyproject.toml`/`uv.lock`. **No new dependency is expected** — `httpx`, `scrapy`, `pydantic` (runtime) and `syrupy`, `vcrpy` (dev) are already present. Mention any dep touched in the completion report.
- DB tests live in `tests/db/` (need `podman compose up -d db`; on this workstation `HW_RADAR_DB_PORT=5433`); pure tests in `tests/unit/` (no DB). DB tests that call `run_source` (writes from `sync_to_async` threads) use `pytest.mark.django_db(transaction=True, serialized_rollback=True)` to preserve the migration-0005 source seed; pure DB reads use `pytest.mark.django_db`.
- **Public-repo rule (AGENTS.md):** no secrets, credential values, private hostnames, or internal IPs in code/tests/fixtures/commits. eBay OAuth creds are read from env var names only (`EBAY_CLIENT_ID` / `EBAY_CLIENT_SECRET`, OpenBao-injected at runtime); tests use synthetic tokens. Cassette/fixture bodies are **synthetic** (OQ8 posture) — never captured live. No access token is ever logged.
- **C-007 scraping guardrails are encoded, not conventional.** Scrapy paths keep `ROBOTSTXT_OBEY=True` + AUTOTHROTTLE (via `scrapy_support.BASE_SETTINGS`). httpx paths route through the Task B1 robots-preflight guard; `store.seagate.com` is hard-blocked (robots `Disallow: /`).
- **Source `site_key` = seeded `normalized_name`.** `run_source` looks up `SourceSite` by `adapter.site_key` against `normalized_name`. Every adapter's `site_key` MUST be one of the migration-0005 seeds: `serverpartdeals`, `goharddrive`, `wd-recertified`, `seagate-recertified`, `ebay`.
- **`enabled=True` is operational, not a migration.** Connector migrations flip only `heartbeat_enabled`/`fast_lane` (config shape). The `enabled=True` go-live is an ADR-0016 UPDATE gated by the Task E3 operational gate, so no deploy auto-starts scraping.
- Cadence/backoff/fingerprint-threshold numbers are OQ9/OQ17-provisional tunables — they live in `SourceConfig` rows or named module constants, never scattered magic numbers.
- Conventional commits on `dev`, GPG-signed. This plan ends with the **MS-1d `dev→main` PR** (merge commit, CI + dependency-review green).
- Migrations are expand/contract; new columns nullable-or-defaulted. The heartbeat cagg migration is **`atomic = False`** (TimescaleDB refuses `CREATE MATERIALIZED VIEW ... WITH (timescaledb.continuous)` inside a transaction).

---

## Design source & inputs

- Design: `docs/superpowers/specs/2026-07-05-ms1-ingestion-design.md` (§MS-1d + §S-1/S-3/S-4 + §3 matrix + §6 risks).
- ADR-0015 (heartbeat grain + volatility scheduling); OQ17 storage research `docs/research/2026-07-04-availability-heartbeat-retention-and-storage-policy.md`.
- Endpoint recon `docs/research/2026-07-04-wd-seagate-recert-endpoint-recon.md`, re-verified live 2026-07-06 (all five endpoints healthy; robots posture unchanged; `store.seagate.com` still `Disallow: /`; eBay production Browse live, token 7200 s, search HTTP 200).
- Master spec §19 MS-1 acceptance; DR-005 (append-not-duplicate), DR-008 (eBay ≤6 h / delete-on-delist), FR-002 (fast-lane intersection), FR-004 (FX stamping).

**Plan-time recon carry-forwards (fold into the named tasks):**
- **WD (Task C3):** the `query=recertified` OCC sweep surfaces *consumer* recert (My Book/Elements/My Passport). The enterprise Gold/Red/Ultrastar recert catalog sits under different category facets — enumerate the enterprise facet at C3 build time; the walking connector may start on the consumer sweep and narrow to enterprise once the facet is found.
- **goHardDrive (Task C2):** no JSON-LD / price microdata; Volusion storefront, prices in `.product_productprice` / `.pricecolor` selectors; robots `Crawl-delay: 2`. Verify selectors against a freshly-saved fixture at build time.
- **Seagate (Task C4):** bootstrap JSON on the robots-allowed `www.seagate.com` category page (`final_price`, `stock_status`, `ST…NM…` SKUs), `Crawl-delay: 20` → httpx cadence floor ≥ 20 s.

---

## File Structure

```
src/hw_radar/catalog/models/base.py            # MODIFY: +2 RetentionClass values; extend BOUNDED_RETENTION_CLASSES
src/hw_radar/catalog/models/evidence.py        # MODIFY: +AvailabilityHeartbeatObservation, +AvailabilityHeartbeatEvent, +HeartbeatDecision
src/hw_radar/catalog/models/__init__.py        # MODIFY: export new models/enums
src/hw_radar/catalog/migrations/0009_heartbeat_models.py       # NEW: two tables + retention constraints (managed)
src/hw_radar/catalog/migrations/0010_heartbeat_timescale.py    # NEW (atomic=False): hypertable, compression, retention, cagg
src/hw_radar/catalog/migrations/0011_enable_heartbeat_flags.py # NEW: per-source heartbeat_enabled/fast_lane flips (data migration)

src/hw_radar/acquisition/classify.py           # MODIFY (B0): map httpx.TransportError → TRANSIENT
src/hw_radar/acquisition/contracts.py          # MODIFY (B4): ParsedListing.raw_url (per-item raw association)
src/hw_radar/acquisition/http.py               # NEW: httpx GET helper + robots-preflight guard (shared, C-007 for JSON paths; RFC-9309 fail-closed)
src/hw_radar/acquisition/heartbeat.py          # NEW: fingerprint + decision logic + HeartbeatReading/HeartbeatProbe protocol + run_heartbeat
src/hw_radar/acquisition/pipeline.py           # MODIFY: thread expires_at through run_source/_persist_all; per-grain resolution counts in detail_json
src/hw_radar/acquisition/sources/serverpartdeals.py   # NEW
src/hw_radar/acquisition/sources/goharddrive.py       # NEW (Scrapy)
src/hw_radar/acquisition/sources/wd.py                # NEW
src/hw_radar/acquisition/sources/seagate.py           # NEW
src/hw_radar/acquisition/sources/ebay.py              # NEW (OAuth2 client-credentials)
src/hw_radar/acquisition/sources/__init__.py   # MODIFY: register all five adapters in ADAPTERS
src/hw_radar/poller/service.py                 # MODIFY: schedule heartbeat jobs for heartbeat_enabled sources

tests/unit/test_http_guard.py                  # NEW: robots preflight (allow/deny, store.seagate.com block)
tests/unit/test_heartbeat_decision.py          # NEW: fingerprint + decide() transition matrix (pure)
tests/db/test_heartbeat_models.py              # NEW: retention constraints, hypertable existence, event dual-write
tests/db/test_source_serverpartdeals.py        # NEW (per-connector: fetch/parse/persist + snapshot)
tests/db/test_source_goharddrive.py            # NEW
tests/db/test_source_wd.py                     # NEW
tests/db/test_source_seagate.py                # NEW
tests/db/test_source_ebay.py                   # NEW (OAuth mint + ≤6h expiry + retention class)
tests/db/test_ms1_acceptance.py                # NEW: per-source ≥1 listing, FX stamp, append-not-duplicate, per-grain counts
tests/db/test_poller_heartbeat.py              # NEW: heartbeat job fires full pipeline only on transition
tests/fixtures/ms1d/                           # NEW: synthetic fixtures (goHardDrive HTML; JSON bodies inline in tests)
docs/handoff/deployed.md                       # MODIFY (Task E3): operational enable runbook + SA-004 gate checklist
```

**Interfaces reused verbatim (do not redefine):**
- `SourceAdapter` protocol: `name: str, site_key: str, run_kind: RunKind, expects_json: bool, async fetch() -> RawBatch, parse(batch) -> list[ParsedListing]` (`acquisition/contracts.py:60`).
- `RawItem(url, http_status=200, content_type="application/json", payload_json=None, payload_text=None)`; `RawBatch(source, fetched_at, items)`; `ParsedListing(source_listing_key, url, title, price>0, currency="USD", shipping_price=None, stock_status="unknown", quantity_available=None, seller_name="", condition_label="", ships_from_country="US", attrs={})`.
- `run_source(adapter, resolver, *, retention_class=MERCHANT_FACT, run_kind=None, fetch_timeout_s=120.0) -> tuple[ScraperRun, RunOutcome]` (`acquisition/pipeline.py:136`).
- Registry: `ADAPTERS: dict[str, Callable[[], SourceAdapter]]` (`acquisition/sources/__init__.py`).
- httpx pattern (inject-or-own-and-close): see `fx.py:65` / `deadman.py:21`.
- httpx test mock: `httpx.MockTransport(handler)` (see `tests/db/test_fx_service.py:66`).
- `StockStatus`: `in_stock / out_of_stock / preorder / unknown`.

---

## Phase A — Heartbeat storage substrate

### Task A1: New retention classes

**Files:**
- Modify: `src/hw_radar/catalog/models/base.py:4-26`
- Test: `tests/unit/test_settings.py` is unrelated — add `tests/unit/test_retention_classes.py`

**Interfaces:**
- Produces: `RetentionClass.AVAILABILITY_HEARTBEAT` (value `"availability_heartbeat"`, 30-day TTL) and `RetentionClass.AVAILABILITY_HEARTBEAT_EVENT` (value `"availability_heartbeat_event"`, 365-day TTL); both added to `BOUNDED_RETENTION_CLASSES`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_retention_classes.py
from hw_radar.catalog.models.base import (
    BOUNDED_RETENTION_CLASSES,
    INDEFINITE_RETENTION_CLASSES,
    RetentionClass,
    retention_constraints,
)


def test_heartbeat_classes_exist_and_are_bounded() -> None:
    assert RetentionClass.AVAILABILITY_HEARTBEAT.value == "availability_heartbeat"
    assert RetentionClass.AVAILABILITY_HEARTBEAT_EVENT.value == "availability_heartbeat_event"
    assert RetentionClass.AVAILABILITY_HEARTBEAT in BOUNDED_RETENTION_CLASSES
    assert RetentionClass.AVAILABILITY_HEARTBEAT_EVENT in BOUNDED_RETENTION_CLASSES
    # bounded ⇒ NOT indefinite (a row of this class must carry expires_at)
    assert RetentionClass.AVAILABILITY_HEARTBEAT not in INDEFINITE_RETENTION_CLASSES


def test_new_bounded_classes_flow_into_constraint_predicate() -> None:
    # retention_constraints bakes the bounded list into the CHECK; the two new
    # classes must appear so new-table constraints accept them.
    constraints = retention_constraints("availability_heartbeat_observation")
    ttl = next(c for c in constraints if c.name.endswith("_retention_ttl_coherent"))
    assert "availability_heartbeat" in str(ttl.condition)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_retention_classes.py -v`
Expected: FAIL — `AttributeError: AVAILABILITY_HEARTBEAT`.

- [ ] **Step 3: Implement**

```python
# base.py — inside RetentionClass, after MANUFACTURER_REFERENCE:
    AVAILABILITY_HEARTBEAT = "availability_heartbeat", "Availability heartbeat (30d)"
    AVAILABILITY_HEARTBEAT_EVENT = "availability_heartbeat_event", "Heartbeat event (365d)"

# base.py — extend BOUNDED_RETENTION_CLASSES:
BOUNDED_RETENTION_CLASSES: tuple[RetentionClass, ...] = (
    RetentionClass.EBAY_LISTING_OBSERVATION,
    RetentionClass.AMAZON_EPHEMERAL,
    RetentionClass.TRANSIENT_DISCOVERY,
    RetentionClass.AVAILABILITY_HEARTBEAT,
    RetentionClass.AVAILABILITY_HEARTBEAT_EVENT,
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_retention_classes.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/hw_radar/catalog/models/base.py tests/unit/test_retention_classes.py
git commit -m "feat(retention): add availability_heartbeat + _event bounded classes (ADR-0015 SA-005)"
```

### Task A2: Heartbeat models

**Files:**
- Modify: `src/hw_radar/catalog/models/evidence.py` (append), `src/hw_radar/catalog/models/__init__.py` (export)
- Test: covered by Task A3's DB test (models need a migration to exist in the DB)

**Interfaces:**
- Produces: `HeartbeatDecision` (TextChoices: `unchanged / transition_detected / ambiguous / failed`); `AvailabilityHeartbeatObservation(RetentionGoverned)` keyed at the source variant/SKU grain; `AvailabilityHeartbeatEvent(RetentionGoverned)` for non-`unchanged` rows.
- Consumes: `RetentionGoverned`, `retention_constraints` (base.py); `SourceSite` (market.py).

Design note: the observation is keyed on the **source's** variant/SKU identifier (`source_sku`), not our `ProductVariant` FK — resolution to a `ProductVariant` happens only when a transition fires the full pipeline, so a heartbeat row cannot assume one exists (ADR-0015 "variant/SKU grain", read the source field never a product rollup).

- [ ] **Step 1: Write the model code**

```python
# evidence.py — append (imports already present: RetentionGoverned, retention_constraints, models, ClassVar)
from hw_radar.catalog.models.market import SourceSite  # add to imports


class HeartbeatDecision(models.TextChoices):
    """ADR-0015 heartbeat decision outcomes."""

    UNCHANGED = "unchanged", "Unchanged"
    TRANSITION_DETECTED = "transition_detected", "Transition detected"
    AMBIGUOUS = "ambiguous", "Ambiguous"
    FAILED = "failed", "Failed"


class AvailabilityHeartbeatObservation(RetentionGoverned):
    """ADR-0015 cheap variant/SKU-grain availability poll (hypertable, 30d raw).

    One row per probe reading. `unchanged` rows stay here and never touch
    offer_snapshot; non-`unchanged` rows are ALSO written to
    AvailabilityHeartbeatEvent (365d) by the poller (OQ17 split-table pattern —
    chunk-granular retention cannot keep two classes at two TTLs in one table)."""

    # CR-001: TimescaleDB requires every unique index — including the PK — to
    # contain the partitioning column (observed_at). Django's default `id` PK
    # would make create_hypertable() FAIL. Mirror OfferSnapshot's
    # CompositePrimaryKey (market.py:137). (source_site_id, source_sku,
    # observed_at) is unique per probe — heartbeats are written serially per source.
    pk = models.CompositePrimaryKey("source_site_id", "source_sku", "observed_at")
    source_site = models.ForeignKey(SourceSite, on_delete=models.PROTECT, related_name="heartbeats")
    source_sku = models.CharField(max_length=255)  # the source's variant/SKU key
    observed_at = models.DateTimeField()
    decision = models.CharField(max_length=20, choices=HeartbeatDecision.choices)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, blank=True, default="")
    stock_status = models.CharField(max_length=20, blank=True, default="")
    shipping_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fingerprint = models.CharField(max_length=64)  # sha256 of price+stock+shipping
    http_status = models.PositiveSmallIntegerField(default=0)
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    endpoint = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "availability_heartbeat_observation"
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["source_site", "source_sku", "-observed_at"], name="hb_obs_sku_time")
        ]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            *retention_constraints("availability_heartbeat_observation")
        ]


class AvailabilityHeartbeatEvent(RetentionGoverned):
    """OQ17 small plain (non-hypertable) table: the rare non-`unchanged` rows,
    retained 365d, read exclusively by fingerprint-tuning diagnostics."""

    source_site = models.ForeignKey(
        SourceSite, on_delete=models.PROTECT, related_name="heartbeat_events"
    )
    source_sku = models.CharField(max_length=255)
    observed_at = models.DateTimeField()
    decision = models.CharField(max_length=20, choices=HeartbeatDecision.choices)
    prev_fingerprint = models.CharField(max_length=64, blank=True, default="")
    fingerprint = models.CharField(max_length=64)
    detail_json: models.JSONField[dict[str, object]] = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "availability_heartbeat_event"
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["source_site", "-observed_at"], name="hb_event_site_time")
        ]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            *retention_constraints("availability_heartbeat_event")
        ]
```

- [ ] **Step 2: Export the new symbols**

```python
# catalog/models/__init__.py — add to the evidence import block and __all__:
from hw_radar.catalog.models.evidence import (
    AvailabilityHeartbeatEvent,
    AvailabilityHeartbeatObservation,
    HeartbeatDecision,
    # ...existing evidence exports...
)
```

- [ ] **Step 3: Verify import + type-check (no migration yet)**

Run: `uv run basedpyright src/hw_radar/catalog/models/evidence.py`
Expected: 0 errors.

- [ ] **Step 4: Commit**

```bash
git add src/hw_radar/catalog/models/evidence.py src/hw_radar/catalog/models/__init__.py
git commit -m "feat(heartbeat): add AvailabilityHeartbeatObservation/Event models + HeartbeatDecision"
```

### Task A3: Heartbeat migrations (tables → hypertable → cagg) + retention tests

**Files:**
- Create: `0009_heartbeat_models.py` (managed, standard makemigrations output), `0010_heartbeat_timescale.py` (`atomic=False`)
- Test: `tests/db/test_heartbeat_models.py`

**Interfaces:**
- Consumes: models from A2. Produces: `availability_heartbeat_observation` hypertable (monthly chunks, compression `segmentby source_site_id`, 30d retention, daily cagg `availability_heartbeat_daily`) + plain `availability_heartbeat_event` table.

- [ ] **Step 1: Generate the model migration**

Run: `HW_RADAR_DB_PORT=5433 uv run python manage.py makemigrations catalog --name heartbeat_models`
Expected: creates `0009_heartbeat_models.py` with `CreateModel` for both tables incl. `retention_constraints`. Confirm it has `dependencies = [("catalog", "0008_refdata_seed")]`.

**Autodetector fix required (Django ticket #23956/#27768 pattern):** makemigrations may emit the `source_site` FK as a **post-`CreateModel` `AddField`** rather than inline in `CreateModel`. That is fatal for `AvailabilityHeartbeatObservation` because its `CompositePrimaryKey("source_site_id", ...)` references `source_site_id`, which doesn't exist until the FK is added — `migrate` fails with `FieldDoesNotExist: no field named 'source_site_id'`. Hand-edit 0009 to **inline `source_site` into each model's `CreateModel` `fields=[...]`** (remove the separate `AddField`), and document the reason in-file. Re-run `makemigrations --check` to confirm no drift.

- [ ] **Step 2: Write the failing DB test**

```python
# tests/db/test_heartbeat_models.py
from datetime import UTC, datetime, timedelta

import pytest
from django.db import connection, transaction
from django.db.utils import IntegrityError

from hw_radar.catalog.models import (
    AvailabilityHeartbeatEvent,
    AvailabilityHeartbeatObservation,
    HeartbeatDecision,
    RetentionClass,
    SourceSite,
)

pytestmark = pytest.mark.django_db


def _site() -> SourceSite:
    return SourceSite.objects.get(normalized_name="serverpartdeals")  # migration-0005 seed


def test_bounded_class_requires_expires_at() -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        AvailabilityHeartbeatObservation.objects.create(
            source_site=_site(), source_sku="SKU1", observed_at=datetime.now(UTC),
            decision=HeartbeatDecision.UNCHANGED, fingerprint="a" * 64,
            retention_class=RetentionClass.AVAILABILITY_HEARTBEAT, expires_at=None,  # violates TTL-coherent
        )


def test_observation_persists_with_expiry() -> None:
    now = datetime.now(UTC)
    obs = AvailabilityHeartbeatObservation.objects.create(
        source_site=_site(), source_sku="SKU1", observed_at=now,
        decision=HeartbeatDecision.UNCHANGED, fingerprint="a" * 64,
        retention_class=RetentionClass.AVAILABILITY_HEARTBEAT, expires_at=now + timedelta(days=30),
    )
    assert obs.pk is not None


def test_observation_table_is_hypertable() -> None:
    with connection.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM timescaledb_information.hypertables "
            "WHERE hypertable_name = 'availability_heartbeat_observation';"
        )
        assert cur.fetchone() is not None


def test_event_table_is_not_a_hypertable() -> None:
    with connection.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM timescaledb_information.hypertables "
            "WHERE hypertable_name = 'availability_heartbeat_event';"
        )
        assert cur.fetchone() is None
```

- [ ] **Step 3: Run test to verify it fails**

Run: `HW_RADAR_DB_PORT=5433 uv run pytest tests/db/test_heartbeat_models.py -v`
Expected: FAIL on `test_observation_table_is_hypertable` (0009 makes a plain table; hypertable DDL is 0010).

- [ ] **Step 4: Write the TimescaleDB migration**

```python
# src/hw_radar/catalog/migrations/0010_heartbeat_timescale.py
from django.db import migrations

# cagg cannot be created inside a transaction; retention/compression policies
# are background jobs. Pattern mirrors 0003_offer_snapshot_hypertable (noop
# reverse — forward-only; a real revert rebuilds from an empty DB).
SETUP = """
SELECT create_hypertable(
    'availability_heartbeat_observation', by_range('observed_at', INTERVAL '1 month'),
    migrate_data => TRUE
);
ALTER TABLE availability_heartbeat_observation SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'source_site_id',
    timescaledb.compress_orderby = 'observed_at DESC'
);
SELECT add_compression_policy('availability_heartbeat_observation', INTERVAL '7 days');
SELECT add_retention_policy('availability_heartbeat_observation', INTERVAL '30 days');
CREATE MATERIALIZED VIEW availability_heartbeat_daily
WITH (timescaledb.continuous) AS
SELECT source_site_id,
       time_bucket('1 day', observed_at) AS day,
       decision,
       count(*) AS n
FROM availability_heartbeat_observation
GROUP BY source_site_id, day, decision
WITH NO DATA;
SELECT add_continuous_aggregate_policy(
    'availability_heartbeat_daily',
    -- start_offset MUST span >= 2 bucket widths (48h for a 1-day bucket) or
    -- TimescaleDB rejects the policy ("refresh window too small"). 3 days back
    -- to 1 hour back = 71h window, comfortably inside the 30-day retention.
    start_offset => INTERVAL '3 days', end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour'
);
"""


class Migration(migrations.Migration):
    atomic = False  # TimescaleDB rejects continuous-aggregate DDL inside a transaction
    dependencies = [("catalog", "0009_heartbeat_models")]
    operations = [migrations.RunSQL(SETUP, reverse_sql=migrations.RunSQL.noop)]
```

- [ ] **Step 5: Run migrations + test to verify it passes**

Run: `HW_RADAR_DB_PORT=5433 uv run python manage.py migrate && HW_RADAR_DB_PORT=5433 uv run pytest tests/db/test_heartbeat_models.py tests/db/test_migrations.py -v`
Expected: PASS (incl. the `makemigrations --check` gate in `test_migrations.py`).

- [ ] **Step 6: Commit**

```bash
git add src/hw_radar/catalog/migrations/0009_heartbeat_models.py src/hw_radar/catalog/migrations/0010_heartbeat_timescale.py tests/db/test_heartbeat_models.py
git commit -m "feat(heartbeat): hypertable + daily cagg + 30d retention; event table (OQ17)"
```

---

## Phase B — Shared connector infrastructure

### Task B0: Classify `httpx.TransportError` as transient (prerequisite for all httpx connectors)

**Files:**
- Modify: `src/hw_radar/acquisition/classify.py`
- Test: `tests/unit/test_classify.py`

**Interfaces:**
- Produces: `classify_exception` maps `httpx.TransportError` (and its subclasses — `ConnectError`, `ReadTimeout`, `ConnectTimeout`, `PoolTimeout`, `ProtocolError`, …) to `RunFailureClass.TRANSIENT`.

Rationale (CR-003): `httpx.TransportError` derives from `httpx.HTTPError(Exception)`, **not** from `OSError`/`ConnectionError`/`TimeoutError`, so the current `classify_exception` (`classify.py:25-28`) returns `UNKNOWN` for a routine API timeout — which pauses the source for manual intervention (`lifecycle.py:56-59`) instead of backing off. This is a prerequisite for C1/C3/C4/C5, and the open TODO "classify `httpx.TransportError` as transient before non-USD/API sources go live." Must land before any httpx connector.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_classify.py — add
import httpx
import pytest

from hw_radar.acquisition.classify import classify_exception
from hw_radar.catalog.models import RunFailureClass


@pytest.mark.parametrize(
    "exc",
    [
        httpx.ConnectError("refused"),
        httpx.ReadTimeout("slow"),
        httpx.ConnectTimeout("slow"),
        httpx.PoolTimeout("pool"),
        httpx.RemoteProtocolError("bad frame"),
    ],
)
def test_httpx_transport_errors_are_transient(exc: httpx.TransportError) -> None:
    assert classify_exception(exc) is RunFailureClass.TRANSIENT
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/unit/test_classify.py -k transport -v`
Expected: FAIL — currently returns `UNKNOWN`.

- [ ] **Step 3: Implement**

```python
# classify.py — add httpx.TransportError to the transient branch. Keep the
# existing built-in tuple; add the httpx base (all transport subclasses inherit).
import httpx  # add to imports

# inside classify_exception, extend the transient isinstance check:
    if isinstance(exc, TimeoutError | ConnectionError | OSError | httpx.TransportError):
        return RunFailureClass.TRANSIENT
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/unit/test_classify.py -v`
Expected: PASS (existing cases unaffected).

- [ ] **Step 5: Commit**

```bash
git add src/hw_radar/acquisition/classify.py tests/unit/test_classify.py
git commit -m "fix(classify): map httpx.TransportError to TRANSIENT (CR-003; API connectors back off, not pause)"
```

### Task B1: httpx robots-preflight guard (fail-closed on unreachable robots)

**Files:**
- Create: `src/hw_radar/acquisition/http.py`
- Test: `tests/unit/test_http_guard.py`

**Interfaces:**
- Produces: `HONEST_UA` (reuse `scrapy_support.USER_AGENT`); `async def robots_allows(url: str, *, client: httpx.AsyncClient, user_agent: str = HONEST_UA) -> bool`; `class RobotsDisallowed(Exception)`; `async def get(url, *, client, params=None, headers=None, user_agent=HONEST_UA, check_robots=True) -> httpx.Response` (raises `RobotsDisallowed` if the path is not allowed). httpx bypasses Scrapy's `ROBOTSTXT_OBEY`, so this is the C-007 enforcement point for JSON paths.
- **RFC 9309 fail-closed (CR-005):** robots fetch **2xx** → parse rules; **4xx** (incl. 404 = no robots) → *unrestricted*, allow; **5xx OR a transport error** → robots is *unreachable*, so **deny by default** (`robots_allows` returns `False` → `get` raises `RobotsDisallowed`). Never fetch the target when permission cannot be verified. The prior "fail-open on HTTPError / parse 5xx body as rules" behavior is wrong and must not ship.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_http_guard.py
import httpx
import pytest

from hw_radar.acquisition.http import (
    RobotsDisallowed,
    RobotsUnavailable,
    get,
    robots_allows,
)

DISALLOW_ALL = "User-agent: *\nDisallow: /\n"
ALLOW = "User-agent: *\nDisallow: /admin\n"


def _transport(*, robots_status: int, robots_body: str = "", robots_raises: bool = False) -> httpx.MockTransport:
    """robots_status drives the /robots.txt response; a non-/robots.txt path
    returns 200 {"ok": true}. robots_raises simulates a network transport error."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            if robots_raises:
                raise httpx.ConnectError("robots unreachable")
            return httpx.Response(robots_status, text=robots_body)
        return httpx.Response(200, json={"ok": True})

    return httpx.MockTransport(handler)


@pytest.mark.anyio
async def test_explicit_disallow_raises() -> None:
    tr = _transport(robots_status=200, robots_body=DISALLOW_ALL)
    async with httpx.AsyncClient(transport=tr) as c:
        with pytest.raises(RobotsDisallowed):
            await get("https://store.seagate.com/graphql", client=c)


@pytest.mark.anyio
async def test_allowed_path_fetches() -> None:
    tr = _transport(robots_status=200, robots_body=ALLOW)
    async with httpx.AsyncClient(transport=tr) as c:
        resp = await get("https://serverpartdeals.com/collections/x/products.json", client=c)
        assert resp.status_code == 200 and resp.json() == {"ok": True}


@pytest.mark.anyio
async def test_robots_404_is_unrestricted() -> None:  # RFC 9309: 4xx ⇒ allow
    tr = _transport(robots_status=404)
    async with httpx.AsyncClient(transport=tr) as c:
        resp = await get("https://api.westerndigital.com/x/products", client=c)
        assert resp.status_code == 200


@pytest.mark.anyio
async def test_robots_503_denies_and_does_not_fetch_target() -> None:  # RFC 9309: 5xx ⇒ deny
    tr = _transport(robots_status=503)
    async with httpx.AsyncClient(transport=tr) as c:
        with pytest.raises(RobotsUnavailable):
            await get("https://serverpartdeals.com/x/products.json", client=c)
        assert await robots_allows("https://serverpartdeals.com/x", client=c) is False


@pytest.mark.anyio
async def test_robots_network_error_denies() -> None:  # RFC 9309: unreachable ⇒ deny
    tr = _transport(robots_status=200, robots_raises=True)
    async with httpx.AsyncClient(transport=tr) as c:
        with pytest.raises(RobotsUnavailable):
            await get("https://serverpartdeals.com/x/products.json", client=c)
```

(Use the project's existing async-test idiom — check `tests/db/test_fx_service.py` and match it; do not add a new async plugin dependency. `RobotsUnavailable` subclasses `ConnectionError`, so `classify_exception` already maps it to `TRANSIENT` — an unreachable-robots run backs off rather than pausing; `RobotsDisallowed` stays `UNKNOWN` → pause, correct for a persistent disallow. Clear `_ROBOTS_CACHE` between tests via an autouse fixture since it is process-global.)

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/unit/test_http_guard.py -v`
Expected: FAIL — `ModuleNotFoundError: hw_radar.acquisition.http`.

- [ ] **Step 3: Implement**

```python
# src/hw_radar/acquisition/http.py
"""Shared httpx GET with an explicit robots.txt preflight.

httpx bypasses Scrapy's ROBOTSTXT_OBEY, so JSON/API connectors (WD, Seagate,
ServerPartDeals, eBay) MUST route through here to keep the C-007 guardrail
honest. robots.txt is parsed once per host per process (cheap, correctness-first
cache — a long-lived poller re-reads on restart, which is acceptable at this
cadence). store.seagate.com (Disallow: /) is blocked by this, not by convention.
"""

from __future__ import annotations

from urllib.robotparser import RobotFileParser

import httpx

from hw_radar.acquisition.scrapy_support import USER_AGENT as HONEST_UA

# Cache only SUCCESSFUL robots parses (keyed by origin). Unreachable robots
# (5xx / transport error) is NOT cached — a transient outage must be re-checked
# next call, not frozen into a permanent block for the process lifetime.
_ROBOTS_CACHE: dict[str, RobotFileParser] = {}


class RobotsDisallowed(Exception):
    """robots.txt EXPLICITLY disallows the path (persistent). Classifies UNKNOWN
    → pauses the source for human review — correct: we should not poll a path the
    site forbids (e.g. store.seagate.com)."""

    def __init__(self, url: str) -> None:
        super().__init__(f"robots.txt disallows {url}")


class RobotsUnavailable(ConnectionError):
    """robots.txt UNREACHABLE (5xx / network) — RFC 9309 requires complete
    disallow. Subclasses ConnectionError so the existing classify_exception maps
    it to TRANSIENT → the source backs off and retries, rather than fetching
    without permission or pausing."""


async def _robots_for(url: str, *, client: httpx.AsyncClient) -> RobotFileParser | None:
    """Return a parser for the origin's robots rules, or None if UNREACHABLE."""
    parts = httpx.URL(url)
    origin = f"{parts.scheme}://{parts.host}"
    cached = _ROBOTS_CACHE.get(origin)
    if cached is not None:
        return cached
    try:
        resp = await client.get(f"{origin}/robots.txt")
    except httpx.HTTPError:
        return None  # RFC 9309: network-unreachable ⇒ deny (not cached — retry next call)
    if resp.status_code >= 500:
        return None  # RFC 9309: server error ⇒ unreachable ⇒ deny (not cached)
    parser = RobotFileParser()
    # 4xx (incl. 404 = no robots) ⇒ unrestricted; 2xx ⇒ parse the rules.
    parser.parse(resp.text.splitlines() if resp.status_code < 400 else [])
    _ROBOTS_CACHE[origin] = parser
    return parser


async def robots_allows(url: str, *, client: httpx.AsyncClient, user_agent: str = HONEST_UA) -> bool:
    """False when explicitly disallowed OR when robots is unreachable (fail-closed)."""
    parser = await _robots_for(url, client=client)
    return parser is not None and parser.can_fetch(user_agent, url)


async def get(
    url: str,
    *,
    client: httpx.AsyncClient,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    user_agent: str = HONEST_UA,
    check_robots: bool = True,
) -> httpx.Response:
    if check_robots:
        parser = await _robots_for(url, client=client)
        if parser is None:
            raise RobotsUnavailable(f"robots.txt unreachable for {url}")  # transient → backoff
        if not parser.can_fetch(user_agent, url):
            raise RobotsDisallowed(url)  # persistent disallow → never fetch this path
    merged = {"User-Agent": user_agent, **(headers or {})}
    return await client.get(url, params=params, headers=merged)
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/unit/test_http_guard.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/hw_radar/acquisition/http.py tests/unit/test_http_guard.py
git commit -m "feat(acquisition): shared httpx get with robots preflight (C-007 for JSON paths)"
```

### Task B2: Heartbeat fingerprint + decision logic

**Files:**
- Create: `src/hw_radar/acquisition/heartbeat.py`
- Test: `tests/unit/test_heartbeat_decision.py`

**Interfaces:**
- Produces (pure, no DB): `fingerprint(*, price, currency, stock_status, shipping) -> str`; `@dataclass(frozen=True) HeartbeatReading(source_sku, price, currency, stock_status, shipping_price, http_status, latency_ms, endpoint)`; `decide(prev: HeartbeatReading | None, new: HeartbeatReading | None, *, price_drop_pct: float = 0.0) -> HeartbeatDecision`. `HeartbeatProbe` protocol (`async def probe(self) -> list[HeartbeatReading]`) is added here for adapters to implement. The DB-facing `run_heartbeat` lands in Task D1 (needs the ORM).
- Consumes: `HeartbeatDecision` (catalog.models).

Decision rules (ADR-0015): `new is None` (fetch/parse failed) → `failed`; `prev is None` (first sighting) → `transition_detected` (fire the pipeline to establish the baseline); missing/unknown stock on `new` → `ambiguous`; OOS↔in-stock flip OR a material price drop → `transition_detected`; identical fingerprint → `unchanged`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_heartbeat_decision.py
from decimal import Decimal

from hw_radar.acquisition.heartbeat import HeartbeatReading, decide, fingerprint
from hw_radar.catalog.models import HeartbeatDecision


def _r(price: str, stock: str, ship: str | None = None) -> HeartbeatReading:
    return HeartbeatReading(
        source_sku="SKU1", price=Decimal(price), currency="USD", stock_status=stock,
        shipping_price=Decimal(ship) if ship else None, http_status=200, latency_ms=42, endpoint="x",
    )


def test_identical_is_unchanged() -> None:
    r = _r("100.00", "in_stock")
    assert decide(r, _r("100.00", "in_stock")) is HeartbeatDecision.UNCHANGED


def test_first_sighting_is_transition() -> None:
    assert decide(None, _r("100.00", "in_stock")) is HeartbeatDecision.TRANSITION_DETECTED


def test_oos_to_in_stock_is_transition() -> None:
    assert decide(_r("100.00", "out_of_stock"), _r("100.00", "in_stock")) is HeartbeatDecision.TRANSITION_DETECTED


def test_price_drop_is_transition() -> None:
    assert decide(_r("100.00", "in_stock"), _r("80.00", "in_stock")) is HeartbeatDecision.TRANSITION_DETECTED


def test_unknown_stock_is_ambiguous() -> None:
    assert decide(_r("100.00", "in_stock"), _r("100.00", "unknown")) is HeartbeatDecision.AMBIGUOUS


def test_failed_fetch_is_failed() -> None:
    assert decide(_r("100.00", "in_stock"), None) is HeartbeatDecision.FAILED


def test_fingerprint_stable_and_sensitive() -> None:
    a = fingerprint(price=Decimal("100.00"), currency="USD", stock_status="in_stock", shipping=None)
    assert a == fingerprint(price=Decimal("100.00"), currency="USD", stock_status="in_stock", shipping=None)
    assert a != fingerprint(price=Decimal("80.00"), currency="USD", stock_status="in_stock", shipping=None)
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/unit/test_heartbeat_decision.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

```python
# src/hw_radar/acquisition/heartbeat.py
"""ADR-0015 heartbeat: cheap variant/SKU-grain availability fingerprinting.

Pure logic here (fingerprint + decide) is table-tested with no DB. The DB-facing
run_heartbeat (writes observations, dual-writes events, fires the full pipeline
on transition) lands in the poller task (D1)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from hw_radar.catalog.models import HeartbeatDecision

_UNKNOWN_STOCK = {"", "unknown"}


@dataclass(frozen=True)
class HeartbeatReading:
    source_sku: str
    price: Decimal | None
    currency: str
    stock_status: str
    shipping_price: Decimal | None
    http_status: int
    latency_ms: int | None
    endpoint: str


def fingerprint(*, price: Decimal | None, currency: str, stock_status: str, shipping: Decimal | None) -> str:
    basis = f"{price}|{currency}|{stock_status}|{shipping}"
    return hashlib.sha256(basis.encode()).hexdigest()


def _fp(r: HeartbeatReading) -> str:
    return fingerprint(price=r.price, currency=r.currency, stock_status=r.stock_status, shipping=r.shipping_price)


def decide(
    prev: HeartbeatReading | None, new: HeartbeatReading | None, *, price_drop_pct: float = 0.0
) -> HeartbeatDecision:
    if new is None:
        return HeartbeatDecision.FAILED
    if new.stock_status in _UNKNOWN_STOCK:
        return HeartbeatDecision.AMBIGUOUS
    if prev is None:
        return HeartbeatDecision.TRANSITION_DETECTED  # baseline sighting fires the pipeline once
    if _fp(prev) == _fp(new):
        return HeartbeatDecision.UNCHANGED
    if prev.stock_status != new.stock_status:
        return HeartbeatDecision.TRANSITION_DETECTED
    if prev.price is not None and new.price is not None and new.price < prev.price:
        drop = float((prev.price - new.price) / prev.price)
        if drop >= price_drop_pct:  # default 0.0 ⇒ any drop is material
            return HeartbeatDecision.TRANSITION_DETECTED
    return HeartbeatDecision.UNCHANGED  # price rose / non-material change ⇒ no snapshot


class HeartbeatProbe(Protocol):
    """A source adapter that also exposes a cheap availability probe.
    heartbeat_enabled sources implement this alongside SourceAdapter."""

    site_key: str

    async def probe(self) -> list[HeartbeatReading]: ...
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/unit/test_heartbeat_decision.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/hw_radar/acquisition/heartbeat.py tests/unit/test_heartbeat_decision.py
git commit -m "feat(heartbeat): fingerprint + decide() transition logic + HeartbeatProbe protocol"
```

### Task B3: Thread `expires_at` through the pipeline (bounded-retention persist)

**Files:**
- Modify: `src/hw_radar/acquisition/pipeline.py` (`run_source`, `_persist_all`, `_normalize` unaffected)
- Test: `tests/db/test_pipeline.py` (add cases)

**Interfaces:**
- Produces: `run_source(..., retention_class=MERCHANT_FACT, expires_policy: Callable[[datetime], datetime | None] | None = None, ...)`. When `expires_policy` is given, `_persist_all` stamps `expires_at = expires_policy(batch.fetched_at)` on raw payload, listing, and (via listing) snapshot — required so eBay's bounded `ebay_listing_observation` rows satisfy the DR-001 TTL-coherent CHECK. `merchant_fact` callers pass no policy (None → indefinite).

Rationale: closes the persist.py docstring's deferred item and the TODO "pass `expires_at` through `run_source`". A policy callable (not a fixed datetime) keeps the TTL relative to each observation's fetch time (DR-008 ≤6 h for eBay).

- [ ] **Step 1: Write the failing test**

```python
# tests/db/test_pipeline.py — add (pytestmark already transaction=True, serialized_rollback=True)
from datetime import timedelta
from hw_radar.catalog.models import RetentionClass, RawPayload

def test_bounded_retention_stamps_expires_at() -> None:
    adapter = FakeAdapter([ok_item()], [ok_parsed()])
    run, _ = asyncio.run(
        run_source(
            adapter, NullResolver(),
            retention_class=RetentionClass.EBAY_LISTING_OBSERVATION,
            expires_policy=lambda observed: observed + timedelta(hours=6),
        )
    )
    assert run.status == RunStatus.SUCCESS
    listing = Listing.objects.get(source_site__normalized_name="demo")
    assert listing.retention_class == RetentionClass.EBAY_LISTING_OBSERVATION
    assert listing.expires_at is not None  # bounded class ⇒ CHECK would have rejected a null
    assert RawPayload.objects.filter(retention_class=RetentionClass.EBAY_LISTING_OBSERVATION).exists()
```

(Ensure `ok_item()`/`ok_parsed()` produce a USD listing so no FX lookup is needed; `FakeAdapter.site_key = "demo"`.)

- [ ] **Step 2: Run to verify it fails**

Run: `HW_RADAR_DB_PORT=5433 uv run pytest tests/db/test_pipeline.py::test_bounded_retention_stamps_expires_at -v`
Expected: FAIL — `run_source() got an unexpected keyword argument 'expires_policy'`.

- [ ] **Step 3: Implement**

```python
# pipeline.py — signature + wiring
from collections.abc import Callable
from datetime import datetime

def _persist_all(site, batch, normalized, retention_class, expires_at):  # add expires_at param
    raw = (
        store_raw(batch.items[0], fetched_at=batch.fetched_at,
                  retention_class=retention_class, expires_at=expires_at)
        if batch.items else None
    )
    listing_ids, upserted, appended = [], 0, 0
    observed_at = batch.fetched_at
    for record in normalized:
        listing, _created = upsert_listing(site, record, retention_class, expires_at=expires_at)
        append_snapshot(listing, record, observed_at=observed_at, raw=raw)  # inherits listing TTL
        listing_ids.append(listing.pk); upserted += 1; appended += 1
    return listing_ids, upserted, appended

async def run_source(
    adapter, resolver, *,
    retention_class=RetentionClass.MERCHANT_FACT,
    expires_policy: Callable[[datetime], datetime | None] | None = None,
    run_kind=None, fetch_timeout_s=FETCH_TIMEOUT_S,
):
    ...
    # after normalize, before _persist_all:
    expires_at = expires_policy(batch.fetched_at) if expires_policy else None
    listing_ids, upserted, appended = await sync_to_async(_persist_all)(
        site, batch, normalized, retention_class, expires_at
    )
    ...
```

- [ ] **Step 4: Run to verify it passes**

Run: `HW_RADAR_DB_PORT=5433 uv run pytest tests/db/test_pipeline.py -v`
Expected: PASS (existing cases unaffected — default `expires_policy=None` preserves current behavior).

- [ ] **Step 5: Commit**

```bash
git add src/hw_radar/acquisition/pipeline.py tests/db/test_pipeline.py
git commit -m "feat(pipeline): thread expires_at through run_source for bounded retention (eBay TTL)"
```

### Task B4: Per-item raw payload persistence + snapshot→raw association

**Files:**
- Modify: `src/hw_radar/acquisition/contracts.py` (`ParsedListing` gains `raw_url`), `src/hw_radar/acquisition/pipeline.py` (`_persist_all`)
- Test: `tests/db/test_pipeline.py`

**Interfaces:**
- Produces: `ParsedListing.raw_url: str = ""` — the `RawItem.url` this listing was parsed from. `_persist_all` now persists **every** `batch.items` entry as a `RawPayload` (not just `items[0]`) and links each `OfferSnapshot` to the raw payload matching its listing's `raw_url` (fallback: the sole raw when the batch has one item, else `None`).

Rationale (CR-002): current `_persist_all` stores only `batch.items[0]` and links every snapshot to that one raw row (`pipeline.py:101-105`). For WD (search sweep + per-product fetches → many `RawItem`s) that silently drops provenance and mis-associates evidence. TODO.md must-do: "store per-item raw payload rows." A count-only test would pass while provenance is wrong — so the test asserts row identity, not just counts.

- [ ] **Step 1: Write the failing test**

```python
# tests/db/test_pipeline.py — add
def test_per_item_raw_payloads_are_stored_and_associated() -> None:
    # two RawItems, each producing one listing tagged with its own raw_url
    items = [ok_item(url="https://x.test/a"), ok_item(url="https://x.test/b")]
    parsed = [ok_parsed(key="A", raw_url="https://x.test/a"),
              ok_parsed(key="B", raw_url="https://x.test/b")]
    adapter = FakeAdapter(items, parsed)
    asyncio.run(run_source(adapter, NullResolver()))
    assert RawPayload.objects.count() == 2  # not 1 (items[0]-only bug is dead)
    snap_a = OfferSnapshot.objects.get(listing__source_listing_key="A")
    assert snap_a.raw_payload is not None and snap_a.raw_payload.endpoint == "https://x.test/a"
    snap_b = OfferSnapshot.objects.get(listing__source_listing_key="B")
    assert snap_b.raw_payload.endpoint == "https://x.test/b"
```

(Extend the test module's `ok_item`/`ok_parsed` helpers with the `url`/`key`/`raw_url` kwargs.)

- [ ] **Step 2: Run to verify it fails**

Run: `HW_RADAR_DB_PORT=5433 uv run pytest tests/db/test_pipeline.py::test_per_item_raw_payloads_are_stored_and_associated -v`
Expected: FAIL — `RawPayload.objects.count() == 1`.

- [ ] **Step 3: Implement**

```python
# contracts.py — ParsedListing: add (backward-compatible default)
    raw_url: str = ""  # RawItem.url this listing was parsed from (per-item raw association)

# pipeline.py — _persist_all: persist EVERY item (a list, so duplicate URLs are
# NOT collapsed — CR-002), then build a url→raw map for association (first raw
# per url wins; duplicate source URLs are rare but must not drop a stored row).
def _persist_all(site, batch, normalized, retention_class, expires_at):
    raws = [
        store_raw(item, fetched_at=batch.fetched_at,
                  retention_class=retention_class, expires_at=expires_at)
        for item in batch.items
    ]  # len(raws) == len(batch.items) — every RawItem persisted
    by_url: dict[str, RawPayload] = {}
    for item, raw in zip(batch.items, raws, strict=True):
        by_url.setdefault(item.url, raw)
    sole = raws[0] if len(raws) == 1 else None
    listing_ids, upserted, appended = [], 0, 0
    observed_at = batch.fetched_at
    for record in normalized:
        listing, _created = upsert_listing(site, record, retention_class, expires_at=expires_at)
        raw = by_url.get(record.raw_url) or sole  # per-item; fallback to the sole raw
        append_snapshot(listing, record, observed_at=observed_at, raw=raw)
        listing_ids.append(listing.pk); upserted += 1; appended += 1
    return listing_ids, upserted, appended
```

Also add a test case asserting a batch with **two RawItems sharing a URL** persists two `RawPayload` rows (no collapse) — pins the CR-002-residual fix.

Note: `NormalizedListing` extends `ParsedListing`, so `record.raw_url` is available on the normalized record. Adapters set `raw_url` in `parse()` (add to C1/C3/C4/C5 — WD is the load-bearing multi-item case).

- [ ] **Step 4: Run to verify it passes**

Run: `HW_RADAR_DB_PORT=5433 uv run pytest tests/db/test_pipeline.py -v`
Expected: PASS (single-item connectors keep working via the `sole` fallback).

- [ ] **Step 5: Commit**

```bash
git add src/hw_radar/acquisition/contracts.py src/hw_radar/acquisition/pipeline.py tests/db/test_pipeline.py
git commit -m "fix(pipeline): persist every raw item + associate snapshot→raw by url (CR-002)"
```

---

## Phase C — Connectors (design build order)

> Shared test harness (define once, reuse across C1–C5, E2): a connector DB test builds the adapter with an injected `httpx.MockTransport` returning **synthetic** bodies, calls `run_source(adapter, NullResolver())` on the module-scoped event loop, and asserts on `Listing`/`OfferSnapshot` rows for the seeded `normalized_name`. Adapters take an optional `client: httpx.AsyncClient | None = None` (inject-or-own-and-close, per `fx.py`) so tests inject the mock and production owns the client. Snapshot the normalized `ParsedListing` list with `syrupy` (`snapshot` fixture) where a stable shape is worth pinning.

### Task C1: ServerPartDeals (httpx Shopify `products.json`)

**Files:**
- Create: `src/hw_radar/acquisition/sources/serverpartdeals.py`
- Modify: `src/hw_radar/acquisition/sources/__init__.py` (register)
- Create: `src/hw_radar/catalog/migrations/0011_enable_heartbeat_flags.py` (data migration; this task seeds only the SPD flip — WD/Seagate/eBay flips are appended by C3/C4/C5, or make it one migration edited across tasks; prefer one migration finalized in E1 — see note)
- Test: `tests/db/test_source_serverpartdeals.py`

**Interfaces:**
- Consumes: `http.get`, `ParsedListing`, `RawItem`, `RawBatch`, `HeartbeatReading`. `site_key = "serverpartdeals"`, `run_kind = RunKind.FULL`, `expects_json = True`.
- Produces: `ServerPartDealsAdapter` implementing `SourceAdapter` + `HeartbeatProbe`. Config: `heartbeat_enabled=True`, `fast_lane=False` (churning — FR-002 excludes it from the fast lane; the DB CHECK `source_config_fast_lane_eligible` would reject `fast_lane=True` here).

Shopify shape: `GET /collections/manufacturer-recertified-drives/products.json?limit=250` → `products[]` each with `title`, `handle`, `variants[]` (`id`, `sku`, `price`, `available`, `title`). One `ParsedListing` per variant; `source_listing_key = f"{product_handle}:{variant_id}"`; stock from `available` (True→in_stock / False→out_of_stock).

- [ ] **Step 1: Write the failing test**

```python
# tests/db/test_source_serverpartdeals.py
import asyncio
from collections.abc import Iterator

import httpx
import pytest

from hw_radar.acquisition.contracts import NullResolver
from hw_radar.acquisition.pipeline import run_source
from hw_radar.acquisition.sources.serverpartdeals import ServerPartDealsAdapter
from hw_radar.catalog.models import Listing, OfferSnapshot, RunStatus, StockStatus

pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)

SYNTHETIC = {  # synthetic Shopify products.json (OQ8: not captured live)
    "products": [
        {"title": "Seagate Exos X20 20TB Recertified", "handle": "exos-x20-20tb-recert",
         "variants": [{"id": 111, "sku": "ST20000NM002D-RECERT", "price": "279.99", "available": True, "title": "Default"}]},
        {"title": "WD Ultrastar DC HC560 20TB Recertified", "handle": "hc560-20tb-recert",
         "variants": [{"id": 222, "sku": "WUH722020BLE-RECERT", "price": "289.99", "available": False, "title": "Default"}]},
    ]
}


@pytest.fixture(scope="module")
def loop() -> Iterator[asyncio.AbstractEventLoop]:
    lo = asyncio.new_event_loop(); asyncio.set_event_loop(lo)
    yield lo
    asyncio.set_event_loop(None); lo.close()


def _mock() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /admin\n")
        return httpx.Response(200, json=SYNTHETIC)

    return httpx.MockTransport(handler)


def test_serverpartdeals_persists_two_variants(loop: asyncio.AbstractEventLoop) -> None:
    adapter = ServerPartDealsAdapter(client=httpx.AsyncClient(transport=_mock()))
    run, _ = loop.run_until_complete(run_source(adapter, NullResolver()))
    assert run.status == RunStatus.SUCCESS
    assert run.records_valid == 2
    listings = Listing.objects.filter(source_site__normalized_name="serverpartdeals")
    assert listings.count() == 2
    oos = OfferSnapshot.objects.get(listing__source_listing_key="hc560-20tb-recert:222")
    assert oos.stock_status == StockStatus.OUT_OF_STOCK
```

- [ ] **Step 2: Run to verify it fails**

Run: `HW_RADAR_DB_PORT=5433 uv run pytest tests/db/test_source_serverpartdeals.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement the adapter**

```python
# src/hw_radar/acquisition/sources/serverpartdeals.py
"""ServerPartDeals connector: Shopify /products.json (T2, churning, heartbeat-not-fast-lane)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import httpx

from hw_radar.acquisition import http
from hw_radar.acquisition.contracts import ParsedListing, RawBatch, RawItem
from hw_radar.acquisition.heartbeat import HeartbeatReading
from hw_radar.catalog.models import RunKind

COLLECTION_URL = "https://serverpartdeals.com/collections/manufacturer-recertified-drives/products.json"


class ServerPartDealsAdapter:
    name = "serverpartdeals"
    site_key = "serverpartdeals"
    run_kind = RunKind.FULL
    expects_json = True

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def _fetch_json(self) -> tuple[httpx.Response, bool]:
        owns = self._client is None
        client = self._client or httpx.AsyncClient(timeout=30.0)
        try:
            return await http.get(COLLECTION_URL, client=client, params={"limit": "250"}), owns
        finally:
            if owns:
                await client.aclose()

    async def fetch(self) -> RawBatch:
        owns = self._client is None
        client = self._client or httpx.AsyncClient(timeout=30.0)
        try:
            resp = await http.get(COLLECTION_URL, client=client, params={"limit": "250"})
            item = RawItem(
                url=str(resp.url), http_status=resp.status_code,
                content_type=resp.headers.get("content-type", "application/json"),
                payload_json=resp.json() if resp.status_code == 200 else None,
                payload_text=resp.text,
            )
            return RawBatch(source=self.name, fetched_at=datetime.now(UTC), items=[item])
        finally:
            if owns:
                await client.aclose()

    def parse(self, batch: RawBatch) -> list[ParsedListing]:
        out: list[ParsedListing] = []
        for item in batch.items:
            data = item.payload_json or {}
            for product in data.get("products", []):
                handle = str(product["handle"])
                for variant in product.get("variants", []):
                    out.append(
                        ParsedListing(
                            source_listing_key=f"{handle}:{variant['id']}",
                            url=f"https://serverpartdeals.com/products/{handle}",
                            title=str(product["title"]),
                            price=Decimal(str(variant["price"])),
                            stock_status="in_stock" if variant.get("available") else "out_of_stock",
                            raw_url=item.url,  # per-item raw-payload association (Task B4)
                            attrs={"sku": variant.get("sku", ""), "variant_title": variant.get("title", "")},
                        )
                    )
        return out

    async def probe(self) -> list[HeartbeatReading]:
        batch = await self.fetch()
        return [
            HeartbeatReading(
                source_sku=p.source_listing_key, price=p.price, currency=p.currency,
                stock_status=p.stock_status, shipping_price=p.shipping_price,
                http_status=200, latency_ms=None, endpoint=COLLECTION_URL,
            )
            for p in self.parse(batch)
        ]
```

- [ ] **Step 4: Register + run tests**

```python
# sources/__init__.py
from hw_radar.acquisition.sources.serverpartdeals import ServerPartDealsAdapter
ADAPTERS = {"demo": DemoAdapter, "serverpartdeals": ServerPartDealsAdapter}
```

Run: `HW_RADAR_DB_PORT=5433 uv run pytest tests/db/test_source_serverpartdeals.py -v`
Expected: PASS.

- [ ] **Step 5: Flip `heartbeat_enabled` (data migration)**

Create `0011_enable_heartbeat_flags.py` seeding the SPD flip only for now (WD/Seagate/eBay flips added by their tasks; see the note under Task E1 on consolidating):

```python
from django.db import migrations

FLAGS = {  # (heartbeat_enabled, fast_lane) — fast_lane per FR-002 (drop_prone ∩ cheap signal)
    "serverpartdeals": (True, False),  # churning ⇒ heartbeat but never fast-laned
}


def apply(apps, schema_editor):
    SourceConfig = apps.get_model("catalog", "SourceConfig")
    for key, (hb, fl) in FLAGS.items():
        SourceConfig.objects.filter(source_site__normalized_name=key).update(heartbeat_enabled=hb, fast_lane=fl)


class Migration(migrations.Migration):
    dependencies = [("catalog", "0010_heartbeat_timescale")]
    operations = [migrations.RunPython(apply, migrations.RunPython.noop)]
```

Run: `HW_RADAR_DB_PORT=5433 uv run python manage.py migrate && HW_RADAR_DB_PORT=5433 uv run pytest tests/db/test_ops_models.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/hw_radar/acquisition/sources/serverpartdeals.py src/hw_radar/acquisition/sources/__init__.py src/hw_radar/catalog/migrations/0011_enable_heartbeat_flags.py tests/db/test_source_serverpartdeals.py
git commit -m "feat(connector): ServerPartDeals Shopify products.json adapter + heartbeat probe"
```

### Task C2: goHardDrive (Scrapy spider over Volusion HTML)

**Files:**
- Create: `src/hw_radar/acquisition/sources/goharddrive.py`, `tests/fixtures/ms1d/goharddrive_category.html` (synthetic, trimmed to 2 products)
- Modify: `sources/__init__.py`
- Test: `tests/db/test_source_goharddrive.py`

**Interfaces:**
- `site_key = "goharddrive"`, `run_kind = RunKind.FULL`, `expects_json = False`. No heartbeat (`cheap_signal = none`; config stays `heartbeat_enabled=False`, `fast_lane=False`). Full pipeline at T2 cadence.
- Scrapy tier (robots `Crawl-delay: 2`, `ROBOTSTXT_OBEY=True` via `scrapy_support.BASE_SETTINGS`); mirror `DemoAdapter`'s `run_spider` structure. Parse `.product_productprice` / `.pricecolor` selectors + product `-p/*.htm` links (Volusion). Prices lack a `$\d+.\d+` literal in raw HTML → strip non-numeric before `Decimal`.

- [ ] **Step 1: Create the synthetic fixture** (`tests/fixtures/ms1d/goharddrive_category.html`) with two `<div class="productlist">`-style blocks each carrying a product link (`-p/gNN.htm`), a title, and a `<span class="product_productprice">$149.99</span>`. Keep it minimal and clearly synthetic.

- [ ] **Step 2: Write the failing test** (mirror `tests/db/test_pipeline_demo.py`: module-scoped `scrapy_loop`, `run_until_complete(run_source(GoHardDriveAdapter(fixture=...), NullResolver()))`, assert 2 listings for `normalized_name="goharddrive"` with correct `item_price`).

- [ ] **Step 3: Run to verify it fails.** `HW_RADAR_DB_PORT=5433 uv run pytest tests/db/test_source_goharddrive.py -v` → FAIL (module missing).

- [ ] **Step 4: Implement** a `GoHardDriveSpider(scrapy.Spider)` (NO `ROBOTSTXT_OBEY=False` override — production spider obeys robots; the `file://` fixture path is used only in tests, and the demo's file-exception is test-only) + `GoHardDriveAdapter` with `fetch()` calling `run_spider(GoHardDriveSpider, start_url=...)` and `parse()` extracting title/price/link. Price cleanup: `Decimal(re.sub(r"[^0-9.]", "", price_text))`. Reuse the `# pyright:` header block from `sources/demo.py`.

- [ ] **Step 5: Register, run tests, verify PASS.**

- [ ] **Step 6: Commit** `feat(connector): goHardDrive Volusion HTML scraper (Scrapy, no cheap signal)`.

### Task C3: WD Recertified (httpx OCC JSON)

**Files:**
- Create: `src/hw_radar/acquisition/sources/wd.py`
- Modify: `sources/__init__.py`, `0011_enable_heartbeat_flags.py` (add `"wd-recertified": (True, True)`)
- Test: `tests/db/test_source_wd.py`

**Interfaces:**
- `site_key = "wd-recertified"`, `expects_json = True`, `run_kind = RunKind.FULL`. Config: `heartbeat_enabled=True`, `fast_lane=True` (drop_prone ∩ occ_json — CHECK passes).
- Two-step OCC fetch (recon-confirmed 2026-07-06): `GET /wdwebservices/v2/us/products/search?query=recertified&fields=products(code)` → codes; then per code `GET /wdwebservices/v2/us/products/{code}?fields=code,name,variantOptions(code,priceData(FULL),stock(FULL))`. One `ParsedListing` per `variantOptions[]`: `source_listing_key = variant.code` (e.g. `RWDBBGB0040HBK-NESN`), `price = priceData.value`, `stock_status` from `stock.stockLevelStatus` + `saleable` (variant `saleable=false` ⇒ out_of_stock even if `inStock`). `api.westerndigital.com` has no robots.txt (404 ⇒ unrestricted) — the B1 guard returns allowed.
- **Plan-time carry-forward:** `query=recertified` surfaces consumer recert. At build time, enumerate the enterprise Gold/Red/Ultrastar recert facet (category/facet param on the OCC search) and prefer it; if not found this task, land the consumer sweep as the walking connector and open a follow-up TODO for the enterprise facet (do not block the connector on it — MS-1's per-source gate needs ≥1 listing, which the consumer sweep satisfies).

- [ ] **Steps:** failing test (synthetic search + per-product MockTransport responses, assert a `saleable=false` variant → `out_of_stock`) → run fail → implement adapter (search sweep → gather variant fetches; `probe()` reads `saleable ∧ stockLevelStatus`) → register → flip flags in 0011 → run PASS → commit `feat(connector): WD Recertified OCC JSON adapter (fast-lane, heartbeat)`.

### Task C4: Seagate Recertified (httpx category-page bootstrap JSON)

**Files:**
- Create: `src/hw_radar/acquisition/sources/seagate.py`
- Modify: `sources/__init__.py`, `0011_enable_heartbeat_flags.py` (add `"seagate-recertified": (True, True)`)
- Test: `tests/db/test_source_seagate.py`

**Interfaces:**
- `site_key = "seagate-recertified"`, `expects_json = False` (HTML page carrying JSON — content-type is text/html; `expects_json=False` avoids the anti_bot "JSON endpoint answered text/html" misclassification), `run_kind = RunKind.FULL`. Config: `heartbeat_enabled=True`, `fast_lane=True` (drop_prone ∩ bootstrap_json).
- `GET https://www.seagate.com/products/seagate-recertified/exos-recertified/` via `http.get` (robots-allowed, `Crawl-delay: 20` → the heartbeat cadence floor is ≥ 20 s, enforced by `SourceConfig.cadence_ceiling_s=300` already ≥ 20; add a module constant `MIN_INTERVAL_S = 20` asserted in a test). Extract per-SKU bootstrap JSON (`ST…NM…` keys, `final_price`, `stock_status`) with a bounded regex/JSON extraction. `store.seagate.com` must NEVER be fetched — the B1 guard blocks it (robots `Disallow: /`); add an explicit test asserting a `store.seagate.com` URL raises `RobotsDisallowed`.

- [ ] **Steps:** failing test (synthetic HTML with 2 embedded SKU JSON blobs + a store.seagate.com block assertion) → fail → implement (parse bootstrap JSON; `source_listing_key = SKU`; `stock_status` map `IN_STOCK→in_stock`) → register → flip flags → run PASS → commit `feat(connector): Seagate Recertified bootstrap-JSON adapter (robots-safe, fast-lane)`.

### Task C5: eBay (httpx Browse API, OAuth2 client-credentials)

**Files:**
- Create: `src/hw_radar/acquisition/sources/ebay.py`
- Modify: `sources/__init__.py`, `0011_enable_heartbeat_flags.py` (add `"ebay": (True, True)`)
- Test: `tests/db/test_source_ebay.py`

**Interfaces:**
- `site_key = "ebay"`, `expects_json = True`, `run_kind = RunKind.FULL`. Config: `heartbeat_enabled=True`, `fast_lane=True` (the Browse poll IS the heartbeat — no separate tier). Sequenced last to harden the contract before OAuth.
- OAuth2 client-credentials: `POST {base}/identity/v1/oauth2/token` (Basic `b64(client_id:client_secret)`, `grant_type=client_credentials`, `scope=https://api.ebay.com/oauth/api_scope`) → cache token until `expires_in`; then `GET {base}/buy/browse/v1/item_summary/search?q=...&limit=...` with `Authorization: Bearer …` + `X-EBAY-C-MARKETPLACE-ID: EBAY_US`. Creds from env: `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET`, base `EBAY_API_BASE` (default `https://api.ebay.com`) — OpenBao-injected at runtime; **never logged, never in the repo**. Verified live 2026-07-06 (token 7200 s; search HTTP 200).
- Parse `itemSummaries[]` → `ParsedListing` (`source_listing_key = itemId`, `price = price.value`, `currency = price.currency`, `shipping_price` from `shippingOptions[0].shippingCost.value` when present, `ships_from_country` from `itemLocation.country`, `seller_name` from `seller.username`).
- **Retention TTL (partial DR-008):** the eBay run calls `run_source(adapter, resolver, retention_class=RetentionClass.EBAY_LISTING_OBSERVATION, expires_policy=lambda observed: observed + timedelta(hours=6))` — the Task B3 `expires_policy` path (B4 per-item raw applies too). This bounds observation *staleness* to ≤6 h but **does NOT by itself satisfy the eBay delete-on-delist obligation** (see the delist gate below). Non-USD listings are FX-stamped by the pipeline and flagged international by `fx.stamp`. Bypass the B1 robots guard for `api.ebay.com` (an authorized API, not a crawl — `check_robots=False`), but keep the honest UA.
- **Token cache robustness (CR-007 note):** cache the token with a **safety skew** (treat it as expired `expires_in - 300 s` early) and on a **401** from the search call, invalidate the cache and re-mint once before failing. eBay rate-limits the token endpoint, so do not mint per request.

- [ ] **Steps:** failing test (MockTransport: `/identity/v1/oauth2/token` → synthetic token JSON `{"access_token":"SYNTH","expires_in":7200,"token_type":"Application Access Token"}`; `/buy/browse/v1/item_summary/search` → synthetic `itemSummaries`; a first-call `401` then success proves the re-mint path; assert a non-USD item gets `is_international=True` + `usd_item_price` set, and that the listing's `retention_class == ebay_listing_observation` with non-null `expires_at`; assert no token string appears in `caplog`) → fail → implement adapter (token cache with skew + 401 re-mint; `probe()` reuses the search response — the Browse poll doubles as the heartbeat) → register → flip flags → run PASS → commit `feat(connector): eBay Browse API adapter (OAuth2, ≤6h retention, heartbeat-native)`.

**CR-004 — eBay delete-on-delist gate (does NOT ship as auto-enable in MS-1d):** the ≤6 h TTL bounds staleness but is not the delete-on-delist path. Per owner decision (STATUS.md 2026-07-05, TODO.md IR-002): hard delete is never the path; delist must become a **Listing-grain soft-delete / terminal state** (mirroring `RetentionGoverned` + an `is_current` flag) that does **not** relax the resolution-edge `superseded_by` `PROTECT`. That is a schema addition (`Listing` has no soft-delete field today) beyond MS-1d's adapter scope. **Decision:** MS-1d ships the eBay *connector* (fetch/parse/persist/heartbeat) but eBay **`enabled=True` go-live stays BLOCKED** until a separate Listing-grain soft-delete plan lands. Record this block in Task E3's runbook (eBay is the one source whose operational enable is gated on more than the SA-004 checklist), and do not claim DR-008 is fully satisfied. A follow-up TODO carries the soft-delete plan.

---

## Phase D — Poller heartbeat scheduling

### Task D1: `run_heartbeat` + schedule heartbeat jobs

**Files:**
- Modify: `src/hw_radar/acquisition/heartbeat.py` (add DB-facing `run_heartbeat`), `src/hw_radar/poller/service.py` (schedule + job)
- Test: `tests/db/test_poller_heartbeat.py`, `tests/unit/test_poller.py` (job registration)

**Interfaces:**
- Produces: `async def run_heartbeat(adapter: HeartbeatProbe, config: SourceConfig, resolver: ListingResolver) -> None` — probes, loads each SKU's last observation, `decide()`s, writes an `AvailabilityHeartbeatObservation`, dual-writes an `AvailabilityHeartbeatEvent` for non-`unchanged`, and fires `run_source(adapter, resolver, run_kind=RunKind.HEARTBEAT→FULL)` once when ANY SKU is `transition_detected`/`ambiguous`.
- **Retention per source (CR-NEW-001 — the eBay carve-out covers BOTH heartbeat tables, not just observations):**
  - non-eBay: observation → `availability_heartbeat` / `expires_at = observed + 30d`; event → `availability_heartbeat_event` / `expires_at = observed + 365d`.
  - **eBay:** BOTH the observation AND the event row carry `retention_class = ebay_listing_observation` / `expires_at = observed + 6h` (ADR-0015 rule-6 source-restricted class caps the blanket heartbeat TTLs; design §108-109). A source-restricted retention helper (`heartbeat_retention_for(config) -> (RetentionClass, timedelta)`) centralizes this so no eBay heartbeat row ever lands on a 365-day path. Test: a synthetic eBay heartbeat transition asserts both rows carry `ebay_listing_observation` with a ≤6 h `expires_at`.
- `poll_heartbeat(site_key, registry, scheduler)` mirrors `poll_source` **fully** (CR-006 residual): admission gate with `run_kind=RunKind.HEARTBEAT`, `apply_run_outcome` on the returned `RunOutcome`, and interval reschedule when `current_interval_s` changes — not just admission.
- `build_scheduler` job model (CR-006 — ADR-0015 requires a slow repair crawl for *every* source, since CDN edge cache floors achievable freshness regardless of poll rate):
  - **heartbeat-enabled, non-eBay** (WD, Seagate, ServerPartDeals): TWO jobs — a fast `poll-heartbeat-{key}` at `current_interval_s` (the fast-lane/heartbeat cadence) **and** a slow repair `poll-{key}` at `cadence_baseline_s` (the slow end — full pipeline regardless of heartbeat, catching edge-cache-masked changes). Distinct cadences, distinct job IDs.
  - **eBay**: ONE job — `poll-heartbeat-ebay` only. The Browse poll IS both the heartbeat and the full fetch (natively-both source), so a separate repair `poll-ebay` would double-poll; document this as the intentional single-job exception.
  - **heartbeat-disabled** (goHardDrive): unchanged — one `poll-{key}` full-pipeline job at `current_interval_s`.
- Test `build_scheduler` asserts: WD/Seagate/SPD each have BOTH `poll-heartbeat-{key}` and `poll-{key}` at distinct intervals; eBay has ONLY `poll-heartbeat-ebay`; goHardDrive has ONLY `poll-goharddrive`.

- [ ] **Steps:** failing DB test (two probes with an OOS→in_stock transition ⇒ exactly one `offer_snapshot` written and one `AvailabilityHeartbeatEvent`; a run of identical probes ⇒ zero snapshots — the ADR-0015 Confirmation criterion) → fail → implement `run_heartbeat` + poller wiring → run PASS (incl. `tests/unit/test_poller.py` asserting heartbeat jobs are registered for `heartbeat_enabled` sources) → commit `feat(poller): heartbeat scheduling — fire full pipeline only on transition (ADR-0015)`.

---

## Phase E — Operational gate + MS-1 acceptance

### Task E1: Per-grain resolution counts in the run report

**Files:**
- Modify: `src/hw_radar/acquisition/pipeline.py` (`run_source` detail_json)
- Test: `tests/db/test_pipeline.py`

**Interfaces:**
- After the resolver loop, `run.detail_json["grain_counts"] = {"none": n, "family": n, "model": n, "variant": n}` computed from `Listing.resolution_grain` over the run's `listing_ids`. This gives MS-1e a real denominator (Codex SA-003) and satisfies the MS-1d Exit "each source's run report records per-grain resolution counts."

- [ ] **Steps:** failing test (a run with a resolver stub that resolves 1 listing to family grain ⇒ `detail_json["grain_counts"]["family"] == 1`) → fail → implement (query `Listing.objects.filter(pk__in=listing_ids).values_list("resolution_grain")`, tally) → run PASS → commit `feat(pipeline): record per-grain resolution counts per run (SA-003)`.

**Note on 0011 consolidation:** if C1/C3/C4/C5 each edited `0011_enable_heartbeat_flags.py`, confirm the final `FLAGS` dict is `{serverpartdeals:(True,False), wd-recertified:(True,True), seagate-recertified:(True,True), ebay:(True,True)}` and goHardDrive is absent (stays False/False). Re-run `test_ops_models.py` after any edit.

### Task E2: MS-1 acceptance suite

**Files:**
- Create: `tests/db/test_ms1_acceptance.py`
- Test: itself

**Interfaces:** one parametrized test per source proving spec §19 MS-1 acceptance (minus ratification):
1. **≥1 normalized listing** per source on a synthetic run (all 5 adapters via MockTransport / fixture).
2. **FX stamping (FR-004):** a synthetic non-USD eBay item carries `fx_rate`, `fx_pair`, `fx_rate_date`, `usd_item_price`; USD items stamp identity (rate 1.0). `is_international` set for non-US `ships_from_country`.
3. **Append-not-duplicate (DR-005):** running the same source twice appends a second `OfferSnapshot` and leaves `Listing.count()` unchanged.
4. **Per-grain counts present:** each run's `detail_json["grain_counts"]` sums to `records_valid`.
5. **Live-resolver integration (CR-007 — guards against a NullResolver-only false positive):** at least one representative connector (ServerPartDeals) runs through the real `CatalogResolver()` — not `NullResolver`. **The product catalog is NOT seeded by a migration** — `0008_refdata_seed` only creates `RefdataConfig` (Codex CR-007). Seed the reference corpus **inside the test** the way the existing refdata tests do (`import_refdata` / `refdata.refresh.run_refresh()`, cf. `tests/db/test_refdata_refresh.py:165`), then feed a synthetic listing whose MPN/alias **matches a seeded alias** (e.g. a seeded Seagate Exos or WD Ultrastar SKU from the MS-1c corpus). Assert the run succeeds AND `detail_json["grain_counts"]` shows **≥1 non-`none` grain** (family or better) — proving the adapter→`CatalogResolver`→grain path resolves, not merely executes. Optionally drive it through `poll_source` (wires `CatalogResolver` + admission) after setting the seed row `enabled=True` in-test to also exercise scheduler admission.

- [ ] **Steps:** write the five assertions as parametrized cases; for case 5, seed refdata in-test and use an alias-matching synthetic listing → run (cases 1–4 pass on the Phase C connectors; case 5 exercises `CatalogResolver` with a real catalog hit — fix any adapter gaps surfaced here) → commit `test(ms1): per-source acceptance + live-resolver integration (≥1 listing, FX, append-not-dup, grain counts, CatalogResolver non-none grain)`.

### Task E3: Operational gate (SA-004) + enable runbook

**Files:**
- Modify: `docs/handoff/deployed.md`
- No code — this is the pre-real-data gate that must pass **before the first `enabled=True` flip**.

- [ ] **Step 1:** Verify (don't assume — handoff says "wired 2026-07-05c"): (1) hourly **TimescaleDB-aware** logical dumps cover `availability_heartbeat_observation`, `availability_heartbeat_event`, and `raw_payload`; (2) the CT-116 disk-space alert is active (raw payloads grow); (3) raw payloads are DB-resident in this design (no disk-path payload stage ships in MS-1d — if one is added, the CT-116 subvol must enter restic `BACKUP_PATHS` first); (4) the restore path is documented (runbook §18.6). Record the verification result (pass/fail per item) in `deployed.md`.
- [ ] **Step 2:** Document the operational enable procedure in `deployed.md`: after the gate passes, flip `enabled=True` one source at a time via SQL UPDATE (ADR-0016), watch `scraper_runs` for the first successful run + non-`grain=none` resolution, then proceed to the next. Order: ServerPartDeals → goHardDrive → WD → Seagate → **eBay (BLOCKED)**.
- [ ] **Step 3 (CR-004):** Record the **eBay go-live block** explicitly in `deployed.md`: eBay's connector ships in MS-1d but its `enabled=True` flip is gated on a *separate* Listing-grain soft-delete/terminal-state plan satisfying the delete-on-delist obligation (TODO IR-002) — not just the SA-004 checklist. The other four sources gate only on SA-004.
- [ ] **Step 4: Commit** `docs(deployed): MS-1d operational gate + enable runbook; eBay go-live blocked pending delist plan (SA-004, CR-004)`.

### Task E4: Full gate + dev→main PR

- [ ] **Step 1:** Full gate green:

```bash
HW_RADAR_DB_PORT=5433 uv run ruff format --check . && HW_RADAR_DB_PORT=5433 uv run ruff check . \
  && HW_RADAR_DB_PORT=5433 uv run basedpyright \
  && HW_RADAR_DB_PORT=5433 uv run coverage run -m pytest && HW_RADAR_DB_PORT=5433 uv run coverage report \
  && HW_RADAR_DB_PORT=5433 uv run pip-audit
```

Expected: all green; coverage ≥ 85% branch; pip-audit clean.

- [ ] **Step 2:** Open the `dev→main` PR (merge commit; CI + dependency-review green). PR body: the five connectors, the heartbeat subsystem, the MS-1d Exit checklist with per-source ≥1-listing evidence, and the note that `enabled=True` remains gated by the Task E3 operational gate (no source auto-enabled by this merge).

---

## Self-Review

**Spec coverage (design §MS-1d):**
- Five adapters, build order ServerPartDeals→goHardDrive→WD→Seagate→eBay → Tasks C1–C5. ✅
- Pydantic validation + `raw_payload` persistence + per-source failure isolation → inherited from `run_source`/pipeline (NFR-001 already enforced); adapters add no cross-source coupling. ✅
- Heartbeat storage (hypertable + event table + 2 retention classes + eBay carve-out) → Tasks A1–A3, D1. ✅
- Heartbeat schema requirements (SA-005: new `RetentionClass` values in `BOUNDED_RETENTION_CLASSES`, constraint lists; eBay carve-out) → Task A1 + A3 + D1. ✅
- Pre-real-data operational gate (SA-004) before first `enabled=True` → Task E3 (gates go-live, not the merge). ✅
- Endpoint re-verification at plan time → **done 2026-07-06** (recorded above), carried into C2/C3/C4. ✅
- Exit criteria (5/5 ≥1 listing, FX stamps, append-not-duplicate, per-grain counts, resolution evidence SA-003) → Tasks E1–E2. ✅
- `expires_at` through `run_source` (open TODO) → Task B3. ✅
- Transient classification of `httpx.TransportError` before API sources (TODO) → **Task B0** (concrete TDD task before all httpx connectors). ✅
- Per-item raw payload rows (TODO) → **Task B4** (persist every `RawItem`, associate snapshot→raw by url). ✅
- eBay delete-on-delist (TODO IR-002) → **Task C5 delist gate + E3**: connector ships, but eBay `enabled=True` is BLOCKED pending a separate Listing-grain soft-delete plan; DR-008 is not claimed satisfied by TTL alone. ✅

**Codex round-1 findings (CR-001..CR-007) — all confirmed against the repo and resolved:**
- CR-001 (hypertable PK) → Task A2 `CompositePrimaryKey("source_site_id","source_sku","observed_at")`.
- CR-002 (first-item-only raw) → Task B4.
- CR-003 (`httpx.TransportError`→UNKNOWN) → Task B0.
- CR-004 (eBay delist absent) → C5 delist gate + E3 go-live block.
- CR-005 (robots fail-open) → Task B1 RFC-9309 fail-closed (`RobotsUnavailable(ConnectionError)`→TRANSIENT; 5xx/network deny).
- CR-006 (repair-crawl path) → Task D1 two-job model (fast heartbeat + slow repair; eBay single-job exception).
- CR-007 (NullResolver-only acceptance) → E2 case 5 (live `CatalogResolver` integration) + C5 token skew/401 re-mint.

**Codex round-2 residuals (verdict: minor correction) — resolved:**
- CR-002 residual (dict-comprehension collapsed duplicate raw URLs) → B4 now stores every `RawItem` as a list, then maps by url (first-wins) + a duplicate-URL test.
- CR-007 residual (false "migration-0008 seeds catalog" claim — 0008 seeds only `RefdataConfig`) → E2 case 5 now seeds refdata in-test via `import_refdata`/`run_refresh()`, uses an alias-matching listing, and asserts ≥1 non-`none` grain.
- CR-NEW-001 (eBay heartbeat *event* rows on the 365d path) → D1 eBay carve-out now covers BOTH heartbeat tables (`ebay_listing_observation`/≤6h) via a `heartbeat_retention_for(config)` helper + test.
- CR-006 residual → D1 `poll_heartbeat` mirrors `poll_source` fully (outcome application + reschedule, not just admission).

**Deviations flagged for owner/reviewer (Appendix B process):**
- **MockTransport instead of vcrpy cassettes** for httpx connectors. Rationale: cassettes are synthetic-only (OQ8) and never recorded live, so vcrpy's record-replay adds machinery without benefit; `httpx.MockTransport` is the established pattern (`test_fx_service.py`) and keeps synthetic bodies inline and reviewable. `syrupy` snapshots of normalized output are still used. vcrpy remains available if a reviewer prefers it.
- **Seagate full-fetch via httpx, not Scrapy.** The design S-3 routes scrape-tier through Scrapy, but Seagate's full parse and its heartbeat are the *same* single robots-allowed category-page GET; using one httpx path (behind the B1 robots guard, honoring the 20 s floor) avoids two transports for one request. goHardDrive (a true multi-page HTML crawl) stays on Scrapy.

**Placeholder scan:** no TBD/TODO-in-code; every code step shows real code; C2/C3/C4/C5 compress *repeated harness* prose but each adapter's distinct fetch/parse is shown or fully specified with exact endpoints, keys, and field maps. Before implementing C2–C5, an executor should expand each to the same 6-step TDD shape as C1 (the harness is identical; only the parse logic and synthetic bodies differ).

**Type consistency:** `site_key` values match migration-0005 `normalized_name`s exactly; `HeartbeatReading`/`HeartbeatDecision`/`decide` signatures are consistent A2↔B2↔D1; `expires_policy` callable signature is consistent B3↔C5; `ParsedListing.raw_url` is consistent B4↔C1–C5. Phase B task order: **B0** (classify) → **B1** (robots) → **B2** (heartbeat logic) → **B3** (expires_at) → **B4** (per-item raw), all before Phase C connectors.
