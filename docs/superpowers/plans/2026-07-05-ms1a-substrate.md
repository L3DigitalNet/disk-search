# MS-1a — Ingestion Substrate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the acquisition substrate — source registry rows, `scraper_runs`, the full C.2 admission machinery (two-level token buckets, back-off ladder, ADR-0017 lifecycle), the §12.1 failure classifier, the adapter contract, the Frankfurter FX service, Scrapy-on-the-shared-asyncio-loop, and a fixture-backed demo source proving poller → pipeline → persist end-to-end — so MS-1b/c/d can plug matching, catalog, and real connectors into a working spine.

**Architecture:** One systemd-supervised APScheduler poller process (ADR-0012) owns per-source scheduling and all shared admission state in memory, checkpointed to PostgreSQL. Scrape-tier fetching is Scrapy with the asyncio reactor sharing the poller loop; API/FX/heartbeat calls use `httpx` (OQ21). Pipeline stages (`fetch → parse → normalize → resolve → persist`) are independently testable; entity-resolve is a stub (`grain = none`) until MS-1b. Design source: `docs/superpowers/specs/2026-07-05-ms1-ingestion-design.md` (MS-1a section) + master spec §8/§10/§12/C.1/C.2 + ADRs 0012/0014/0016/0017.

**Tech Stack:** Django 6 ORM (PostgreSQL + TimescaleDB), APScheduler 3.11.x (`AsyncIOScheduler`), Scrapy (asyncio reactor, `CrawlerRunner`), httpx, Pydantic v2, asgiref `sync_to_async`; uv · Ruff · BasedPyright strict · pytest + coverage · pip-audit.

## Global Constraints

- Toolchain contract is `AGENTS.md`: fix pass (`uv run ruff format . && uv run ruff check . --fix`) before every commit; full gate (`uv run python -m scripts.check`) green before claiming a task complete. Coverage threshold **85% branch**.
- **BasedPyright strict** on `src/` + `tests/`; APScheduler and Scrapy ship no types — scope pragmas per-file exactly as `src/hw_radar/poller/__init__.py` already does (`# pyright: reportMissingTypeStubs=false, ...` with a one-line reason).
- Dependencies **only** via `uv add` / `uv add --dev`; never hand-edit `pyproject.toml`/`uv.lock`. Allowed additions (spec §8.6): `scrapy`, `pydantic`, `httpx` (OQ21); dev: `vcrpy`, `syrupy`. Mention every dep added in the completion report.
- DB tests live in `tests/db/` (need `podman compose up -d db`); pure tests in `tests/unit/` (no DB). `pytest-django` provides `db`/fixtures; `DJANGO_SETTINGS_MODULE = hw_radar.settings` comes from `pyproject.toml`.
- Scraping guardrails (spec §8.5 / C-007) are **encoded, not conventional**: `ROBOTSTXT_OBEY=True`, AUTOTHROTTLE on, honest User-Agent, hard timeouts. The demo spider's `file://` fixture is the sole, documented robots exception (per-spider `custom_settings`, test-only).
- Public repo: no secrets, internal hostnames, or infra addresses in code/docs/commits. Env names + OpenBao paths only.
- Cadence/backoff/breaker **numbers are OQ9/OQ7-provisional tunables** — they live in `SourceConfig` rows and module-level constants, never scattered magic numbers.
- Conventional commits on `dev`, GPG-signed. This plan ends with the **MS-1a `dev→main` PR**.
- Migrations are expand/contract (spec §8.5); new columns nullable-or-defaulted.
- APScheduler job defaults stay `max_instances=1`, `coalesce=True` (ADR-0012); per-source `misfire_grace_time` from `SourceConfig`.
- **Scrapy reactor contract (design §MS-1a, Codex SA-006):** the asyncio reactor is installed exactly once before anything imports `twisted.internet.reactor`; no module-level Twisted reactor imports; the runner primitive is **`AsyncCrawlerRunner`** (fallback `CrawlerRunner` + `Deferred.asFuture(loop)` only if the pinned Scrapy lacks it); one long-lived loop per process — **Scrapy-touching tests share ONE module-scoped event loop** (multi-`asyncio.run()` patterns are forbidden for them) and must prove two consecutive crawls on that loop.

## File Structure

```
src/hw_radar/catalog/models/ops.py            # NEW: SourceConfig, ScraperRun, FxRateDaily, SchedulerCheckpoint (+ enums)
src/hw_radar/catalog/models/market.py         # MODIFY: Listing.is_international; OfferSnapshot.usd_item_price
src/hw_radar/catalog/models/__init__.py       # MODIFY: export new models/enums
src/hw_radar/catalog/admin.py                 # MODIFY: register ops models
src/hw_radar/catalog/migrations/0004_ops_substrate.py   # generated + reviewed
src/hw_radar/catalog/migrations/0005_seed_sources.py    # hand-written data migration (5 sources + demo)
src/hw_radar/acquisition/__init__.py          # NEW (empty package marker)
src/hw_radar/acquisition/contracts.py         # NEW: Pydantic models + SourceAdapter/ListingResolver protocols
src/hw_radar/acquisition/classify.py          # NEW: §12.1 failure classifier + soft-block signals (EC-007)
src/hw_radar/acquisition/fx.py                # NEW: Frankfurter service + FX stamping (ADR-0008)
src/hw_radar/acquisition/persist.py           # NEW: listing upsert + snapshot append + raw payload
src/hw_radar/acquisition/pipeline.py          # NEW: stage runner + ScraperRun + lifecycle application
src/hw_radar/acquisition/deadman.py           # NEW: Uptime-Kuma dead-man push (§18.5)
src/hw_radar/acquisition/scheduling/__init__.py
src/hw_radar/acquisition/scheduling/buckets.py    # NEW: TokenBucket + two-level BucketRegistry (pure)
src/hw_radar/acquisition/scheduling/backoff.py    # NEW: ladder math + Retry-After clamp + auto-ramp (pure)
src/hw_radar/acquisition/scheduling/lifecycle.py  # NEW: ADR-0017 state machine (pure)
src/hw_radar/acquisition/scheduling/admission.py  # NEW: ordered admission gate (pure)
src/hw_radar/acquisition/scheduling/apply.py      # NEW: lifecycle/backoff/ramp applied to SourceConfig rows
src/hw_radar/acquisition/scheduling/checkpoint.py # NEW: bucket-state checkpoint to PostgreSQL (ERR-007)
src/hw_radar/acquisition/scrapy_support.py    # NEW: asyncio reactor install, base settings, run_spider()
src/hw_radar/acquisition/sources/__init__.py  # NEW: adapter registry (demo only at MS-1a)
src/hw_radar/acquisition/sources/demo.py      # NEW: fixture-backed walking-skeleton adapter + spider
src/hw_radar/poller/__init__.py               # REWRITE: django.setup + job registration from SourceConfig
src/hw_radar/poller/__main__.py               # MODIFY: DJANGO_SETTINGS_MODULE default
tests/unit/test_buckets.py                    # NEW
tests/unit/test_backoff.py                    # NEW
tests/unit/test_lifecycle.py                  # NEW
tests/unit/test_admission.py                  # NEW
tests/unit/test_classify.py                   # NEW
tests/unit/test_contracts.py                  # NEW
tests/unit/test_fx_stamp.py                   # NEW (pure stamping paths)
tests/unit/test_deadman.py                    # NEW (httpx MockTransport)
tests/unit/test_poller.py                     # MODIFY: adjust to rewritten poller
tests/db/test_ops_models.py                   # NEW: constraints on SourceConfig/ScraperRun/FxRateDaily
tests/db/test_fx_service.py                   # NEW: rate cache + refresh (mock transport)
tests/db/test_persist.py                      # NEW: upsert/append semantics (DR-005 at substrate level)
tests/db/test_pipeline_demo.py                # NEW: end-to-end walking skeleton incl. Scrapy-on-loop
tests/db/test_checkpoint.py                   # NEW: bucket checkpoint round-trip
tests/fixtures/demo_listings.html             # NEW: JSON-LD fixture page for the demo spider
```

**Interfaces locked by this plan** (later tasks and MS-1b/c/d consume these exact names):

- `contracts.ParsedListing` / `contracts.NormalizedListing` (Pydantic), `contracts.SourceAdapter` (Protocol: `name: str`, `site_key: str`, `run_kind: RunKind`, `expects_json: bool`, `async fetch() -> RawBatch`, `parse(batch: RawBatch) -> list[ParsedListing]`), `contracts.ListingResolver` (Protocol: `resolve_listing(listing_id: int) -> None`).
- `pipeline.run_source(adapter, resolver) -> ScraperRun` — the one entry point the poller schedules.
- `scheduling.apply.apply_run_outcome(config, outcome, now, rand) -> None` — the only mutator of `SourceConfig` scheduling state.
- `fx.stamp(parsed, observed_date) -> NormalizedListing` (raises `fx.MissingRateError`), `fx.refresh_daily(currencies) -> int`.
- `scrapy_support.run_spider(spider_cls, **spider_kwargs) -> list[dict[str, object]]` (async).

---

### Task 1: Dependencies, ops models, schema additions, source seed

**Files:**
- Modify: `pyproject.toml` (via `uv add` only)
- Create: `src/hw_radar/catalog/models/ops.py`
- Modify: `src/hw_radar/catalog/models/market.py`, `src/hw_radar/catalog/models/__init__.py`, `src/hw_radar/catalog/admin.py`
- Create: `src/hw_radar/catalog/migrations/0004_ops_substrate.py` (generated), `0005_seed_sources.py` (hand-written)
- Test: `tests/db/test_ops_models.py`

**Interfaces:**
- Consumes: `TimeStamped`, `SourceSite`, `StockStatus`, `retention_constraints` (existing).
- Produces: `SourceConfig` (incl. the separate `heartbeat_enabled` / `fast_lane` booleans per the design §3 matrix), `ScraperRun`, `FxRateDaily`, `SchedulerCheckpoint`, enums `SourceTier`, `VolatilityProfile`, `CheapSignal`, `LifecycleState`, `RunKind`, `RunStatus`, `RunFailureClass`; `Listing.is_international`; `OfferSnapshot.usd_item_price`. Every later task imports these from `hw_radar.catalog.models`.

- [ ] **Step 1: Add dependencies**

```bash
uv add scrapy pydantic httpx
uv add --dev vcrpy syrupy
```

Expected: `uv.lock` updated; `uv run python -c "import scrapy, pydantic, httpx"` exits 0. (`vcrpy`/`syrupy` are used from MS-1d cassettes onward but belong to the substrate's declared test stack — spec §8.6.)

- [ ] **Step 2: Write the failing tests**

`tests/db/test_ops_models.py`:

```python
from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError
from django.utils import timezone

from hw_radar.catalog.models import (
    CheapSignal,
    FxRateDaily,
    LifecycleState,
    Listing,
    OfferSnapshot,
    RetentionClass,
    RunKind,
    RunStatus,
    ScraperRun,
    SourceConfig,
    SourceSite,
    SourceTier,
    SourceType,
    VolatilityProfile,
)

pytestmark = pytest.mark.django_db


def make_site(name: str = "Demo Site", key: str = "demo-site") -> SourceSite:
    return SourceSite.objects.create(
        name=name, normalized_name=key, source_type=SourceType.OTHER
    )


def make_config(site: SourceSite, **overrides: object) -> SourceConfig:
    defaults: dict[str, object] = {
        "source_site": site,
        "tier": SourceTier.T2_SPECIALIST,
        "domain": "example.com",
        "cadence_baseline_s": 3600,
        "cadence_ceiling_s": 900,
        "current_interval_s": 3600,
    }
    defaults.update(overrides)
    return SourceConfig.objects.create(**defaults)


def test_source_config_defaults_are_safe() -> None:
    config = make_config(make_site())
    assert config.enabled is False  # sources ship disabled until their connector lands
    assert config.lifecycle_state == LifecycleState.ACTIVE
    assert config.heartbeat_enabled is False  # orthogonal to fast_lane (design §3 matrix)
    assert config.fast_lane is False
    assert config.volatility_profile == VolatilityProfile.STABLE
    assert config.cheap_signal == CheapSignal.NONE
    assert config.consecutive_failures == 0
    assert config.clean_polls == 0


def test_ceiling_must_not_be_slower_than_baseline() -> None:
    with pytest.raises(IntegrityError):
        make_config(make_site(), cadence_baseline_s=900, cadence_ceiling_s=3600)


def test_fast_lane_requires_drop_prone_and_cheap_signal() -> None:
    with pytest.raises(IntegrityError):
        make_config(make_site(), fast_lane=True)  # stable + no signal


def test_fast_lane_allowed_when_eligible() -> None:
    config = make_config(
        make_site(),
        fast_lane=True,
        volatility_profile=VolatilityProfile.DROP_PRONE,
        cheap_signal=CheapSignal.SHOPIFY_PRODUCTS_JSON,
    )
    assert config.fast_lane is True


def test_scraper_run_records_lifecycle_of_a_run() -> None:
    site = make_site()
    run = ScraperRun.objects.create(
        source_site=site, run_kind=RunKind.FULL, started_at=timezone.now()
    )
    assert run.status == RunStatus.RUNNING
    assert run.failure_class == ""
    run.status = RunStatus.SUCCESS
    run.finished_at = timezone.now()
    run.records_fetched = 3
    run.save()
    stored = ScraperRun.objects.get(pk=run.pk)
    assert stored.status == RunStatus.SUCCESS
    assert stored.records_fetched == 3


def test_fx_rate_unique_per_date_and_pair() -> None:
    day = timezone.now().date()
    FxRateDaily.objects.create(rate_date=day, base="EUR", quote="USD", rate=Decimal("1.08"))
    with pytest.raises(IntegrityError):
        FxRateDaily.objects.create(rate_date=day, base="EUR", quote="USD", rate=Decimal("1.09"))


def test_usd_item_price_generated_column() -> None:
    site = make_site()
    listing = Listing.objects.create(
        source_site=site,
        source_listing_key="sku-1",
        canonical_url="https://example.com/sku-1",
        url_hash="a" * 64,
        title_raw="Demo 16TB drive",
        retention_class=RetentionClass.MERCHANT_FACT,
    )
    OfferSnapshot.objects.create(
        listing=listing,
        observed_at=timezone.now(),
        currency="EUR",
        item_price=Decimal("100.00"),
        fx_rate=Decimal("1.080000"),
        fx_pair="EUR/USD",
        fx_rate_date=timezone.now().date(),
        fx_source="frankfurter",
        retention_class=RetentionClass.MERCHANT_FACT,
    )
    snap = OfferSnapshot.objects.get(listing=listing)
    assert snap.usd_item_price == Decimal("108.0000")


def test_listing_is_international_defaults_false() -> None:
    site = make_site()
    listing = Listing.objects.create(
        source_site=site,
        source_listing_key="sku-2",
        canonical_url="https://example.com/sku-2",
        url_hash="b" * 64,
        title_raw="Demo 8TB drive",
        retention_class=RetentionClass.MERCHANT_FACT,
    )
    assert listing.is_international is False


def test_seeded_sources_exist_and_are_disabled() -> None:
    # Migration 0005 seeds the five MS-1 sources + demo, all disabled until
    # their connector lands (MS-1d flips each on as it ships).
    expected = {
        "wd-recertified": SourceTier.T1_MANUFACTURER,
        "seagate-recertified": SourceTier.T1_MANUFACTURER,
        "serverpartdeals": SourceTier.T2_SPECIALIST,
        "goharddrive": SourceTier.T2_SPECIALIST,
        "ebay": SourceTier.T0_OFFICIAL_API,
        "demo": SourceTier.T2_SPECIALIST,
    }
    for key, tier in expected.items():
        config = SourceConfig.objects.get(source_site__normalized_name=key)
        assert config.tier == tier, key
        assert config.enabled is False, key
        assert config.heartbeat_enabled is False, key  # flipped at MS-1d per the design matrix
        assert config.fast_lane is False, key  # flipped at MS-1d (WD/Seagate/eBay only, FR-002)
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
podman compose up -d db
uv run pytest tests/db/test_ops_models.py -v
```

Expected: FAIL — `ImportError: cannot import name 'SourceConfig'`.

- [ ] **Step 4: Implement the ops models**

`src/hw_radar/catalog/models/ops.py`:

```python
# pyright: reportIncompatibleVariableOverride=false
# django-types treats concrete nested Meta classes as incompatible with abstract
# base model Meta classes; Django's model metaclass handles this pattern.
"""Scraper-ops grain (spec §9 "scraper-ops" group): source registry + run records.

SourceConfig is the C.2 per-source scheduling registry as settings rows
(ADR-0016 pattern): every number here is an OQ9-provisional tunable, changed
by UPDATE, not deploy. ScraperRun is the §18.5 observability substrate.
FxRateDaily is the ADR-0008 daily-rate cache. SchedulerCheckpoint persists
in-memory admission state for ERR-007 crash recovery.
"""

from __future__ import annotations

from typing import ClassVar

from django.db import models

from hw_radar.catalog.models.base import TimeStamped
from hw_radar.catalog.models.market import SourceSite


class SourceTier(models.TextChoices):
    T0_OFFICIAL_API = "t0", "T0 — official API"
    T1_MANUFACTURER = "t1", "T1 — manufacturer-direct"
    T2_SPECIALIST = "t2", "T2 — specialist/VAR"
    T3_ANTI_BOT = "t3", "T3 — anti-bot-exposed"
    T4_REFURB_REGIONAL = "t4", "T4 — refurb/regional"


class VolatilityProfile(models.TextChoices):
    DROP_PRONE = "drop_prone", "Drop-prone"
    CHURNING = "churning", "Churning"
    STABLE = "stable", "Stable"


class CheapSignal(models.TextChoices):
    SHOPIFY_PRODUCTS_JSON = "shopify_products_json", "Shopify /products.json"
    WOOCOMMERCE_STORE_API = "woocommerce_store_api", "WooCommerce Store API"
    EBAY_BROWSE = "ebay_browse", "eBay Browse API"
    OCC_JSON = "occ_json", "SAP Commerce OCC JSON"
    BOOTSTRAP_JSON = "bootstrap_json", "Category-page bootstrap JSON"
    NONE = "none", "None"


class LifecycleState(models.TextChoices):
    """ADR-0017 source lifecycle. SKIP is terminal pending human re-review."""

    ACTIVE = "active", "Active"
    BACKING_OFF = "backing_off", "Backing off"
    PAUSED_PENDING_FIX = "paused_pending_fix", "Paused pending fix"
    SKIP = "skip", "Skip (permanent)"


class RunKind(models.TextChoices):
    FULL = "full", "Full pipeline"
    HEARTBEAT = "heartbeat", "Availability heartbeat"
    REFERENCE = "reference", "Reference-catalog ingest"
    PROBE = "probe", "Recovery probe"


class RunStatus(models.TextChoices):
    RUNNING = "running", "Running"
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"


class RunFailureClass(models.TextChoices):
    """§12.1 classification tree, evaluated in this order."""

    TRANSIENT = "transient", "Transient"
    ANTI_BOT = "anti_bot", "Anti-bot / soft block"
    PARSER_ROT = "parser_rot", "Parser rot"
    DEGRADATION = "degradation", "Degradation"
    UNKNOWN = "unknown", "Unknown (escalate)"


class SourceConfig(TimeStamped):
    source_site = models.OneToOneField(
        SourceSite, on_delete=models.PROTECT, related_name="config"
    )
    enabled = models.BooleanField(default=False)
    tier = models.CharField(max_length=2, choices=SourceTier.choices)
    domain = models.CharField(max_length=255)
    cadence_baseline_s = models.PositiveIntegerField()
    cadence_ceiling_s = models.PositiveIntegerField()
    current_interval_s = models.PositiveIntegerField()
    volatility_profile = models.CharField(
        max_length=20, choices=VolatilityProfile.choices, default=VolatilityProfile.STABLE
    )
    cheap_signal = models.CharField(
        max_length=30, choices=CheapSignal.choices, default=CheapSignal.NONE
    )
    # heartbeat_enabled = "a cheap probe gates the full pipeline" (any verified signal);
    # fast_lane = FR-002's drop-prone AND cheap-signal intersection ONLY. Separate on
    # purpose: ServerPartDeals is heartbeat-enabled at T2 cadence but never fast-laned.
    heartbeat_enabled = models.BooleanField(default=False)
    fast_lane = models.BooleanField(default=False)
    lifecycle_state = models.CharField(
        max_length=20, choices=LifecycleState.choices, default=LifecycleState.ACTIVE
    )
    consecutive_failures = models.PositiveIntegerField(default=0)
    consecutive_parser_rot = models.PositiveIntegerField(default=0)
    clean_polls = models.PositiveIntegerField(default=0)
    backoff_until = models.DateTimeField(null=True, blank=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    bucket_rate_per_min = models.FloatField(default=6.0)
    bucket_burst = models.PositiveIntegerField(default=3)
    misfire_grace_s = models.PositiveIntegerField(default=60)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "source_config"
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=models.Q(cadence_ceiling_s__lte=models.F("cadence_baseline_s")),
                name="source_config_ceiling_lte_baseline",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(fast_lane=False)
                    | (
                        models.Q(volatility_profile=VolatilityProfile.DROP_PRONE)
                        & ~models.Q(cheap_signal=CheapSignal.NONE)
                    )
                ),
                name="source_config_fast_lane_eligible",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.source_site.normalized_name} [{self.tier}]"


class ScraperRun(models.Model):
    source_site = models.ForeignKey(SourceSite, on_delete=models.PROTECT, related_name="runs")
    run_kind = models.CharField(max_length=20, choices=RunKind.choices, default=RunKind.FULL)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=RunStatus.choices, default=RunStatus.RUNNING)
    failure_class = models.CharField(
        max_length=20, choices=RunFailureClass.choices, blank=True, default=""
    )
    records_fetched = models.PositiveIntegerField(default=0)
    records_valid = models.PositiveIntegerField(default=0)
    listings_upserted = models.PositiveIntegerField(default=0)
    snapshots_appended = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True, default="")
    detail_json: models.JSONField[dict[str, object]] = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "scraper_runs"
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["source_site", "-started_at"], name="scraper_runs_site_started")
        ]


class FxRateDaily(models.Model):
    """One row per (date, base→quote); ADR-0008 daily Frankfurter rate cache."""

    rate_date = models.DateField()
    base = models.CharField(max_length=3)
    quote = models.CharField(max_length=3, default="USD")
    rate = models.DecimalField(max_digits=12, decimal_places=6)
    source = models.CharField(max_length=50, default="frankfurter")
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "fx_rate_daily"
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["rate_date", "base", "quote"], name="fx_rate_daily_unique_pair_date"
            )
        ]


class SchedulerCheckpoint(TimeStamped):
    """ERR-007: in-memory admission state (token buckets) checkpointed for restart."""

    key = models.CharField(max_length=50, unique=True)
    state_json: models.JSONField[dict[str, object]] = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "scheduler_checkpoint"
```

Schema additions in `src/hw_radar/catalog/models/market.py` — add to `Listing` (after `listing_fingerprint`):

```python
    is_international = models.BooleanField(default=False)
```

and to `OfferSnapshot` (after `fx_source`), with `usd_item_price` mirroring the existing `total_landed_price` GeneratedField pattern:

```python
    usd_item_price = models.GeneratedField(
        expression=models.F("item_price") * Coalesce(models.F("fx_rate"), models.Value(Decimal("1"))),
        output_field=models.DecimalField(max_digits=14, decimal_places=4),
        db_persist=True,
    )
```

Update `src/hw_radar/catalog/models/__init__.py`: add imports + `__all__` entries for `CheapSignal`, `FxRateDaily`, `LifecycleState`, `RunFailureClass`, `RunKind`, `RunStatus`, `SchedulerCheckpoint`, `ScraperRun`, `SourceConfig`, `SourceTier`, `VolatilityProfile` (alphabetical, matching the existing style).

Register in `src/hw_radar/catalog/admin.py` (mirroring existing registrations):

```python
from hw_radar.catalog.models import FxRateDaily, ScraperRun, SourceConfig

admin.site.register(SourceConfig)
admin.site.register(ScraperRun)
admin.site.register(FxRateDaily)
```

- [ ] **Step 5: Generate the schema migration, write the seed migration**

```bash
uv run python manage.py makemigrations catalog --name ops_substrate
```

Review the generated `0004_ops_substrate.py`: it must contain the four new models, the two `SourceConfig` check constraints, `listing.is_international`, and the `usd_item_price` generated column. No hand edits expected (both GeneratedField and CompositePrimaryKey survived makemigrations at MS-0).

`src/hw_radar/catalog/migrations/0005_seed_sources.py` (hand-written data migration; C.2 tier cadences: T0 600/120 · T1 1800/300 · T2 3600/900):

```python
# Seeds the five MS-1 sources + the demo walking-skeleton source. All disabled;
# MS-1d enables each as its connector lands, flips heartbeat_enabled where a cheap
# signal is verified (WD/Seagate/SPD/eBay), and fast_lane strictly per FR-002
# (WD/Seagate/eBay only — SPD is churning, never fast-laned; design 3 matrix).
# Cadence numbers are OQ9-provisional tunables (spec C.2).
from django.db import migrations

SOURCES = [
    # (name, normalized_name, source_type, tier, domain, baseline_s, ceiling_s,
    #  volatility, cheap_signal)
    ("WD Recertified Store", "wd-recertified", "manufacturer_store", "t1",
     "www.westerndigital.com", 1800, 300, "drop_prone", "occ_json"),
    ("Seagate Recertified Store", "seagate-recertified", "manufacturer_store", "t1",
     "www.seagate.com", 1800, 300, "drop_prone", "bootstrap_json"),
    ("ServerPartDeals", "serverpartdeals", "specialist_reseller", "t2",
     "serverpartdeals.com", 3600, 900, "churning", "shopify_products_json"),
    ("goHardDrive", "goharddrive", "specialist_reseller", "t2",
     "www.goharddrive.com", 3600, 900, "churning", "none"),
    ("eBay", "ebay", "marketplace", "t0",
     "api.ebay.com", 600, 120, "drop_prone", "ebay_browse"),
    ("Demo (walking skeleton)", "demo", "other", "t2",
     "demo.invalid", 3600, 900, "stable", "none"),
]


def seed(apps, schema_editor):
    SourceSite = apps.get_model("catalog", "SourceSite")
    SourceConfig = apps.get_model("catalog", "SourceConfig")
    for name, key, source_type, tier, domain, baseline, ceiling, volatility, signal in SOURCES:
        site, _ = SourceSite.objects.get_or_create(
            normalized_name=key, defaults={"name": name, "source_type": source_type}
        )
        SourceConfig.objects.get_or_create(
            source_site=site,
            defaults={
                "tier": tier,
                "domain": domain,
                "cadence_baseline_s": baseline,
                "cadence_ceiling_s": ceiling,
                "current_interval_s": baseline,
                "volatility_profile": volatility,
                "cheap_signal": signal,
                # enabled/fast_lane stay at their False defaults deliberately.
            },
        )


def unseed(apps, schema_editor):
    SourceConfig = apps.get_model("catalog", "SourceConfig")
    keys = [row[1] for row in SOURCES]
    SourceConfig.objects.filter(source_site__normalized_name__in=keys).delete()


class Migration(migrations.Migration):
    dependencies = [("catalog", "0004_ops_substrate")]
    operations = [migrations.RunPython(seed, unseed)]
```

```bash
uv run python manage.py migrate
```

Expected: `Applying catalog.0004_ops_substrate... OK`, `Applying catalog.0005_seed_sources... OK`.

- [ ] **Step 6: Run tests to verify they pass**

```bash
uv run pytest tests/db/test_ops_models.py -v
```

Expected: all PASS. (If `usd_item_price` scale differs, assert against `Decimal("108.0000")` exactly — the column is (14,4).)

- [ ] **Step 7: Gate and commit**

```bash
uv run ruff format . && uv run ruff check . --fix
uv run python -m scripts.check
git add pyproject.toml uv.lock src/hw_radar/catalog tests/db/test_ops_models.py
git commit -m "feat(ops): source registry, scraper_runs, FX cache, checkpoint models (MS-1a T1)"
```

---

### Task 2: Scheduling substrate — buckets, back-off, lifecycle, admission (pure)

**Files:**
- Create: `src/hw_radar/acquisition/__init__.py`, `src/hw_radar/acquisition/scheduling/__init__.py`
- Create: `src/hw_radar/acquisition/scheduling/buckets.py`, `backoff.py`, `lifecycle.py`, `admission.py`
- Test: `tests/unit/test_buckets.py`, `tests/unit/test_backoff.py`, `tests/unit/test_lifecycle.py`, `tests/unit/test_admission.py`

**Interfaces:**
- Consumes: `LifecycleState`, `RunKind` from `hw_radar.catalog.models` (enum values only — these modules touch no DB).
- Produces: `TokenBucket`, `BucketRegistry` (`configure_source`, `admit(source_key, domain, now_s) -> bool`, `to_state()`/`from_state()`); `backoff_delay_s(failures, rand)`, `clamp_retry_after(seconds, baseline_s)`, `interval_after_success(current_s, ceiling_s, clean_polls)`, `interval_after_latency_spike(current_s, baseline_s)`; `LifecycleEvent`, `transition(state, event, consecutive_parser_rot)`; `AdmissionDecision`, `check_admission(...)`. Task 5's `apply.py` and Task 7's poller consume all of these.

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_buckets.py`:

```python
from hw_radar.acquisition.scheduling.buckets import BucketRegistry, TokenBucket


def test_bucket_starts_full_and_depletes() -> None:
    bucket = TokenBucket(capacity=3.0, refill_per_s=1.0 / 60, tokens=3.0, updated_at=0.0)
    assert bucket.acquire(now_s=0.0)
    assert bucket.acquire(now_s=0.0)
    assert bucket.acquire(now_s=0.0)
    assert not bucket.acquire(now_s=0.0)  # burst exhausted


def test_bucket_refills_over_time() -> None:
    bucket = TokenBucket(capacity=3.0, refill_per_s=1.0 / 60, tokens=0.0, updated_at=0.0)
    assert not bucket.acquire(now_s=30.0)  # only 0.5 tokens accrued
    assert bucket.acquire(now_s=90.0)  # 1.5 accrued since t=0 → spend 1


def test_bucket_never_exceeds_capacity() -> None:
    bucket = TokenBucket(capacity=2.0, refill_per_s=10.0, tokens=2.0, updated_at=0.0)
    bucket.refill(now_s=100.0)
    assert bucket.tokens == 2.0


def test_registry_requires_both_levels() -> None:
    registry = BucketRegistry()
    registry.configure_source("src-a", rate_per_min=60.0, burst=1, now_s=0.0)
    registry.configure_source("src-b", rate_per_min=60.0, burst=1, now_s=0.0)
    # Same domain: one tight domain bucket throttles both sources.
    registry.configure_domain("example.com", rate_per_min=60.0, burst=1, now_s=0.0)
    assert registry.admit("src-a", "example.com", now_s=0.0)
    # src-b has its own full source bucket, but the shared domain bucket is empty.
    assert not registry.admit("src-b", "example.com", now_s=0.0)


def test_registry_denial_consumes_no_tokens() -> None:
    registry = BucketRegistry()
    registry.configure_source("src-a", rate_per_min=60.0, burst=1, now_s=0.0)
    registry.configure_domain("example.com", rate_per_min=60.0, burst=0, now_s=0.0)
    assert not registry.admit("src-a", "example.com", now_s=0.0)
    # The failed domain check must not have burned the source token (both-or-neither).
    registry.configure_domain("example.com", rate_per_min=60.0, burst=1, now_s=0.0)
    assert registry.admit("src-a", "example.com", now_s=0.0)


def test_registry_state_round_trip() -> None:
    registry = BucketRegistry()
    registry.configure_source("src-a", rate_per_min=6.0, burst=3, now_s=10.0)
    registry.admit("src-a", "example.com", now_s=10.0)
    restored = BucketRegistry.from_state(registry.to_state())
    assert restored.to_state() == registry.to_state()
```

`tests/unit/test_backoff.py`:

```python
from hw_radar.acquisition.scheduling.backoff import (
    BACKOFF_CAP_S,
    backoff_delay_s,
    clamp_retry_after,
    interval_after_latency_spike,
    interval_after_success,
)


def test_backoff_ladder_doubles_and_caps() -> None:
    # rand()=1.0 exposes the envelope: 10min * 2^failures, capped at 24h (AW-003).
    assert backoff_delay_s(1, rand=lambda: 1.0) == 1200.0
    assert backoff_delay_s(2, rand=lambda: 1.0) == 2400.0
    assert backoff_delay_s(20, rand=lambda: 1.0) == BACKOFF_CAP_S


def test_backoff_is_fully_jittered() -> None:
    # random(0,1) multiplier — rand()=0 collapses the delay (spec C.2 formula).
    assert backoff_delay_s(5, rand=lambda: 0.0) == 0.0


def test_retry_after_clamped_to_1s_and_baseline() -> None:
    assert clamp_retry_after(0.0, baseline_s=3600) == 1.0
    assert clamp_retry_after(120.0, baseline_s=3600) == 120.0
    assert clamp_retry_after(999_999.0, baseline_s=3600) == 3600.0  # AW-002 clamp


def test_auto_ramp_halves_after_four_clean_polls() -> None:
    # AW-004: 4th consecutive clean poll halves the interval, floored at ceiling.
    interval, clean = interval_after_success(3600, ceiling_s=900, clean_polls=3)
    assert (interval, clean) == (1800, 0)  # ramped, counter reset
    interval, clean = interval_after_success(3600, ceiling_s=900, clean_polls=0)
    assert (interval, clean) == (3600, 1)  # counting up, no ramp yet


def test_auto_ramp_floors_at_ceiling() -> None:
    interval, _ = interval_after_success(1000, ceiling_s=900, clean_polls=3)
    assert interval == 900


def test_latency_spike_doubles_interval_capped_at_baseline() -> None:
    # AW-005: slow down, don't stop; never drift slower than baseline.
    assert interval_after_latency_spike(900, baseline_s=3600) == 1800
    assert interval_after_latency_spike(3000, baseline_s=3600) == 3600
```

`tests/unit/test_lifecycle.py`:

```python
import pytest

from hw_radar.acquisition.scheduling.lifecycle import (
    PARSER_ROT_TRIP_THRESHOLD,
    LifecycleEvent,
    transition,
)
from hw_radar.catalog.models import LifecycleState


def test_success_returns_to_active() -> None:
    assert (
        transition(LifecycleState.BACKING_OFF, LifecycleEvent.SUCCESS, consecutive_parser_rot=0)
        == LifecycleState.ACTIVE
    )


def test_transient_never_circuit_breaks() -> None:
    # ERR-001: transients back off but never trip the breaker.
    state = LifecycleState.ACTIVE
    for _ in range(50):
        state = transition(state, LifecycleEvent.TRANSIENT_FAILURE, consecutive_parser_rot=0)
    assert state == LifecycleState.BACKING_OFF


def test_anti_bot_trips_immediately() -> None:
    # ERR-002: circuit-break on the anti_bot verdict.
    assert (
        transition(LifecycleState.ACTIVE, LifecycleEvent.ANTI_BOT, consecutive_parser_rot=0)
        == LifecycleState.PAUSED_PENDING_FIX
    )


def test_parser_rot_trips_only_when_sustained() -> None:
    # AW-006: "sustained parser_rot" — first hit backs off, threshold-th consecutive hit trips.
    first = transition(LifecycleState.ACTIVE, LifecycleEvent.PARSER_ROT, consecutive_parser_rot=0)
    assert first == LifecycleState.BACKING_OFF
    tripped = transition(
        LifecycleState.BACKING_OFF,
        LifecycleEvent.PARSER_ROT,
        consecutive_parser_rot=PARSER_ROT_TRIP_THRESHOLD - 1,
    )
    assert tripped == LifecycleState.PAUSED_PENDING_FIX


def test_paused_recovers_only_via_probe_success() -> None:
    paused = LifecycleState.PAUSED_PENDING_FIX
    assert transition(paused, LifecycleEvent.SUCCESS, consecutive_parser_rot=0) == paused
    assert (
        transition(paused, LifecycleEvent.PROBE_SUCCESS, consecutive_parser_rot=0)
        == LifecycleState.ACTIVE
    )


def test_skip_is_terminal_except_manual_reactivate() -> None:
    skip = LifecycleState.SKIP
    for event in LifecycleEvent:
        if event is LifecycleEvent.MANUAL_REACTIVATE:
            continue
        assert transition(skip, event, consecutive_parser_rot=0) == skip
    assert (
        transition(skip, LifecycleEvent.MANUAL_REACTIVATE, consecutive_parser_rot=0)
        == LifecycleState.ACTIVE
    )


def test_degradation_is_a_signal_not_a_transition() -> None:
    # ERR-004: degradation alerts; it does not change scheduling state.
    assert (
        transition(LifecycleState.ACTIVE, LifecycleEvent.DEGRADATION, consecutive_parser_rot=0)
        == LifecycleState.ACTIVE
    )


@pytest.mark.parametrize("state", list(LifecycleState))
def test_manual_skip_wins_from_any_state(state: LifecycleState) -> None:
    assert (
        transition(state, LifecycleEvent.MANUAL_SKIP, consecutive_parser_rot=0)
        == LifecycleState.SKIP
    )
```

`tests/unit/test_admission.py`:

```python
from datetime import UTC, datetime, timedelta

from hw_radar.acquisition.scheduling.admission import DenyReason, check_admission
from hw_radar.acquisition.scheduling.buckets import BucketRegistry
from hw_radar.catalog.models import LifecycleState, RunKind

NOW = datetime(2026, 7, 5, 12, 0, tzinfo=UTC)


def registry() -> BucketRegistry:
    reg = BucketRegistry()
    reg.configure_source("demo", rate_per_min=60.0, burst=3, now_s=0.0)
    return reg


def admit(**overrides: object):
    kwargs: dict[str, object] = {
        "enabled": True,
        "lifecycle_state": LifecycleState.ACTIVE,
        "run_kind": RunKind.FULL,
        "backoff_until": None,
        "now": NOW,
        "registry": registry(),
        "source_key": "demo",
        "domain": "example.com",
        "now_s": 0.0,
    }
    kwargs.update(overrides)
    return check_admission(**kwargs)  # type: ignore[arg-type]


def test_admits_healthy_source() -> None:
    assert admit().admitted


def test_denies_disabled() -> None:
    decision = admit(enabled=False)
    assert (decision.admitted, decision.reason) == (False, DenyReason.DISABLED)


def test_denies_skip_even_for_probe() -> None:
    decision = admit(lifecycle_state=LifecycleState.SKIP, run_kind=RunKind.PROBE)
    assert decision.reason == DenyReason.SKIPPED


def test_paused_denies_full_but_admits_probe() -> None:
    # ADR-0017: paused_pending_fix runs only the daily recovery probe.
    assert admit(lifecycle_state=LifecycleState.PAUSED_PENDING_FIX).reason == DenyReason.PAUSED
    assert admit(
        lifecycle_state=LifecycleState.PAUSED_PENDING_FIX, run_kind=RunKind.PROBE
    ).admitted


def test_denies_while_backoff_pending() -> None:
    decision = admit(backoff_until=NOW + timedelta(minutes=5))
    assert decision.reason == DenyReason.BACKING_OFF


def test_backoff_expiry_admits() -> None:
    assert admit(backoff_until=NOW - timedelta(seconds=1)).admitted


def test_denies_on_exhausted_bucket() -> None:
    reg = BucketRegistry()
    reg.configure_source("demo", rate_per_min=60.0, burst=0, now_s=0.0)
    decision = admit(registry=reg)
    assert decision.reason == DenyReason.BUCKET
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/test_buckets.py tests/unit/test_backoff.py tests/unit/test_lifecycle.py tests/unit/test_admission.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'hw_radar.acquisition'`.

- [ ] **Step 3: Implement the pure scheduling modules**

`src/hw_radar/acquisition/__init__.py` and `src/hw_radar/acquisition/scheduling/__init__.py`: empty package markers (docstring only).

`src/hw_radar/acquisition/scheduling/buckets.py`:

```python
"""Two-level token buckets (per-source + per-domain), C.2.

Pure and clock-injected: callers pass `now_s` from a monotonic-ish clock; the
poller uses `time.monotonic()`. Serializable for the ERR-007 checkpoint.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

DOMAIN_RATE_PER_MIN = 30.0  # politeness default per domain; OQ9-provisional
DOMAIN_BURST = 10


@dataclass
class TokenBucket:
    capacity: float
    refill_per_s: float
    tokens: float
    updated_at: float

    def refill(self, now_s: float) -> None:
        elapsed = max(0.0, now_s - self.updated_at)
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_per_s)
        self.updated_at = now_s

    def can_acquire(self, now_s: float, cost: float = 1.0) -> bool:
        self.refill(now_s)
        return self.tokens >= cost

    def acquire(self, now_s: float, cost: float = 1.0) -> bool:
        if not self.can_acquire(now_s, cost):
            return False
        self.tokens -= cost
        return True


def _bucket(rate_per_min: float, burst: int, now_s: float) -> TokenBucket:
    return TokenBucket(
        capacity=float(burst), refill_per_s=rate_per_min / 60.0, tokens=float(burst), updated_at=now_s
    )


@dataclass
class BucketRegistry:
    source_buckets: dict[str, TokenBucket] = field(default_factory=dict)
    domain_buckets: dict[str, TokenBucket] = field(default_factory=dict)

    def configure_source(self, key: str, *, rate_per_min: float, burst: int, now_s: float) -> None:
        self.source_buckets[key] = _bucket(rate_per_min, burst, now_s)

    def configure_domain(self, domain: str, *, rate_per_min: float, burst: int, now_s: float) -> None:
        self.domain_buckets[domain] = _bucket(rate_per_min, burst, now_s)

    def _domain(self, domain: str, now_s: float) -> TokenBucket:
        if domain not in self.domain_buckets:
            self.configure_domain(
                domain, rate_per_min=DOMAIN_RATE_PER_MIN, burst=DOMAIN_BURST, now_s=now_s
            )
        return self.domain_buckets[domain]

    def admit(self, source_key: str, domain: str, now_s: float) -> bool:
        """Both-or-neither: a denial must not burn tokens at the other level."""
        source = self.source_buckets.get(source_key)
        if source is None:
            return False
        domain_bucket = self._domain(domain, now_s)
        if not (source.can_acquire(now_s) and domain_bucket.can_acquire(now_s)):
            return False
        source.acquire(now_s)
        domain_bucket.acquire(now_s)
        return True

    def to_state(self) -> dict[str, object]:
        def dump(buckets: dict[str, TokenBucket]) -> dict[str, dict[str, float]]:
            return {
                key: {
                    "capacity": b.capacity,
                    "refill_per_s": b.refill_per_s,
                    "tokens": b.tokens,
                    "updated_at": b.updated_at,
                }
                for key, b in buckets.items()
            }

        return {"sources": dump(self.source_buckets), "domains": dump(self.domain_buckets)}

    @classmethod
    def from_state(cls, state: dict[str, object]) -> BucketRegistry:
        def load(raw: object) -> dict[str, TokenBucket]:
            out: dict[str, TokenBucket] = {}
            for key, values in cast("dict[str, dict[str, float]]", raw).items():
                out[key] = TokenBucket(**values)
            return out

        return cls(
            source_buckets=load(state.get("sources", {})),
            domain_buckets=load(state.get("domains", {})),
        )
```

`src/hw_radar/acquisition/scheduling/backoff.py`:

```python
"""Back-off ladder, Retry-After clamp, auto-ramp, latency-spike math (C.2, AW-002..005).

Pure functions with injected randomness. All numbers OQ9-provisional.
"""

from __future__ import annotations

from collections.abc import Callable

BACKOFF_BASE_S = 600.0  # 10 min
BACKOFF_CAP_S = 86_400.0  # 24 h
RETRY_AFTER_MIN_S = 1.0
AUTO_RAMP_CLEAN_POLLS = 4


def backoff_delay_s(consecutive_failures: int, rand: Callable[[], float]) -> float:
    """AW-003: random(0,1) × min(24 h, 10 min × 2^failures)."""
    envelope = min(BACKOFF_CAP_S, BACKOFF_BASE_S * 2**consecutive_failures)
    return rand() * envelope


def clamp_retry_after(retry_after_s: float, baseline_s: int) -> float:
    """AW-002: honor Retry-After verbatim, clamped to 1 s..baseline."""
    return min(max(retry_after_s, RETRY_AFTER_MIN_S), float(baseline_s))


def interval_after_success(
    current_s: int, ceiling_s: int, clean_polls: int
) -> tuple[int, int]:
    """AW-004 earned auto-ramp: the Nth consecutive clean poll halves the interval.

    Returns (new_interval_s, new_clean_polls); the counter resets on ramp.
    """
    polls = clean_polls + 1
    if polls >= AUTO_RAMP_CLEAN_POLLS:
        return max(ceiling_s, current_s // 2), 0
    return current_s, polls


def interval_after_latency_spike(current_s: int, baseline_s: int) -> int:
    """AW-005: halve cadence (double the interval), never slower than baseline."""
    return min(baseline_s, current_s * 2)
```

`src/hw_radar/acquisition/scheduling/lifecycle.py`:

```python
"""ADR-0017 source lifecycle as a pure transition function.

States live in catalog.models.LifecycleState (they persist on SourceConfig);
this module owns the legal transitions. Degradation is deliberately a signal,
not a transition (ERR-004). Transients never trip the breaker (ERR-001).
"""

from __future__ import annotations

from enum import StrEnum

from hw_radar.catalog.models import LifecycleState

PARSER_ROT_TRIP_THRESHOLD = 2  # consecutive parser_rot runs before pausing; tunable


class LifecycleEvent(StrEnum):
    SUCCESS = "success"
    TRANSIENT_FAILURE = "transient_failure"
    ANTI_BOT = "anti_bot"
    PARSER_ROT = "parser_rot"
    DEGRADATION = "degradation"
    UNKNOWN_FAILURE = "unknown_failure"
    PROBE_SUCCESS = "probe_success"
    PROBE_FAILURE = "probe_failure"
    MANUAL_SKIP = "manual_skip"
    MANUAL_REACTIVATE = "manual_reactivate"


def transition(
    state: LifecycleState, event: LifecycleEvent, *, consecutive_parser_rot: int
) -> LifecycleState:
    if event is LifecycleEvent.MANUAL_SKIP:
        return LifecycleState.SKIP
    if state is LifecycleState.SKIP:
        if event is LifecycleEvent.MANUAL_REACTIVATE:
            return LifecycleState.ACTIVE
        return LifecycleState.SKIP
    if event is LifecycleEvent.MANUAL_REACTIVATE:
        return LifecycleState.ACTIVE
    if state is LifecycleState.PAUSED_PENDING_FIX:
        if event is LifecycleEvent.PROBE_SUCCESS:
            return LifecycleState.ACTIVE
        return LifecycleState.PAUSED_PENDING_FIX
    match event:
        case LifecycleEvent.SUCCESS | LifecycleEvent.PROBE_SUCCESS:
            return LifecycleState.ACTIVE
        case LifecycleEvent.ANTI_BOT:
            return LifecycleState.PAUSED_PENDING_FIX
        case LifecycleEvent.PARSER_ROT:
            if consecutive_parser_rot + 1 >= PARSER_ROT_TRIP_THRESHOLD:
                return LifecycleState.PAUSED_PENDING_FIX
            return LifecycleState.BACKING_OFF
        case LifecycleEvent.TRANSIENT_FAILURE | LifecycleEvent.UNKNOWN_FAILURE:
            return LifecycleState.BACKING_OFF
        case LifecycleEvent.DEGRADATION | LifecycleEvent.PROBE_FAILURE:
            return state
        case LifecycleEvent.MANUAL_SKIP | LifecycleEvent.MANUAL_REACTIVATE:  # pragma: no cover
            raise AssertionError("handled above")
```

`src/hw_radar/acquisition/scheduling/admission.py`:

```python
"""Ordered admission gate for a source run (C.2; ADR-0016's ordered-gate pattern).

Order: cheapest/most-final check first — disabled → SKIP → paused (probe-only)
→ back-off window → token buckets. The buckets are checked last so a denial
higher up never burns tokens.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from hw_radar.acquisition.scheduling.buckets import BucketRegistry
from hw_radar.catalog.models import LifecycleState, RunKind


class DenyReason(StrEnum):
    DISABLED = "disabled"
    SKIPPED = "skipped"
    PAUSED = "paused_pending_fix"
    BACKING_OFF = "backing_off"
    BUCKET = "bucket_exhausted"


@dataclass(frozen=True)
class AdmissionDecision:
    admitted: bool
    reason: DenyReason | None = None


def check_admission(
    *,
    enabled: bool,
    lifecycle_state: LifecycleState,
    run_kind: RunKind,
    backoff_until: datetime | None,
    now: datetime,
    registry: BucketRegistry,
    source_key: str,
    domain: str,
    now_s: float,
) -> AdmissionDecision:
    if not enabled:
        return AdmissionDecision(False, DenyReason.DISABLED)
    if lifecycle_state is LifecycleState.SKIP:
        return AdmissionDecision(False, DenyReason.SKIPPED)
    if lifecycle_state is LifecycleState.PAUSED_PENDING_FIX and run_kind is not RunKind.PROBE:
        return AdmissionDecision(False, DenyReason.PAUSED)
    if backoff_until is not None and backoff_until > now:
        return AdmissionDecision(False, DenyReason.BACKING_OFF)
    if not registry.admit(source_key, domain, now_s):
        return AdmissionDecision(False, DenyReason.BUCKET)
    return AdmissionDecision(True)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/test_buckets.py tests/unit/test_backoff.py tests/unit/test_lifecycle.py tests/unit/test_admission.py -v
```

Expected: all PASS.

- [ ] **Step 5: Gate and commit**

```bash
uv run ruff format . && uv run ruff check . --fix
uv run python -m scripts.check
git add src/hw_radar/acquisition tests/unit/test_buckets.py tests/unit/test_backoff.py tests/unit/test_lifecycle.py tests/unit/test_admission.py
git commit -m "feat(scheduling): token buckets, back-off ladder, ADR-0017 lifecycle, admission gate (MS-1a T2)"
```

---

### Task 3: Adapter contracts + §12.1 failure classifier

**Files:**
- Create: `src/hw_radar/acquisition/contracts.py`, `src/hw_radar/acquisition/classify.py`
- Test: `tests/unit/test_contracts.py`, `tests/unit/test_classify.py`

**Interfaces:**
- Consumes: `RunFailureClass` from `hw_radar.catalog.models`.
- Produces: `RawItem`, `RawBatch`, `ParsedListing`, `NormalizedListing`, `SourceAdapter` (Protocol), `ListingResolver` (Protocol), `NullResolver`; `classify_exception(exc)`, `classify_response(...)`. Task 5's pipeline and every MS-1d connector consume these exact names.

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_contracts.py`:

```python
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from hw_radar.acquisition.contracts import (
    NullResolver,
    ParsedListing,
    RawBatch,
    RawItem,
)


def test_parsed_listing_coerces_and_validates() -> None:
    listing = ParsedListing(
        source_listing_key="sku-1",
        url="https://example.com/sku-1",
        title="Demo 16TB",
        price=Decimal("199.99"),
    )
    assert listing.currency == "USD"
    assert listing.ships_from_country == "US"
    assert listing.attrs == {}


def test_parsed_listing_rejects_negative_price() -> None:
    with pytest.raises(ValidationError):
        ParsedListing(
            source_listing_key="sku-1",
            url="https://example.com/sku-1",
            title="Demo",
            price=Decimal("-1"),
        )


def test_raw_batch_holds_items() -> None:
    batch = RawBatch(
        source="demo",
        fetched_at=datetime(2026, 7, 5, tzinfo=UTC),
        items=[RawItem(url="https://example.com", payload_text="<html></html>")],
    )
    assert batch.items[0].http_status == 200


def test_null_resolver_is_a_no_op() -> None:
    # MS-1a stub: listings persist at grain=none; MS-1b swaps in the real resolver.
    NullResolver().resolve_listing(listing_id=123)
```

`tests/unit/test_classify.py`:

```python
import pytest

from hw_radar.acquisition.classify import classify_exception, classify_response
from hw_radar.catalog.models import RunFailureClass


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (500, RunFailureClass.TRANSIENT),
        (502, RunFailureClass.TRANSIENT),
        (504, RunFailureClass.TRANSIENT),
        (408, RunFailureClass.TRANSIENT),
        (401, RunFailureClass.ANTI_BOT),
        (403, RunFailureClass.ANTI_BOT),
        (429, RunFailureClass.ANTI_BOT),
        (503, RunFailureClass.ANTI_BOT),  # §12.1 puts 503 in the anti_bot family
    ],
)
def test_status_classification(status: int, expected: RunFailureClass) -> None:
    assert (
        classify_response(
            http_status=status,
            content_type="text/html",
            expected_json=False,
            body_text="",
            median_body_bytes=None,
        )
        == expected
    )


def test_json_endpoint_answering_html_is_anti_bot() -> None:
    # ERR-002: a JSON endpoint returning text/html is a challenge interstitial.
    verdict = classify_response(
        http_status=200,
        content_type="text/html",
        expected_json=True,
        body_text="<html>checking your browser</html>",
        median_body_bytes=None,
    )
    assert verdict == RunFailureClass.ANTI_BOT


def test_challenge_markers_reclassify_a_200() -> None:
    verdict = classify_response(
        http_status=200,
        content_type="text/html",
        expected_json=False,
        body_text="<script src='/cdn-cgi/challenge-platform/x.js'></script>",
        median_body_bytes=None,
    )
    assert verdict == RunFailureClass.ANTI_BOT


def test_body_size_outlier_is_soft_block() -> None:
    # EC-007: HTTP 200 but <20% of the rolling median body size.
    verdict = classify_response(
        http_status=200,
        content_type="text/html",
        expected_json=False,
        body_text="x" * 100,
        median_body_bytes=10_000,
    )
    assert verdict == RunFailureClass.ANTI_BOT


def test_healthy_200_returns_none() -> None:
    assert (
        classify_response(
            http_status=200,
            content_type="application/json",
            expected_json=True,
            body_text='{"items": []}' * 100,
            median_body_bytes=1000,
        )
        is None
    )


def test_network_exceptions_are_transient() -> None:
    assert classify_exception(TimeoutError()) == RunFailureClass.TRANSIENT
    assert classify_exception(OSError("dns")) == RunFailureClass.TRANSIENT


def test_unexpected_exception_is_unknown() -> None:
    assert classify_exception(ValueError("boom")) == RunFailureClass.UNKNOWN
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/test_contracts.py tests/unit/test_classify.py -v
```

Expected: FAIL — `ModuleNotFoundError` for both modules.

- [ ] **Step 3: Implement contracts and classifier**

`src/hw_radar/acquisition/contracts.py`:

```python
"""C.1 adapter contract: Pydantic I/O models + structural protocols.

Adapters own fetch/parse only; normalization (FX), resolution, and persistence
are pipeline-owned so every source shares one code path (spec C.1: "no
per-source code beyond the adapter").
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from hw_radar.catalog.models import RunKind


class RawItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    url: str
    http_status: int = 200
    content_type: str = "application/json"
    payload_json: dict[str, object] | None = None
    payload_text: str | None = None


class RawBatch(BaseModel):
    source: str
    fetched_at: datetime
    items: list[RawItem] = Field(default_factory=list)


class ParsedListing(BaseModel):
    source_listing_key: str
    url: str
    title: str
    price: Decimal = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    shipping_price: Decimal | None = None
    stock_status: str = "unknown"
    quantity_available: int | None = None
    seller_name: str = ""
    condition_label: str = ""
    ships_from_country: str = "US"
    attrs: dict[str, object] = Field(default_factory=dict)


class NormalizedListing(ParsedListing):
    """ParsedListing + the ADR-0008 FX stamp + the FR-004 international flag."""

    fx_rate: Decimal
    fx_pair: str
    fx_rate_date: date
    fx_source: str
    is_international: bool


class SourceAdapter(Protocol):
    name: str
    site_key: str
    run_kind: RunKind
    expects_json: bool  # drives the anti_bot "JSON endpoint answered text/html" check

    async def fetch(self) -> RawBatch: ...

    def parse(self, batch: RawBatch) -> list[ParsedListing]: ...


class ListingResolver(Protocol):
    def resolve_listing(self, listing_id: int) -> None: ...


class NullResolver:
    """MS-1a stub: listings stay at grain=none. MS-1b installs the ADR-0019 resolver."""

    def resolve_listing(self, listing_id: int) -> None:
        return None
```

`src/hw_radar/acquisition/classify.py`:

```python
"""§12.1 failure classification (evaluated in tree order) + EC-007 soft-block signals.

transient → anti_bot → parser_rot → degradation → UNKNOWN. This module covers
the response/exception half; parser_rot is asserted by the pipeline when a 200
authentic page fails extraction, and degradation is computed from run metrics.
"""

from __future__ import annotations

from hw_radar.catalog.models import RunFailureClass

TRANSIENT_STATUSES = frozenset({408, 500, 502, 504})
ANTI_BOT_STATUSES = frozenset({401, 403, 429, 503})
CHALLENGE_MARKERS = (
    "challenge-platform",  # Cloudflare
    "cf-chl",
    "cf_chl",
    "datadome",
    "captcha",
    "checking your browser",
)
SOFT_BLOCK_BODY_RATIO = 0.2  # EC-007 body-size outlier threshold


def classify_exception(exc: Exception) -> RunFailureClass:
    if isinstance(exc, TimeoutError | ConnectionError | OSError):
        return RunFailureClass.TRANSIENT
    return RunFailureClass.UNKNOWN


def classify_response(
    *,
    http_status: int,
    content_type: str,
    expected_json: bool,
    body_text: str,
    median_body_bytes: int | None,
) -> RunFailureClass | None:
    """Classify a completed HTTP response; None means healthy-so-far."""
    if http_status in TRANSIENT_STATUSES:
        return RunFailureClass.TRANSIENT
    if http_status in ANTI_BOT_STATUSES:
        return RunFailureClass.ANTI_BOT
    if expected_json and "json" not in content_type:
        return RunFailureClass.ANTI_BOT
    lowered = body_text.lower()
    if any(marker in lowered for marker in CHALLENGE_MARKERS):
        return RunFailureClass.ANTI_BOT
    if (
        median_body_bytes is not None
        and median_body_bytes > 0
        and len(body_text) < median_body_bytes * SOFT_BLOCK_BODY_RATIO
    ):
        return RunFailureClass.ANTI_BOT
    if http_status >= 400:
        return RunFailureClass.UNKNOWN
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/test_contracts.py tests/unit/test_classify.py -v
```

Expected: all PASS.

- [ ] **Step 5: Gate and commit**

```bash
uv run ruff format . && uv run ruff check . --fix
uv run python -m scripts.check
git add src/hw_radar/acquisition/contracts.py src/hw_radar/acquisition/classify.py tests/unit/test_contracts.py tests/unit/test_classify.py
git commit -m "feat(acquisition): adapter contracts + 12.1 failure classifier (MS-1a T3)"
```

---

### Task 4: FX service (ADR-0008)

**Files:**
- Create: `src/hw_radar/acquisition/fx.py`
- Test: `tests/unit/test_fx_stamp.py` (identity path, no DB), `tests/db/test_fx_service.py`

**Interfaces:**
- Consumes: `ParsedListing`/`NormalizedListing` (Task 3), `FxRateDaily` (Task 1).
- Produces: `stamp(parsed, observed_date) -> NormalizedListing` (raises `MissingRateError`), `refresh_daily(currencies, client=None) -> int` (async), constants `DEFAULT_CURRENCIES`, `MAX_RATE_AGE_DAYS`. Task 5's pipeline and Task 7's daily job consume these.

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_fx_stamp.py`:

```python
from datetime import date
from decimal import Decimal

from hw_radar.acquisition.contracts import ParsedListing
from hw_radar.acquisition.fx import stamp


def usd_listing(country: str = "US") -> ParsedListing:
    return ParsedListing(
        source_listing_key="sku-1",
        url="https://example.com/sku-1",
        title="Demo 16TB",
        price=Decimal("199.99"),
        ships_from_country=country,
    )


def test_usd_listing_gets_identity_stamp_without_db() -> None:
    # FR-004 auditability: USD rows still carry a stored rate (identity).
    normalized = stamp(usd_listing(), observed_date=date(2026, 7, 5))
    assert normalized.fx_rate == Decimal("1")
    assert normalized.fx_pair == "USD/USD"
    assert normalized.fx_source == "identity"
    assert normalized.fx_rate_date == date(2026, 7, 5)
    assert normalized.is_international is False


def test_international_flag_follows_ship_origin_not_currency() -> None:
    # EC-003: a USD-priced listing shipping from abroad is still international.
    normalized = stamp(usd_listing(country="DE"), observed_date=date(2026, 7, 5))
    assert normalized.is_international is True
```

`tests/db/test_fx_service.py`:

```python
import asyncio
from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest

from hw_radar.acquisition.contracts import ParsedListing
from hw_radar.acquisition.fx import MissingRateError, refresh_daily, stamp
from hw_radar.catalog.models import FxRateDaily

pytestmark = pytest.mark.django_db


def eur_listing() -> ParsedListing:
    return ParsedListing(
        source_listing_key="sku-eu",
        url="https://example.de/sku-eu",
        title="Demo 16TB (EU)",
        price=Decimal("100.00"),
        currency="EUR",
        ships_from_country="DE",
    )


def test_stamp_uses_newest_rate_on_or_before_observed_date() -> None:
    FxRateDaily.objects.create(rate_date=date(2026, 7, 1), base="EUR", rate=Decimal("1.05"))
    FxRateDaily.objects.create(rate_date=date(2026, 7, 4), base="EUR", rate=Decimal("1.08"))
    normalized = stamp(eur_listing(), observed_date=date(2026, 7, 5))
    assert normalized.fx_rate == Decimal("1.08")
    assert normalized.fx_pair == "EUR/USD"
    assert normalized.fx_rate_date == date(2026, 7, 4)
    assert normalized.is_international is True


def test_stamp_raises_when_no_rate_cached() -> None:
    with pytest.raises(MissingRateError):
        stamp(eur_listing(), observed_date=date(2026, 7, 5))


def test_stamp_rejects_stale_rate() -> None:
    # ADR-0008 is a *daily* rate; a weeks-old rate must not silently stamp.
    FxRateDaily.objects.create(rate_date=date(2026, 5, 1), base="EUR", rate=Decimal("1.02"))
    with pytest.raises(MissingRateError):
        stamp(eur_listing(), observed_date=date(2026, 7, 5))


@pytest.mark.django_db(transaction=True, serialized_rollback=True)
def test_refresh_daily_fetches_and_upserts() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        base = request.url.params["base"]
        return httpx.Response(
            200, json={"base": base, "date": "2026-07-04", "rates": {"USD": 1.0842}}
        )

    transport = httpx.MockTransport(handler)

    async def drive() -> int:
        async with httpx.AsyncClient(transport=transport) as client:
            return await refresh_daily(("EUR", "GBP"), client=client)

    stored = asyncio.run(drive())
    assert stored == 2
    row = FxRateDaily.objects.get(base="EUR", rate_date=date(2026, 7, 4))
    assert row.rate == Decimal("1.0842")
    assert row.quote == "USD"
    # Idempotent: a second refresh updates, never duplicates.
    asyncio.run(drive())
    assert FxRateDaily.objects.filter(base="EUR").count() == 1
```

> `refresh_daily` writes through `sync_to_async` threads, hence `transaction=True`; `serialized_rollback=True` restores the migration-seeded rows the truncation would otherwise destroy.

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/test_fx_stamp.py tests/db/test_fx_service.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'hw_radar.acquisition.fx'`.

- [ ] **Step 3: Implement the FX service**

`src/hw_radar/acquisition/fx.py`:

```python
"""ADR-0008 currency normalization: Frankfurter daily-rate cache + per-listing stamp.

USD listings stamp identity (rate 1, source "identity") so FR-004's "100%
of observations carry a stored rate" is auditable by query, not by absence.
The international flag follows ship-origin, not currency (EC-003).
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import cast

import httpx
from asgiref.sync import sync_to_async

from hw_radar.acquisition.contracts import NormalizedListing, ParsedListing
from hw_radar.catalog.models import FxRateDaily

FRANKFURTER_BASE_URL = "https://api.frankfurter.dev/v1"
DEFAULT_CURRENCIES: tuple[str, ...] = ("EUR", "GBP", "CAD")
MAX_RATE_AGE_DAYS = 7  # a "daily" rate older than this refuses to stamp
HTTP_TIMEOUT_S = 10.0
HOME_COUNTRY = "US"


class MissingRateError(LookupError):
    """No usable cached rate for (currency, observed_date)."""


def stamp(parsed: ParsedListing, observed_date: date) -> NormalizedListing:
    is_international = parsed.ships_from_country != HOME_COUNTRY
    if parsed.currency == "USD":
        return NormalizedListing(
            **parsed.model_dump(),
            fx_rate=Decimal("1"),
            fx_pair="USD/USD",
            fx_rate_date=observed_date,
            fx_source="identity",
            is_international=is_international,
        )
    row = (
        FxRateDaily.objects.filter(
            base=parsed.currency, quote="USD", rate_date__lte=observed_date
        )
        .order_by("-rate_date")
        .first()
    )
    if row is None or row.rate_date < observed_date - timedelta(days=MAX_RATE_AGE_DAYS):
        raise MissingRateError(f"no fresh {parsed.currency}/USD rate on {observed_date}")
    return NormalizedListing(
        **parsed.model_dump(),
        fx_rate=row.rate,
        fx_pair=f"{parsed.currency}/USD",
        fx_rate_date=row.rate_date,
        fx_source=row.source,
        is_international=is_international,
    )


def _store_rate(base: str, rate_date: date, rate: Decimal) -> None:
    FxRateDaily.objects.update_or_create(
        rate_date=rate_date, base=base, quote="USD", defaults={"rate": rate}
    )


async def refresh_daily(
    currencies: tuple[str, ...] = DEFAULT_CURRENCIES, *, client: httpx.AsyncClient | None = None
) -> int:
    """Fetch base→USD for each currency; upsert the daily cache; return count stored."""
    owns_client = client is None
    active = client or httpx.AsyncClient(timeout=HTTP_TIMEOUT_S)
    try:
        stored = 0
        for base in currencies:
            response = await active.get(
                f"{FRANKFURTER_BASE_URL}/latest", params={"base": base, "symbols": "USD"}
            )
            response.raise_for_status()
            data = cast("dict[str, object]", response.json())
            rate_date = date.fromisoformat(cast("str", data["date"]))
            rate = Decimal(str(cast("dict[str, float]", data["rates"])["USD"]))
            await sync_to_async(_store_rate)(base, rate_date, rate)
            stored += 1
        return stored
    finally:
        if owns_client:
            await active.aclose()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/test_fx_stamp.py tests/db/test_fx_service.py -v
```

Expected: all PASS.

- [ ] **Step 5: Gate and commit**

```bash
uv run ruff format . && uv run ruff check . --fix
uv run python -m scripts.check
git add src/hw_radar/acquisition/fx.py tests/unit/test_fx_stamp.py tests/db/test_fx_service.py
git commit -m "feat(fx): Frankfurter daily-rate cache + ADR-0008 observation stamping (MS-1a T4)"
```

---

### Task 5: Persist stage, lifecycle application, checkpoint, pipeline runner

**Files:**
- Create: `src/hw_radar/acquisition/persist.py`, `src/hw_radar/acquisition/scheduling/apply.py`, `src/hw_radar/acquisition/scheduling/checkpoint.py`, `src/hw_radar/acquisition/pipeline.py`
- Test: `tests/db/test_persist.py`, `tests/db/test_checkpoint.py`, `tests/db/test_pipeline.py`

**Interfaces:**
- Consumes: everything from Tasks 1–4.
- Produces: `persist.upsert_listing(site, normalized, retention_class) -> tuple[Listing, bool]`, `persist.append_snapshot(listing, normalized, observed_at, raw=None) -> OfferSnapshot`, `persist.store_raw(item, fetched_at, retention_class) -> RawPayload`; `apply.RunOutcome`, `apply.apply_run_outcome(config, outcome, now, rand)`; `checkpoint.save_buckets(registry)`, `checkpoint.load_buckets(now_s) -> BucketRegistry`; `pipeline.run_source(adapter, resolver) -> tuple[ScraperRun, RunOutcome]`. Task 7's poller composes admission → `run_source` → `apply_run_outcome`.

- [ ] **Step 1: Write the failing tests**

`tests/db/test_persist.py`:

```python
from datetime import UTC, datetime, date
from decimal import Decimal

import pytest
from django.utils import timezone

from hw_radar.acquisition.contracts import NormalizedListing, RawItem
from hw_radar.acquisition.persist import append_snapshot, store_raw, upsert_listing
from hw_radar.catalog.models import (
    Listing,
    OfferSnapshot,
    RetentionClass,
    SourceSite,
    SourceType,
)

pytestmark = pytest.mark.django_db


def site() -> SourceSite:
    return SourceSite.objects.get(normalized_name="demo")  # seeded by migration 0005


def normalized(key: str = "sku-1", title: str = "Demo 16TB") -> NormalizedListing:
    return NormalizedListing(
        source_listing_key=key,
        url=f"https://demo.invalid/{key}",
        title=title,
        price=Decimal("199.99"),
        fx_rate=Decimal("1"),
        fx_pair="USD/USD",
        fx_rate_date=date(2026, 7, 5),
        fx_source="identity",
        is_international=False,
        stock_status="in_stock",
    )


def test_rerun_appends_snapshots_never_duplicates_listings() -> None:
    # DR-005 at substrate level: the MS-1 acceptance invariant.
    s = site()
    listing1, created1 = upsert_listing(s, normalized(), RetentionClass.MERCHANT_FACT)
    append_snapshot(listing1, normalized(), observed_at=timezone.now())
    listing2, created2 = upsert_listing(s, normalized(), RetentionClass.MERCHANT_FACT)
    append_snapshot(listing2, normalized(), observed_at=timezone.now())
    assert (created1, created2) == (True, False)
    assert listing1.pk == listing2.pk
    assert Listing.objects.filter(source_site=s).count() == 1
    assert OfferSnapshot.objects.filter(listing=listing1).count() == 2


def test_upsert_refreshes_mutable_fields() -> None:
    s = site()
    upsert_listing(s, normalized(), RetentionClass.MERCHANT_FACT)
    listing, _ = upsert_listing(s, normalized(title="Demo 16TB — price drop"), RetentionClass.MERCHANT_FACT)
    assert listing.title_raw == "Demo 16TB — price drop"


def test_snapshot_carries_fx_stamp_and_stock() -> None:
    s = site()
    listing, _ = upsert_listing(s, normalized(), RetentionClass.MERCHANT_FACT)
    snap = append_snapshot(listing, normalized(), observed_at=timezone.now())
    assert snap.fx_pair == "USD/USD"
    assert snap.fx_source == "identity"
    assert snap.stock_status == "in_stock"
    assert snap.retention_class == RetentionClass.MERCHANT_FACT


def test_store_raw_hashes_content() -> None:
    item = RawItem(url="https://demo.invalid/page", payload_text="<html>x</html>")
    raw = store_raw(item, fetched_at=datetime(2026, 7, 5, tzinfo=UTC), retention_class=RetentionClass.MERCHANT_FACT)
    assert len(raw.content_hash) == 64
    assert raw.http_status == 200
```

`tests/db/test_checkpoint.py`:

```python
import pytest

from hw_radar.acquisition.scheduling.buckets import BucketRegistry
from hw_radar.acquisition.scheduling.checkpoint import load_buckets, save_buckets

pytestmark = pytest.mark.django_db


def test_checkpoint_round_trip_rebases_clock() -> None:
    registry = BucketRegistry()
    registry.configure_source("demo", rate_per_min=6.0, burst=3, now_s=100.0)
    registry.admit("demo", "demo.invalid", now_s=100.0)
    save_buckets(registry)

    restored = load_buckets(now_s=5.0)  # fresh process: monotonic clock restarted
    bucket = restored.source_buckets["demo"]
    assert bucket.tokens == 2.0  # spent token survived the restart
    # Rebase: stale monotonic timestamps from the dead process must not grant
    # a huge refill credit in the new one.
    assert bucket.updated_at == 5.0


def test_load_without_checkpoint_returns_empty_registry() -> None:
    registry = load_buckets(now_s=0.0)
    assert registry.source_buckets == {}
```

`tests/db/test_pipeline.py` (a fake in-test adapter proves the runner before Scrapy exists):

```python
import asyncio
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from hw_radar.acquisition.contracts import NullResolver, ParsedListing, RawBatch, RawItem
from hw_radar.acquisition.pipeline import run_source
from hw_radar.acquisition.scheduling.apply import RunOutcome
from hw_radar.acquisition.scheduling.lifecycle import LifecycleEvent
from hw_radar.catalog.models import (
    Listing,
    OfferSnapshot,
    RunFailureClass,
    RunKind,
    RunStatus,
    ScraperRun,
)

# transaction=True: run_source writes from sync_to_async threads.
# serialized_rollback=True: TransactionTestCase truncation would otherwise delete
# the migration-0005 seed rows for every later test in the session.
pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)

FETCHED_AT = datetime(2026, 7, 5, 12, 0, tzinfo=UTC)


class FakeAdapter:
    name = "fake"
    site_key = "demo"
    run_kind = RunKind.FULL
    expects_json = True

    def __init__(self, items: list[RawItem], parsed: list[ParsedListing]) -> None:
        self._items = items
        self._parsed = parsed

    async def fetch(self) -> RawBatch:
        return RawBatch(source=self.name, fetched_at=FETCHED_AT, items=self._items)

    def parse(self, batch: RawBatch) -> list[ParsedListing]:
        return self._parsed


def ok_item() -> RawItem:
    return RawItem(url="https://demo.invalid/a", payload_json={"sku": "a"})


def ok_parsed() -> ParsedListing:
    return ParsedListing(
        source_listing_key="sku-a",
        url="https://demo.invalid/a",
        title="Demo 8TB",
        price=Decimal("99.99"),
    )


def test_success_path_persists_and_reports() -> None:
    adapter = FakeAdapter([ok_item()], [ok_parsed()])
    run, outcome = asyncio.run(run_source(adapter, NullResolver()))
    assert run.status == RunStatus.SUCCESS
    assert outcome.event is LifecycleEvent.SUCCESS
    assert run.records_fetched == 1
    assert run.records_valid == 1
    assert run.listings_upserted == 1
    assert run.snapshots_appended == 1
    assert Listing.objects.filter(source_site__normalized_name="demo").count() == 1
    assert OfferSnapshot.objects.count() == 1


def test_rerun_is_append_only() -> None:
    adapter = FakeAdapter([ok_item()], [ok_parsed()])
    asyncio.run(run_source(adapter, NullResolver()))
    asyncio.run(run_source(adapter, NullResolver()))
    assert Listing.objects.filter(source_site__normalized_name="demo").count() == 1
    assert OfferSnapshot.objects.count() == 2
    assert ScraperRun.objects.count() == 2


def test_anti_bot_response_fails_the_run() -> None:
    blocked = RawItem(url="https://demo.invalid/a", http_status=403, content_type="text/html")
    adapter = FakeAdapter([blocked], [])
    run, outcome = asyncio.run(run_source(adapter, NullResolver()))
    assert run.status == RunStatus.FAILED
    assert run.failure_class == RunFailureClass.ANTI_BOT
    assert outcome.event is LifecycleEvent.ANTI_BOT
    assert Listing.objects.count() == 0


def test_zero_records_on_authentic_200_is_parser_rot() -> None:
    # ERR-003/EC-009: fetch looked healthy, extractor produced nothing.
    adapter = FakeAdapter([ok_item()], [])
    run, outcome = asyncio.run(run_source(adapter, NullResolver()))
    assert run.failure_class == RunFailureClass.PARSER_ROT
    assert outcome.event is LifecycleEvent.PARSER_ROT


def test_adapter_crash_is_classified() -> None:
    class Exploding(FakeAdapter):
        async def fetch(self) -> RawBatch:
            raise TimeoutError("socket timed out")

    run, outcome = asyncio.run(run_source(Exploding([], []), NullResolver()))
    assert run.status == RunStatus.FAILED
    assert run.failure_class == RunFailureClass.TRANSIENT
    assert outcome.event is LifecycleEvent.TRANSIENT_FAILURE
```

Also add lifecycle-application tests to the same file:

```python
import random
from datetime import timedelta

from django.utils import timezone

from hw_radar.acquisition.scheduling.apply import apply_run_outcome
from hw_radar.catalog.models import LifecycleState, SourceConfig


def test_apply_success_ramps_and_clears_backoff() -> None:
    config = SourceConfig.objects.get(source_site__normalized_name="demo")
    config.clean_polls = 3
    config.backoff_until = timezone.now() + timedelta(hours=1)
    now = timezone.now()
    apply_run_outcome(config, RunOutcome(LifecycleEvent.SUCCESS), now=now, rand=random.random)
    config.refresh_from_db()
    assert config.lifecycle_state == LifecycleState.ACTIVE
    assert config.current_interval_s == 1800  # 3600 halved, floored at 900
    assert config.clean_polls == 0
    assert config.backoff_until is None
    assert config.consecutive_failures == 0
    assert config.last_success_at is not None


def test_apply_transient_backs_off_and_resets_interval() -> None:
    config = SourceConfig.objects.get(source_site__normalized_name="demo")
    config.current_interval_s = 900
    now = timezone.now()
    apply_run_outcome(
        config, RunOutcome(LifecycleEvent.TRANSIENT_FAILURE), now=now, rand=lambda: 1.0
    )
    config.refresh_from_db()
    assert config.lifecycle_state == LifecycleState.BACKING_OFF
    assert config.consecutive_failures == 1
    assert config.clean_polls == 0
    assert config.current_interval_s == 3600  # AW-003: cadence resets to baseline
    assert config.backoff_until is not None
    assert config.backoff_until > now


def test_apply_honors_retry_after_verbatim() -> None:
    config = SourceConfig.objects.get(source_site__normalized_name="demo")
    now = timezone.now()
    apply_run_outcome(
        config,
        RunOutcome(LifecycleEvent.TRANSIENT_FAILURE, retry_after_s=120.0),
        now=now,
        rand=lambda: 1.0,
    )
    config.refresh_from_db()
    assert config.backoff_until is not None
    assert abs((config.backoff_until - now).total_seconds() - 120.0) < 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/db/test_persist.py tests/db/test_checkpoint.py tests/db/test_pipeline.py -v
```

Expected: FAIL — `ModuleNotFoundError` for the four new modules.

- [ ] **Step 3: Implement persist, apply, checkpoint, pipeline**

`src/hw_radar/acquisition/persist.py`:

```python
"""Persist stage: listing upsert + observation append + raw evidence (DR-005).

Re-running acquisition APPENDS offer_snapshot rows and never duplicates
listing rows — the MS-1 acceptance invariant lives here, keyed on the
(source_site, source_listing_key) unique constraint from MS-0.
"""

from __future__ import annotations

import hashlib
from datetime import datetime

from hw_radar.acquisition.contracts import NormalizedListing, RawItem
from hw_radar.catalog.models import (
    Listing,
    OfferSnapshot,
    RawPayload,
    RetentionClass,
    SourceSite,
    StockStatus,
)


def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def store_raw(
    item: RawItem, *, fetched_at: datetime, retention_class: RetentionClass
) -> RawPayload:
    body = item.payload_text or ""
    return RawPayload.objects.create(
        provider="acquisition",
        endpoint=item.url,
        fetched_at=fetched_at,
        response_json=item.payload_json,
        response_text=item.payload_text,
        content_hash=hashlib.sha256((body or str(item.payload_json)).encode()).hexdigest(),
        http_status=item.http_status,
        retention_class=retention_class,
    )


def upsert_listing(
    site: SourceSite, normalized: NormalizedListing, retention_class: RetentionClass
) -> tuple[Listing, bool]:
    return Listing.objects.update_or_create(
        source_site=site,
        source_listing_key=normalized.source_listing_key,
        defaults={
            "canonical_url": normalized.url,
            "url_hash": url_hash(normalized.url),
            "title_raw": normalized.title,
            "condition_label_raw": normalized.condition_label,
            "is_international": normalized.is_international,
            "retention_class": retention_class,
        },
    )


def append_snapshot(
    listing: Listing,
    normalized: NormalizedListing,
    *,
    observed_at: datetime,
    raw: RawPayload | None = None,
) -> OfferSnapshot:
    stock = (
        normalized.stock_status
        if normalized.stock_status in StockStatus.values
        else StockStatus.UNKNOWN
    )
    return OfferSnapshot.objects.create(
        listing=listing,
        observed_at=observed_at,
        currency=normalized.currency,
        item_price=normalized.price,
        shipping_price=normalized.shipping_price,
        stock_status=stock,
        quantity_available=normalized.quantity_available,
        fx_rate=normalized.fx_rate,
        fx_pair=normalized.fx_pair,
        fx_rate_date=normalized.fx_rate_date,
        fx_source=normalized.fx_source,
        attrs_json=dict(normalized.attrs),
        raw_payload=raw,
        retention_class=listing.retention_class,
    )
```

`src/hw_radar/acquisition/scheduling/apply.py`:

```python
"""The single mutator of SourceConfig scheduling state.

Composes the pure pieces (lifecycle transition, back-off ladder, auto-ramp)
into one save. Nothing else writes these fields — keeping every scheduling
decision auditable at one code point.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from hw_radar.acquisition.scheduling.backoff import (
    backoff_delay_s,
    clamp_retry_after,
    interval_after_success,
)
from hw_radar.acquisition.scheduling.lifecycle import LifecycleEvent, transition
from hw_radar.catalog.models import LifecycleState, SourceConfig

_SUCCESS_EVENTS = frozenset({LifecycleEvent.SUCCESS, LifecycleEvent.PROBE_SUCCESS})
_FAILURE_EVENTS = frozenset(
    {
        LifecycleEvent.TRANSIENT_FAILURE,
        LifecycleEvent.ANTI_BOT,
        LifecycleEvent.PARSER_ROT,
        LifecycleEvent.UNKNOWN_FAILURE,
        LifecycleEvent.PROBE_FAILURE,
    }
)


@dataclass(frozen=True)
class RunOutcome:
    event: LifecycleEvent
    retry_after_s: float | None = None


def apply_run_outcome(
    config: SourceConfig,
    outcome: RunOutcome,
    *,
    now: datetime,
    rand: Callable[[], float],
) -> None:
    event = outcome.event
    new_state = transition(
        LifecycleState(config.lifecycle_state),
        event,
        consecutive_parser_rot=config.consecutive_parser_rot,
    )
    config.last_run_at = now

    if event in _SUCCESS_EVENTS:
        config.last_success_at = now
        config.consecutive_failures = 0
        config.consecutive_parser_rot = 0
        config.backoff_until = None
        config.current_interval_s, config.clean_polls = interval_after_success(
            config.current_interval_s, config.cadence_ceiling_s, config.clean_polls
        )
    elif event in _FAILURE_EVENTS:
        config.consecutive_failures += 1
        config.clean_polls = 0
        config.consecutive_parser_rot = (
            config.consecutive_parser_rot + 1 if event is LifecycleEvent.PARSER_ROT else 0
        )
        # AW-003: cadence resets to baseline; the back-off window rides on top.
        config.current_interval_s = config.cadence_baseline_s
        delay_s = (
            clamp_retry_after(outcome.retry_after_s, config.cadence_baseline_s)
            if outcome.retry_after_s is not None
            else backoff_delay_s(config.consecutive_failures, rand)
        )
        config.backoff_until = now + timedelta(seconds=delay_s)

    config.lifecycle_state = new_state
    config.save(
        update_fields=[
            "lifecycle_state",
            "consecutive_failures",
            "consecutive_parser_rot",
            "clean_polls",
            "current_interval_s",
            "backoff_until",
            "last_run_at",
            "last_success_at",
            "updated_at",
        ]
    )
```

`src/hw_radar/acquisition/scheduling/checkpoint.py`:

```python
"""ERR-007 crash recovery: token-bucket state checkpointed to PostgreSQL.

On load, every bucket's updated_at is REBASED to the caller's current
monotonic clock: the dead process's monotonic timestamps are meaningless in a
new process, and rebasing (no refill credit across restart) is the
conservative direction for politeness.
"""

from __future__ import annotations

from typing import cast

from hw_radar.acquisition.scheduling.buckets import BucketRegistry
from hw_radar.catalog.models import SchedulerCheckpoint

BUCKETS_KEY = "bucket_registry"


def save_buckets(registry: BucketRegistry) -> None:
    SchedulerCheckpoint.objects.update_or_create(
        key=BUCKETS_KEY, defaults={"state_json": cast("dict[str, object]", registry.to_state())}
    )


def load_buckets(*, now_s: float) -> BucketRegistry:
    row = SchedulerCheckpoint.objects.filter(key=BUCKETS_KEY).first()
    if row is None:
        return BucketRegistry()
    registry = BucketRegistry.from_state(row.state_json)
    for bucket in (*registry.source_buckets.values(), *registry.domain_buckets.values()):
        bucket.updated_at = now_s
    return registry
```

`src/hw_radar/acquisition/pipeline.py`:

```python
"""Stage runner: fetch → parse → normalize → resolve → persist, in a ScraperRun.

Stages are independently re-runnable (§8.1); a resolver failure never blocks
persistence (C.3 — the listing lands unresolved). ORM work runs through
sync_to_async because the runner lives on the poller's event loop.
"""

from __future__ import annotations

import logging
import statistics

from asgiref.sync import sync_to_async
from django.utils import timezone
from pydantic import ValidationError

from hw_radar.acquisition import fx
from hw_radar.acquisition.classify import classify_exception, classify_response
from hw_radar.acquisition.contracts import (
    ListingResolver,
    NormalizedListing,
    RawBatch,
    SourceAdapter,
)
from hw_radar.acquisition.persist import append_snapshot, store_raw, upsert_listing
from hw_radar.acquisition.scheduling.apply import RunOutcome
from hw_radar.acquisition.scheduling.lifecycle import LifecycleEvent
from hw_radar.catalog.models import (
    RetentionClass,
    RunFailureClass,
    RunKind,
    RunStatus,
    ScraperRun,
    SourceSite,
)

logger = logging.getLogger(__name__)

MEDIAN_BODY_WINDOW = 10  # recent successful runs consulted for EC-007 body-size outliers

_EVENT_BY_CLASS: dict[RunFailureClass, LifecycleEvent] = {
    RunFailureClass.TRANSIENT: LifecycleEvent.TRANSIENT_FAILURE,
    RunFailureClass.ANTI_BOT: LifecycleEvent.ANTI_BOT,
    RunFailureClass.PARSER_ROT: LifecycleEvent.PARSER_ROT,
    RunFailureClass.DEGRADATION: LifecycleEvent.DEGRADATION,
    RunFailureClass.UNKNOWN: LifecycleEvent.UNKNOWN_FAILURE,
}


class FetchFailure(Exception):
    def __init__(self, failure_class: RunFailureClass, message: str) -> None:
        super().__init__(message)
        self.failure_class = failure_class


def _median_body_bytes(site: SourceSite) -> int | None:
    sizes = [
        size
        for size in ScraperRun.objects.filter(source_site=site, status=RunStatus.SUCCESS)
        .order_by("-started_at")
        .values_list("detail_json__body_bytes", flat=True)[:MEDIAN_BODY_WINDOW]
        if isinstance(size, int) and size > 0
    ]
    return int(statistics.median(sizes)) if sizes else None


def _classify_batch(batch: RawBatch, *, expects_json: bool, median: int | None) -> None:
    for item in batch.items:
        verdict = classify_response(
            http_status=item.http_status,
            content_type=item.content_type,
            expected_json=expects_json,
            body_text=item.payload_text or "",
            median_body_bytes=median,
        )
        if verdict is not None:
            raise FetchFailure(verdict, f"{item.url} classified {verdict}")


def _persist_all(
    site: SourceSite,
    batch: RawBatch,
    normalized: list[NormalizedListing],
    retention_class: RetentionClass,
) -> tuple[int, int]:
    raw = store_raw(batch.items[0], fetched_at=batch.fetched_at, retention_class=retention_class) if batch.items else None
    upserted = 0
    appended = 0
    for record in normalized:
        listing, _created = upsert_listing(site, record, retention_class)
        append_snapshot(listing, record, observed_at=batch.fetched_at, raw=raw)
        upserted += 1
        appended += 1
    return upserted, appended


async def _normalize(parsed_records: list, observed_date) -> list[NormalizedListing]:
    normalized: list[NormalizedListing] = []
    for parsed in parsed_records:
        try:
            normalized.append(await sync_to_async(fx.stamp)(parsed, observed_date))
        except fx.MissingRateError:
            await fx.refresh_daily((parsed.currency,))
            normalized.append(await sync_to_async(fx.stamp)(parsed, observed_date))
    return normalized


async def run_source(
    adapter: SourceAdapter,
    resolver: ListingResolver,
    *,
    retention_class: RetentionClass = RetentionClass.MERCHANT_FACT,
) -> tuple[ScraperRun, RunOutcome]:
    site = await sync_to_async(SourceSite.objects.get)(normalized_name=adapter.site_key)
    run = await sync_to_async(ScraperRun.objects.create)(
        source_site=site, run_kind=adapter.run_kind, started_at=timezone.now()
    )
    try:
        batch = await adapter.fetch()
        median = await sync_to_async(_median_body_bytes)(site)
        _classify_batch(batch, expects_json=adapter.expects_json, median=median)
        try:
            parsed = adapter.parse(batch)
        except ValidationError as exc:
            raise FetchFailure(RunFailureClass.PARSER_ROT, f"validation failed: {exc}") from exc
        if batch.items and not parsed:
            raise FetchFailure(RunFailureClass.PARSER_ROT, "authentic fetch yielded 0 records")
        normalized = await _normalize(parsed, batch.fetched_at.date())
        upserted, appended = await sync_to_async(_persist_all)(
            site, batch, normalized, retention_class
        )
        run.records_fetched = len(batch.items)
        run.records_valid = len(normalized)
        run.listings_upserted = upserted
        run.snapshots_appended = appended
        run.detail_json = {
            "body_bytes": sum(len(item.payload_text or "") for item in batch.items)
        }
        run.status = RunStatus.SUCCESS
        run.finished_at = timezone.now()
        await sync_to_async(run.save)()
        event = (
            LifecycleEvent.PROBE_SUCCESS
            if adapter.run_kind is RunKind.PROBE
            else LifecycleEvent.SUCCESS
        )
        return run, RunOutcome(event)
    except FetchFailure as exc:
        return await _finalize_failure(run, exc.failure_class, str(exc))
    except Exception as exc:  # noqa: BLE001 — every crash must classify + record (NFR-001)
        return await _finalize_failure(run, classify_exception(exc), repr(exc))


async def _finalize_failure(
    run: ScraperRun, failure_class: RunFailureClass, message: str
) -> tuple[ScraperRun, RunOutcome]:
    logger.warning("run %s failed: %s (%s)", run.pk, failure_class, message)
    run.status = RunStatus.FAILED
    run.failure_class = failure_class
    run.error = message[:2000]
    run.finished_at = timezone.now()
    await sync_to_async(run.save)()
    return run, RunOutcome(_EVENT_BY_CLASS[failure_class])
```

Then run the resolver after persist inside `run_source` (before the success save): call `await sync_to_async(resolver.resolve_listing)(listing_id)` per upserted listing. To keep listing ids available, have `_persist_all` return `list[int]` of listing ids alongside the counts and iterate:

```python
        listing_ids, upserted, appended = await sync_to_async(_persist_all)(
            site, batch, normalized, retention_class
        )
        for listing_id in listing_ids:
            await sync_to_async(resolver.resolve_listing)(listing_id)
```

(Adjust `_persist_all`'s return to `tuple[list[int], int, int]` accordingly — the resolver call is behavior MS-1b relies on, so it must be wired now even though `NullResolver` is a no-op.)

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/db/test_persist.py tests/db/test_checkpoint.py tests/db/test_pipeline.py -v
```

Expected: all PASS. (`test_pipeline.py` uses `transaction=True` because `run_source` writes from `sync_to_async` threads.)

- [ ] **Step 5: Gate and commit**

```bash
uv run ruff format . && uv run ruff check . --fix
uv run python -m scripts.check
git add src/hw_radar/acquisition tests/db/test_persist.py tests/db/test_checkpoint.py tests/db/test_pipeline.py
git commit -m "feat(pipeline): stage runner, persist stage, lifecycle application, checkpoints (MS-1a T5)"
```

---

### Task 6: Scrapy on the shared loop + demo walking skeleton

**Files:**
- Create: `src/hw_radar/acquisition/scrapy_support.py`, `src/hw_radar/acquisition/sources/__init__.py`, `src/hw_radar/acquisition/sources/demo.py`, `tests/fixtures/demo_listings.html`
- Test: `tests/db/test_pipeline_demo.py`

**Interfaces:**
- Consumes: `run_source`, contracts, `RunKind`.
- Produces: `scrapy_support.install_asyncio_reactor()`, `scrapy_support.run_spider(spider_cls, **kwargs) -> list[dict[str, object]]` (async), `scrapy_support.BASE_SETTINGS`; `sources.ADAPTERS: dict[str, Callable[[], SourceAdapter]]`; `sources.demo.DemoAdapter`. MS-1d connectors subclass nothing — they implement the protocol and register in `ADAPTERS`.

- [ ] **Step 1: Create the fixture**

`tests/fixtures/demo_listings.html`:

```html
<!doctype html>
<html>
<head><title>Demo recert store</title></head>
<body>
<h1>Recertified drives</h1>
<script type="application/ld+json">
{"@type": "Product", "sku": "DEMO-16TB-R", "name": "Demo Exos-like 16TB Recertified",
 "offers": {"@type": "Offer", "price": "189.99", "priceCurrency": "USD",
            "availability": "https://schema.org/InStock"}}
</script>
<script type="application/ld+json">
{"@type": "Product", "sku": "DEMO-8TB-R", "name": "Demo IronWolf-like 8TB Recertified",
 "offers": {"@type": "Offer", "price": "99.99", "priceCurrency": "USD",
            "availability": "https://schema.org/InStock"}}
</script>
</body>
</html>
```

- [ ] **Step 2: Write the failing test**

`tests/db/test_pipeline_demo.py`:

```python
import asyncio
from collections.abc import Iterator

import pytest

from hw_radar.acquisition.contracts import NullResolver
from hw_radar.acquisition.pipeline import run_source
from hw_radar.acquisition.sources import ADAPTERS
from hw_radar.acquisition.sources.demo import DemoAdapter
from hw_radar.catalog.models import Listing, OfferSnapshot, RunStatus, ScraperRun

# See test_pipeline.py: serialized_rollback preserves the migration seed.
pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)


@pytest.fixture(scope="module")
def scrapy_loop() -> Iterator[asyncio.AbstractEventLoop]:
    # SINGLE loop for every Scrapy-touching test in this module (design §MS-1a
    # reactor-lifecycle rule): the asyncio reactor binds to the loop present at
    # install; fresh per-test asyncio.run() loops would race a stale reactor.
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    asyncio.set_event_loop(None)
    loop.close()


def test_demo_adapter_is_registered() -> None:
    assert ADAPTERS["demo"] is DemoAdapter


def test_walking_skeleton_end_to_end(scrapy_loop: asyncio.AbstractEventLoop) -> None:
    # The MS-1a exit criterion: Scrapy (asyncio reactor, shared loop) → parse →
    # FX-stamp → resolve(stub) → persist, all under one event loop, no network.
    run, _outcome = scrapy_loop.run_until_complete(run_source(DemoAdapter(), NullResolver()))
    assert run.status == RunStatus.SUCCESS
    assert run.records_valid == 2
    listings = Listing.objects.filter(source_site__normalized_name="demo")
    assert listings.count() == 2
    assert {listing.source_listing_key for listing in listings} == {"DEMO-16TB-R", "DEMO-8TB-R"}
    snap = OfferSnapshot.objects.filter(listing__in=listings).first()
    assert snap is not None
    assert snap.fx_pair == "USD/USD"  # FR-004 identity stamp present


def test_two_consecutive_crawls_one_process_one_loop(
    scrapy_loop: asyncio.AbstractEventLoop,
) -> None:
    # Codex SA-006 requirement: the second scheduled crawl is where a wrong
    # reactor/runner integration breaks — prove both crawls inside ONE coroutine
    # on the module loop, and that re-runs append (DR-005).
    async def two_runs() -> None:
        await run_source(DemoAdapter(), NullResolver())
        await run_source(DemoAdapter(), NullResolver())

    scrapy_loop.run_until_complete(two_runs())
    assert Listing.objects.filter(source_site__normalized_name="demo").count() == 2
    assert OfferSnapshot.objects.count() == 4
    assert ScraperRun.objects.filter(status=RunStatus.SUCCESS).count() == 2
```

- [ ] **Step 3: Run test to verify it fails**

```bash
uv run pytest tests/db/test_pipeline_demo.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'hw_radar.acquisition.scrapy_support'`.

- [ ] **Step 4: Implement Scrapy support and the demo source**

`src/hw_radar/acquisition/scrapy_support.py`:

```python
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
# Scrapy/Twisted ship no py.typed; exceptions scoped to this integration module.
"""Scrapy on the poller's asyncio event loop (ADR-0012 single-process design).

install_asyncio_reactor() MUST run before anything imports
twisted.internet.reactor — the poller calls it first thing in run(); tests
get it via run_spider() itself. BASE_SETTINGS encodes the C-007 guardrails
(spec §8.5): robots on, autothrottle on, honest UA, hard timeouts.
"""

from __future__ import annotations

import asyncio

from scrapy import signals
from scrapy.crawler import AsyncCrawlerRunner
from scrapy.settings import Settings
from scrapy.utils.reactor import install_reactor, is_asyncio_reactor_installed

ASYNCIO_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
USER_AGENT = "hw-radar/0.1 (personal price monitor; +https://github.com/L3DigitalNet/hw-radar)"

BASE_SETTINGS: dict[str, object] = {
    "TWISTED_REACTOR": ASYNCIO_REACTOR,
    "ROBOTSTXT_OBEY": True,
    "AUTOTHROTTLE_ENABLED": True,
    "AUTOTHROTTLE_START_DELAY": 1.0,
    "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
    "DOWNLOAD_TIMEOUT": 30,
    "RETRY_ENABLED": True,
    "RETRY_TIMES": 1,  # AW-001: one in-run retry
    "USER_AGENT": USER_AGENT,
    "TELNETCONSOLE_ENABLED": False,
    "LOG_ENABLED": False,
}


def install_asyncio_reactor() -> None:
    if not is_asyncio_reactor_installed():
        install_reactor(ASYNCIO_REACTOR)


async def run_spider(spider_cls: type, **spider_kwargs: object) -> list[dict[str, object]]:
    """Run one spider on the current loop; return its scraped items as dicts.

    AsyncCrawlerRunner is the asyncio-native primitive the Scrapy docs prescribe
    (design §MS-1a / Codex SA-006). Documented fallback ONLY if the pinned Scrapy
    lacks it: CrawlerRunner + `runner.crawl(...).asFuture(asyncio.get_running_loop())`.
    """
    install_asyncio_reactor()
    settings = Settings()
    settings.setdict(BASE_SETTINGS, priority="project")
    items: list[dict[str, object]] = []

    def collect(item: dict[str, object], response: object, spider: object) -> None:
        items.append(dict(item))

    runner = AsyncCrawlerRunner(settings)
    crawler = runner.create_crawler(spider_cls)
    crawler.signals.connect(collect, signal=signals.item_scraped)
    await runner.crawl(crawler, **spider_kwargs)
    return items
```

`src/hw_radar/acquisition/sources/__init__.py`:

```python
"""Adapter registry: site_key → adapter factory. MS-1d connectors register here."""

from collections.abc import Callable

from hw_radar.acquisition.contracts import SourceAdapter
from hw_radar.acquisition.sources.demo import DemoAdapter

ADAPTERS: dict[str, Callable[[], SourceAdapter]] = {
    "demo": DemoAdapter,
}
```

`src/hw_radar/acquisition/sources/demo.py`:

```python
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false
# Scrapy ships no py.typed; exceptions scoped to this module.
"""Walking-skeleton source: a Scrapy spider over a local file:// JSON-LD fixture.

Proves poller → Scrapy(asyncio reactor) → parse → FX → resolve → persist with
zero network. ROBOTSTXT_OBEY=False here is the single sanctioned exception
(file:// cannot serve robots.txt); production spiders MUST NOT copy it (C-007).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import ClassVar

import scrapy

from hw_radar.acquisition.contracts import ParsedListing, RawBatch, RawItem
from hw_radar.acquisition.scrapy_support import run_spider
from hw_radar.catalog.models import RunKind

FIXTURE = Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "demo_listings.html"


class DemoSpider(scrapy.Spider):
    name = "demo"
    custom_settings: ClassVar[dict[str, object]] = {"ROBOTSTXT_OBEY": False}  # file:// only

    def __init__(self, fixture_url: str, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.start_urls = [fixture_url]

    def parse(self, response: scrapy.http.Response) -> Iterator[dict[str, str]]:
        for blob in response.css('script[type="application/ld+json"]::text').getall():
            yield {"jsonld": blob, "url": response.url}


class DemoAdapter:
    name = "demo"
    site_key = "demo"
    run_kind = RunKind.FULL
    expects_json = False

    def __init__(self, fixture: Path = FIXTURE) -> None:
        self._fixture = fixture

    async def fetch(self) -> RawBatch:
        scraped = await run_spider(DemoSpider, fixture_url=self._fixture.as_uri())
        items = [
            RawItem(
                url=str(entry["url"]),
                content_type="text/html",
                payload_text=str(entry["jsonld"]),
            )
            for entry in scraped
        ]
        return RawBatch(source=self.name, fetched_at=datetime.now(tz=UTC), items=items)

    def parse(self, batch: RawBatch) -> list[ParsedListing]:
        parsed: list[ParsedListing] = []
        for item in batch.items:
            data = json.loads(item.payload_text or "{}")
            offer = data["offers"]
            parsed.append(
                ParsedListing(
                    source_listing_key=str(data["sku"]),
                    url=item.url,
                    title=str(data["name"]),
                    price=Decimal(str(offer["price"])),
                    currency=str(offer.get("priceCurrency", "USD")),
                    stock_status=(
                        "in_stock" if "InStock" in str(offer.get("availability", "")) else "unknown"
                    ),
                )
            )
        return parsed
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/db/test_pipeline_demo.py -v
```

Expected: all PASS. The module-scoped `scrapy_loop` fixture is load-bearing: the reactor binds to the loop present at install, so every Scrapy-touching test must run on that one loop (`install_asyncio_reactor()` stays idempotent via `is_asyncio_reactor_installed()`, and nothing may import `twisted.internet.reactor` at module level).

- [ ] **Step 6: Gate and commit**

```bash
uv run ruff format . && uv run ruff check . --fix
uv run python -m scripts.check
git add src/hw_radar/acquisition tests/fixtures/demo_listings.html tests/db/test_pipeline_demo.py
git commit -m "feat(scrapy): asyncio-reactor crawl runner + demo walking skeleton (MS-1a T6)"
```

---

### Task 7: Poller wiring — jobs from SourceConfig, FX cron, dead-man push, checkpoints

**Files:**
- Create: `src/hw_radar/acquisition/deadman.py`
- Rewrite: `src/hw_radar/poller/__init__.py`; Modify: `src/hw_radar/poller/__main__.py`
- Test: `tests/unit/test_deadman.py`, `tests/unit/test_poller.py` (adjust), `tests/db/test_poller_jobs.py`

**Interfaces:**
- Consumes: everything above.
- Produces: `poller.build_scheduler(registry, configs) -> AsyncIOScheduler`, `poller.poll_source(site_key, registry, scheduler)` (async), `poller.run()`; `deadman.push(client=None) -> bool` (async), `deadman.ENV_VAR`. The systemd unit contract (`python -m hw_radar.poller`) is unchanged.

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_deadman.py`:

```python
import asyncio

import httpx
import pytest

from hw_radar.acquisition.deadman import ENV_VAR, push


def test_push_is_noop_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_VAR, raising=False)
    assert asyncio.run(push()) is False


def test_push_hits_configured_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_VAR, "https://kuma.invalid/api/push/token")
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json={"ok": True})

    async def drive() -> bool:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await push(client=client)

    assert asyncio.run(drive()) is True
    assert seen == ["https://kuma.invalid/api/push/token"]


def test_push_survives_network_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    # The dead-man job must never crash the poller (§18.5: absence alerts off-box).
    monkeypatch.setenv(ENV_VAR, "https://kuma.invalid/api/push/token")

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    async def drive() -> bool:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await push(client=client)

    assert asyncio.run(drive()) is False
```

Adjust `tests/unit/test_poller.py` — `build_scheduler` now takes `(registry, configs)`; the heartbeat/SIGTERM/job-defaults tests keep their assertions but construct with an empty config list:

```python
from hw_radar.acquisition.scheduling.buckets import BucketRegistry
from hw_radar.poller import HEARTBEAT_SECONDS, build_scheduler, heartbeat, run


def empty_scheduler():
    return build_scheduler(BucketRegistry(), configs=[])
```

(replace every bare `build_scheduler()` call with `empty_scheduler()`; the SIGTERM test drives `run(configs=[])` — see the implementation signature below. The three service jobs are always present:)

```python
def test_service_jobs_always_registered() -> None:
    scheduler = empty_scheduler()
    for job_id in ("poller-heartbeat", "fx-refresh", "deadman-push", "bucket-checkpoint"):
        assert scheduler.get_job(job_id) is not None, job_id
```

`tests/db/test_poller_jobs.py`:

```python
import pytest

from hw_radar.acquisition.scheduling.buckets import BucketRegistry
from hw_radar.catalog.models import SourceConfig
from hw_radar.poller import build_scheduler

pytestmark = pytest.mark.django_db


def test_disabled_sources_get_no_jobs() -> None:
    # Seed ships everything disabled; the scheduler must reflect that.
    registry = BucketRegistry()
    configs = list(SourceConfig.objects.select_related("source_site").filter(enabled=True))
    scheduler = build_scheduler(registry, configs=configs)
    assert scheduler.get_job("poll-demo") is None


def test_enabled_source_gets_job_with_config_cadence_and_bucket() -> None:
    SourceConfig.objects.filter(source_site__normalized_name="demo").update(enabled=True)
    registry = BucketRegistry()
    configs = list(SourceConfig.objects.select_related("source_site").filter(enabled=True))
    scheduler = build_scheduler(registry, configs=configs)
    job = scheduler.get_job("poll-demo")
    assert job is not None
    assert job.trigger.interval.total_seconds() == 3600  # seeded baseline
    assert job.misfire_grace_time == 60
    assert "demo" in registry.source_buckets
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/test_deadman.py tests/unit/test_poller.py tests/db/test_poller_jobs.py -v
```

Expected: FAIL — `deadman` missing; `build_scheduler()` signature mismatch.

- [ ] **Step 3: Implement dead-man push and the poller**

`src/hw_radar/acquisition/deadman.py`:

```python
"""§18.5 dead-man's switch: push liveness to the off-box Uptime Kuma monitor.

No URL configured (dev) → silent no-op. Failures return False and log — the
watchdog alerts on ABSENCE of pushes, so this function must never raise.
The push URL is rendered by bao-agent (HW_RADAR_KUMA_PUSH_URL); never commit it.
"""

from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

ENV_VAR = "HW_RADAR_KUMA_PUSH_URL"
TIMEOUT_S = 10.0


async def push(*, client: httpx.AsyncClient | None = None) -> bool:
    url = os.environ.get(ENV_VAR, "")
    if not url:
        return False
    owns_client = client is None
    active = client or httpx.AsyncClient(timeout=TIMEOUT_S)
    try:
        response = await active.get(url)
        return response.status_code < 400
    except httpx.HTTPError as exc:
        logger.warning("dead-man push failed: %r", exc)
        return False
    finally:
        if owns_client:
            await active.aclose()
```

`src/hw_radar/poller/__init__.py` (full rewrite):

```python
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false
# APScheduler 3.x ships no py.typed/stubs; keep these exact-rule exceptions scoped here.
"""Single systemd-supervised poller owning all acquisition scheduling (ADR-0012).

Per-source interval jobs are registered from SourceConfig rows; the admission
gate (buckets → back-off → lifecycle) runs inside each job, so a denied tick
is cheap. Auto-ramp/back-off changes to current_interval_s reschedule the
source's job in place. Django ORM calls go through sync_to_async — this
module is only ever imported after django.setup() (__main__ or pytest-django).
"""

from __future__ import annotations

import asyncio
import logging
import random
import signal
import time
from collections.abc import Sequence
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from asgiref.sync import sync_to_async
from django.utils import timezone

from hw_radar.acquisition import deadman, fx
from hw_radar.acquisition.contracts import NullResolver
from hw_radar.acquisition.pipeline import run_source
from hw_radar.acquisition.scheduling.admission import check_admission
from hw_radar.acquisition.scheduling.apply import apply_run_outcome
from hw_radar.acquisition.scheduling.buckets import BucketRegistry
from hw_radar.acquisition.scheduling.checkpoint import load_buckets, save_buckets
from hw_radar.acquisition.scrapy_support import install_asyncio_reactor
from hw_radar.acquisition.sources import ADAPTERS
from hw_radar.catalog.models import LifecycleState, RunKind, SourceConfig

if TYPE_CHECKING:
    from apscheduler.job import Job

logger = logging.getLogger(__name__)

HEARTBEAT_SECONDS = 60
DEADMAN_SECONDS = 60
CHECKPOINT_SECONDS = 60
FX_REFRESH_HOUR_UTC = 6


def heartbeat() -> None:
    logger.info("poller heartbeat: alive")


async def poll_source(site_key: str, registry: BucketRegistry, scheduler: AsyncIOScheduler) -> None:
    config = await sync_to_async(
        SourceConfig.objects.select_related("source_site").get
    )(source_site__normalized_name=site_key)
    decision = check_admission(
        enabled=config.enabled,
        lifecycle_state=LifecycleState(config.lifecycle_state),
        run_kind=RunKind.FULL,
        backoff_until=config.backoff_until,
        now=timezone.now(),
        registry=registry,
        source_key=site_key,
        domain=config.domain,
        now_s=time.monotonic(),
    )
    if not decision.admitted:
        logger.info("source %s not admitted: %s", site_key, decision.reason)
        return
    factory = ADAPTERS.get(site_key)
    if factory is None:
        logger.warning("source %s enabled but has no adapter registered", site_key)
        return
    _run, outcome = await run_source(factory(), NullResolver())
    interval_before = config.current_interval_s
    await sync_to_async(apply_run_outcome)(
        config, outcome, now=timezone.now(), rand=random.random
    )
    if config.current_interval_s != interval_before:
        job: Job | None = scheduler.get_job(f"poll-{site_key}")
        if job is not None:
            scheduler.reschedule_job(
                f"poll-{site_key}",
                trigger="interval",
                seconds=config.current_interval_s,
                jitter=max(1, config.current_interval_s // 10),
            )
            logger.info(
                "source %s rescheduled: %ss → %ss",
                site_key,
                interval_before,
                config.current_interval_s,
            )


async def refresh_fx_job() -> None:
    stored = await fx.refresh_daily()
    logger.info("fx refresh: %s pairs stored", stored)


async def deadman_job() -> None:
    await deadman.push()


async def checkpoint_job(registry: BucketRegistry) -> None:
    await sync_to_async(save_buckets)(registry)


def build_scheduler(
    registry: BucketRegistry, configs: Sequence[SourceConfig]
) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(job_defaults={"max_instances": 1, "coalesce": True})
    scheduler.add_job(heartbeat, "interval", seconds=HEARTBEAT_SECONDS, id="poller-heartbeat")
    scheduler.add_job(refresh_fx_job, "cron", hour=FX_REFRESH_HOUR_UTC, id="fx-refresh")
    scheduler.add_job(deadman_job, "interval", seconds=DEADMAN_SECONDS, id="deadman-push")
    scheduler.add_job(
        checkpoint_job, "interval", seconds=CHECKPOINT_SECONDS, id="bucket-checkpoint",
        args=[registry],
    )
    for config in configs:
        key = config.source_site.normalized_name
        registry.configure_source(
            key,
            rate_per_min=config.bucket_rate_per_min,
            burst=config.bucket_burst,
            now_s=time.monotonic(),
        )
        scheduler.add_job(
            poll_source,
            "interval",
            seconds=config.current_interval_s,
            jitter=max(1, config.current_interval_s // 10),
            misfire_grace_time=config.misfire_grace_s,
            id=f"poll-{key}",
            args=[key, registry, scheduler],
        )
    return scheduler


async def run(configs: Sequence[SourceConfig] | None = None) -> None:
    install_asyncio_reactor()  # before APScheduler starts; Scrapy shares this loop
    registry = await sync_to_async(load_buckets)(now_s=time.monotonic())
    if configs is None:
        configs = await sync_to_async(
            lambda: list(
                SourceConfig.objects.select_related("source_site").filter(enabled=True)
            )
        )()
    scheduler = build_scheduler(registry, configs)
    scheduler.start()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    logger.info("poller started (%s source job(s))", len(configs))
    await stop.wait()
    scheduler.shutdown(wait=False)
    await sync_to_async(save_buckets)(registry)
    logger.info("poller stopped")
```

`src/hw_radar/poller/__main__.py` (rewrite — django.setup() must precede the poller import chain, which now imports models):

```python
import asyncio
import logging
import os


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s"
    )
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hw_radar.settings")
    import django

    django.setup()

    from hw_radar.poller import run

    asyncio.run(run())


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/test_deadman.py tests/unit/test_poller.py tests/db/test_poller_jobs.py -v
```

Expected: all PASS (the SIGTERM test now calls `run(configs=[])`, which skips the DB read; buckets checkpoint on shutdown needs the DB — if that write makes the unit test require a DB, guard it: `save_buckets` failures at shutdown are logged, not raised — wrap in try/except with `logger.warning`).

- [ ] **Step 5: Verify the process contract manually**

```bash
podman compose up -d db
uv run python -m hw_radar.poller &
sleep 5 && kill -TERM %1 && wait
```

Expected: "poller started (0 source job(s))" (all sources ship disabled), heartbeat line, then "poller stopped". No tracebacks.

- [ ] **Step 6: Gate and commit**

```bash
uv run ruff format . && uv run ruff check . --fix
uv run python -m scripts.check
git add src/hw_radar/acquisition/deadman.py src/hw_radar/poller tests/unit/test_deadman.py tests/unit/test_poller.py tests/db/test_poller_jobs.py
git commit -m "feat(poller): jobs from source registry, FX cron, dead-man push, checkpoints (MS-1a T7)"
```

---

### Task 8: Closeout — docs, operator follow-ups, MS-1a PR

**Files:**
- Modify: `docs/handoff.md`, `TODO.md` (both local/git-ignored — updated, not committed)
- Verify: nothing in `deploy/` needs changes (`python -m hw_radar.poller` contract unchanged)

- [ ] **Step 1: Full verification**

```bash
uv run python -m scripts.check
```

Expected: every gate step green, coverage ≥85%.

- [ ] **Step 2: Local docs**

- `docs/handoff.md`: add the MS-1a session entry (substrate landed; all sources seeded disabled; demo source proves the loop; fast_lane flags deliberately False until MS-1d).
- `TODO.md` `## Claude`: add two operator-visible follow-ups: (1) add `HW_RADAR_KUMA_PUSH_URL` to the CT's bao-agent template + create the Kuma push monitor (dead-man alerting is inert until then); (2) MS-1d must flip `enabled` per connector and `fast_lane` for WD/Seagate/SPD once heartbeat gating exists.
- Spec Deviations Log: no deviations expected from this plan; if any step deviated, record it in §Deviations before the PR.

- [ ] **Step 3: Open the MS-1a PR**

```bash
git push origin dev
gh pr create --base main --head dev \
  --title "MS-1a — Ingestion substrate (scheduler, contracts, FX, walking skeleton)" \
  --body "First MS-1 increment per docs/superpowers/specs/2026-07-05-ms1-ingestion-design.md: source registry + scraper_runs + FX cache models; two-level token buckets, back-off ladder, ADR-0017 lifecycle + admission gate; §12.1 classifier; adapter contracts; Frankfurter FX service (ADR-0008); Scrapy on the shared asyncio loop (ADR-0012/0014); Kuma dead-man push; fixture-backed demo source proving fetch→parse→normalize→resolve(stub)→persist end-to-end. All real sources seeded disabled; connectors arrive in MS-1d."
```

Merge (merge commit, not squash) once `check` + `dependency-review` are green. Prod deploy runs on merge; the poller restarts with zero enabled sources — behaviorally identical to the MS-0 stub except for the heartbeat/FX/dead-man service jobs.

---

## Self-review notes (author pass, 2026-07-05)

- **Spec coverage (MS-1a slice):** C.2 substrate → Tasks 1/2/5/7; ADR-0017 lifecycle → Tasks 2/5; §12.1 classifier → Task 3; ADR-0008 FX + FR-004 stamps → Tasks 1/4; C.1 adapter contract → Task 3; ADR-0012 loop-sharing + ADR-0014 guardrails → Task 6; §18.5 dead-man + ERR-007 checkpoints → Tasks 5/7. Heartbeat gating, real connectors, matcher: deliberately MS-1b/d, not gaps.
- **Known simplifications (accepted at MS-1a, revisited later):** latency-spike detection (AW-005 math exists in `backoff.py`; the trigger — 3-poll latency median — wires up when connectors produce real timings in MS-1d); degradation thresholds (ERR-004 formulas land with the MS-5 canary); `store_raw` persists the first batch item as run-level evidence rather than per-listing raw rows (per-listing linkage becomes meaningful with real per-item payloads in MS-1d).
- **Type consistency check:** `run_source` returns `tuple[ScraperRun, RunOutcome]` everywhere (Task 5 impl, Task 5/6 tests, Task 7 `poll_source`); `build_scheduler(registry, configs)` matches all three test files; `check_admission` kwargs match Task 2 tests and Task 7 call site; `_persist_all` return-shape adjustment is stated inline where the resolver loop is wired.
