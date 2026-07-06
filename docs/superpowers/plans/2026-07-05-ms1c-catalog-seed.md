# MS-1c — Catalog Seed (ADR-0018) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the ADR-0018 reference-data path — `refdata/` with the truncated `fetch → parse → normalize → persist` pipeline seeding `product_family` / `product_model` / `drive_spec` / `product_alias` from curated first-party seed documents (Seagate Exos recertified, Seagate IronWolf Pro, WD Ultrastar DC HC550), all rows `retention_class = manufacturer_reference` — plus the C.3.4 occurrence-triggered discovery loop, the monthly refresh poller job that re-runs rungs 1–2 over the backfill queue, and the MS-1b carry-forward checks (alias-conflict aggregation, `unchanged_miss` freshness, brand-equivalence-aware cross-manufacturer collision detection, provisional-family reconciliation — the real-corpus SanDisk↔WD verification stays deferred to the first SSD seed, see D7).

**Architecture:** `src/hw_radar/refdata/` is a new module (not a Django app): `contracts.py` (Pydantic v2 seed-document schema + pure conflict detection), `loader.py` (reads `refdata/seeds/*.json`), `persist.py` (validate-then-write importer, one transaction, conflicts fail the whole import into review), `discovery.py` (backfill-queue threshold scan → `ReferenceFetchRequest` rows), `refresh.py` (orchestrates import → reconsider → discovery). Catalog aliases pass through `matching.normalize.normalize_alias_text` — the single-normalizer invariant (ADR-0019 rule 1); families/models key on the same normalizers the resolver uses, so seeded rows *adopt* rung-2 provisional rows instead of duplicating them. `CatalogResolver` grows a `reconsider` mode (prior=None, bypasses rung 0) so seeded aliases can upgrade family-grain listings, and a `last_evaluated_at` freshness stamp on unchanged re-evaluations. Reference ingest writes **no** `offer_snapshot`/score/alert/heartbeat rows and never gates the observation stream. Design sources: `docs/superpowers/specs/2026-07-05-ms1-ingestion-design.md` §MS-1c, `docs/research/2026-07-05-ms1c-catalog-seed-inputs.md`, master spec Appendix C.3.4 + IR-007 + DR-009, ADR-0018, ADR-0019.

**Tech Stack:** Python 3.14, Pydantic v2 (already a dependency), Django 6 ORM + TimescaleDB/PostgreSQL, APScheduler (existing poller). **No new dependencies** (runtime or dev).

## Owner decisions recorded by this plan

These settle the "Open inputs for the MS-1c plan" from the research doc:

- **D1 — Curated seed documents, no live fetch in MS-1c.** The "fetch/parse" stages are realized as hand-curated JSON seed documents checked into `src/hw_radar/refdata/seeds/`, each carrying provenance (first-party datasheet/manual URLs + retrieval dates). Typed spec fields are populated **only from first-party sources**; merchant pages chose *which* families to seed but never populate authoritative fields. Live datasheet fetching/PDF parsing is deferred to a later milestone; the `load_seed_documents(seed_dir)` seam is where it will plug in.
- **D2 — Family naming follows the first-party datasheet.** The recertified `ST…NM…C` ladder seeds as broad family **`Exos`** (Seagate's recert datasheet groups them without X-generation, and rung 2 decodes to `exos` — the seed adopts that provisional row). `IronWolf Pro` and `Ultrastar DC HC550` seed under their datasheet names. Narrower `Exos X16/X18/X20/X24` families are **deferred** until their datasheet rows are selected (research: "Ready after matching datasheet row selected") — they arrive as additional seed documents, no code change.
- **D2a — Full-fan-out acceptance family = Exos recertified; HC550 is a bounded starter subset** (Codex CR-001). The design exit ("one enterprise family lands with its full per-MPN variant/alias fan-out") is satisfied by the **Exos recertified** family: its first-party datasheet ladder is exactly the six `ST…C` SKUs this plan seeds — complete coverage of the published family. The WD HC550 first-party matrix is much larger (14/16/18 TB, six SATA + nine SAS rows, 4Kn/security variants); this plan deliberately seeds only the four research-evidenced recert-market rows and **must not claim** full HC550 fan-out anywhere (tests, ADR confirmation, PR body). The remaining HC550 matrix lands as a data-only seed-document extension when the HC560/HC570 expansion is worked.
- **D3 — The per-MPN "variant fan-out" is `ProductModel` rows, not `ProductVariant` rows.** SATA vs SAS vs `…ALE604`/`…ALE6L4` suffixes are distinct manufacturer model numbers → one `ProductModel` + `DriveSpec` + alias each. `ProductVariant`'s unique key is condition/packaging/recert/warranty — marketplace axes the reference catalog must not encode (research "Seed row mapping"). Variant rows remain resolver-on-demand.
- **D4 — Conflicts fail the whole import into review.** Any two aliases normalizing to the same key with different targets (within seeds, across seeds, or against existing DB aliases — including cross-manufacturer collisions, the generalized SanDisk↔WD check) abort the import before any write. Nothing is auto-selected.
- **D5 — Evidence freshness is a mutable `last_evaluated_at` column on `listing_resolution`,** stamped whenever the resolver re-evaluates a listing and writes no new edge (unchanged accept/miss/error, unchanged reconsider). It is deliberately *not* in the `evidence` JSON — edges stay append-only; the stamp is operational state, the one mutable field besides `is_current`/`superseded_by`.
- **D6 — WD `0F…` orderable part numbers seed as `alias_type = retail_pn`** (they are orderable/retail part numbers, distinct from the model-number MPN, and must not claim the `mpn` slot).
- **D7 — SanDisk↔WD verification scope** (Codex CR-004): MS-1c implements *generic* cross-manufacturer collision detection whose conflict descriptors distinguish `brand-equivalent` (SanDisk/WD/HGST lineage, via `ladder.brands_consistent`) from `cross-brand` collisions, with a targeted synthetic test for the brand-equivalent path. The **real-corpus** SanDisk↔WD verification the research ledger asks for can only run against an actual SSD seed — it stays a deferred TODO item gating the first WD/SanDisk SSD family seed, and this plan's docs/PR must not claim it closed.
- **D8 — Reference import is single-writer.** The importer's validate-then-write conflict check is not concurrency-safe against alias writes racing between `_db_conflicts()` and `_import_alias()`; the defensive re-check aborts rather than retargets. Acceptable because the only writers are the monthly poller job and the manual `import_refdata` command (never run concurrently); recorded in the persist.py docstring.

## Global Constraints

- Toolchain contract is `AGENTS.md`: fix pass (`uv run ruff format . && uv run ruff check . --fix`) before every commit; full gate (`uv run python -m scripts.check`) green before claiming a task complete. Coverage threshold **85% branch**.
- **BasedPyright strict** on `src/` + `tests/`. `refdata/` must type-check with zero pragmas except where django-types' missing `<field>_id` stubs force the established one-line ignore pattern (see `matching/resolver.py::_product_model_id` for the precedent).
- **No new dependencies.** Pydantic v2 is already in `[project] dependencies`.
- DB tests live in `tests/db/` (need live TimescaleDB); pure tests in `tests/unit/`. On this workstation use `HW_RADAR_DB_PORT=5433` when the dev container maps to `127.0.0.1:5433`. If the container is missing/stale: `podman rm -f hw-radar-db; podman run -d --rm --name hw-radar-db -e POSTGRES_DB=hw_radar -e POSTGRES_USER=hw_radar -e POSTGRES_PASSWORD=hw_radar -p 127.0.0.1:5432:5432 docker.io/timescale/timescaledb:2.28.2-pg17` (dev container only — disposable fixture data).
- **Single-normalizer invariant (ADR-0019 rule 1):** every seeded alias key is `matching.normalize.normalize_alias_text(text)`; family normalized names are `matching.normalize.canonicalize_title(name)`; model normalized numbers are `normalize_alias_text(model_number)`. Never fork a second normalizer. The existing parity test in `tests/db/test_resolver.py` must stay green.
- **DR-009:** every seeded `ProductModel` / `DriveSpec` / `ProductAlias` row carries `retention_class = manufacturer_reference`, `expires_at = NULL`. A model absent from a later seed refresh is **retained, never deleted**. Reference ingest writes no `offer_snapshot`/score/alert/heartbeat rows.
- **Null means unknown, never guessed** (suitability-research rule): a typed `DriveSpec` field is populated only when the first-party source states it; otherwise it stays NULL and the raw context rides `spec_json`.
- **Append-only resolution ledger (DR-010)** is unchanged: the resolver additions in this plan write no in-place edge mutations except `is_current`/`superseded_by` (existing) and the new `last_evaluated_at` stamp (D5).
- Thresholds are **ADR-0016 settings rows**: the discovery occurrence threshold lives on `RefdataConfig`, changed by UPDATE not deploy.
- Migrations are expand/contract (spec §8.5); new columns defaulted; reversible.
- Public repo: no secrets, private hostnames, or infra addresses in code/docs/commits.
- Conventional commits on `dev`, GPG-signed. This plan ends with the **MS-1c `dev→main` PR**.
- Bump `matching.MATCHER_VERSION` to `"2026.07.3"` (resolver write-semantics change: reconsider mode + unchanged-target detection), per the C.3.5 "any rule change bumps it" contract.

## File Structure

```
src/hw_radar/refdata/__init__.py                    # NEW: package docstring only
src/hw_radar/refdata/contracts.py                   # NEW: Pydantic seed-document schema, SeedConflict, detect_conflicts()
src/hw_radar/refdata/loader.py                      # NEW: SEED_DIR + load_seed_documents()
src/hw_radar/refdata/persist.py                     # NEW: ImportReport, ImportConflictError, import_documents()
src/hw_radar/refdata/discovery.py                   # NEW: scan_backfill_queue()
src/hw_radar/refdata/refresh.py                     # NEW: RefreshReport, run_refresh()
src/hw_radar/refdata/seeds/seagate-exos-recertified.json   # NEW: 6 models
src/hw_radar/refdata/seeds/seagate-ironwolf-pro.json       # NEW: 5 models
src/hw_radar/refdata/seeds/wd-ultrastar-dc-hc550.json      # NEW: 4 models, 6 aliases
src/hw_radar/catalog/models/ops.py                  # MODIFY: + RefdataConfig
src/hw_radar/catalog/models/resolution.py           # MODIFY: + ListingResolution.last_evaluated_at,
                                                    #          FetchRequestStatus, ReferenceFetchRequest
src/hw_radar/catalog/models/__init__.py             # MODIFY: export new models/enums
src/hw_radar/catalog/admin.py                       # MODIFY: register RefdataConfig, ReferenceFetchRequest
src/hw_radar/catalog/migrations/0008_refdata_seed.py       # generated + reviewed
src/hw_radar/catalog/management/__init__.py         # NEW (empty)
src/hw_radar/catalog/management/commands/__init__.py       # NEW (empty)
src/hw_radar/catalog/management/commands/import_refdata.py # NEW: manual import/refresh entry point
src/hw_radar/matching/__init__.py                   # MODIFY: MATCHER_VERSION bump
src/hw_radar/matching/resolver.py                   # MODIFY: reconsider mode, unchanged-target skip, freshness stamp
src/hw_radar/poller/service.py                      # MODIFY: monthly refdata-refresh job
tests/unit/test_refdata_contracts.py                # NEW: schema validation + conflict detection (pure)
tests/unit/test_refdata_loader.py                   # NEW: repo seed documents parse + invariants
tests/unit/test_poller.py                           # MODIFY: refdata-refresh job registered
tests/db/test_refdata_import.py                     # NEW: importer semantics (DR-009, idempotence, adoption, conflicts, retention)
tests/db/test_refdata_refresh.py                    # NEW: reconsider upgrades, freshness, discovery, run_refresh
tests/db/test_refdata_acceptance.py                 # NEW: MS-1c exit criteria end-to-end
tests/db/test_resolver.py                           # MODIFY: unchanged-target + last_evaluated_at coverage
```

**Interfaces locked by this plan** (MS-1d/e consume these exact names):

- `refdata.contracts.SeedDocument` (Pydantic) with `.manufacturer_key: str`, `.manufacturer_name: str`, `.family_name: str`, `.models: tuple[SeedModel, ...]`; `SeedModel.model_number: str`, `.spec: SeedSpec`, `.aliases: tuple[SeedAlias, ...]`; `SeedAlias.normalized: str` (property = `normalize_alias_text(text)`).
- `refdata.contracts.detect_conflicts(docs: Sequence[SeedDocument]) -> tuple[SeedConflict, ...]` (pure).
- `refdata.loader.load_seed_documents(seed_dir: Path | None = None) -> list[SeedDocument]`; `refdata.loader.SEED_DIR: Path`.
- `refdata.persist.import_documents(docs: Sequence[SeedDocument]) -> ImportReport`; raises `refdata.persist.ImportConflictError` (attribute `.conflicts: list[str]`) with **no rows written**.
- `refdata.discovery.scan_backfill_queue() -> int` (number of newly enqueued `ReferenceFetchRequest` rows).
- `refdata.refresh.run_refresh(seed_dir: Path | None = None) -> RefreshReport`.
- `matching.resolver.CatalogResolver.resolve_listing(listing_id: int, *, reconsider: bool = False) -> None` — `reconsider=True` bypasses rung 0 (prior=None) so rungs 1–2 run against the freshly seeded catalog.
- `catalog.models.RefdataConfig` (settings row; `RefdataConfig.current()` classmethod), `catalog.models.ReferenceFetchRequest`, `catalog.models.FetchRequestStatus`, `ListingResolution.last_evaluated_at: datetime`.
- Manufacturer keys (fixed vocabulary, matches MS-1b brand keys): `seagate`, `western_digital`, `toshiba`.

---

### Task 1: Seed-document contracts, loader, and the Exos recertified seed

**Files:**
- Create: `src/hw_radar/refdata/__init__.py`
- Create: `src/hw_radar/refdata/contracts.py`
- Create: `src/hw_radar/refdata/loader.py`
- Create: `src/hw_radar/refdata/seeds/seagate-exos-recertified.json`
- Test: `tests/unit/test_refdata_contracts.py`
- Test: `tests/unit/test_refdata_loader.py`

**Interfaces:**
- Consumes: `matching.normalize.normalize_alias_text` (MS-1b).
- Produces: `SeedDocument`, `SeedModel`, `SeedSpec`, `SeedAlias`, `SeedProvenance`, `SeedSource`, `SeedConflict`, `detect_conflicts()`, `SEED_SCHEMA`, `load_seed_documents()`, `SEED_DIR`. Tasks 2/4/6 import these exact names.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_refdata_contracts.py
"""Seed-document schema (ADR-0018 D1): shape validation + pure conflict detection."""

import pydantic
import pytest

from hw_radar.matching.normalize import normalize_alias_text
from hw_radar.refdata.contracts import (
    SEED_SCHEMA,
    SeedAlias,
    SeedDocument,
    detect_conflicts,
)

VALID_DOC = {
    "schema": SEED_SCHEMA,
    "manufacturer_name": "Seagate",
    "manufacturer_key": "seagate",
    "family_name": "Exos",
    "provenance": {
        "source_kind": "first_party_datasheet",
        "sources": [
            {
                "url": "https://www.seagate.com/content/dam/seagate/en/content-fragments/products/datasheets/exos-recertified-drive/exos-recertified-drive-DS2045-2-2010US-October-2020-en_US.pdf",
                "title": "Seagate Exos Recertified Drive datasheet DS2045.2",
                "retrieved": "2026-07-05",
            }
        ],
    },
    "models": [
        {
            "model_number": "ST16000NM002C",
            "spec": {
                "media_type": "hdd",
                "interface": "SATA 6Gb/s",
                "form_factor": "3.5",
                "capacity_tb": "16",
                "sector_format": "512e",
                "recording_tech": "cmr",
                "market_tier": "enterprise",
                "model_family": "Exos",
            },
            "aliases": [
                {"alias_type": "mpn", "text": "ST16000NM002C", "is_primary": True}
            ],
        }
    ],
}


def _doc(**overrides: object) -> dict[str, object]:
    return {**VALID_DOC, **overrides}


def test_valid_document_parses() -> None:
    doc = SeedDocument.model_validate(VALID_DOC)
    assert doc.manufacturer_key == "seagate"
    assert doc.models[0].spec.capacity_tb is not None
    assert doc.models[0].spec.rpm is None  # null = unknown, never guessed


def test_alias_normalized_is_the_join_key() -> None:
    alias = SeedAlias(alias_type="mpn", text="WUH721818ALE6L4", is_primary=True)
    assert alias.normalized == normalize_alias_text("WUH721818ALE6L4")


def test_wrong_schema_id_rejected() -> None:
    with pytest.raises(pydantic.ValidationError):
        SeedDocument.model_validate(_doc(**{"schema": "hw-radar.refdata.seed/v0"}))


def test_manufacturer_key_must_be_normalized() -> None:
    with pytest.raises(pydantic.ValidationError):
        SeedDocument.model_validate(_doc(manufacturer_key="Western Digital"))


def test_model_requires_alias_covering_its_own_model_number() -> None:
    broken = _doc(
        models=[
            {
                "model_number": "ST16000NM002C",
                "spec": {"media_type": "hdd"},
                "aliases": [{"alias_type": "retail_pn", "text": "0F00000"}],
            }
        ]
    )
    with pytest.raises(pydantic.ValidationError):
        SeedDocument.model_validate(broken)


def test_model_requires_exactly_one_primary_alias() -> None:
    broken = _doc(
        models=[
            {
                "model_number": "ST16000NM002C",
                "spec": {"media_type": "hdd"},
                "aliases": [{"alias_type": "mpn", "text": "ST16000NM002C"}],
            }
        ]
    )
    with pytest.raises(pydantic.ValidationError):
        SeedDocument.model_validate(broken)


def test_extra_fields_rejected() -> None:
    with pytest.raises(pydantic.ValidationError):
        SeedDocument.model_validate(_doc(surprise="field"))


def test_detect_conflicts_same_key_different_targets() -> None:
    doc_a = SeedDocument.model_validate(VALID_DOC)
    doc_b = SeedDocument.model_validate(
        _doc(
            manufacturer_name="Western Digital",
            manufacturer_key="western_digital",
            family_name="Ultrastar DC HC550",
            models=[
                {
                    "model_number": "WUH721818ALE6L4",
                    "spec": {"media_type": "hdd"},
                    "aliases": [
                        {"alias_type": "mpn", "text": "WUH721818ALE6L4", "is_primary": True},
                        # deliberate collision with doc_a's ST16000NM002C:
                        {"alias_type": "retail_pn", "text": "st16000nm002c"},
                    ],
                }
            ],
        )
    )
    conflicts = detect_conflicts([doc_a, doc_b])
    assert len(conflicts) == 1
    assert conflicts[0].normalized_text == normalize_alias_text("ST16000NM002C")
    assert len(conflicts[0].targets) == 2


def test_detect_conflicts_same_key_same_target_is_not_a_conflict() -> None:
    doc = SeedDocument.model_validate(VALID_DOC)
    assert detect_conflicts([doc, doc]) == ()
```

```python
# tests/unit/test_refdata_loader.py
"""The repo's own seed documents must always parse and stay conflict-free.
Corpus-size-independent by design (Codex CR-002): these invariants hold at
every task boundary; the exact corpus-count test lands with the full corpus
in Task 2, so no commit ever carries a known-red test."""

from hw_radar.matching.normalize import normalize_alias_text
from hw_radar.refdata.contracts import detect_conflicts
from hw_radar.refdata.loader import load_seed_documents


def test_repo_seed_documents_parse() -> None:
    docs = load_seed_documents()
    assert docs, "seed corpus must never be empty"
    assert all(doc.models for doc in docs)


def test_repo_seed_documents_have_no_conflicts() -> None:
    assert detect_conflicts(load_seed_documents()) == ()


def test_every_alias_is_normalize_alias_text_of_its_raw_form() -> None:
    for doc in load_seed_documents():
        for model in doc.models:
            for alias in model.aliases:
                assert alias.normalized == normalize_alias_text(alias.text)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_refdata_contracts.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'hw_radar.refdata'`

- [ ] **Step 3: Write the package, contracts, and loader**

```python
# src/hw_radar/refdata/__init__.py
"""ADR-0018 reference-data ingest (MS-1c): the truncated fetch→parse→normalize→
persist pipeline for the manufacturer spec catalog. Writes product_family /
product_model / drive_spec / product_alias with retention_class =
manufacturer_reference and STOPS — no offer_snapshot/score/alert/heartbeat rows,
and it never gates the observation stream (ADR-0018 rules 1 & 6). Pure schema in
contracts.py; only persist/discovery/refresh touch the ORM."""
```

```python
# src/hw_radar/refdata/contracts.py
"""Seed-document schema (plan decision D1): one product family per JSON document,
hand-curated from FIRST-PARTY datasheets/manuals whose URLs + retrieval dates ride
the provenance block. Typed spec fields are populated only when the first-party
source states them — None means UNKNOWN, never guessed (suitability rule).
Pure: no Django imports; persist.py owns the ORM. Alias join keys are
matching.normalize.normalize_alias_text — the ADR-0019 single-normalizer
invariant; never fork a second normalizer."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from hw_radar.matching.normalize import normalize_alias_text

SEED_SCHEMA = "hw-radar.refdata.seed/v1"

_MANUFACTURER_KEY = re.compile(r"^[a-z][a-z0-9_]*$")


class SeedSource(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    url: str
    title: str
    retrieved: date


class SeedProvenance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_kind: Literal[
        "first_party_datasheet", "first_party_manual", "first_party_page"
    ]
    sources: tuple[SeedSource, ...] = Field(min_length=1)


class SeedAlias(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    # oem_pn and house SKUs are LISTING-DERIVED aliases (ADR-0019 rule 7);
    # the catalog never seeds them — hence the narrow Literal.
    alias_type: Literal["mpn", "retail_pn", "region_pn"]
    text: str = Field(min_length=1)
    is_primary: bool = False

    @property
    def normalized(self) -> str:
        return normalize_alias_text(self.text)


class SeedSpec(BaseModel):
    """Field names mirror catalog.models.DriveSpec verbatim so persist.py can
    model_dump(exclude_none=True) straight into update_or_create defaults."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    media_type: Literal["hdd", "ssd"]
    interface: str | None = None
    form_factor: str | None = None
    capacity_tb: Decimal | None = None
    rpm: int | None = None
    cache_mb: int | None = None
    recording_tech: Literal["cmr", "smr_dm", "smr_hm"] | None = None
    sector_format: Literal["512n", "512e", "4kn"] | None = None
    sed: bool | None = None
    workload_tb_year: int | None = None
    market_tier: str = ""
    model_family: str = ""
    spec_json: dict[str, object] = Field(default_factory=dict)


class SeedModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    model_number: str = Field(min_length=1)
    spec: SeedSpec
    aliases: tuple[SeedAlias, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _aliases_coherent(self) -> SeedModel:
        primaries = [a for a in self.aliases if a.is_primary]
        if len(primaries) != 1:
            msg = f"{self.model_number}: exactly one primary alias required"
            raise ValueError(msg)
        own_key = normalize_alias_text(self.model_number)
        if all(a.normalized != own_key for a in self.aliases):
            # Rung-1 joinability guarantee: the model number itself must be
            # an alias, or listings printing it can never exact-match.
            msg = f"{self.model_number}: no alias covers the model number"
            raise ValueError(msg)
        return self


class SeedDocument(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    schema_id: Literal["hw-radar.refdata.seed/v1"] = Field(alias="schema")
    manufacturer_name: str = Field(min_length=1)
    manufacturer_key: str
    family_name: str = Field(min_length=1)
    provenance: SeedProvenance
    models: tuple[SeedModel, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _key_normalized(self) -> SeedDocument:
        if not _MANUFACTURER_KEY.fullmatch(self.manufacturer_key):
            msg = f"manufacturer_key {self.manufacturer_key!r} is not a normalized key"
            raise ValueError(msg)
        return self


@dataclass(frozen=True)
class SeedConflict:
    """Two aliases normalize to one key but point at different targets — the
    rung-1 hit-aggregation carry-forward: fail into review, never pick one."""

    alias_type_set: tuple[str, ...]
    normalized_text: str
    targets: tuple[str, ...]  # "manufacturer_key/model_number", sorted

    def describe(self) -> str:
        types = ",".join(self.alias_type_set)
        targets = " vs ".join(self.targets)
        return f"[{types}] {self.normalized_text!r} → {targets}"


def detect_conflicts(docs: Sequence[SeedDocument]) -> tuple[SeedConflict, ...]:
    """Pure within/across-document conflict scan. DB-side conflicts (existing
    aliases, cross-manufacturer collisions) live in persist._db_conflicts."""

    targets_by_key: dict[str, set[str]] = {}
    types_by_key: dict[str, set[str]] = {}
    for doc in docs:
        for model in doc.models:
            target = f"{doc.manufacturer_key}/{model.model_number}"
            for alias in model.aliases:
                targets_by_key.setdefault(alias.normalized, set()).add(target)
                types_by_key.setdefault(alias.normalized, set()).add(alias.alias_type)
    return tuple(
        SeedConflict(
            alias_type_set=tuple(sorted(types_by_key[key])),
            normalized_text=key,
            targets=tuple(sorted(targets)),
        )
        for key, targets in sorted(targets_by_key.items())
        if len(targets) > 1
    )
```

```python
# src/hw_radar/refdata/loader.py
"""Seed-document loader — MS-1c's whole "fetch+parse" stage (plan decision D1:
curated in-repo documents; a live datasheet fetcher would replace THIS seam).
Seeds ship inside the package so deploy (rsync, ADR-0006) carries them."""

from __future__ import annotations

from pathlib import Path

from hw_radar.refdata.contracts import SeedDocument

SEED_DIR = Path(__file__).resolve().parent / "seeds"


def load_seed_documents(seed_dir: Path | None = None) -> list[SeedDocument]:
    directory = seed_dir if seed_dir is not None else SEED_DIR
    paths = sorted(directory.glob("*.json"))
    if not paths:
        msg = f"no seed documents found in {directory}"
        raise FileNotFoundError(msg)
    return [
        SeedDocument.model_validate_json(path.read_text(encoding="utf-8"))
        for path in paths
    ]
```

- [ ] **Step 4: Write the Exos recertified seed document**

Only research-doc-evidenced fields are typed; `rpm`/`cache_mb`/`workload_tb_year` stay null pending the Task 2 first-party enrichment pass.

```json
{
  "schema": "hw-radar.refdata.seed/v1",
  "manufacturer_name": "Seagate",
  "manufacturer_key": "seagate",
  "family_name": "Exos",
  "provenance": {
    "source_kind": "first_party_datasheet",
    "sources": [
      {
        "url": "https://www.seagate.com/content/dam/seagate/en/content-fragments/products/datasheets/exos-recertified-drive/exos-recertified-drive-DS2045-2-2010US-October-2020-en_US.pdf",
        "title": "Seagate Exos Recertified Drive datasheet DS2045.2",
        "retrieved": "2026-07-05"
      },
      {
        "url": "https://www.seagate.com/products/seagate-recertified/exos-recertified/",
        "title": "Seagate direct Exos recertified category page",
        "retrieved": "2026-07-05"
      }
    ]
  },
  "models": [
    {
      "model_number": "ST16000NM002C",
      "spec": {
        "media_type": "hdd",
        "interface": "SATA 6Gb/s",
        "form_factor": "3.5",
        "capacity_tb": "16",
        "sector_format": "512e",
        "recording_tech": "cmr",
        "market_tier": "enterprise",
        "model_family": "Exos",
        "spec_json": {"seagate_recertified_sku": true}
      },
      "aliases": [{"alias_type": "mpn", "text": "ST16000NM002C", "is_primary": true}]
    },
    {
      "model_number": "ST20000NM002C",
      "spec": {
        "media_type": "hdd",
        "interface": "SATA 6Gb/s",
        "form_factor": "3.5",
        "capacity_tb": "20",
        "sector_format": "512e",
        "recording_tech": "cmr",
        "market_tier": "enterprise",
        "model_family": "Exos",
        "spec_json": {"seagate_recertified_sku": true}
      },
      "aliases": [{"alias_type": "mpn", "text": "ST20000NM002C", "is_primary": true}]
    },
    {
      "model_number": "ST22000NM000C",
      "spec": {
        "media_type": "hdd",
        "interface": "SATA 6Gb/s",
        "form_factor": "3.5",
        "capacity_tb": "22",
        "sector_format": "512e",
        "recording_tech": "cmr",
        "market_tier": "enterprise",
        "model_family": "Exos",
        "spec_json": {"seagate_recertified_sku": true}
      },
      "aliases": [{"alias_type": "mpn", "text": "ST22000NM000C", "is_primary": true}]
    },
    {
      "model_number": "ST24000NM000C",
      "spec": {
        "media_type": "hdd",
        "interface": "SATA 6Gb/s",
        "form_factor": "3.5",
        "capacity_tb": "24",
        "sector_format": "512e",
        "recording_tech": "cmr",
        "market_tier": "enterprise",
        "model_family": "Exos",
        "spec_json": {"seagate_recertified_sku": true}
      },
      "aliases": [{"alias_type": "mpn", "text": "ST24000NM000C", "is_primary": true}]
    },
    {
      "model_number": "ST26000NM000C",
      "spec": {
        "media_type": "hdd",
        "interface": "SATA 6Gb/s",
        "form_factor": "3.5",
        "capacity_tb": "26",
        "sector_format": "512e",
        "recording_tech": "cmr",
        "market_tier": "enterprise",
        "model_family": "Exos",
        "spec_json": {"seagate_recertified_sku": true}
      },
      "aliases": [{"alias_type": "mpn", "text": "ST26000NM000C", "is_primary": true}]
    },
    {
      "model_number": "ST28000NM000C",
      "spec": {
        "media_type": "hdd",
        "interface": "SATA 6Gb/s",
        "form_factor": "3.5",
        "capacity_tb": "28",
        "sector_format": "512e",
        "recording_tech": "cmr",
        "market_tier": "enterprise",
        "model_family": "Exos",
        "spec_json": {"seagate_recertified_sku": true}
      },
      "aliases": [{"alias_type": "mpn", "text": "ST28000NM000C", "is_primary": true}]
    }
  ]
}
```

- [ ] **Step 5: Run the tests — everything committed in this task must be green**

Run: `uv run pytest tests/unit/test_refdata_contracts.py tests/unit/test_refdata_loader.py -v`
Expected: PASS (all — the loader tests are corpus-size-independent, so they pass against the single Exos document)

- [ ] **Step 6: Fix pass and commit**

```bash
uv run ruff format . && uv run ruff check . --fix
git add src/hw_radar/refdata tests/unit/test_refdata_contracts.py tests/unit/test_refdata_loader.py
git commit -m "feat(refdata): seed-document contracts, loader, Exos recertified seed (ADR-0018 D1)"
```

---

### Task 2: IronWolf Pro + Ultrastar DC HC550 seeds, first-party enrichment pass

**Files:**
- Create: `src/hw_radar/refdata/seeds/seagate-ironwolf-pro.json`
- Create: `src/hw_radar/refdata/seeds/wd-ultrastar-dc-hc550.json`
- Modify: `src/hw_radar/refdata/seeds/seagate-exos-recertified.json` (enrichment only)
- Test: `tests/unit/test_refdata_loader.py` (now fully green)

**Interfaces:**
- Consumes: `SeedDocument` schema from Task 1.
- Produces: the full 3-document / 15-model / 17-alias seed corpus that Tasks 4–8 import.

- [ ] **Step 1: Write the IronWolf Pro seed document**

```json
{
  "schema": "hw-radar.refdata.seed/v1",
  "manufacturer_name": "Seagate",
  "manufacturer_key": "seagate",
  "family_name": "IronWolf Pro",
  "provenance": {
    "source_kind": "first_party_datasheet",
    "sources": [
      {
        "url": "https://www.seagate.com/files/www-content/datasheets/pdfs/ironwolf-pro-20tb-DS1914-21-2206US-en_US.pdf",
        "title": "Seagate IronWolf Pro datasheet DS1914.21",
        "retrieved": "2026-07-05"
      }
    ]
  },
  "models": [
    {
      "model_number": "ST20000NE000",
      "spec": {
        "media_type": "hdd",
        "interface": "SATA 6Gb/s",
        "form_factor": "3.5",
        "capacity_tb": "20",
        "sector_format": "512e",
        "recording_tech": "cmr",
        "market_tier": "nas",
        "model_family": "IronWolf Pro"
      },
      "aliases": [{"alias_type": "mpn", "text": "ST20000NE000", "is_primary": true}]
    },
    {
      "model_number": "ST18000NE000",
      "spec": {
        "media_type": "hdd",
        "interface": "SATA 6Gb/s",
        "form_factor": "3.5",
        "capacity_tb": "18",
        "sector_format": "512e",
        "recording_tech": "cmr",
        "market_tier": "nas",
        "model_family": "IronWolf Pro"
      },
      "aliases": [{"alias_type": "mpn", "text": "ST18000NE000", "is_primary": true}]
    },
    {
      "model_number": "ST16000NE000",
      "spec": {
        "media_type": "hdd",
        "interface": "SATA 6Gb/s",
        "form_factor": "3.5",
        "capacity_tb": "16",
        "sector_format": "512e",
        "recording_tech": "cmr",
        "market_tier": "nas",
        "model_family": "IronWolf Pro"
      },
      "aliases": [{"alias_type": "mpn", "text": "ST16000NE000", "is_primary": true}]
    },
    {
      "model_number": "ST14000NE0008",
      "spec": {
        "media_type": "hdd",
        "interface": "SATA 6Gb/s",
        "form_factor": "3.5",
        "capacity_tb": "14",
        "sector_format": "512e",
        "recording_tech": "cmr",
        "market_tier": "nas",
        "model_family": "IronWolf Pro"
      },
      "aliases": [{"alias_type": "mpn", "text": "ST14000NE0008", "is_primary": true}]
    },
    {
      "model_number": "ST12000NE0008",
      "spec": {
        "media_type": "hdd",
        "interface": "SATA 6Gb/s",
        "form_factor": "3.5",
        "capacity_tb": "12",
        "sector_format": "512e",
        "recording_tech": "cmr",
        "market_tier": "nas",
        "model_family": "IronWolf Pro"
      },
      "aliases": [{"alias_type": "mpn", "text": "ST12000NE0008", "is_primary": true}]
    }
  ]
}
```

- [ ] **Step 2: Write the Ultrastar DC HC550 seed document — deliberately a bounded starter subset (D2a)**

This document seeds only the **four research-evidenced recert-market rows**, not WD's full HC550 matrix (which spans 14/16/18 TB with six SATA + nine SAS rows and 4Kn/security variants — Codex CR-001). Nothing in code, tests, or docs may describe this as the full HC550 fan-out; the full-fan-out acceptance family is Exos recertified. `rpm=7200`, `cache_mb=512`, `workload_tb_year=550` are family-wide values stated in the WD HC550 datasheet (research-doc evidence row). `…ALE604` is a **distinct model number** from `…ALE6L4` (power-disable-pin/security position in the WD OEM model matrix); it stays its own `ProductModel` with the open suffix question recorded in `spec_json`.

```json
{
  "schema": "hw-radar.refdata.seed/v1",
  "manufacturer_name": "Western Digital",
  "manufacturer_key": "western_digital",
  "family_name": "Ultrastar DC HC550",
  "provenance": {
    "source_kind": "first_party_datasheet",
    "sources": [
      {
        "url": "https://documents.westerndigital.com/content/dam/doc-library/en_us/assets/public/western-digital/product/data-center-drives/ultrastar-dc-hc500-series/data-sheet-ultrastar-dc-hc550.pdf",
        "title": "WD Ultrastar DC HC550 datasheet",
        "retrieved": "2026-07-05"
      },
      {
        "url": "https://documents.westerndigital.com/content/dam/doc-library/en_us/assets/public/western-digital/product/data-center-drives/ultrastar-dc-hc500-series/product-manual-ultrastar-dc-hc550-sata-oem-spec.pdf",
        "title": "WD Ultrastar DC HC550 SATA OEM product manual",
        "retrieved": "2026-07-05"
      },
      {
        "url": "https://documents.westerndigital.com/content/dam/doc-library/en_us/assets/public/western-digital/product/data-center-drives/ultrastar-dc-hc500-series/product-manual-ultrastar-dc-hc550-sas-oem-spec.pdf",
        "title": "WD Ultrastar DC HC550 SAS OEM product manual",
        "retrieved": "2026-07-05"
      }
    ]
  },
  "models": [
    {
      "model_number": "WUH721818ALE6L4",
      "spec": {
        "media_type": "hdd",
        "interface": "SATA 6Gb/s",
        "form_factor": "3.5",
        "capacity_tb": "18",
        "rpm": 7200,
        "cache_mb": 512,
        "sector_format": "512e",
        "recording_tech": "cmr",
        "workload_tb_year": 550,
        "market_tier": "enterprise",
        "model_family": "Ultrastar DC HC550"
      },
      "aliases": [
        {"alias_type": "mpn", "text": "WUH721818ALE6L4", "is_primary": true},
        {"alias_type": "retail_pn", "text": "0F38459"}
      ]
    },
    {
      "model_number": "WUH721818AL5201",
      "spec": {
        "media_type": "hdd",
        "interface": "SAS 12Gb/s",
        "form_factor": "3.5",
        "capacity_tb": "18",
        "rpm": 7200,
        "cache_mb": 512,
        "sector_format": "512e",
        "recording_tech": "cmr",
        "workload_tb_year": 550,
        "market_tier": "enterprise",
        "model_family": "Ultrastar DC HC550"
      },
      "aliases": [
        {"alias_type": "mpn", "text": "WUH721818AL5201", "is_primary": true},
        {"alias_type": "retail_pn", "text": "0F38352"}
      ]
    },
    {
      "model_number": "WUH721816ALE6L4",
      "spec": {
        "media_type": "hdd",
        "interface": "SATA 6Gb/s",
        "form_factor": "3.5",
        "capacity_tb": "16",
        "rpm": 7200,
        "cache_mb": 512,
        "recording_tech": "cmr",
        "workload_tb_year": 550,
        "market_tier": "enterprise",
        "model_family": "Ultrastar DC HC550"
      },
      "aliases": [{"alias_type": "mpn", "text": "WUH721816ALE6L4", "is_primary": true}]
    },
    {
      "model_number": "WUH721816ALE604",
      "spec": {
        "media_type": "hdd",
        "interface": "SATA 6Gb/s",
        "form_factor": "3.5",
        "capacity_tb": "16",
        "rpm": 7200,
        "cache_mb": 512,
        "recording_tech": "cmr",
        "workload_tb_year": 550,
        "market_tier": "enterprise",
        "model_family": "Ultrastar DC HC550",
        "spec_json": {
          "suffix_note": "ALE604 vs ALE6L4: distinct WD model numbers (power-disable pin / security position per HC550 SATA OEM manual); kept as separate product_model rows"
        }
      },
      "aliases": [{"alias_type": "mpn", "text": "WUH721816ALE604", "is_primary": true}]
    }
  ]
}
```

- [ ] **Step 3: First-party enrichment pass (bounded, fallback = leave null)**

Attempt to fetch the two Seagate datasheet PDFs (URLs in the seed provenance blocks) with `tavily_extract`/WebFetch. For each model row, fill `rpm`, `cache_mb`, `workload_tb_year` (and `sector_format` for `WUH721816ALE6L4`/`WUH721816ALE604` from the HC550 SATA OEM manual) **only when the first-party document states the value for that specific model**. Also cross-check the four HC550 rows and both `0F…` part numbers against the WD datasheet tables. If a fetch fails or the PDF is unreadable, leave the field null — null means unknown, never guessed. Never copy typed values from merchant pages. Update the `retrieved` date on any source actually re-fetched.

- [ ] **Step 4: Add the corpus-count test (lands with the corpus it counts — Codex CR-002)**

Append to `tests/unit/test_refdata_loader.py`:

```python
def test_repo_seed_corpus_totals() -> None:
    docs = load_seed_documents()
    assert {d.manufacturer_key for d in docs} == {"seagate", "western_digital"}
    assert sum(len(d.models) for d in docs) == 15
    assert sum(len(m.aliases) for d in docs for m in d.models) == 17
```

- [ ] **Step 5: Run the loader tests — now fully green**

Run: `uv run pytest tests/unit/test_refdata_loader.py tests/unit/test_refdata_contracts.py -v`
Expected: PASS (15 models across 3 documents, zero conflicts, alias parity holds)

- [ ] **Step 6: Fix pass and commit**

```bash
uv run ruff format . && uv run ruff check . --fix
git add src/hw_radar/refdata/seeds tests/unit/test_refdata_loader.py
git commit -m "feat(refdata): IronWolf Pro + Ultrastar DC HC550 (starter subset) seed documents"
```

---

### Task 3: Schema — RefdataConfig, ReferenceFetchRequest, edge freshness column

**Files:**
- Modify: `src/hw_radar/catalog/models/ops.py` (append `RefdataConfig`)
- Modify: `src/hw_radar/catalog/models/resolution.py` (add `last_evaluated_at`; append `FetchRequestStatus`, `ReferenceFetchRequest`)
- Modify: `src/hw_radar/catalog/models/__init__.py` (export `RefdataConfig`, `ReferenceFetchRequest`, `FetchRequestStatus`)
- Modify: `src/hw_radar/catalog/admin.py`
- Create: `src/hw_radar/catalog/migrations/0008_refdata_seed.py` (generated)
- Test: `tests/db/test_refdata_refresh.py` (model-shape tests only at this task)

**Interfaces:**
- Consumes: `TimeStamped` from `catalog.models.base`.
- Produces: `RefdataConfig.current() -> RefdataConfig` (fields: `enabled: bool = True`, `discovery_occurrence_threshold: int = 3`, `last_refresh_at: datetime | None`, `last_report_json: dict`); `ReferenceFetchRequest` (fields: `hypothesis_key` unique, `mpn_hypothesis`, `vendor_hint`, `occurrences_at_enqueue`, `status`, `notes`); `ListingResolution.last_evaluated_at` (default `timezone.now`). Tasks 5–7 use these exact names.

- [ ] **Step 1: Write the failing model-shape tests**

```python
# tests/db/test_refdata_refresh.py
"""RefdataConfig settings row, ReferenceFetchRequest queue, and (later tasks)
the reconsider/discovery/refresh loop."""

import pytest

from hw_radar.catalog.models import (
    FetchRequestStatus,
    RefdataConfig,
    ReferenceFetchRequest,
)

pytestmark = pytest.mark.django_db


def test_refdata_config_current_is_a_get_or_create_singleton() -> None:
    first = RefdataConfig.current()
    second = RefdataConfig.current()
    assert first.pk == second.pk == 1
    assert first.enabled is True
    assert first.discovery_occurrence_threshold == 3  # ADR-0016 tunable default


def test_reference_fetch_request_dedupes_on_hypothesis_key() -> None:
    ReferenceFetchRequest.objects.create(
        hypothesis_key="seagate:st99000nm999",
        mpn_hypothesis="st99000nm999",
        vendor_hint="seagate",
        occurrences_at_enqueue=3,
    )
    row, created = ReferenceFetchRequest.objects.get_or_create(
        hypothesis_key="seagate:st99000nm999",
        defaults={
            "mpn_hypothesis": "st99000nm999",
            "vendor_hint": "seagate",
            "occurrences_at_enqueue": 5,
        },
    )
    assert created is False
    assert row.status == FetchRequestStatus.PENDING
```

- [ ] **Step 2: Run to verify failure**

Run: `HW_RADAR_DB_PORT=5433 uv run pytest tests/db/test_refdata_refresh.py -v`
Expected: FAIL with `ImportError: cannot import name 'RefdataConfig'`

- [ ] **Step 3: Add the models**

Append to `src/hw_radar/catalog/models/ops.py`:

```python
class RefdataConfig(TimeStamped):
    """ADR-0016 settings row for ADR-0018 reference ingest: the C.3.4 discovery
    occurrence threshold and the refresh kill-switch, changed by UPDATE not
    deploy. Single row (pk=1) via current(); refdata.refresh stamps the last
    run's report here (no ScraperRun row — reference ingest has no SourceSite)."""

    enabled = models.BooleanField(default=True)
    discovery_occurrence_threshold = models.PositiveIntegerField(default=3)
    last_refresh_at = models.DateTimeField(null=True, blank=True)
    last_report_json: models.JSONField[dict[str, object]] = models.JSONField(
        default=dict, blank=True
    )

    class Meta:
        db_table = "refdata_config"

    @classmethod
    def current(cls) -> "RefdataConfig":
        row, _ = cls.objects.get_or_create(pk=1)
        return row
```

Append to `src/hw_radar/catalog/models/resolution.py` (and add `last_evaluated_at` inside `ListingResolution`, directly under `resolved_at`):

```python
    # Mutable freshness stamp (MS-1b carry-forward: unchanged_miss evidence
    # freshness). Updated in place whenever the resolver re-evaluates the
    # listing and writes NO new edge — the deliberate exception, alongside
    # is_current/superseded_by, to the append-only rule. Deliberately NOT in
    # the evidence JSON: evidence describes the verdict, this describes when
    # the verdict was last reconfirmed.
    last_evaluated_at = models.DateTimeField(default=timezone.now)
```

```python
class FetchRequestStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    DONE = "done", "Done"
    DISMISSED = "dismissed", "Dismissed"


class ReferenceFetchRequest(TimeStamped):
    """C.3.4 discovery loop, made concrete: a decoded-but-unknown MPN whose
    occurrence count crossed RefdataConfig.discovery_occurrence_threshold.
    Worked manually (Django admin) in MS-1c — 'targeted reference fetch' means
    a human/agent authors the missing seed document; rows are the queue, not
    an automated fetcher."""

    hypothesis_key = models.CharField(max_length=300, unique=True)
    mpn_hypothesis = models.CharField(max_length=200)
    vendor_hint = models.CharField(max_length=50, blank=True, default="")
    occurrences_at_enqueue = models.PositiveIntegerField()
    status = models.CharField(
        max_length=10, choices=FetchRequestStatus.choices, default=FetchRequestStatus.PENDING
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "reference_fetch_request"
```

`resolution.py` already imports `timezone`; `ReferenceFetchRequest` needs `TimeStamped` added to its `from hw_radar.catalog.models.base import ...` line.

Export all three from `catalog/models/__init__.py` (alphabetical, matching the existing style).

Append to `src/hw_radar/catalog/admin.py` (import the new models in the existing import block):

```python
@admin.register(RefdataConfig)
class RefdataConfigAdmin(
    admin.ModelAdmin  # pyright: ignore[reportMissingTypeArgument]
    # see ListingResolutionAdmin: runtime ModelAdmin isn't subscriptable
):
    list_display = ("pk", "enabled", "discovery_occurrence_threshold", "last_refresh_at")


@admin.register(ReferenceFetchRequest)
class ReferenceFetchRequestAdmin(
    admin.ModelAdmin  # pyright: ignore[reportMissingTypeArgument]
):
    list_display = (
        "hypothesis_key",
        "vendor_hint",
        "occurrences_at_enqueue",
        "status",
        "created_at",
    )
    list_filter = ("status", "vendor_hint")
    search_fields = ("hypothesis_key", "mpn_hypothesis")
```

- [ ] **Step 4: Generate and review the migration**

```bash
uv run python manage.py makemigrations catalog -n refdata_seed
```

Review `0008_refdata_seed.py`: it must contain exactly `CreateModel RefdataConfig`, `CreateModel ReferenceFetchRequest`, and `AddField listing_resolution.last_evaluated_at` with a `django.utils.timezone.now` default — nothing else. (If the autodetector emits anything more, stop and reconcile before committing.)

- [ ] **Step 5: Run the tests**

Run: `HW_RADAR_DB_PORT=5433 uv run pytest tests/db/test_refdata_refresh.py tests/db/test_migrations.py -v`
Expected: PASS (including the repo's `makemigrations --check` guard)

- [ ] **Step 6: Fix pass and commit**

```bash
uv run ruff format . && uv run ruff check . --fix
git add src/hw_radar/catalog tests/db/test_refdata_refresh.py
git commit -m "feat(catalog): RefdataConfig settings row, reference-fetch queue, edge freshness column"
```

---

### Task 4: The importer — validate-then-write, adoption, DR-009

**Files:**
- Create: `src/hw_radar/refdata/persist.py`
- Test: `tests/db/test_refdata_import.py`

**Interfaces:**
- Consumes: `SeedDocument`/`detect_conflicts` (Task 1), `matching.normalize` (MS-1b), `matching.ladder.brands_consistent` (MS-1b), catalog identity models (MS-0).
- Produces: `import_documents(docs: Sequence[SeedDocument]) -> ImportReport`; `ImportConflictError(conflicts: list[str])`; `ImportReport` dataclass with fields `manufacturers_created`, `families_created`, `families_adopted: list[str]`, `models_created`, `models_seen`, `specs_written`, `aliases_created`, `aliases_adopted`, `unreconciled_families: list[str]`, and method `as_json() -> dict[str, object]`. Tasks 6/7 consume these exact names.

- [ ] **Step 1: Write the failing tests**

```python
# tests/db/test_refdata_import.py
"""ADR-0018 importer semantics: DR-009 stamping, idempotence, provisional-family
adoption, discontinued retention, conflict fail-into-review, SanDisk/WD
cross-manufacturer collision detection."""

from decimal import Decimal

import pytest

from hw_radar.catalog.models import (
    AliasSourceKind,
    AliasType,
    Category,
    DriveSpec,
    Manufacturer,
    ProductAlias,
    ProductFamily,
    ProductModel,
    RetentionClass,
)
from hw_radar.matching.normalize import normalize_alias_text
from hw_radar.refdata.loader import load_seed_documents
from hw_radar.refdata.persist import ImportConflictError, import_documents

pytestmark = pytest.mark.django_db


@pytest.fixture
def docs():  # the real repo corpus — the fixtures ARE the seed
    return load_seed_documents()


def test_import_writes_the_full_corpus_with_dr009_stamps(docs) -> None:
    report = import_documents(docs)
    assert report.models_created == 15
    assert report.aliases_created == 17
    assert ProductModel.objects.count() == 15
    assert DriveSpec.objects.count() == 15
    for model in ProductModel.objects.all():
        assert model.retention_class == RetentionClass.MANUFACTURER_REFERENCE
        assert model.expires_at is None
    for alias in ProductAlias.objects.all():
        assert alias.retention_class == RetentionClass.MANUFACTURER_REFERENCE
        assert alias.source_kind == AliasSourceKind.CATALOG_AUTHORITATIVE
        assert alias.source_site is None
    spec = DriveSpec.objects.get(product_model__model_number="WUH721818ALE6L4")
    assert spec.capacity_tb == Decimal("18")
    assert spec.cache_mb == 512


def test_import_is_idempotent(docs) -> None:
    import_documents(docs)
    report = import_documents(docs)
    assert report.models_created == 0
    assert report.aliases_created == 0
    assert ProductModel.objects.count() == 15
    assert ProductAlias.objects.count() == 17


def test_import_adopts_rung2_provisional_family(docs) -> None:
    # Simulate MS-1b: rung 2 materialized a provisional broad 'exos' family.
    seagate = Manufacturer.objects.create(name="Seagate", normalized_name="seagate")
    category = Category.objects.get_or_create(slug="drive", defaults={"name": "Drive"})[0]
    provisional = ProductFamily.objects.create(
        manufacturer=seagate, category=category, name="Exos", normalized_name="exos"
    )
    report = import_documents(docs)
    assert "exos" in report.families_adopted
    adopted = ProductFamily.objects.get(manufacturer=seagate, normalized_name="exos")
    assert adopted.pk == provisional.pk  # same row, no duplicate
    assert adopted.models.count() == 6


def test_unadopted_provisional_families_are_reported_not_touched(docs) -> None:
    seagate = Manufacturer.objects.create(name="Seagate", normalized_name="seagate")
    category = Category.objects.get_or_create(slug="drive", defaults={"name": "Drive"})[0]
    ProductFamily.objects.create(
        manufacturer=seagate, category=category, name="Barracuda", normalized_name="barracuda"
    )
    report = import_documents(docs)
    assert "barracuda" in report.unreconciled_families
    assert ProductFamily.objects.filter(normalized_name="barracuda").exists()


def test_discontinued_model_is_retained_on_refresh(docs) -> None:
    import_documents(docs)
    # Simulate the vendor dropping the 12TB IronWolf Pro from a later datasheet.
    trimmed = [
        doc.model_copy(
            update={"models": tuple(m for m in doc.models if m.model_number != "ST12000NE0008")}
        )
        if doc.family_name == "IronWolf Pro"
        else doc
        for doc in docs
    ]
    import_documents(trimmed)
    assert ProductModel.objects.filter(model_number="ST12000NE0008").exists()  # DR-009


def test_existing_listing_derived_alias_same_target_is_adopted(docs) -> None:
    report = import_documents(docs)
    model = ProductModel.objects.get(model_number="ST16000NE000")
    alias = ProductAlias.objects.get(normalized_alias_text=normalize_alias_text("ST16000NE000"))
    # Pre-existing listing_derived alias at the same target upgrades in place —
    # simulate by downgrading, then re-importing.
    alias.source_kind = AliasSourceKind.LISTING_DERIVED
    alias.retention_class = ""
    alias.save(update_fields=["source_kind", "retention_class"])
    report = import_documents(docs)
    alias.refresh_from_db()
    assert alias.source_kind == AliasSourceKind.CATALOG_AUTHORITATIVE
    assert alias.retention_class == RetentionClass.MANUFACTURER_REFERENCE
    assert alias.product_model_id == model.pk
    assert report.aliases_adopted >= 1


def test_alias_pointing_at_a_different_target_fails_into_review(docs) -> None:
    # Generic cross-manufacturer collision: a same-key global alias under a
    # DIFFERENT manufacturer/model aborts the whole import — nothing written.
    samsung = Manufacturer.objects.create(name="Samsung", normalized_name="samsung")
    stranger = ProductModel.objects.create(
        manufacturer=samsung,
        model_number="NOT-A-WD-DRIVE",
        normalized_model_number=normalize_alias_text("NOT-A-WD-DRIVE"),
        retention_class=RetentionClass.MANUFACTURER_REFERENCE,
    )
    ProductAlias.objects.create(
        alias_type=AliasType.MPN,
        normalized_alias_text=normalize_alias_text("WUH721818ALE6L4"),
        product_model=stranger,
        source_kind=AliasSourceKind.LISTING_DERIVED,
    )
    before = ProductModel.objects.count()
    with pytest.raises(ImportConflictError) as excinfo:
        import_documents(docs)
    assert any("wuh721818ale6l4" in c for c in excinfo.value.conflicts)
    assert any("cross-brand" in c for c in excinfo.value.conflicts)
    assert ProductModel.objects.count() == before  # transaction rolled back


def test_brand_equivalent_collision_is_flagged_as_such(docs) -> None:
    # D7: the SanDisk↔WD lineage path — the collision still aborts (different
    # target), but the descriptor says 'brand-equivalent' so review knows this
    # is the Optimus-rebrand case, not a random cross-brand clash. Real-corpus
    # SanDisk↔WD verification stays deferred to the first SSD seed.
    sandisk = Manufacturer.objects.create(name="SanDisk", normalized_name="sandisk")
    rebrand = ProductModel.objects.create(
        manufacturer=sandisk,
        model_number="WUH721818ALE6L4-SD",
        normalized_model_number=normalize_alias_text("WUH721818ALE6L4-SD"),
        retention_class=RetentionClass.MANUFACTURER_REFERENCE,
    )
    ProductAlias.objects.create(
        alias_type=AliasType.MPN,
        normalized_alias_text=normalize_alias_text("WUH721818ALE6L4"),
        product_model=rebrand,
        source_kind=AliasSourceKind.LISTING_DERIVED,
    )
    with pytest.raises(ImportConflictError) as excinfo:
        import_documents(docs)
    assert any("brand-equivalent" in c and "wuh721818ale6l4" in c for c in excinfo.value.conflicts)
```

- [ ] **Step 2: Run to verify failure**

Run: `HW_RADAR_DB_PORT=5433 uv run pytest tests/db/test_refdata_import.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'hw_radar.refdata.persist'`

- [ ] **Step 3: Write the importer**

```python
# src/hw_radar/refdata/persist.py
"""The ADR-0018 persist stage: validate-then-write, one transaction.

Invariants:
- Conflicts (rung-1 hit-aggregation carry-forward) ABORT the whole import with
  nothing written — two aliases normalizing to one key with different targets
  fail into review, never auto-select. This covers within-seed, across-seed,
  and against-DB collisions, including cross-manufacturer ones (descriptors say
  whether the colliding brands are ladder-equivalent — the SanDisk↔WD lineage —
  so review can decide; real-corpus SanDisk↔WD verification is deferred to the
  first SSD seed, plan D7).
- SINGLE-WRITER assumption (plan D8): the conflict precheck is not safe against
  alias writes racing between _db_conflicts() and _import_alias(). Only the
  monthly poller job and the manual import_refdata command may run this, never
  concurrently; the defensive re-check aborts rather than retargets.
- Keys match the resolver's materialization exactly — family get_or_create on
  (manufacturer, canonicalize_title(name)), so seeding 'Exos' ADOPTS the rung-2
  provisional 'exos' row instead of duplicating it (carry-forward #4).
- DR-009: every written ProductModel/DriveSpec/ProductAlias row carries
  retention_class=manufacturer_reference, expires_at NULL. Absent-from-seed
  models are never deleted (append-only).
- Never writes offer_snapshot/score/alert/heartbeat rows (ADR-0018 rule 1)."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field

from django.db import transaction

from hw_radar.catalog.models import (
    AliasSourceKind,
    Category,
    DriveSpec,
    Manufacturer,
    ProductAlias,
    ProductFamily,
    ProductModel,
    RetentionClass,
)
from hw_radar.matching.ladder import brands_consistent
from hw_radar.matching.normalize import canonicalize_title, normalize_alias_text
from hw_radar.refdata.contracts import SeedAlias, SeedDocument, SeedModel, detect_conflicts

logger = logging.getLogger(__name__)


@dataclass
class ImportReport:
    manufacturers_created: int = 0
    families_created: int = 0
    families_adopted: list[str] = field(default_factory=list)
    models_created: int = 0
    models_seen: int = 0
    specs_written: int = 0
    aliases_created: int = 0
    aliases_adopted: int = 0
    unreconciled_families: list[str] = field(default_factory=list)

    def as_json(self) -> dict[str, object]:
        return {
            "manufacturers_created": self.manufacturers_created,
            "families_created": self.families_created,
            "families_adopted": list(self.families_adopted),
            "models_created": self.models_created,
            "models_seen": self.models_seen,
            "specs_written": self.specs_written,
            "aliases_created": self.aliases_created,
            "aliases_adopted": self.aliases_adopted,
            "unreconciled_families": list(self.unreconciled_families),
        }


class ImportConflictError(Exception):
    """Alias-key conflicts detected — the import wrote NOTHING (fail into review)."""

    def __init__(self, conflicts: list[str]) -> None:
        self.conflicts = conflicts
        super().__init__(f"{len(conflicts)} alias conflict(s); import aborted")


def _seed_targets(docs: Sequence[SeedDocument]) -> dict[str, tuple[str, str]]:
    """normalized alias key → (manufacturer_key, normalized model number)."""

    targets: dict[str, tuple[str, str]] = {}
    for doc in docs:
        for model in doc.models:
            for alias in model.aliases:
                targets[alias.normalized] = (
                    doc.manufacturer_key,
                    normalize_alias_text(model.model_number),
                )
    return targets


def _existing_target(row: ProductAlias) -> tuple[str, str] | None:
    model = row.product_model
    if model is None:
        return None  # family/variant-grain alias: always a conflict for a seed key
    return (model.manufacturer.normalized_name, model.normalized_model_number)


def _db_conflicts(docs: Sequence[SeedDocument]) -> list[str]:
    targets = _seed_targets(docs)
    rows = ProductAlias.objects.filter(
        normalized_alias_text__in=list(targets), source_site__isnull=True
    ).select_related("product_model__manufacturer", "product_family__manufacturer")
    conflicts: list[str] = []
    for row in rows:
        seed_target = targets[row.normalized_alias_text]
        existing = _existing_target(row)
        if existing == seed_target:
            continue  # same target → adoption path, not a conflict
        existing_key = existing[0] if existing else "non-model-grain"
        equivalence = (
            "brand-equivalent"
            if existing and brands_consistent(seed_target[0], existing[0])
            else "cross-brand"
        )
        conflicts.append(
            f"[{row.alias_type}] {row.normalized_alias_text!r} → "
            f"seed {seed_target[0]}/{seed_target[1]} vs existing {existing_key}"
            f"/{existing[1] if existing else row.pk} ({equivalence})"
        )
    return conflicts


def import_documents(docs: Sequence[SeedDocument]) -> ImportReport:
    conflicts = [c.describe() for c in detect_conflicts(docs)]
    conflicts += _db_conflicts(docs)
    if conflicts:
        raise ImportConflictError(conflicts)
    report = ImportReport()
    with transaction.atomic():
        for doc in docs:
            _import_document(doc, report)
        report.unreconciled_families = _unreconciled_families(
            sorted({doc.manufacturer_key for doc in docs})
        )
    return report


def _import_document(doc: SeedDocument, report: ImportReport) -> None:
    manufacturer, created = Manufacturer.objects.get_or_create(
        normalized_name=doc.manufacturer_key, defaults={"name": doc.manufacturer_name}
    )
    if created:
        report.manufacturers_created += 1
    elif manufacturer.name != doc.manufacturer_name:
        manufacturer.name = doc.manufacturer_name  # seed display name is authoritative
        manufacturer.save(update_fields=["name", "updated_at"])
    category, _ = Category.objects.get_or_create(slug="drive", defaults={"name": "Drive"})
    family, created = ProductFamily.objects.get_or_create(
        manufacturer=manufacturer,
        normalized_name=canonicalize_title(doc.family_name),
        defaults={"category": category, "name": doc.family_name},
    )
    if created:
        report.families_created += 1
    else:
        # Rung-2 provisional (or prior-seed) family adopted under its
        # authoritative datasheet name (carry-forward #4).
        report.families_adopted.append(family.normalized_name)
        if family.name != doc.family_name:
            family.name = doc.family_name
            family.save(update_fields=["name", "updated_at"])
    for seed_model in doc.models:
        _import_model(manufacturer, family, seed_model, report)


def _import_model(
    manufacturer: Manufacturer,
    family: ProductFamily,
    seed_model: SeedModel,
    report: ImportReport,
) -> None:
    report.models_seen += 1
    model, created = ProductModel.objects.get_or_create(
        manufacturer=manufacturer,
        normalized_model_number=normalize_alias_text(seed_model.model_number),
        defaults={
            "model_number": seed_model.model_number,
            "product_family": family,
            "retention_class": RetentionClass.MANUFACTURER_REFERENCE,
            "expires_at": None,
        },
    )
    if created:
        report.models_created += 1
    else:
        changed: list[str] = []
        if model.product_family_id != family.pk:  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue] - django-types has no <field>_id shadow-attribute stubs
            model.product_family = family
            changed.append("product_family")
        if model.retention_class != RetentionClass.MANUFACTURER_REFERENCE:  # pyright: ignore[reportUnnecessaryComparison] - TextChoices runtime-vs-static quirk, see resolver.py
            model.retention_class = RetentionClass.MANUFACTURER_REFERENCE
            model.expires_at = None
            changed += ["retention_class", "expires_at"]
        if changed:
            model.save(update_fields=[*changed, "updated_at"])
    spec_defaults: dict[str, object] = seed_model.spec.model_dump(exclude_none=True)
    spec_defaults["retention_class"] = RetentionClass.MANUFACTURER_REFERENCE
    spec_defaults["expires_at"] = None
    DriveSpec.objects.update_or_create(product_model=model, defaults=spec_defaults)
    report.specs_written += 1
    for alias in seed_model.aliases:
        _import_alias(model, alias, report)


def _import_alias(model: ProductModel, alias: SeedAlias, report: ImportReport) -> None:
    row = ProductAlias.objects.filter(
        alias_type=alias.alias_type,
        normalized_alias_text=alias.normalized,
        source_site__isnull=True,
    ).first()
    if row is None:
        ProductAlias.objects.create(
            alias_type=alias.alias_type,
            normalized_alias_text=alias.normalized,
            product_model=model,
            source_kind=AliasSourceKind.CATALOG_AUTHORITATIVE,
            is_primary=alias.is_primary,
            retention_class=RetentionClass.MANUFACTURER_REFERENCE,
            expires_at=None,
        )
        report.aliases_created += 1
        return
    existing_model = row.product_model
    if existing_model is None or existing_model.pk != model.pk:
        # Pre-checked in _db_conflicts; unreachable unless a concurrent write
        # raced the check — abort rather than silently retarget (DR-009 posture).
        raise ImportConflictError(
            [f"[{row.alias_type}] {alias.normalized!r} raced to a different target"]
        )
    changed: list[str] = []
    if row.source_kind != AliasSourceKind.CATALOG_AUTHORITATIVE:  # pyright: ignore[reportUnnecessaryComparison] - TextChoices runtime-vs-static quirk, see resolver.py
        row.source_kind = AliasSourceKind.CATALOG_AUTHORITATIVE
        changed.append("source_kind")
    if row.is_primary != alias.is_primary:
        row.is_primary = alias.is_primary
        changed.append("is_primary")
    if row.retention_class != RetentionClass.MANUFACTURER_REFERENCE:  # pyright: ignore[reportUnnecessaryComparison] - TextChoices runtime-vs-static quirk, see resolver.py
        row.retention_class = RetentionClass.MANUFACTURER_REFERENCE
        row.expires_at = None
        changed += ["retention_class", "expires_at"]
    if changed:
        row.save(update_fields=[*changed, "last_seen"])
        report.aliases_adopted += 1


def _unreconciled_families(manufacturer_keys: list[str]) -> list[str]:
    """Families under seeded manufacturers with no models and no aliases: rung-2
    provisional rows the seed did not adopt. Reported for review, never touched."""

    return sorted(
        ProductFamily.objects.filter(manufacturer__normalized_name__in=manufacturer_keys)
        .filter(models__isnull=True, aliases__isnull=True)
        .values_list("normalized_name", flat=True)
        .distinct()
    )
```

- [ ] **Step 4: Run the tests**

Run: `HW_RADAR_DB_PORT=5433 uv run pytest tests/db/test_refdata_import.py -v`
Expected: PASS (all 9)

- [ ] **Step 5: Run the existing parity + resolver suites (must stay green)**

Run: `HW_RADAR_DB_PORT=5433 uv run pytest tests/db/test_resolver.py tests/unit -q`
Expected: PASS

- [ ] **Step 6: Fix pass and commit**

```bash
uv run ruff format . && uv run ruff check . --fix
git add src/hw_radar/refdata/persist.py tests/db/test_refdata_import.py
git commit -m "feat(refdata): validate-then-write importer — DR-009 stamping, adoption, conflict fail-into-review"
```

---

### Task 5: Resolver — reconsider mode, unchanged-target skip, freshness stamp

**Files:**
- Modify: `src/hw_radar/matching/resolver.py`
- Modify: `src/hw_radar/matching/__init__.py` (`MATCHER_VERSION = "2026.07.3"`)
- Test: `tests/db/test_resolver.py` (add tests; existing tests must stay green)

**Interfaces:**
- Consumes: `ladder.decide` (unchanged), `ListingResolution.last_evaluated_at` (Task 3).
- Produces: `CatalogResolver.resolve_listing(listing_id: int, *, reconsider: bool = False) -> None`. Task 6's refresh loop calls it with `reconsider=True`.

- [ ] **Step 1: Write the failing tests** (append to `tests/db/test_resolver.py`, reusing its `site`/`_listing`/`_edge`/`_edge_count` helpers)

```python
def test_rung0_prior_blocks_upgrade_without_reconsider(site: SourceSite) -> None:
    """The trap this task exists for: family-grain prior short-circuits rung 1."""
    listing = _listing(site, "up-1", "seagate exos st16000nm002c 16tb sata")
    CatalogResolver().resolve_listing(listing.pk)  # rung 2 → provisional family
    listing.refresh_from_db()
    assert listing.resolution_grain == ResolutionGrain.FAMILY
    _seed_alias_for("ST16000NM002C")  # helper below: catalog alias + model + spec
    CatalogResolver().resolve_listing(listing.pk)  # normal poll: rung 0 sticks
    listing.refresh_from_db()
    assert listing.resolution_grain == ResolutionGrain.FAMILY


def test_reconsider_upgrades_family_grain_via_seeded_alias(site: SourceSite) -> None:
    listing = _listing(site, "up-2", "seagate exos st16000nm002c 16tb sata")
    CatalogResolver().resolve_listing(listing.pk)
    _seed_alias_for("ST16000NM002C")
    CatalogResolver().resolve_listing(listing.pk, reconsider=True)
    listing.refresh_from_db()
    assert listing.resolution_grain == ResolutionGrain.MODEL
    edge = _edge(listing, is_current=True)
    assert edge.method == "exact_alias"
    assert edge.evidence.get("reconsider") is True


def test_reconsider_same_outcome_stamps_freshness_without_new_edge(
    site: SourceSite,
) -> None:
    listing = _listing(site, "fresh-1", "mystery drive with no tokens at all")
    CatalogResolver().resolve_listing(listing.pk)  # grain none edge
    edge = _edge(listing, is_current=True)
    stamp_before = edge.last_evaluated_at
    edges_before = _edge_count(listing)
    CatalogResolver().resolve_listing(listing.pk, reconsider=True)
    edge.refresh_from_db()
    assert _edge_count(listing) == edges_before  # no edge spam
    assert edge.last_evaluated_at > stamp_before  # but freshness recorded


def test_unchanged_rung0_accept_stamps_freshness(site: SourceSite) -> None:
    listing = _listing(site, "fresh-2", "seagate exos st16000nm002c 16tb sata")
    CatalogResolver().resolve_listing(listing.pk)
    edge = _edge(listing, is_current=True)
    stamp_before = edge.last_evaluated_at
    CatalogResolver().resolve_listing(listing.pk)  # rung-0 unchanged re-poll
    edge.refresh_from_db()
    assert edge.last_evaluated_at > stamp_before
```

Add the `_seed_alias_for` helper to the same file (module level, near `_listing`):

```python
def _seed_alias_for(model_number: str) -> ProductModel:
    """Catalog-authoritative alias + model + spec, as the Task-4 importer writes them."""
    seagate, _ = Manufacturer.objects.get_or_create(
        normalized_name="seagate", defaults={"name": "Seagate"}
    )
    model, _ = ProductModel.objects.get_or_create(
        manufacturer=seagate,
        normalized_model_number=normalize_alias_text(model_number),
        defaults={
            "model_number": model_number,
            "retention_class": RetentionClass.MANUFACTURER_REFERENCE,
        },
    )
    DriveSpec.objects.update_or_create(
        product_model=model,
        defaults={
            "media_type": MediaType.HDD,
            "capacity_tb": Decimal("16"),
            "retention_class": RetentionClass.MANUFACTURER_REFERENCE,
        },
    )
    ProductAlias.objects.get_or_create(
        alias_type=AliasType.MPN,
        normalized_alias_text=normalize_alias_text(model_number),
        source_site=None,
        defaults={
            "product_model": model,
            "source_kind": AliasSourceKind.CATALOG_AUTHORITATIVE,
            "retention_class": RetentionClass.MANUFACTURER_REFERENCE,
        },
    )
    return model
```

(Extend the file's imports as needed: `Decimal`, `AliasSourceKind`, `AliasType`, `DriveSpec`, `Manufacturer`, `MediaType`, `ProductAlias`, `ProductModel`, `RetentionClass`, `normalize_alias_text` — several are already imported.)

- [ ] **Step 2: Run to verify failure**

Run: `HW_RADAR_DB_PORT=5433 uv run pytest tests/db/test_resolver.py -v -k "reconsider or freshness or blocks_upgrade"`
Expected: FAIL — `resolve_listing() got an unexpected keyword argument 'reconsider'` (and the freshness tests fail on the missing stamp behavior)

- [ ] **Step 3: Implement the resolver changes**

Four edits to `src/hw_radar/matching/resolver.py` (plus the version bump):

**(a)** `from dataclasses import replace` added to imports. `_run_ladder` gains the mode:

```python
def _run_ladder(
    listing: Listing, *, reconsider: bool = False
) -> tuple[str, ExtractedAttributes, list[MpnCandidate], ladder.Verdict]:
    canonical = canonicalize_title(f"{listing.title_raw} {listing.condition_label_raw}".strip())
    extracted = vocab.extract(canonical)
    candidates = mpn.extract_candidates(
        canonical,
        structured_mpn=_structured_mpn(listing),
        source_key=listing.source_site.normalized_name,
    )
    # reconsider (C.3.4 catalog-refresh re-run): prior=None bypasses rung 0 so
    # rungs 1-2 get a shot at freshly seeded aliases — otherwise a family-grain
    # listing re-accepts its prior forever and the catalog seed can never
    # upgrade it. The veto still runs; unchanged outcomes write no edge.
    prior = None if reconsider else _prior_from_listing(listing)
    verdict = ladder.decide(
        extracted,
        candidates,
        prior,
        _alias_hits(
            candidates,
            listing.source_site_id,  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType, reportAttributeAccessIssue] - django-types has no <field>_id shadow-attribute stubs
        ),
        _first_decode(candidates),
    )
    if reconsider:
        verdict = replace(verdict, evidence={**verdict.evidence, "reconsider": True})
    return canonical, extracted, candidates, verdict
```

**(b)** A freshness helper + a target-tuple boundary helper (next to `_product_model_id`, same single-ignore pattern):

```python
def _stamp_evaluated(current: ListingResolution) -> None:
    current.last_evaluated_at = timezone.now()
    current.save(update_fields=["last_evaluated_at"])


def _edge_target_ids(edge: ListingResolution) -> tuple[int | None, int | None, int | None]:
    return (edge.product_family_id, edge.product_model_id, edge.product_variant_id)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType, reportAttributeAccessIssue] - django-types has no <field>_id shadow-attribute stubs
```

**(c)** In `_apply`, the existing unchanged early-return gains the stamp:

```python
    if unchanged_accept or unchanged_miss or unchanged_error:
        # Routine re-poll with an unchanged outcome: no edge spam
        # (append-only ≠ append-always). Distinct NEW errors DO append (CR-001).
        # But freshness IS recorded (MS-1b carry-forward): a long-lived miss
        # only looks re-examined when something actually re-ran the ladder.
        if current is not None:
            _stamp_evaluated(current)
        if canonical and locked.title_normalized != canonical:
            locked.title_normalized = canonical
            locked.save(update_fields=["title_normalized"])
        return
```

**(d)** After the `if accepted: grain, family, model, variant, on_demand = _materialize(...)` block, before evidence assembly, the unchanged-target skip (this is what stops reconsider re-accepts from appending one edge per refresh — `_materialize`'s get_or_creates are idempotent, so running it first is safe):

```python
    if accepted and current is not None and "error" not in current.evidence:
        new_targets = (
            family.pk if grain == ResolutionGrain.FAMILY and family is not None else None,
            model.pk if grain == ResolutionGrain.MODEL and model is not None else None,
            variant.pk if grain == ResolutionGrain.VARIANT and variant is not None else None,
        )
        if current.grain == grain and _edge_target_ids(current) == new_targets:
            # Same accept, same target (a reconsider re-hit, or a rung-1 accept
            # identical to the current edge): freshness only, no new edge.
            _stamp_evaluated(current)
            if canonical and locked.title_normalized != canonical:
                locked.title_normalized = canonical
                locked.save(update_fields=["title_normalized"])
            return
```

**(e)** `resolve_listing` threads the flag (both the happy path and the CR-001 fallback keep working):

```python
    def resolve_listing(self, listing_id: int, *, reconsider: bool = False) -> None:
        listing = Listing.objects.select_related("source_site").get(pk=listing_id)
        try:
            canonical, extracted, candidates, verdict = _run_ladder(
                listing, reconsider=reconsider
            )
        except Exception as exc:  # ladder failure → error verdict (C.3)
            logger.exception("matcher crashed for listing %s", listing_id)
            canonical, extracted, candidates = "", ExtractedAttributes(), []
            verdict = _error_verdict(exc)
        try:
            _apply(listing, canonical, extracted, candidates, verdict)
        except Exception as exc:
            logger.exception("resolution apply failed for listing %s", listing_id)
            _apply(listing, canonical, ExtractedAttributes(), [], _error_verdict(exc))
```

**(f)** `src/hw_radar/matching/__init__.py`: `MATCHER_VERSION = "2026.07.3"` (comment stays; this bump = reconsider mode + unchanged-target write semantics).

- [ ] **Step 4: Run the full resolver suite**

Run: `HW_RADAR_DB_PORT=5433 uv run pytest tests/db/test_resolver.py tests/db/test_resolution_models.py tests/db/test_backfill_view.py -v`
Expected: PASS — the new tests AND every pre-existing MS-1b test (especially `test_rung0_reobservation_appends_no_duplicate_edge` and `test_unresolved_repoll_appends_no_duplicate_none_edge`, which now also exercise the stamp path).

- [ ] **Step 5: Fix pass and commit**

```bash
uv run ruff format . && uv run ruff check . --fix
git add src/hw_radar/matching tests/db/test_resolver.py
git commit -m "feat(matching): reconsider mode + evidence freshness; matcher 2026.07.3"
```

---

### Task 6: Discovery loop + refresh orchestration

**Files:**
- Create: `src/hw_radar/refdata/discovery.py`
- Create: `src/hw_radar/refdata/refresh.py`
- Test: `tests/db/test_refdata_refresh.py` (extend)

**Interfaces:**
- Consumes: `UnknownModelBackfill` view (MS-1b), `RefdataConfig`/`ReferenceFetchRequest` (Task 3), `import_documents` (Task 4), `CatalogResolver(..., reconsider=True)` (Task 5), `matching.types.GRAIN_ORDER`.
- Produces: `scan_backfill_queue() -> int`; `run_refresh(seed_dir: Path | None = None) -> RefreshReport` with fields `ran: bool`, `conflicts: list[str]`, `import_report: ImportReport | None`, `reconsidered: int`, `upgraded: int`, `errors: int`, `discovery_enqueued: int`, method `as_json()`. Task 7's poller job and command consume these exact names.

- [ ] **Step 1: Write the failing tests** (append to `tests/db/test_refdata_refresh.py`)

```python
from hw_radar.catalog.models import (
    Listing,
    Manufacturer,
    ProductAlias,
    ProductModel,
    ResolutionGrain,
    RetentionClass,
    SourceSite,
)
from hw_radar.matching.resolver import CatalogResolver
from hw_radar.refdata.discovery import scan_backfill_queue
from hw_radar.refdata.refresh import run_refresh


@pytest.fixture
def site(db: None) -> SourceSite:
    return SourceSite.objects.create(name="Demo", normalized_name="demo")


def _listing(site: SourceSite, key: str, title: str) -> Listing:
    return Listing.objects.create(
        source_site=site,
        source_listing_key=key,
        canonical_url=f"https://example.test/{key}",
        url_hash=key,
        title_raw=title,
        retention_class=RetentionClass.MERCHANT_FACT,
    )


def _unknown_decoded_listings(site: SourceSite, count: int) -> None:
    """count listings decoding to the same unknown Seagate MPN hypothesis."""
    resolver = CatalogResolver()
    for i in range(count):
        listing = _listing(site, f"unk-{i}", "seagate st99000nm999 99tb sata hdd")
        resolver.resolve_listing(listing.pk)


def test_scan_enqueues_hypotheses_at_or_above_threshold(site: SourceSite) -> None:
    _unknown_decoded_listings(site, 3)  # default threshold = 3
    assert scan_backfill_queue() == 1
    request = ReferenceFetchRequest.objects.get()
    assert request.mpn_hypothesis == "st99000nm999"
    assert request.vendor_hint == "seagate"
    assert request.occurrences_at_enqueue >= 3


def test_scan_below_threshold_enqueues_nothing(site: SourceSite) -> None:
    _unknown_decoded_listings(site, 2)
    assert scan_backfill_queue() == 0


def test_scan_is_idempotent_and_skips_synthetic_keys(site: SourceSite) -> None:
    _unknown_decoded_listings(site, 3)
    _listing(site, "no-tokens", "mystery drive nothing decodable")
    CatalogResolver().resolve_listing(Listing.objects.get(source_listing_key="no-tokens").pk)
    assert scan_backfill_queue() == 1
    assert scan_backfill_queue() == 0  # dedup on hypothesis_key
    assert ReferenceFetchRequest.objects.count() == 1


def test_run_refresh_imports_reconsiders_and_scans(site: SourceSite) -> None:
    listing = _listing(site, "rr-1", "seagate exos st16000nm002c 16tb sata")
    CatalogResolver().resolve_listing(listing.pk)  # family grain before the seed
    report = run_refresh()
    assert report.ran is True
    assert report.conflicts == []
    assert report.import_report is not None
    assert report.reconsidered >= 1
    assert report.upgraded >= 1  # family → model via the seeded Exos alias
    listing.refresh_from_db()
    assert listing.resolution_grain == ResolutionGrain.MODEL
    config = RefdataConfig.current()
    assert config.last_refresh_at is not None
    assert config.last_report_json["upgraded"] >= 1


def test_run_refresh_disabled_is_a_noop(site: SourceSite) -> None:
    config = RefdataConfig.current()
    config.enabled = False
    config.save(update_fields=["enabled"])
    report = run_refresh()
    assert report.ran is False
    assert ProductModel.objects.count() == 0


def test_run_refresh_conflicted_import_still_reconsiders(site: SourceSite) -> None:
    # Enrich-never-gate: a conflicted (rolled-back) import must not stop the
    # queue re-run against previously seeded aliases. The listing is created
    # UNRESOLVED (grain none) and never resolved before the conflicted refresh,
    # so its upgrade can ONLY come from that refresh's reconsider pass — an
    # implementation that returns early after ImportConflictError leaves it at
    # none and fails this test (Codex CR-NEW-001).
    run_refresh()  # first refresh seeds the catalog
    samsung = Manufacturer.objects.create(name="Samsung", normalized_name="samsung")
    stranger = ProductModel.objects.create(
        manufacturer=samsung,
        model_number="XYZ-1",
        normalized_model_number="xyz1",
        retention_class=RetentionClass.MANUFACTURER_REFERENCE,
    )
    alias = ProductAlias.objects.get(normalized_alias_text="st16000nm002c")
    alias.pk = None
    alias.product_model = stranger
    alias.alias_type = "retail_pn"
    alias.save()  # forged collision → next import conflicts
    # Brand gate note: the forged alias targets a SAMSUNG model, so the WD
    # listing's rung-1 lookup filters it via brands_consistent — the reconsider
    # pass still sees a single viable target and can accept.
    listing = _listing(site, "rr-2", "wd ultrastar wuh721818ale6l4 18tb sata")
    assert listing.resolution_grain == ResolutionGrain.NONE  # pre-refresh: unresolved
    report = run_refresh()
    assert report.ran is True
    assert report.conflicts  # import failed into review...
    assert report.reconsidered >= 1  # ...but the queue re-run still happened
    assert report.upgraded >= 1
    listing.refresh_from_db()
    assert listing.resolution_grain in (ResolutionGrain.MODEL, ResolutionGrain.VARIANT)
```

- [ ] **Step 2: Run to verify failure**

Run: `HW_RADAR_DB_PORT=5433 uv run pytest tests/db/test_refdata_refresh.py -v`
Expected: new tests FAIL with `ModuleNotFoundError: No module named 'hw_radar.refdata.discovery'`

- [ ] **Step 3: Write discovery and refresh**

```python
# src/hw_radar/refdata/discovery.py
"""C.3.4 discovery loop: decoded-but-unknown MPNs crossing the occurrence
threshold become ReferenceFetchRequest rows — the ADR-0018 'unmatched listings
are the discovery signal for catalog gaps' made operational. Threshold is an
ADR-0016 settings row (RefdataConfig). Synthetic 'listing:<id>' hypothesis keys
(no decoded MPN) never enqueue — there is nothing targeted to fetch."""

from __future__ import annotations

from hw_radar.catalog.models import (
    RefdataConfig,
    ReferenceFetchRequest,
    UnknownModelBackfill,
)


def scan_backfill_queue() -> int:
    config = RefdataConfig.current()
    created = 0
    rows = UnknownModelBackfill.objects.filter(
        occurrences__gte=config.discovery_occurrence_threshold,
        mpn_hypothesis__isnull=False,
    )
    for row in rows:
        _, was_created = ReferenceFetchRequest.objects.get_or_create(
            hypothesis_key=row.hypothesis_key,
            defaults={
                "mpn_hypothesis": row.mpn_hypothesis or "",
                "vendor_hint": row.vendor_hint or "",
                "occurrences_at_enqueue": int(row.occurrences),
            },
        )
        created += int(was_created)
    return created
```

```python
# src/hw_radar/refdata/refresh.py
"""The monthly ADR-0018 refresh: import seeds → reconsider the backfill queue
(rungs 1-2 against the fresh catalog, C.3.4 way #1) → discovery scan (way #2).
Order matters: reconsider drains the queue before discovery counts it.

Enrich-never-gate (ADR-0018 rule 6): a conflicted import rolls back and is
REPORTED, but the reconsider pass and discovery scan still run against the
previously seeded catalog; one bad listing never halts the loop."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from django.utils import timezone

from hw_radar.catalog.models import Listing, RefdataConfig, ResolutionGrain
from hw_radar.matching.resolver import CatalogResolver
from hw_radar.matching.types import GRAIN_ORDER, Grain
from hw_radar.refdata.discovery import scan_backfill_queue
from hw_radar.refdata.loader import load_seed_documents
from hw_radar.refdata.persist import ImportConflictError, ImportReport, import_documents

logger = logging.getLogger(__name__)


@dataclass
class RefreshReport:
    ran: bool
    conflicts: list[str] = field(default_factory=list)
    import_report: ImportReport | None = None
    reconsidered: int = 0
    upgraded: int = 0
    errors: int = 0
    discovery_enqueued: int = 0

    def as_json(self) -> dict[str, object]:
        return {
            "ran": self.ran,
            "conflicts": list(self.conflicts),
            "import": self.import_report.as_json() if self.import_report else None,
            "reconsidered": self.reconsidered,
            "upgraded": self.upgraded,
            "errors": self.errors,
            "discovery_enqueued": self.discovery_enqueued,
        }


def run_refresh(seed_dir: Path | None = None) -> RefreshReport:
    config = RefdataConfig.current()
    if not config.enabled:
        logger.info("refdata refresh disabled (RefdataConfig.enabled=False)")
        return RefreshReport(ran=False)
    report = RefreshReport(ran=True)
    docs = load_seed_documents(seed_dir)
    try:
        report.import_report = import_documents(docs)
    except ImportConflictError as exc:
        report.conflicts = exc.conflicts
        logger.error("refdata import failed into review: %s conflict(s)", len(exc.conflicts))
    resolver = CatalogResolver()
    pending = list(
        Listing.objects.filter(
            resolution_grain__in=[ResolutionGrain.NONE, ResolutionGrain.FAMILY]
        ).values_list("pk", "resolution_grain")
    )
    for pk, grain_before in pending:
        try:
            resolver.resolve_listing(pk, reconsider=True)
        except Exception:  # double-fallback failure — never halts the loop
            logger.exception("reconsider failed for listing %s", pk)
            report.errors += 1
            continue
        report.reconsidered += 1
        grain_after = Listing.objects.values_list("resolution_grain", flat=True).get(pk=pk)
        if GRAIN_ORDER[Grain(grain_after)] > GRAIN_ORDER[Grain(grain_before)]:
            report.upgraded += 1
    report.discovery_enqueued = scan_backfill_queue()
    config.last_refresh_at = timezone.now()
    config.last_report_json = report.as_json()
    config.save(update_fields=["last_refresh_at", "last_report_json", "updated_at"])
    return report
```

- [ ] **Step 4: Run the tests**

Run: `HW_RADAR_DB_PORT=5433 uv run pytest tests/db/test_refdata_refresh.py -v`
Expected: PASS (all)

- [ ] **Step 5: Fix pass and commit**

```bash
uv run ruff format . && uv run ruff check . --fix
git add src/hw_radar/refdata/discovery.py src/hw_radar/refdata/refresh.py tests/db/test_refdata_refresh.py
git commit -m "feat(refdata): C.3.4 discovery loop + monthly refresh orchestration"
```

---

### Task 7: Management command + poller wiring

**Files:**
- Create: `src/hw_radar/catalog/management/__init__.py` (empty)
- Create: `src/hw_radar/catalog/management/commands/__init__.py` (empty)
- Create: `src/hw_radar/catalog/management/commands/import_refdata.py`
- Modify: `src/hw_radar/poller/service.py`
- Test: `tests/db/test_refdata_refresh.py` (command tests), `tests/unit/test_poller.py` (job registration)

**Interfaces:**
- Consumes: `run_refresh`, `import_documents`, `load_seed_documents`, `ImportConflictError`.
- Produces: `manage.py import_refdata [--refresh] [--seed-dir PATH]`; poller job id `refdata-refresh` (monthly cron: day 1, 07:00 UTC — after the 06:00 FX refresh, off the fast path per ADR-0018 rule 3).

- [ ] **Step 1: Write the failing tests**

Append to `tests/db/test_refdata_refresh.py`:

```python
from django.core.management import CommandError, call_command


def test_import_refdata_command_imports_the_seeds(db: None) -> None:
    call_command("import_refdata")
    assert ProductModel.objects.count() == 15


def test_import_refdata_command_fails_loudly_on_conflicts(db: None) -> None:
    samsung = Manufacturer.objects.create(name="Samsung", normalized_name="samsung")
    stranger = ProductModel.objects.create(
        manufacturer=samsung,
        model_number="XYZ-2",
        normalized_model_number="xyz2",
        retention_class=RetentionClass.MANUFACTURER_REFERENCE,
    )
    ProductAlias.objects.create(
        alias_type="mpn",
        normalized_alias_text="st16000nm002c",
        product_model=stranger,
        source_kind="listing_derived",
    )
    with pytest.raises(CommandError):
        call_command("import_refdata")
```

Append to `tests/unit/test_poller.py` (match the file's existing build_scheduler test style):

```python
def test_refdata_refresh_job_registered_on_utc_cron() -> None:
    scheduler = build_scheduler(BucketRegistry(), [])
    job = scheduler.get_job("refdata-refresh")
    assert job is not None
    # Codex CR-003: APScheduler cron triggers default to the SCHEDULER timezone,
    # which defaults to LOCAL time — the *_UTC constants are only honest if the
    # scheduler is pinned to UTC.
    assert str(job.trigger.timezone) == "UTC"


def test_scheduler_is_pinned_to_utc() -> None:
    scheduler = build_scheduler(BucketRegistry(), [])
    assert str(scheduler.timezone) == "UTC"
    fx = scheduler.get_job("fx-refresh")
    assert fx is not None
    assert str(fx.trigger.timezone) == "UTC"  # FX_REFRESH_HOUR_UTC now truthful
```

- [ ] **Step 2: Run to verify failure**

Run: `HW_RADAR_DB_PORT=5433 uv run pytest tests/db/test_refdata_refresh.py -k command -v && uv run pytest tests/unit/test_poller.py -k refdata -v`
Expected: FAIL — `Unknown command: 'import_refdata'`; `assert None is not None`

- [ ] **Step 3: Write the command**

```python
# src/hw_radar/catalog/management/commands/import_refdata.py
"""Manual entry point for ADR-0018 reference ingest. Default: import the seed
documents only. --refresh runs the full monthly loop (import + backfill-queue
reconsider + discovery scan) — the same code path as the poller job. Conflicts
exit non-zero with the full descriptor list (fail into review, D4)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from hw_radar.refdata.loader import load_seed_documents
from hw_radar.refdata.persist import ImportConflictError, import_documents
from hw_radar.refdata.refresh import run_refresh


class Command(BaseCommand):
    help = "Import ADR-0018 reference seed documents (--refresh: full monthly loop)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--refresh", action="store_true", help="run the full refresh loop")
        parser.add_argument("--seed-dir", type=Path, default=None)

    def handle(self, *args: Any, **options: Any) -> None:
        seed_dir: Path | None = options["seed_dir"]
        if options["refresh"]:
            report = run_refresh(seed_dir)
            self.stdout.write(json.dumps(report.as_json(), indent=2, default=str))
            if report.conflicts:
                raise CommandError(f"{len(report.conflicts)} alias conflict(s) — see report")
            return
        docs = load_seed_documents(seed_dir)
        try:
            report = import_documents(docs)
        except ImportConflictError as exc:
            raise CommandError("import aborted:\n" + "\n".join(exc.conflicts)) from exc
        self.stdout.write(json.dumps(report.as_json(), indent=2, default=str))
```

- [ ] **Step 4: Wire the poller job**

In `src/hw_radar/poller/service.py`:

```python
# with the other module constants:
REFDATA_REFRESH_DAY = 1  # monthly-order cadence, its own axis (ADR-0018 rule 3)
REFDATA_REFRESH_HOUR_UTC = 7  # after the 06:00 FX refresh

# with the other job functions:
async def refdata_refresh_job() -> None:
    """ADR-0018 monthly reference refresh — slow path, never heartbeat/fast-lane."""
    report = await sync_to_async(refdata_refresh.run_refresh)()
    logger.info("refdata refresh: %s", report.as_json())

# import at top (module-level model imports are already the file's pattern):
from hw_radar.refdata import refresh as refdata_refresh

# in build_scheduler(): pin the scheduler to UTC (Codex CR-003 — APScheduler
# defaults to LOCAL time, so FX_REFRESH_HOUR_UTC and REFDATA_REFRESH_HOUR_UTC
# were only aspirational; cron triggers inherit the scheduler timezone):
    scheduler = AsyncIOScheduler(
        job_defaults={"max_instances": 1, "coalesce": True}, timezone="UTC"
    )

# in build_scheduler(), after the recovery-probes job:
    scheduler.add_job(
        refdata_refresh_job,
        "cron",
        day=REFDATA_REFRESH_DAY,
        hour=REFDATA_REFRESH_HOUR_UTC,
        id="refdata-refresh",
    )
```

The `timezone="UTC"` pin changes when the *existing* `fx-refresh` cron fires on any non-UTC host — that is the fix, not a regression: the constant has always claimed UTC (`FX_REFRESH_HOUR_UTC`). Check the deployment container's timezone (`timedatectl` / `TZ`) at execution time; if it already runs UTC, deployed behavior is unchanged — note the finding in the PR body either way.

- [ ] **Step 5: Run the tests**

Run: `HW_RADAR_DB_PORT=5433 uv run pytest tests/db/test_refdata_refresh.py tests/unit/test_poller.py tests/db/test_poller_jobs.py -v`
Expected: PASS (all, including pre-existing poller tests)

- [ ] **Step 6: Fix pass and commit**

```bash
uv run ruff format . && uv run ruff check . --fix
git add src/hw_radar/catalog/management src/hw_radar/poller/service.py tests/db/test_refdata_refresh.py tests/unit/test_poller.py
git commit -m "feat(poller): monthly refdata-refresh job + import_refdata command"
```

---

### Task 8: MS-1c acceptance, docs, verification gate, PR

**Files:**
- Test: `tests/db/test_refdata_acceptance.py`
- Modify: `docs/specs/hw-radar-master-spec.md` (§17.3 DR-009 traceability row)
- Modify: `docs/adr/adr-0018-manufacturer-spec-catalog.md` (Confirmation note)
- Modify: `STATUS.md`, `TODO.md`, `docs/handoff/state.md`, `docs/handoff/specs-plans.md`

**Interfaces:**
- Consumes: everything above. Produces the MS-1c exit evidence and the `dev→main` PR.

- [ ] **Step 1: Write the acceptance tests (design-doc exit criteria, verbatim)**

```python
# tests/db/test_refdata_acceptance.py
"""MS-1c exit criteria (design doc §MS-1c + ADR-0018 Confirmation): one family
lands with its full per-MPN fan-out; a listing matching a seeded alias inherits
authoritative drive_spec; DR-009 stamping holds; ingest writes no observation
rows."""

from decimal import Decimal

import pytest

from hw_radar.catalog.models import (
    Condition,
    Listing,
    OfferSnapshot,
    ProductFamily,
    ResolutionGrain,
    RetentionClass,
    SourceSite,
)
from hw_radar.matching.resolver import CatalogResolver
from hw_radar.refdata.loader import load_seed_documents
from hw_radar.refdata.persist import import_documents

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def seeded() -> None:
    import_documents(load_seed_documents())


@pytest.fixture
def site() -> SourceSite:
    return SourceSite.objects.create(name="Demo", normalized_name="demo")


def _listing(site: SourceSite, key: str, title: str, condition: str = "") -> Listing:
    return Listing.objects.create(
        source_site=site,
        source_listing_key=key,
        canonical_url=f"https://example.test/{key}",
        url_hash=key,
        title_raw=title,
        condition_label_raw=condition,
        retention_class=RetentionClass.MERCHANT_FACT,
    )


def test_exos_recertified_lands_as_one_family_with_full_datasheet_fanout() -> None:
    # D2a: the FULL-fan-out acceptance family. The Seagate recert datasheet's
    # published ladder is exactly these six SKUs — complete first-party
    # coverage, unlike HC550 (a deliberate subset, tested below).
    family = ProductFamily.objects.get(normalized_name="exos")
    numbers = set(family.models.values_list("model_number", flat=True))
    assert numbers == {
        "ST16000NM002C",
        "ST20000NM002C",
        "ST22000NM000C",
        "ST24000NM000C",
        "ST26000NM000C",
        "ST28000NM000C",
    }
    for model in family.models.all():
        assert model.retention_class == RetentionClass.MANUFACTURER_REFERENCE
        assert model.aliases.filter(is_primary=True).count() == 1


def test_hc550_starter_subset_spans_sata_and_sas_with_retail_pn_aliases() -> None:
    # D2a: HC550 is a BOUNDED STARTER SUBSET of WD's much larger first-party
    # matrix (14/16/18TB, 6 SATA + 9 SAS rows) — never call it full fan-out.
    family = ProductFamily.objects.get(normalized_name="ultrastar dc hc550")
    models = list(family.models.all())
    assert len(models) == 4  # research-evidenced recert-market rows only
    interfaces = set(
        family.models.values_list("drive_spec__interface", flat=True)
    )
    assert interfaces == {"SATA 6Gb/s", "SAS 12Gb/s"}  # per-MPN interface fan-out
    retail_pns = sum(m.aliases.filter(alias_type="retail_pn").count() for m in models)
    assert retail_pns == 2  # both WD 0F… orderable part numbers


def test_listing_matching_seeded_alias_inherits_authoritative_drive_spec(
    site: SourceSite,
) -> None:
    listing = _listing(site, "acc-1", "Seagate Exos ST20000NM002C 20TB SATA Enterprise HDD")
    CatalogResolver().resolve_listing(listing.pk)
    listing.refresh_from_db()
    assert listing.resolution_grain == ResolutionGrain.MODEL
    assert listing.product_model is not None
    spec = listing.product_model.drive_spec
    assert spec.capacity_tb == Decimal("20")
    assert spec.sector_format == "512e"
    assert spec.retention_class == RetentionClass.MANUFACTURER_REFERENCE


def test_recert_listing_reaches_variant_grain_with_inherited_spec(
    site: SourceSite,
) -> None:
    listing = _listing(
        site,
        "acc-2",
        "Seagate IronWolf Pro ST20000NE000 20TB SATA NAS HDD",
        condition="Manufacturer Recertified",
    )
    CatalogResolver().resolve_listing(listing.pk)
    listing.refresh_from_db()
    assert listing.resolution_grain == ResolutionGrain.VARIANT
    assert listing.product_variant is not None
    assert listing.product_variant.condition == Condition.RECERTIFIED
    spec = listing.product_variant.product_model.drive_spec
    assert spec.capacity_tb == Decimal("20")


def test_reference_ingest_writes_no_observation_rows() -> None:
    # ADR-0018 rule 1: catalog ingest stops at persist — the seeded fixture
    # (autouse) must have produced zero snapshots/listings.
    assert OfferSnapshot.objects.count() == 0
    assert Listing.objects.count() == 0
```

- [ ] **Step 2: Run the acceptance tests**

Run: `HW_RADAR_DB_PORT=5433 uv run pytest tests/db/test_refdata_acceptance.py -v`
Expected: PASS (all 5)

- [ ] **Step 3: Full verification gate**

```bash
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
HW_RADAR_DB_PORT=5433 uv run coverage run -m pytest
uv run coverage report   # ≥ 85% branch
uv run pip-audit
```

Expected: all green. Fix anything that isn't before proceeding.

- [ ] **Step 4: Documentation updates**

- `docs/specs/hw-radar-master-spec.md` §17.3: update the DR-009 traceability row from "Verified (columns)" to verified-by-test, citing `tests/db/test_refdata_acceptance.py` and `tests/db/test_refdata_import.py::test_discontinued_model_is_retained_on_refresh`.
- `docs/adr/adr-0018-manufacturer-spec-catalog.md`: append a dated line to the Confirmation section — implemented 2026-07-05 at MS-1c; confirmation criteria covered by the acceptance suite (**Exos recertified** as the full-fan-out family per D2a, spec inheritance, backfill-not-dropped [existing MS-1b tests], discontinued-model retention); bump `updated`.
- `TODO.md`: replace the "MS-1c catalog seed inputs" agent-tracked item with a narrower deferred item: "SanDisk↔WD real-corpus alias verification: run against seeded catalog aliases before the first WD/SanDisk SSD family seed (plan D7; brand-equivalence descriptor machinery landed at MS-1c)". Leave the MS-1d/ADR-0019 items.
- `STATUS.md`: add the MS-1c completed-outcome line.
- `docs/handoff/state.md`: live state → MS-1c implemented; next work MS-1d connectors (re-verify endpoints + eBay smoke at plan time, per design S-4); note `import_refdata --refresh` as the manual refresh entry point.
- `docs/handoff/specs-plans.md`: add this plan's row.

- [ ] **Step 5: Commit docs and open the PR**

```bash
uv run ruff format . && uv run ruff check . --fix
git add tests/db/test_refdata_acceptance.py docs/specs/hw-radar-master-spec.md docs/adr/adr-0018-manufacturer-spec-catalog.md STATUS.md TODO.md docs/handoff/state.md docs/handoff/specs-plans.md
git commit -m "test(refdata): MS-1c acceptance suite; docs: DR-009 traceability + ADR-0018 confirmation"
git push origin dev
gh pr create --base main --head dev \
  --title "MS-1c: catalog seed — ADR-0018 refdata pipeline, discovery loop, reconsider mode" \
  --body "Implements docs/superpowers/plans/2026-07-05-ms1c-catalog-seed.md: curated first-party seed corpus (Exos recertified [full datasheet fan-out], IronWolf Pro, Ultrastar DC HC550 [bounded starter subset] — 15 models, 17 aliases), validate-then-write importer with conflict fail-into-review and provisional-family adoption, C.3.4 discovery loop, monthly refresh with resolver reconsider mode, edge freshness stamping, scheduler pinned to UTC. Matcher 2026.07.3. MS-1b carry-forwards: rung-1 aggregation, unchanged_miss freshness, and provisional-family reconciliation closed; SanDisk↔WD landed as brand-equivalence-aware conflict detection with real-corpus verification deferred to the first SSD seed (plan D7)."
```

Wait for CI + dependency review green; merge with a merge commit per the repo's git model.

---

## Self-Review

- **Spec coverage:** design §MS-1c line-by-line — truncated pipeline writing the four row types with `manufacturer_reference` and no side effects (Tasks 1/4, acceptance test 5); families confirmed from live inventory and recorded (research doc + D2/D2a, seed corpus Tasks 1–2); sourcing precedence + normalizer parity (D1, loader/contracts, parity assertions); monthly poller job off the fast path, UTC-pinned (Task 7); discontinued-retention acceptance (Task 4 test); C.3.4 discovery loop wired with settings-row threshold (Tasks 3/6); exit criteria — full family fan-out (Exos recertified, D2a), alias→spec inheritance, DR-009 — all in Task 8. Research-doc carry-forwards: rung-1 aggregation → D4 conflict machinery (Tasks 1/4); `unchanged_miss` freshness → D5 `last_evaluated_at` (Tasks 3/5); SanDisk↔WD → brand-equivalence-aware collision detection with a targeted synthetic test, real-corpus verification deferred (D7, Task 4); provisional reconciliation → key-compatible adoption + unreconciled report (Task 4). Research open inputs #1–4 settled by D1–D3 + the fixture-format schema.
- **Placeholder scan:** no TBDs; the one deliberately bounded step (Task 2 enrichment) has a concrete fallback rule (leave null) rather than deferred work.
- **Type consistency:** `resolve_listing(listing_id, *, reconsider=False)` used identically in Tasks 5/6; `ImportReport`/`RefreshReport` field names match between definition (Tasks 4/6) and consumers (Tasks 6/7); `RefdataConfig.current()` / `discovery_occurrence_threshold` / `hypothesis_key` consistent across Tasks 3/6; seed counts (15 models / 17 aliases) consistent across loader tests, import tests, and acceptance tests.
- **Codex findings applied:** round 1 — CR-001 → D2a + acceptance-family swap; CR-002 → corpus-count test moved to Task 2, every task boundary green; CR-003 → scheduler `timezone="UTC"` + trigger assertions; CR-004 → D7 wording + brand-equivalent descriptor test; single-writer note → D8 + persist.py docstring. Round 2 — CR-NEW-001 → conflicted-refresh test restructured so the listing starts unresolved and only the conflicted refresh's reconsider pass can upgrade it (all four round-1 findings confirmed resolved; audits under `docs/codex-reviews/`).
