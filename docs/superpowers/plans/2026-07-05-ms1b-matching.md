# MS-1b — Matching Layer (ADR-0019 rungs 0–2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the ADR-0019 matching layer — the pure extraction stack (N1 canonicalization, N2 controlled vocabularies, N3 MPN-candidate extraction, N4 per-vendor grammar decoders), the rung-0–2 conservative match ladder with the hard-attribute contradiction veto, the append-only `listing_resolution` edge table with denormalized current-resolution FKs on `listing`, the DB-facing `CatalogResolver` that replaces MS-1a's `NullResolver`, and the `unknown_model_backfill` view — so listings resolve onto the ADR-0010 identity ladder and MS-1c catalog ingest can share the same normalizer.

**Architecture:** `src/hw_radar/matching/` is a **pure-function library** (no I/O, no ORM) per spec C.3's "pure-function library plus a resolver service" split — only `matching/resolver.py` touches Django. The resolver feeds DB state into the pure ladder as plain dataclasses, writes append-only `ListingResolution` edges, refreshes the denormalized FKs on `Listing`, creates `ProductVariant` rows on demand (model grain + known condition), materializes provisional `ProductFamily` rows for rung-2 decodes, and lazily emits OEM/house-SKU `ProductAlias` rows from dual-labeled listings. Resolver failure never gates ingestion (grain=none edge with the error in evidence; `pipeline.run_source` keeps its own catch). Design sources: `docs/superpowers/specs/2026-07-05-ms1-ingestion-design.md` §MS-1b, master spec Appendix C.3, ADR-0019, ADR-0010.

**Tech Stack:** Python 3.14 stdlib (`re`, `unicodedata`, dataclasses, enums) for the pure library; Django 6 ORM + PostgreSQL for resolver/models/view. **No new dependencies** (runtime or dev).

## Global Constraints

- Toolchain contract is `AGENTS.md`: fix pass (`uv run ruff format . && uv run ruff check . --fix`) before every commit; full gate (`uv run python -m scripts.check`) green before claiming a task complete. Coverage threshold **85% branch**.
- **BasedPyright strict** on `src/` + `tests/`. The matching library must type-check with zero pragmas (it is pure Python); model files reuse the existing `# pyright: reportIncompatibleVariableOverride=false` header pattern where nested `Meta` classes demand it.
- **No new dependencies.** The matching library is stdlib-only by design. Do not add `hypothesis` — idempotence is property-tested via the golden corpus + seeded-random fuzz vectors.
- DB tests live in `tests/db/` (need the live TimescaleDB); pure tests in `tests/unit/`. **Local workstation has no compose provider** — if the DB container is missing or fails password auth (a stale-password container was seen 2026-07-05i), recreate it: `podman rm -f hw-radar-db; podman run -d --rm --name hw-radar-db -e POSTGRES_DB=hw_radar -e POSTGRES_USER=hw_radar -e POSTGRES_PASSWORD=hw_radar -p 127.0.0.1:5432:5432 docker.io/timescale/timescaledb:2.28.2-pg17`. **⚠ Destructive to the local dev container only** — it holds disposable test-fixture data, nothing else; do not run it against any non-dev host. The image tag matches `compose.yaml` and CI (`check.yml`), both green on it; if the pull fails locally, verify the tag on Docker Hub before substituting.
- **Single-normalizer invariant (ADR-0019 rule 1):** `matching.normalize.normalize_alias_text` is the ONLY alias join key. MS-1c refdata must import it; nothing may fork a second normalizer. The parity test in `tests/db/test_resolver.py` is the CI guard.
- **Decoder contract is deliberately weak (ADR-0019 rule 3):** grammars derive family/capacity/generation ONLY. Never decode variant-level semantics (interface variant, sector format, SED/FIPS, endurance) from a code string.
- **Only rungs 0–2 auto-accept.** Rungs 3–4 do not exist in MS-1b beyond emitting `review`/`none` outcomes with evidence; `pg_trgm` scoring and the manual queue land later. The hard-attribute contradiction veto runs at EVERY rung including rung 0.
- **Append-only resolution state (DR-010):** edges are never updated or deleted; a new edge sets `superseded_by` on the prior current edge. Exception: an unchanged rung-0 re-observation writes NO new edge (routine polls must not spam one edge per poll — only veto trips, upgrades, or changed outcomes append).
- Confidence constants and thresholds are **OQ-provisional tunables** — module constants in `ladder.py` with a comment; the ADR-0016 settings-row versions arrive with the rung-3/occurrence thresholds (MS-1c).
- `MATCHER_VERSION` is stamped on every edge; any rule change after MS-1b bumps it (C.3.5).
- Migrations are expand/contract (spec §8.5); new columns nullable-or-defaulted. The view migration must be reversible (`DROP VIEW`).
- Public repo: no secrets, internal hostnames, or infra addresses in code/docs/commits.
- Conventional commits on `dev`, GPG-signed. This plan ends with the **MS-1b `dev→main` PR**.
- Evidence payloads use a stable key vocabulary: `mpn_hypothesis`, `vendor_hint`, `candidates`, `veto`, `provenance`, `rule`, `provisional`, `variant_on_demand`, `error`. The backfill view GROUPs on `evidence->>'mpn_hypothesis'` — treat these keys as schema.

## File Structure

```
src/hw_radar/matching/__init__.py            # NEW: MATCHER_VERSION only
src/hw_radar/matching/types.py               # NEW: Grain, Provenance, Attribute[T], ExtractedAttributes,
                                             #      TokenKind, MpnCandidate, DecodeResult (pure)
src/hw_radar/matching/normalize.py           # NEW: N1 canonicalize_title + normalize_alias_text
src/hw_radar/matching/vocab.py               # NEW: N2 controlled vocabularies → ExtractedAttributes
src/hw_radar/matching/mpn.py                 # NEW: N3 code-shaped token extraction (mfr/OEM/house/unknown)
src/hw_radar/matching/grammars/__init__.py   # NEW: decode() registry
src/hw_radar/matching/grammars/seagate.py    # NEW: ST-number grammar
src/hw_radar/matching/grammars/wd.py         # NEW: WD modern + HGST-lineage grammars
src/hw_radar/matching/grammars/toshiba.py    # NEW: MG/MN grammar
src/hw_radar/matching/ladder.py              # NEW: rungs 0–2 + contradiction veto (pure)
src/hw_radar/matching/resolver.py            # NEW: CatalogResolver (DB-facing; implements ListingResolver)
src/hw_radar/catalog/models/base.py          # MODIFY: add ResolutionGrain (avoids market↔resolution cycle)
src/hw_radar/catalog/models/identity.py      # MODIFY: Condition.FOR_PARTS
src/hw_radar/catalog/models/market.py        # MODIFY: Listing denormalized resolution fields
src/hw_radar/catalog/models/resolution.py    # NEW: ListingResolution, ResolutionMethod, UnknownModelBackfill
src/hw_radar/catalog/models/__init__.py      # MODIFY: export new models/enums
src/hw_radar/catalog/admin.py                # MODIFY: register ListingResolution + backfill view (read-only)
src/hw_radar/catalog/migrations/0006_resolution.py     # generated + reviewed
src/hw_radar/catalog/migrations/0007_backfill_view.py  # hand-written RunSQL view
src/hw_radar/poller/service.py               # MODIFY: NullResolver → CatalogResolver
tests/unit/test_normalize.py                 # NEW
tests/unit/test_vocab.py                     # NEW
tests/unit/test_mpn.py                       # NEW
tests/unit/test_grammars.py                  # NEW
tests/unit/test_ladder.py                    # NEW: golden verdict table
tests/db/test_resolution_models.py           # NEW: constraints, supersede semantics
tests/db/test_resolver.py                    # NEW: rung flows, veto, parity, lazy aliases, error path
tests/db/test_backfill_view.py               # NEW
tests/db/test_identity.py                    # MODIFY: FR-003 test upgraded to resolver-driven (in place)
tests/db/test_poller_jobs.py                 # MODIFY: assert CatalogResolver is wired
```

**Interfaces locked by this plan** (MS-1c/d/e consume these exact names):

- `matching.MATCHER_VERSION: str` — stamped on edges; bump on any rule change.
- `matching.normalize.canonicalize_title(text: str) -> str` and `matching.normalize.normalize_alias_text(text: str) -> str` — the single-normalizer contract. **MS-1c refdata MUST normalize catalog aliases through `normalize_alias_text`.**
- `matching.vocab.extract(title: str) -> ExtractedAttributes`; `matching.mpn.extract_candidates(title: str, *, structured_mpn: str | None = None, source_key: str = "") -> list[MpnCandidate]`; `matching.grammars.decode(normalized_token: str) -> DecodeResult | None`.
- `matching.ladder.decide(extracted, candidates, prior, alias_hits, decoded) -> Verdict` (pure; see Task 6 for the dataclass shapes).
- `matching.resolver.CatalogResolver` — implements `acquisition.contracts.ListingResolver`; the poller's resolver from MS-1b on.
- `catalog.models.ListingResolution`, `catalog.models.ResolutionGrain`, `catalog.models.ResolutionMethod`, `catalog.models.UnknownModelBackfill` (unmanaged view model).
- Canonical brand keys (vocab + fixture + MS-1c catalog convention): `seagate`, `western_digital`, `hgst`, `toshiba`, `samsung`, `micron`, `kingston`, `kioxia`, `intel`, `solidigm`. SanDisk normalizes to `western_digital` (Jan-2026 "Optimus" rebrand, same MPNs).

---

### Task 1: Matching package, shared types, N1 normalizer

**Files:**
- Create: `src/hw_radar/matching/__init__.py`
- Create: `src/hw_radar/matching/types.py`
- Create: `src/hw_radar/matching/normalize.py`
- Test: `tests/unit/test_normalize.py`

**Interfaces:**
- Consumes: nothing (pure stdlib).
- Produces: `MATCHER_VERSION`, `types.Grain/Provenance/Attribute/ExtractedAttributes/TokenKind/MpnCandidate/DecodeResult`, `normalize.canonicalize_title(text: str) -> str`, `normalize.normalize_alias_text(text: str) -> str`. Every later task imports these exact names.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_normalize.py
"""N1 canonicalization + the single-normalizer alias key (ADR-0019 rule 1, C.3)."""

import random
import string

from hw_radar.matching.normalize import canonicalize_title, normalize_alias_text

GOLDEN_TITLES = [
    "Seagate Exos X16 16TB ST16000NM001G Factory Recertified Enterprise HDD",
    "WD Red Plus 12TB WD120EFBX NAS Hard Drive – NEW ✅ FREE SHIPPING",
    "Toshiba MG08ACA16TE 16TB 7200RPM SATA 512e CMR 3.5\" L@@K!!",
    "NetApp X477A-R6 4TB 7.2K SAS HDD WD4001FYYG server pull",
    "SAMSUNG MZ‑77E1T0B/AM 870 EVO 1TB 2.5\" SSD lot of 4",
    "HGST Ultrastar HUS724040ALS640 4TB SAS  ships fast  us seller",
    "goHardDrive白ラベル 8TB — white label",
]


def test_canonicalize_casefolds_and_unifies_separators() -> None:
    out = canonicalize_title("SAMSUNG MZ‑77E1T0B/AM 870 EVO")
    assert out == "samsung mz-77e1t0b/am 870 evo"


def test_canonicalize_strips_boilerplate_but_keeps_condition_words() -> None:
    out = canonicalize_title("WD 12TB NEW ✅ FREE SHIPPING L@@K brand new sealed")
    assert "free shipping" not in out
    assert "l@@k" not in out
    assert "brand new" in out  # condition signal is N2's job, never stripped


def test_canonicalize_collapses_whitespace() -> None:
    assert canonicalize_title("  a   b\t c ") == "a b c"


def test_alias_key_strips_all_separators() -> None:
    for raw in ("MZ-77E1T0B/AM", "mz 77e1t0b/am", "MZ‑77E1T0B/AM", "mz_77e1t0b.am"):
        assert normalize_alias_text(raw) == "mz77e1t0bam"


def test_alias_key_matches_catalog_and_listing_renderings() -> None:
    # The parity contract in miniature: catalog-side and listing-side renderings
    # of the same MPN meet at one key.
    assert normalize_alias_text("ST16000NM-001G ") == normalize_alias_text("st16000nm001g")


def test_both_normalizers_are_idempotent_on_golden_corpus() -> None:
    for title in GOLDEN_TITLES:
        once = canonicalize_title(title)
        assert canonicalize_title(once) == once
        key = normalize_alias_text(title)
        assert normalize_alias_text(key) == key


def test_idempotence_holds_under_seeded_fuzz() -> None:
    # Property-style idempotence (C.3): no hypothesis dep — seeded random unicode soup.
    rng = random.Random(20260705)
    alphabet = string.ascii_letters + string.digits + " -_/.\"'!★✅–—‑@#TBtb"
    for _ in range(500):
        s = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 60)))
        once = canonicalize_title(s)
        assert canonicalize_title(once) == once
        key = normalize_alias_text(s)
        assert normalize_alias_text(key) == key
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_normalize.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'hw_radar.matching'`

- [ ] **Step 3: Implement the package**

```python
# src/hw_radar/matching/__init__.py
"""ADR-0019 matching layer: pure extraction library + ladder; resolver.py is the
only module that touches the ORM (spec C.3 "pure-function library plus a resolver
service"). Import-light on purpose — submodules are imported explicitly."""

# Stamped on every listing_resolution edge (C.3.3). Bump on ANY rule change —
# vocab pattern, grammar rule, ladder constant — so re-resolution runs are
# diffable experiments (C.3.5). Format: YYYY.MM.revision.
MATCHER_VERSION = "2026.07.1"
```

```python
# src/hw_radar/matching/types.py
"""Shared value types for the matching layers (N1–N4) and the ladder.

Pure data, frozen: layers exchange these; only resolver.py materializes them
against the DB. Every extracted attribute carries per-attribute confidence and
the producing layer, so match evidence stays explainable (DR-004 applied to
identity, ADR-0019 rule 2)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Grain(StrEnum):
    NONE = "none"
    FAMILY = "family"
    MODEL = "model"
    VARIANT = "variant"


GRAIN_ORDER: dict[Grain, int] = {
    Grain.NONE: 0,
    Grain.FAMILY: 1,
    Grain.MODEL: 2,
    Grain.VARIANT: 3,
}


class Provenance(StrEnum):
    """Grammar-rule authority tiers (ADR-0019 rule 3); flow into match confidence."""

    VENDOR_OFFICIAL = "vendor_official"
    CORROBORATED_COMMUNITY = "corroborated_community"
    INFERRED = "inferred"


@dataclass(frozen=True)
class Attribute[T]:
    value: T
    confidence: float
    layer: str
    source_text: str = ""


@dataclass(frozen=True)
class ExtractedAttributes:
    """N2 output. None means UNKNOWN — never guessed (suitability-research rule).

    condition/recert_channel/packaging/warranty_channel values are the
    catalog TextChoices literals (identity.Condition et al.) so the resolver
    can pass them straight into variant-on-demand creation."""

    capacity_bytes: Attribute[int] | None = None
    interface: Attribute[str] | None = None  # sata | sas | nvme | scsi | usb
    link_speed_gbps: Attribute[float] | None = None
    form_factor: Attribute[str] | None = None  # 3.5 | 2.5 | m.2
    rpm: Attribute[int] | None = None
    cache_mb: Attribute[int] | None = None
    sector_format: Attribute[str] | None = None  # 512n | 512e | 4kn
    recording_tech: Attribute[str] | None = None  # cmr | smr
    security: Attribute[str] | None = None  # sed | fips | ise
    condition: Attribute[str] | None = None
    recert_channel: Attribute[str] | None = None  # factory | seller
    packaging: Attribute[str] | None = None  # retail | bulk
    warranty_months: Attribute[int] | None = None
    warranty_channel: Attribute[str] | None = None  # manufacturer | seller | none
    quantity: Attribute[int] | None = None
    brand: Attribute[str] | None = None  # canonical brand key (see plan Interfaces)


class TokenKind(StrEnum):
    MANUFACTURER_MPN = "manufacturer_mpn"
    OEM_PN = "oem_pn"
    HOUSE_SKU = "house_sku"
    UNKNOWN_CODE = "unknown_code"


@dataclass(frozen=True)
class MpnCandidate:
    raw: str
    normalized: str  # normalize_alias_text(raw) — the product_alias join key
    kind: TokenKind
    vendor_hint: str = ""  # seagate|western_digital|toshiba|samsung|dell_emc|hpe|netapp|lenovo_ibm|""
    confidence: float = 0.5
    from_structured_field: bool = False


@dataclass(frozen=True)
class DecodeResult:
    """N4 output. Family/capacity/generation ONLY (ADR-0019 rule 3): variant
    semantics come from the catalog, never the code string."""

    vendor: str
    family_name: str | None
    capacity_bytes: int | None
    generation: str | None
    provenance: Provenance
    rule: str  # which grammar rule fired — goes into edge evidence
```

```python
# src/hw_radar/matching/normalize.py
"""N1 text canonicalization + the single-normalizer alias key (ADR-0019 rule 1).

Two public functions, one contract:
- canonicalize_title() is the N1 pass every extraction layer reads from.
- normalize_alias_text() is the JOIN KEY for product_alias. Catalog ingest
  (MS-1c refdata) and listing-side candidates MUST both call it; the CI parity
  test in tests/db/test_resolver.py asserts that. Never fork a second
  normalizer — two drifting normalizers are the classic silent killer of
  alias joins (ADR-0019).
Both functions are idempotent (property-tested in tests/unit/test_normalize.py)."""

from __future__ import annotations

import re
import unicodedata

# Unicode dash variants → ASCII hyphen so MPNs like "MZ‑77E1T0B/AM" keep their
# separator through canonicalization (NFKC alone leaves U+2011 untouched).
_DASHES = dict.fromkeys(map(ord, "‐‑‒–—―−"), "-")
# Keep the characters MPNs, capacities, and form factors use; drop emoji/decorations.
_NOISE = re.compile(r"[^a-z0-9 .\-/()\"+%#]")
_WS = re.compile(r"\s+")
_ALNUM_ONLY = re.compile(r"[^a-z0-9]")

# Marketplace decoration with ZERO attribute signal. Deliberately tiny: anything
# that could carry condition/warranty/lot meaning ("brand new", "no warranty",
# "for parts") stays in the text for the N2 vocab layer.
_BOILERPLATE = re.compile(
    r"\b(?:l@@k|wow|free\s+(?:fast\s+)?shipping|fast\s+ship(?:ping)?|"
    r"ships?\s+(?:fast|free|today|same\s+day)|best\s+offer|top\s+seller|"
    r"us\s+seller|hot\s+deal)\b"
)


def canonicalize_title(text: str) -> str:
    folded = unicodedata.normalize("NFKC", text).translate(_DASHES).casefold()
    # Boilerplate BEFORE noise-stripping: patterns like 'l@@k' contain characters
    # the noise pass removes — the other order makes them unreachable.
    cleaned = _BOILERPLATE.sub(" ", folded)
    cleaned = _NOISE.sub(" ", cleaned)
    return _WS.sub(" ", cleaned).strip()


def normalize_alias_text(text: str) -> str:
    """Alias join key: NFKC → casefold → strip every non-alphanumeric.

    'MZ-77E1T0B/AM', 'mz 77e1t0b/am', and 'MZ_77E1T0B.AM' all become
    'mz77e1t0bam' — separator styling never splits an alias join."""

    return _ALNUM_ONLY.sub("", unicodedata.normalize("NFKC", text).casefold())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_normalize.py -q`
Expected: all PASS

- [ ] **Step 5: Fix pass, gate-relevant checks, commit**

```bash
uv run ruff format . && uv run ruff check . --fix
uv run basedpyright src/hw_radar/matching tests/unit/test_normalize.py
git add src/hw_radar/matching tests/unit/test_normalize.py
git commit -m "feat(matching): package skeleton, shared types, N1 normalizer (ADR-0019 rule 1)"
```

---

### Task 2: N2 controlled vocabularies

**Files:**
- Create: `src/hw_radar/matching/vocab.py`
- Test: `tests/unit/test_vocab.py`

**Interfaces:**
- Consumes: `types.Attribute`, `types.ExtractedAttributes`; input is always `canonicalize_title()` output.
- Produces: `vocab.extract(title: str) -> ExtractedAttributes`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_vocab.py
"""N2 controlled vocabularies (spec C.3.1) — table-driven over golden titles."""

from hw_radar.matching.normalize import canonicalize_title
from hw_radar.matching.types import Attribute, ExtractedAttributes
from hw_radar.matching.vocab import extract


def _x(title: str) -> ExtractedAttributes:
    # Extraction over the canonical form, exactly as the resolver does.
    return extract(canonicalize_title(title))


def _value[T](attribute: Attribute[T] | None) -> T:
    # Strict-typing helper: asserts presence, returns the narrowed value.
    assert attribute is not None
    return attribute.value


def test_capacity_tb_and_gb() -> None:
    assert _value(_x("Seagate 16TB Exos").capacity_bytes) == 16_000_000_000_000
    assert _value(_x("Samsung 960GB SSD").capacity_bytes) == 960_000_000_000
    assert _value(_x("WD 1.92TB SSD").capacity_bytes) == 1_920_000_000_000


def test_capacity_never_fires_inside_mpn_tokens() -> None:
    # 'st16000nm001g' has no standalone '<n> tb|gb' token
    assert _x("ST16000NM001G enterprise drive").capacity_bytes is None


def test_conflicting_capacities_drop_confidence() -> None:
    attrs = _x("16TB (2x 8TB bundle)")
    assert attrs.capacity_bytes is not None
    assert attrs.capacity_bytes.value == 16_000_000_000_000  # first mention wins
    assert attrs.capacity_bytes.confidence < 0.7


def test_interface_and_link_speed() -> None:
    attrs = _x("4TB 7.2K SAS 12Gb/s HDD")
    assert _value(attrs.interface) == "sas"
    assert _value(attrs.link_speed_gbps) == 12.0
    assert _value(_x("SATA III drive").interface) == "sata"
    assert _value(_x("NVMe PCIe 4.0 SSD").interface) == "nvme"


def test_form_factor() -> None:
    assert _value(_x('3.5" enterprise HDD').form_factor) == "3.5"
    assert _value(_x("2.5 inch SSD").form_factor) == "2.5"
    assert _value(_x("M.2 2280 NVMe").form_factor) == "m.2"
    assert _x("13.5 lbs box").form_factor is None  # no digit-prefixed false hit


def test_rpm_plain_and_k_forms() -> None:
    assert _value(_x("7200RPM SATA").rpm) == 7200
    assert _value(_x("7.2K RPM SAS").rpm) == 7200
    assert _value(_x("15K RPM SAS").rpm) == 15000


def test_cache_sector_recording_security() -> None:
    attrs = _x("256MB Cache 512e CMR SED drive")
    assert _value(attrs.cache_mb) == 256
    assert _value(attrs.sector_format) == "512e"
    assert _value(attrs.recording_tech) == "cmr"
    assert _value(attrs.security) == "sed"
    assert _value(_x("SMR archive drive").recording_tech) == "smr"


def test_condition_ladder_precedence() -> None:
    assert _value(_x("Seagate 8TB used - for parts").condition) == "for_parts"
    attrs = _x("16TB Factory Recertified drive")
    assert _value(attrs.condition) == "recertified"
    assert _value(attrs.recert_channel) == "factory"
    assert _x("Recertified enterprise HDD").recert_channel is None
    assert _value(_x("Seller refurbished 10TB").condition) == "refurbished"
    assert _value(_x("Renewed 4TB drive").condition) == "refurbished"  # Amazon-speak
    assert _value(_x("Open box WD Gold").condition) == "open_box"
    assert _value(_x("server pull 4TB SAS").condition) == "used"
    assert _value(_x("Brand New sealed 12TB").condition) == "new"
    assert _x("like new 12TB").condition is None  # 'like new' asserts nothing


def test_packaging_and_warranty() -> None:
    assert _value(_x("retail box 4TB").packaging) == "retail"
    assert _value(_x("OEM bare drive 8TB").packaging) == "bulk"
    assert _value(_x("12TB with 5 year warranty").warranty_months) == 60
    assert _value(_x("no warranty as-is").warranty_channel) == "none"
    assert _value(_x("manufacturer warranty included").warranty_channel) == "manufacturer"


def test_quantity_lot_forms_but_never_xn() -> None:
    assert _value(_x("lot of 4 Seagate 16TB").quantity) == 4
    assert _value(_x("2-pack WD Red").quantity) == 2
    assert _value(_x("4x 16TB drives").quantity) == 4
    assert _value(_x("qty 3 enterprise drives").quantity) == 3
    # 'xN' form is unsupported by design: it collides with Seagate family names.
    assert _x("Seagate Exos X16 16TB").quantity is None


def test_brand_normalization_including_optimus_rebrand() -> None:
    assert _value(_x("Seagate Exos 16TB").brand) == "seagate"
    assert _value(_x("Western Digital Gold 12TB").brand) == "western_digital"
    assert _value(_x("WD Red Plus 12TB").brand) == "western_digital"
    assert _value(_x("SanDisk Ultrastar DC HC550 16TB").brand) == "western_digital"
    assert _value(_x("HGST Ultrastar 4TB").brand) == "hgst"
    assert _value(_x("Hitachi Deskstar 4TB").brand) == "hgst"
    assert _value(_x("Toshiba MG08 16TB").brand) == "toshiba"


def test_unknowns_stay_none() -> None:
    attrs = _x("enterprise hard drive")
    for extracted in (
        attrs.capacity_bytes, attrs.interface, attrs.form_factor, attrs.rpm,
        attrs.condition, attrs.brand, attrs.quantity, attrs.security,
    ):
        assert extracted is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_vocab.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'hw_radar.matching.vocab'`

- [ ] **Step 3: Implement vocab.py**

```python
# src/hw_radar/matching/vocab.py
"""N2 controlled vocabularies → typed attributes (spec C.3.1).

Input is ALWAYS canonicalize_title() output (lowercase, single-spaced, ASCII
dashes). Unknown stays None — never guessed. Attribute values reuse the catalog
TextChoices literals so the resolver can feed variant-on-demand creation
directly. Confidence numbers are per-pattern judgment calls, OQ-provisional.

Brand normalization encodes the WD↔SanDisk "Optimus" rebrand exactly as spec
C.3.1 mandates ("same MPNs, new brand", Jan 2026). Verified scope (Codex
CR-004): the rebrand moved WD-BRANDED SSD LINES under the SanDisk name — it is
NOT an HDD claim. Mapping sandisk → western_digital is still safe as a brand
key because brand is only a GATE here — equivalence alone never merges
anything; every rung-1/2 accept requires an MPN/alias hit, so a native SanDisk
product cannot join a WD model unless its exact token hits a WD alias.
Re-verify against seeded catalog aliases at MS-1c; split the key there if the
catalog contradicts the equivalence."""

from __future__ import annotations

import re

from hw_radar.matching.types import Attribute, ExtractedAttributes

_LAYER = "vocab"
_GB = 1_000_000_000
_TB = 1_000_000_000_000

_CAPACITY = re.compile(r"\b(\d+(?:\.\d+)?)\s*(tb|gb)\b")
_RPM_PLAIN = re.compile(r"\b(\d{4,5})\s*rpm\b")
_RPM_K = re.compile(r"\b(\d{1,2}(?:\.\d)?)k\s*rpm\b")
_CACHE = re.compile(r"\b(\d{1,4})\s*mb\s+(?:cache|buffer)\b")
_SECTOR = re.compile(r"\b(512n|512e|4kn)\b")
_LINK_SPEED = re.compile(r"\b(\d+(?:\.\d+)?)\s*gb/?s\b")
_WARRANTY_YEARS = re.compile(r"\b(\d{1,2})\s*[- ]?(?:yr|year)s?\s+warranty\b")
# (?<![\d.]) blocks '13.5' matching as 3.5; unit suffix raises confidence.
_FORM_35 = re.compile(r"(?<![\d.])3\.5\s*(\"|in(?:ch)?\b)?")
_FORM_25 = re.compile(r"(?<![\d.])2\.5\s*(\"|in(?:ch)?\b)?")
_FORM_M2 = re.compile(r"\bm\.?2\b")

_INTERFACES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bnvme\b"), "nvme"),
    (re.compile(r"\bsas\b"), "sas"),
    (re.compile(r"\bsata\b"), "sata"),
    (re.compile(r"\bscsi\b"), "scsi"),
    (re.compile(r"\busb\b"), "usb"),
)

# Ordered, first match wins: for_parts outranks used ("used - for parts");
# factory recert outranks plain recert. 'renewed' is Amazon-speak for seller
# refurb, NOT manufacturer recert. '(?<!like )new' keeps "like new" unasserted.
_CONDITIONS: tuple[tuple[re.Pattern[str], str, str | None, float], ...] = (
    (re.compile(r"\bfor parts\b|\bparts only\b|\bas[- ]is\b|\bnot working\b"),
     "for_parts", None, 0.95),
    (re.compile(r"\b(?:factory|manufacturer) recert(?:ified)?\b"),
     "recertified", "factory", 0.95),
    (re.compile(r"\brecert(?:ified)?\b"), "recertified", None, 0.85),
    (re.compile(r"\bseller refurb(?:ished)?\b"), "refurbished", "seller", 0.95),
    (re.compile(r"\brefurb(?:ished)?\b|\brenewed\b"), "refurbished", None, 0.85),
    (re.compile(r"\bopen box\b"), "open_box", None, 0.9),
    (re.compile(r"\bserver pull\b|\bpull(?:ed)?\b|\bused\b"), "used", None, 0.8),
    (re.compile(r"\bfactory sealed\b|(?<!like )\bnew\b"), "new", None, 0.8),
)

_PACKAGING: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bretail(?:\s+box(?:ed)?)?\b"), "retail"),
    (re.compile(r"\boem\b|\bbulk\b|\bbare drive\b|\bbrown box\b"), "bulk"),
)

_WARRANTY_CHANNELS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bno warranty\b"), "none"),
    (re.compile(r"\bmanufacturer warranty\b"), "manufacturer"),
    (re.compile(r"\bseller warranty\b"), "seller"),
)

# Quantity: digit-FIRST forms only. The 'xN' form (e.g. 'x16') is deliberately
# unsupported — it collides with Seagate family names (Exos X16/X18/X24).
_QUANTITIES: tuple[tuple[re.Pattern[str], float], ...] = (
    (re.compile(r"\blot of (\d{1,3})\b"), 0.95),
    (re.compile(r"\b(\d{1,3})[- ]pack\b"), 0.9),
    (re.compile(r"\bqty:? ?(\d{1,3})\b"), 0.9),
    (re.compile(r"\b(\d{1,3})\s?x\b"), 0.7),
)

# Longest-married-name first so 'western digital' wins over 'wd'.
_BRANDS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bwestern digital\b"), "western_digital"),
    (re.compile(r"\bsandisk\b"), "western_digital"),  # Optimus rebrand, Jan 2026
    (re.compile(r"\bwd\b"), "western_digital"),
    (re.compile(r"\bhgst\b|\bhitachi\b"), "hgst"),
    (re.compile(r"\bseagate\b"), "seagate"),
    (re.compile(r"\btoshiba\b"), "toshiba"),
    (re.compile(r"\bsamsung\b"), "samsung"),
    (re.compile(r"\bsolidigm\b"), "solidigm"),
    (re.compile(r"\bintel\b"), "intel"),
    (re.compile(r"\bmicron\b|\bcrucial\b"), "micron"),
    (re.compile(r"\bkingston\b"), "kingston"),
    (re.compile(r"\bkioxia\b"), "kioxia"),
)


def _capacity(title: str) -> Attribute[int] | None:
    values: list[tuple[int, str]] = []
    for m in _CAPACITY.finditer(title):
        unit = _TB if m.group(2) == "tb" else _GB
        values.append((int(float(m.group(1)) * unit), m.group(0)))
    if not values:
        return None
    distinct = {v for v, _ in values}
    confidence = 0.9 if len(distinct) == 1 else 0.5
    value, source = values[0]
    return Attribute(value=value, confidence=confidence, layer=_LAYER, source_text=source)


def _first_pattern(
    title: str, table: tuple[tuple[re.Pattern[str], str], ...], confidence: float
) -> Attribute[str] | None:
    for pattern, value in table:
        m = pattern.search(title)
        if m:
            return Attribute(
                value=value, confidence=confidence, layer=_LAYER, source_text=m.group(0)
            )
    return None


def _form_factor(title: str) -> Attribute[str] | None:
    for pattern, value in ((_FORM_35, "3.5"), (_FORM_25, "2.5")):
        m = pattern.search(title)
        if m:
            confidence = 0.95 if m.group(1) else 0.7  # bare '3.5' is weaker
            return Attribute(
                value=value, confidence=confidence, layer=_LAYER, source_text=m.group(0)
            )
    m = _FORM_M2.search(title)
    if m:
        return Attribute(value="m.2", confidence=0.85, layer=_LAYER, source_text=m.group(0))
    return None


def _rpm(title: str) -> Attribute[int] | None:
    m = _RPM_PLAIN.search(title)
    if m:
        return Attribute(
            value=int(m.group(1)), confidence=0.95, layer=_LAYER, source_text=m.group(0)
        )
    m = _RPM_K.search(title)
    if m:
        return Attribute(
            value=int(float(m.group(1)) * 1000),
            confidence=0.9,
            layer=_LAYER,
            source_text=m.group(0),
        )
    return None


def _int_pattern(title: str, pattern: re.Pattern[str], scale: int = 1) -> Attribute[int] | None:
    m = pattern.search(title)
    if m is None:
        return None
    return Attribute(
        value=int(m.group(1)) * scale, confidence=0.9, layer=_LAYER, source_text=m.group(0)
    )


def _condition(title: str) -> tuple[Attribute[str] | None, Attribute[str] | None]:
    for pattern, value, channel, confidence in _CONDITIONS:
        m = pattern.search(title)
        if m:
            cond = Attribute(
                value=value, confidence=confidence, layer=_LAYER, source_text=m.group(0)
            )
            chan = (
                Attribute(value=channel, confidence=confidence, layer=_LAYER,
                          source_text=m.group(0))
                if channel
                else None
            )
            return cond, chan
    return None, None


def _quantity(title: str) -> Attribute[int] | None:
    for pattern, confidence in _QUANTITIES:
        m = pattern.search(title)
        if m:
            return Attribute(
                value=int(m.group(1)), confidence=confidence, layer=_LAYER,
                source_text=m.group(0),
            )
    return None


def _link_speed(title: str) -> Attribute[float] | None:
    m = _LINK_SPEED.search(title)
    if m is None:
        return None
    return Attribute(
        value=float(m.group(1)), confidence=0.9, layer=_LAYER, source_text=m.group(0)
    )


def _recording(title: str) -> Attribute[str] | None:
    # PMR is deliberately unmapped: marketing usage is ambiguous (spec C.3.1
    # posture: unknown over guessed).
    if re.search(r"\bcmr\b", title):
        return Attribute(value="cmr", confidence=0.95, layer=_LAYER, source_text="cmr")
    if re.search(r"\bsmr\b", title):
        return Attribute(value="smr", confidence=0.95, layer=_LAYER, source_text="smr")
    return None


def _security(title: str) -> Attribute[str] | None:
    for token in ("sed", "fips", "ise"):
        if re.search(rf"\b{token}\b", title):
            return Attribute(value=token, confidence=0.85, layer=_LAYER, source_text=token)
    return None


def _sector(title: str) -> Attribute[str] | None:
    m = _SECTOR.search(title)
    if m is None:
        return None
    return Attribute(value=m.group(1), confidence=0.95, layer=_LAYER, source_text=m.group(0))


def extract(title: str) -> ExtractedAttributes:
    condition, recert_channel = _condition(title)
    return ExtractedAttributes(
        capacity_bytes=_capacity(title),
        interface=_first_pattern(title, _INTERFACES, 0.9),
        link_speed_gbps=_link_speed(title),
        form_factor=_form_factor(title),
        rpm=_rpm(title),
        cache_mb=_int_pattern(title, _CACHE),
        sector_format=_sector(title),
        recording_tech=_recording(title),
        security=_security(title),
        condition=condition,
        recert_channel=recert_channel,
        packaging=_first_pattern(title, _PACKAGING, 0.85),
        warranty_months=_int_pattern(title, _WARRANTY_YEARS, scale=12),
        warranty_channel=_first_pattern(title, _WARRANTY_CHANNELS, 0.9),
        quantity=_quantity(title),
        brand=_first_pattern(title, _BRANDS, 0.9),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_vocab.py -q`
Expected: all PASS. If a vector fails, fix the PATTERN, not the vector — the vectors encode spec C.3.1 semantics.

- [ ] **Step 5: Fix pass and commit**

```bash
uv run ruff format . && uv run ruff check . --fix
uv run basedpyright src/hw_radar/matching tests/unit/test_vocab.py
git add src/hw_radar/matching/vocab.py tests/unit/test_vocab.py
git commit -m "feat(matching): N2 controlled-vocabulary attribute extraction"
```

---

### Task 3: N3 MPN-candidate extraction

**Files:**
- Create: `src/hw_radar/matching/mpn.py`
- Test: `tests/unit/test_mpn.py`

**Interfaces:**
- Consumes: `normalize.normalize_alias_text`, `types.MpnCandidate`, `types.TokenKind`.
- Produces: `mpn.extract_candidates(title: str, *, structured_mpn: str | None = None, source_key: str = "") -> list[MpnCandidate]` (sorted confidence-desc, deduped on `normalized`); `mpn.HOUSE_SKU_PREFIXES: dict[str, tuple[str, ...]]` (per-source registry, empty until MS-1d fills it).

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_mpn.py
"""N3 code-shaped token extraction (spec C.3.1; OEM shapes per the 2026-07-04
OEM cross-reference research)."""

import pytest

from hw_radar.matching import mpn
from hw_radar.matching.normalize import canonicalize_title
from hw_radar.matching.types import MpnCandidate, TokenKind


def _kinds(
    title: str, *, structured_mpn: str | None = None, source_key: str = ""
) -> dict[str, MpnCandidate]:
    cands = mpn.extract_candidates(
        canonicalize_title(title), structured_mpn=structured_mpn, source_key=source_key
    )
    return {c.normalized: c for c in cands}


@pytest.mark.parametrize(
    ("title", "token", "vendor"),
    [
        ("Seagate Exos ST16000NM001G 16TB", "st16000nm001g", "seagate"),
        ("WD Red Plus WD120EFBX NAS", "wd120efbx", "western_digital"),
        ("WD Ultrastar WUH721816ALE6L4", "wuh721816ale6l4", "western_digital"),
        ("HGST HUS724040ALS640 4TB SAS", "hus724040als640", "western_digital"),
        ("Toshiba MG08ACA16TE 16TB", "mg08aca16te", "toshiba"),
        ("Samsung MZ-77E1T0B/AM 870 EVO", "mz77e1t0bam", "samsung"),
    ],
)
def test_manufacturer_shapes(title: str, token: str, vendor: str) -> None:
    found = _kinds(title)
    assert token in found
    assert found[token].kind is TokenKind.MANUFACTURER_MPN
    assert found[token].vendor_hint == vendor


def test_oem_shapes_are_context_gated() -> None:
    found = _kinds("NetApp X477A-R6 4TB 7.2K SAS HDD WD4001FYYG")
    assert "x477ar6" in found and found["x477ar6"].kind is TokenKind.OEM_PN
    assert found["x477ar6"].vendor_hint == "netapp"
    assert "wd4001fyyg" in found  # dual-labeled: both tokens present
    # Same shape WITHOUT the vendor word: not recognized as OEM.
    ungated = _kinds("random X477A-R6 4TB drive")
    assert all(c.kind is not TokenKind.OEM_PN for c in ungated.values())


def test_netapp_shape_requires_three_digits() -> None:
    # 'x16' (Exos X16) must never read as a NetApp part, even in a NetApp title.
    found = _kinds("NetApp shelf with Seagate Exos X16 ST16000NM001G")
    assert "x16" not in found


def test_emc_tla_and_hpe_and_dpn_and_fru() -> None:
    assert _kinds("EMC 005049070 replacement drive")["005049070"].vendor_hint == "dell_emc"
    assert _kinds("HPE 507125-B21 option kit")["507125b21"].vendor_hint == "hpe"
    dpn = _kinds("Dell DP/N 0F1W2X 4TB")
    assert "f1w2x" in dpn and dpn["f1w2x"].kind is TokenKind.OEM_PN
    fru = _kinds("IBM FRU 39T0361 panel")
    assert "39t0361" in fru and fru["39t0361"].vendor_hint == "lenovo_ibm"


def test_structured_field_outranks_title_tokens() -> None:
    cands = mpn.extract_candidates(
        canonicalize_title("some listing title 16TB"), structured_mpn="ST16000NM001G"
    )
    assert cands[0].normalized == "st16000nm001g"
    assert cands[0].from_structured_field is True
    assert cands[0].kind is TokenKind.MANUFACTURER_MPN
    assert cands[0].confidence > 0.95


def test_house_sku_prefix_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(mpn.HOUSE_SKU_PREFIXES, "serverpartdeals", ("spd-",))
    found = _kinds("SPD-16TB-RECERT enterprise", source_key="serverpartdeals")
    assert "spd16tbrecert" in found
    assert found["spd16tbrecert"].kind is TokenKind.HOUSE_SKU


def test_vocab_tokens_never_become_candidates() -> None:
    found = _kinds("16TB 7200RPM 512e SATA 3.5 inch drive 256MB cache")
    assert found == {}


def test_unknown_code_shaped_token_low_confidence() -> None:
    found = _kinds("mystery drive PN ABC123XYZ99")
    assert "abc123xyz99" in found
    cand = found["abc123xyz99"]
    assert cand.kind is TokenKind.UNKNOWN_CODE
    assert cand.confidence < 0.5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_mpn.py -q`
Expected: FAIL — module not found

- [ ] **Step 3: Implement mpn.py**

```python
# src/hw_radar/matching/mpn.py
"""N3 code-shaped token extraction (spec C.3.1).

Manufacturer-MPN shapes match anywhere in the canonical title. OEM shapes are
CONTEXT-GATED (vendor word present, or label-adjacent like 'dp/n <tok>') —
they are short/ambiguous, and Dell's 5-char DP/N or NetApp's X-prefix would
otherwise fire on arbitrary tokens (the NetApp pattern requires 3–4 digits
precisely so 'Exos X16' can never read as a NetApp part). House SKUs are
recognized via the per-source prefix registry — SOURCE-LOCAL aliases only,
never canonical (ADR-0019 rule 2); the registry is empty until MS-1d
connectors observe real SKU shapes. Structured-field MPNs (JSON-LD `mpn`)
outrank every title-mined token."""

from __future__ import annotations

import re

from hw_radar.matching.normalize import normalize_alias_text
from hw_radar.matching.types import MpnCandidate, TokenKind

_MFR_SHAPES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("seagate", re.compile(r"\bst\d{3,6}[a-z]{2}\d{3}[a-z0-9]?\b")),
    ("western_digital", re.compile(r"\bwd\d{2,4}[a-z]{4}\b")),
    ("western_digital", re.compile(r"\b(?:wuh|wus|huh|hus|hdn)\d{6}[a-z0-9]{4,8}\b")),
    ("toshiba", re.compile(r"\b(?:mg|mn)\d{2}[a-z]{3}\d{1,3}t?[a-z]{0,3}\b")),
    ("samsung", re.compile(r"\bmz-?[a-z0-9]{6,9}(?:/[a-z0-9]{2,4})?\b")),
)

# (vendor, token pattern with ONE capture group, gate pattern or None).
# gate=None means the token pattern itself is label-adjacent (dp/n, fru).
_OEM_RULES: tuple[tuple[str, re.Pattern[str], re.Pattern[str] | None], ...] = (
    ("dell_emc", re.compile(r"\b(00[45]\d{6})\b"), re.compile(r"\b(?:emc|dell)\b")),
    ("dell_emc", re.compile(r"\bdp/?n[: ]*0?([0-9a-z]{5})\b"), None),
    ("hpe", re.compile(r"\b(\d{6}-[a-z0-9]{3})\b"),
     re.compile(r"\b(?:hpe|hp|hewlett|proliant)\b")),
    ("netapp", re.compile(r"\b(x\d{3,4}[a-z]?(?:-r\d)?)\b"), re.compile(r"\bnetapp\b")),
    ("lenovo_ibm", re.compile(r"\bfru[: ]*([0-9a-z]{7})\b"), None),
)

# Per-source house-SKU prefixes (lowercase, matched against canonical tokens).
# Empty by design at MS-1b: MS-1d connector work observes real SKU shapes and
# fills this in (spec C.3.1: house SKUs → source-local aliases, never canonical).
HOUSE_SKU_PREFIXES: dict[str, tuple[str, ...]] = {}

_CODE_SHAPE = re.compile(r"\b[a-z0-9][a-z0-9./-]{5,23}\b")
_TWO_ALPHA = re.compile(r"[a-z].*[a-z]")
_TWO_DIGIT = re.compile(r"\d.*\d")
# Vocab-owned tokens that are code-shaped but never MPN candidates.
_VOCAB_TAILS = re.compile(r"(?:\d(?:\.\d+)?(?:tb|gb|mb|rpm)|gb/s|512e|512n|4kn|inch)$")


def _classify_shape(token: str) -> tuple[TokenKind, str]:
    for vendor, pattern in _MFR_SHAPES:
        if pattern.fullmatch(token):
            return TokenKind.MANUFACTURER_MPN, vendor
    return TokenKind.UNKNOWN_CODE, ""


def extract_candidates(
    title: str, *, structured_mpn: str | None = None, source_key: str = ""
) -> list[MpnCandidate]:
    out: dict[str, MpnCandidate] = {}

    def add(candidate: MpnCandidate) -> None:
        existing = out.get(candidate.normalized)
        if existing is None or candidate.confidence > existing.confidence:
            out[candidate.normalized] = candidate

    if structured_mpn:
        canonical = structured_mpn.casefold().strip()
        kind, vendor = _classify_shape(canonical)
        add(
            MpnCandidate(
                raw=structured_mpn,
                normalized=normalize_alias_text(structured_mpn),
                kind=kind,
                vendor_hint=vendor,
                confidence=0.98,
                from_structured_field=True,
            )
        )

    for vendor, pattern in _MFR_SHAPES:
        for m in pattern.finditer(title):
            add(
                MpnCandidate(
                    raw=m.group(0),
                    normalized=normalize_alias_text(m.group(0)),
                    kind=TokenKind.MANUFACTURER_MPN,
                    vendor_hint=vendor,
                    confidence=0.9,
                )
            )

    for vendor, pattern, gate in _OEM_RULES:
        if gate is not None and not gate.search(title):
            continue
        for m in pattern.finditer(title):
            add(
                MpnCandidate(
                    raw=m.group(1),
                    normalized=normalize_alias_text(m.group(1)),
                    kind=TokenKind.OEM_PN,
                    vendor_hint=vendor,
                    confidence=0.8,
                )
            )

    for prefix in HOUSE_SKU_PREFIXES.get(source_key, ()):
        for m in _CODE_SHAPE.finditer(title):
            if m.group(0).startswith(prefix):
                add(
                    MpnCandidate(
                        raw=m.group(0),
                        normalized=normalize_alias_text(m.group(0)),
                        kind=TokenKind.HOUSE_SKU,
                        vendor_hint="",
                        confidence=0.7,
                    )
                )

    for m in _CODE_SHAPE.finditer(title):
        token = m.group(0)
        normalized = normalize_alias_text(token)
        if normalized in out or not normalized:
            continue
        if not (_TWO_ALPHA.search(token) and _TWO_DIGIT.search(token)):
            continue
        if _VOCAB_TAILS.search(token):
            continue
        add(
            MpnCandidate(
                raw=token,
                normalized=normalized,
                kind=TokenKind.UNKNOWN_CODE,
                vendor_hint="",
                confidence=0.3,
            )
        )

    return sorted(out.values(), key=lambda c: -c.confidence)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_mpn.py -q`
Expected: all PASS. Likely iteration points: the `3.5`/`2.5` tokens match `_CODE_SHAPE`? No — they are 3 chars, below the 6-char minimum. `"sata 3.5 inch"` tokens lack two digits+two alphas. If `test_vocab_tokens_never_become_candidates` fails, extend `_VOCAB_TAILS`, don't weaken the test.

- [ ] **Step 5: Fix pass and commit**

```bash
uv run ruff format . && uv run ruff check . --fix
uv run basedpyright src/hw_radar/matching tests/unit/test_mpn.py
git add src/hw_radar/matching/mpn.py tests/unit/test_mpn.py
git commit -m "feat(matching): N3 MPN/OEM/house-SKU candidate extraction"
```

---

### Task 4: N4 per-vendor grammar decoders

**Files:**
- Create: `src/hw_radar/matching/grammars/__init__.py`
- Create: `src/hw_radar/matching/grammars/seagate.py`
- Create: `src/hw_radar/matching/grammars/wd.py`
- Create: `src/hw_radar/matching/grammars/toshiba.py`
- Test: `tests/unit/test_grammars.py`

**Interfaces:**
- Consumes: `types.DecodeResult`, `types.Provenance`. Input is always a `normalize_alias_text()` token.
- Produces: `grammars.decode(normalized_token: str) -> DecodeResult | None`.

- [ ] **Step 1: Write the failing tests (decoder vectors from datasheets/family pages)**

```python
# tests/unit/test_grammars.py
"""N4 grammar decoder vectors (spec C.3.1; references per the warranty-verification
and SSD part-number research reports). The decoder contract is WEAK by design:
family/capacity/generation only, provenance-tiered."""

import pytest

from hw_radar.matching.grammars import decode
from hw_radar.matching.types import Provenance

_TB = 1_000_000_000_000


def test_seagate_exos() -> None:
    r = decode("st16000nm001g")
    assert r is not None
    assert r.vendor == "seagate"
    assert r.family_name == "exos"
    assert r.capacity_bytes == 16000 * 1_000_000_000
    assert r.generation == "g"
    assert r.provenance is Provenance.CORROBORATED_COMMUNITY  # segment map tier


def test_seagate_ironwolf_and_unknown_segment() -> None:
    r = decode("st4000vn008")
    assert r is not None and r.family_name == "ironwolf"
    unknown = decode("st8000zz123")  # valid shape, unmapped segment
    assert unknown is not None
    assert unknown.family_name is None  # structure decodes; family unasserted
    assert unknown.provenance is Provenance.VENDOR_OFFICIAL  # only official structure used


@pytest.mark.parametrize(
    ("token", "family", "capacity_tb"),
    [
        ("wd120efbx", "red", 12),
        ("wd20efpx", "red", 2),
        ("wd121kryz", "gold", 12),
        ("wd102kfbx", "red pro", 10),
    ],
)
def test_wd_modern(token: str, family: str, capacity_tb: int) -> None:
    r = decode(token)
    assert r is not None
    assert r.vendor == "western_digital"
    assert r.family_name == family
    assert r.capacity_bytes == capacity_tb * _TB
    assert r.provenance is Provenance.CORROBORATED_COMMUNITY


def test_wd_four_digit_capacity_is_never_guessed() -> None:
    r = decode("wd4004fryz")  # 4-digit block: capacity encoding is ambiguous
    assert r is not None
    assert r.family_name == "gold"
    assert r.capacity_bytes is None
    assert r.provenance is Provenance.INFERRED


def test_hgst_lineage_family_only() -> None:
    wd = decode("wuh721816ale6l4")
    assert wd is not None
    assert wd.vendor == "western_digital"
    assert wd.family_name == "ultrastar"
    assert wd.capacity_bytes is None  # HGST capacity digits are ambiguous — vocab carries it
    hgst = decode("hus724040als640")
    assert hgst is not None and hgst.vendor == "hgst" and hgst.family_name == "ultrastar"


@pytest.mark.parametrize(
    ("token", "family", "capacity_tb", "generation"),
    [
        ("mg08aca16te", "mg enterprise capacity", 16, "08"),
        ("mg04aca400e", "mg enterprise capacity", 4, "04"),
        ("mn08aca14t", "n300", 14, "08"),
    ],
)
def test_toshiba_official_grammar(
    token: str, family: str, capacity_tb: int, generation: str
) -> None:
    r = decode(token)
    assert r is not None
    assert r.vendor == "toshiba"
    assert r.family_name == family
    assert r.capacity_bytes == capacity_tb * _TB
    assert r.generation == generation
    assert r.provenance is Provenance.VENDOR_OFFICIAL


def test_non_mpn_tokens_do_not_decode() -> None:
    for token in ("abc123xyz99", "x477ar6", "005049070", "16tb", ""):
        assert decode(token) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_grammars.py -q`
Expected: FAIL — module not found

- [ ] **Step 3: Implement the decoders**

```python
# src/hw_radar/matching/grammars/__init__.py
"""N4 per-vendor MPN grammar registry (spec C.3.1, ADR-0019 rule 3).

Decoders validate a token is a plausible MPN for their vendor and derive
family/capacity/generation ONLY — variant semantics come from the catalog,
never the code string. Each result carries a provenance tier that flows into
rung-2 confidence."""

from __future__ import annotations

from collections.abc import Callable

from hw_radar.matching.grammars import seagate, toshiba, wd
from hw_radar.matching.types import DecodeResult

_DECODERS: tuple[Callable[[str], DecodeResult | None], ...] = (
    seagate.decode,
    wd.decode,
    toshiba.decode,
)


def decode(normalized_token: str) -> DecodeResult | None:
    for decoder in _DECODERS:
        result = decoder(normalized_token)
        if result is not None:
            return result
    return None
```

```python
# src/hw_radar/matching/grammars/seagate.py
"""Seagate ST-number grammar.

Structure per Seagate's official ST Model Number Cheat Sheet (vendor_official):
st + capacity-in-GB digits + 2-letter segment + 3-digit attributes + generation.
The 3-digit attributes block is explicitly variable and NEVER decoded. The
segment→family map rides family pages, not the cheat sheet — that tier is
corroborated_community, and asserting a family drops provenance to it."""

from __future__ import annotations

import re

from hw_radar.matching.types import DecodeResult, Provenance

_GB = 1_000_000_000

_ST = re.compile(r"^st(\d{3,6})([a-z]{2})(\d{3})([a-z0-9]?)$")

# Family pages, not the official cheat sheet → corroborated_community tier.
_SEGMENT_FAMILIES: dict[str, str] = {
    "nm": "exos",
    "ne": "ironwolf pro",
    "vn": "ironwolf",
    "vx": "skyhawk",
    "dm": "barracuda",
}


def decode(token: str) -> DecodeResult | None:
    m = _ST.fullmatch(token)
    if m is None:
        return None
    family = _SEGMENT_FAMILIES.get(m.group(2))
    return DecodeResult(
        vendor="seagate",
        family_name=family,
        capacity_bytes=int(m.group(1)) * _GB,
        generation=m.group(4) or None,
        provenance=(
            Provenance.CORROBORATED_COMMUNITY if family else Provenance.VENDOR_OFFICIAL
        ),
        rule=f"st:{m.group(2)}",
    )
```

```python
# src/hw_radar/matching/grammars/wd.py
"""WD grammars: modern WD retail/enterprise strings + HGST-lineage Ultrastar.

WD publishes NO current master decoder (warranty-verification research):
- 2/3-digit capacity blocks are corroborated_community (family product pages:
  WD20→2TB, WD120→12TB, WD201→20TB).
- The 4-digit block (WD4004FRYZ) and every HGST-style capacity read are
  ambiguous → capacity is asserted as None (inferred tier) and the N2 vocab
  capacity carries the claim. Never guess (ADR-0019 rule 3)."""

from __future__ import annotations

import re

from hw_radar.matching.types import DecodeResult, Provenance

_TB = 1_000_000_000_000

_WD = re.compile(r"^wd(\d{2,4})([a-z]{4})$")
_HGST = re.compile(r"^(wuh|wus|huh|hus|hdn)(\d{6})([a-z0-9]{4,8})$")

# First two suffix letters → family, per WD family product pages.
_SUFFIX_FAMILIES: dict[str, str] = {
    "ef": "red",
    "kf": "red pro",
    "kr": "gold",
    "fr": "gold",
    "pu": "purple",
    "ez": "blue",
}

_HGST_FAMILIES: dict[str, str] = {
    "wuh": "ultrastar",
    "wus": "ultrastar",
    "huh": "ultrastar",
    "hus": "ultrastar",
    "hdn": "deskstar nas",
}


def decode(token: str) -> DecodeResult | None:
    m = _WD.fullmatch(token)
    if m is not None:
        digits, suffix = m.group(1), m.group(2)
        family = _SUFFIX_FAMILIES.get(suffix[:2])
        if len(digits) == 2:
            capacity: int | None = int(digits) * _TB // 10  # WD20 → 2 TB
        elif len(digits) == 3:
            capacity = int(digits[:2]) * _TB  # WD120 → 12 TB, WD201 → 20 TB
        else:
            capacity = None  # 4-digit encoding is ambiguous — never guessed
        provenance = (
            Provenance.INFERRED
            if capacity is None
            else Provenance.CORROBORATED_COMMUNITY
        )
        if family is None and capacity is None:
            return None  # neither field derivable: not a useful decode
        return DecodeResult(
            vendor="western_digital",
            family_name=family,
            capacity_bytes=capacity,
            generation=None,
            provenance=provenance,
            rule=f"wd:{suffix[:2]}",
        )
    m = _HGST.fullmatch(token)
    if m is not None:
        prefix = m.group(1)
        return DecodeResult(
            vendor="western_digital" if prefix.startswith("w") else "hgst",
            family_name=_HGST_FAMILIES[prefix],
            capacity_bytes=None,  # HGST capacity digits ambiguous (4040→4TB, 1816→16TB)
            generation=None,
            provenance=Provenance.CORROBORATED_COMMUNITY,
            rule=f"hgst:{prefix}",
        )
    return None
```

```python
# src/hw_radar/matching/grammars/toshiba.py
"""Toshiba MG/MN grammar — the one vendor_official decoder in the set: Toshiba
publishes "Meaning of Model Number" breaking e.g. MG08ACA16TE into family /
generation / form-factor / speed / interface / capacity / suffix. We assert
family/generation/capacity only (ADR-0019 rule 3). Two capacity encodings:
'16t' (TB) and '400' (hundreds of GB, MG04ACA400E → 4 TB)."""

from __future__ import annotations

import re

from hw_radar.matching.types import DecodeResult, Provenance

_TB = 1_000_000_000_000

_TOSHIBA = re.compile(r"^(mg|mn)(\d{2})([a-z]{3})(?:(\d{1,2})t|(\d)00)([a-z]{0,3})$")

_FAMILIES: dict[str, str] = {"mg": "mg enterprise capacity", "mn": "n300"}


def decode(token: str) -> DecodeResult | None:
    m = _TOSHIBA.fullmatch(token)
    if m is None:
        return None
    if m.group(4) is not None:
        capacity = int(m.group(4)) * _TB  # '16t' → 16 TB
    else:
        capacity = int(m.group(5)) * _TB  # '400' → leading digit is TB (MG04ACA400E → 4 TB)
    return DecodeResult(
        vendor="toshiba",
        family_name=_FAMILIES[m.group(1)],
        capacity_bytes=capacity,
        generation=m.group(2),
        provenance=Provenance.VENDOR_OFFICIAL,
        rule=f"toshiba:{m.group(1)}",
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_grammars.py -q`
Expected: all PASS. Vector-fix discipline: vectors come from datasheets/family pages — if one fails, the grammar is wrong, not the vector.

- [ ] **Step 5: Fix pass and commit**

```bash
uv run ruff format . && uv run ruff check . --fix
uv run basedpyright src/hw_radar/matching tests/unit/test_grammars.py
git add src/hw_radar/matching/grammars tests/unit/test_grammars.py
git commit -m "feat(matching): N4 provenance-tiered vendor grammar decoders"
```

---

### Task 5: Resolution schema — `ListingResolution`, `Listing` denorm fields, `Condition.FOR_PARTS`

**Files:**
- Modify: `src/hw_radar/catalog/models/base.py` (add `ResolutionGrain`)
- Modify: `src/hw_radar/catalog/models/identity.py` (add `Condition.FOR_PARTS`)
- Modify: `src/hw_radar/catalog/models/market.py` (Listing denormalized fields)
- Create: `src/hw_radar/catalog/models/resolution.py`
- Modify: `src/hw_radar/catalog/models/__init__.py`, `src/hw_radar/catalog/admin.py`
- Create: `src/hw_radar/catalog/migrations/0006_resolution.py` (generated + reviewed)
- Test: `tests/db/test_resolution_models.py`

**Interfaces:**
- Consumes: existing `Listing`, `ProductFamily/ProductModel/ProductVariant`, `TimeStamped` patterns.
- Produces: `ResolutionGrain` (values `none|family|model|variant` — identical strings to `matching.types.Grain`), `ResolutionMethod` (values `source_alias|exact_alias|mpn_decode|attribute_match|manual`), `ListingResolution` (fields: `listing`, `grain`, `product_family/product_model/product_variant`, `method`, `confidence`, `matcher_version`, `evidence`, `resolved_at`, `is_current` — DB-enforced one-current-per-listing — and `superseded_by`), `Listing.product_family/product_model/resolution_grain/resolution_confidence`, `Condition.FOR_PARTS = "for_parts"`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/db/test_resolution_models.py
"""C.3.3 resolution-state schema: grain/target coherence, append-only supersede."""

import pytest
from django.db import IntegrityError

from hw_radar.catalog.models import (
    Category,
    Condition,
    Listing,
    ListingResolution,
    Manufacturer,
    ProductFamily,
    ProductModel,
    ProductVariant,
    ResolutionGrain,
    ResolutionMethod,
    RetentionClass,
    SourceSite,
)


@pytest.fixture
def site(db: None) -> SourceSite:
    return SourceSite.objects.create(name="Demo", normalized_name="resdemo")


@pytest.fixture
def listing(site: SourceSite) -> Listing:
    return Listing.objects.create(
        source_site=site,
        source_listing_key="k1",
        canonical_url="https://example.test/1",
        url_hash="h1",
        title_raw="Seagate Exos 16TB ST16000NM001G",
        retention_class=RetentionClass.MERCHANT_FACT,
    )


@pytest.fixture
def model(db: None) -> ProductModel:
    mfr = Manufacturer.objects.create(name="Seagate", normalized_name="seagate")
    return ProductModel.objects.create(
        manufacturer=mfr,
        model_number="ST16000NM001G",
        normalized_model_number="st16000nm001g",
    )


def test_model_grain_edge_holds_only_the_model_fk(listing: Listing, model: ProductModel) -> None:
    edge = ListingResolution.objects.create(
        listing=listing,
        grain=ResolutionGrain.MODEL,
        product_model=model,
        method=ResolutionMethod.EXACT_ALIAS,
        confidence=0.98,
        matcher_version="test",
    )
    assert edge.product_family_id is None and edge.product_variant_id is None


def test_grain_target_coherence_rejects_mismatch(listing: Listing, model: ProductModel) -> None:
    with pytest.raises(IntegrityError):
        ListingResolution.objects.create(
            listing=listing,
            grain=ResolutionGrain.FAMILY,  # family grain but a model target
            product_model=model,
            method=ResolutionMethod.EXACT_ALIAS,
            confidence=0.9,
            matcher_version="test",
        )


def test_none_grain_rejects_any_target(listing: Listing, model: ProductModel) -> None:
    with pytest.raises(IntegrityError):
        ListingResolution.objects.create(
            listing=listing,
            grain=ResolutionGrain.NONE,
            product_model=model,
            matcher_version="test",
        )


def test_accepted_grain_requires_method_and_confidence(
    listing: Listing, model: ProductModel
) -> None:
    with pytest.raises(IntegrityError):
        ListingResolution.objects.create(
            listing=listing,
            grain=ResolutionGrain.MODEL,
            product_model=model,
            method="",  # accepted grain without a method: incoherent
            matcher_version="test",
        )


def test_supersede_chain_keeps_one_current_edge(listing: Listing, model: ProductModel) -> None:
    # The apply order the resolver must follow: demote-old → insert-new → link-old.
    first = ListingResolution.objects.create(
        listing=listing, grain=ResolutionGrain.NONE, matcher_version="test"
    )
    first.is_current = False
    first.save(update_fields=["is_current"])
    second = ListingResolution.objects.create(
        listing=listing,
        grain=ResolutionGrain.MODEL,
        product_model=model,
        method=ResolutionMethod.EXACT_ALIAS,
        confidence=0.98,
        matcher_version="test",
    )
    first.superseded_by = second
    first.save(update_fields=["superseded_by"])
    current = listing.resolutions.filter(is_current=True)
    assert list(current) == [second]


def test_two_current_edges_for_one_listing_are_impossible(
    listing: Listing, model: ProductModel
) -> None:
    # CR-002: the one-current invariant is a DATABASE constraint, not query
    # discipline — concurrent resolver calls must collide here, not corrupt state.
    ListingResolution.objects.create(
        listing=listing, grain=ResolutionGrain.NONE, matcher_version="test"
    )
    with pytest.raises(IntegrityError):
        ListingResolution.objects.create(
            listing=listing,
            grain=ResolutionGrain.MODEL,
            product_model=model,
            method=ResolutionMethod.EXACT_ALIAS,
            confidence=0.98,
            matcher_version="test",
        )


def test_current_edge_cannot_be_superseded(listing: Listing) -> None:
    first = ListingResolution.objects.create(
        listing=listing, grain=ResolutionGrain.NONE, matcher_version="test"
    )
    first.is_current = False
    first.save(update_fields=["is_current"])
    second = ListingResolution.objects.create(
        listing=listing, grain=ResolutionGrain.NONE, matcher_version="test"
    )
    second.superseded_by = first  # a CURRENT edge pointing at a successor is incoherent
    with pytest.raises(IntegrityError):
        second.save(update_fields=["superseded_by"])


def test_listing_carries_denormalized_resolution_fields(listing: Listing) -> None:
    field_names = {f.name for f in Listing._meta.get_fields()}
    assert {
        "product_family",
        "product_model",
        "product_variant",
        "resolution_grain",
        "resolution_confidence",
    } <= field_names
    assert listing.resolution_grain == ResolutionGrain.NONE


def test_for_parts_condition_supports_variant_on_demand(model: ProductModel) -> None:
    variant = ProductVariant.objects.create(
        product_model=model, condition=Condition.FOR_PARTS
    )
    assert variant.condition == "for_parts"


def test_drive_category_still_seeded(db: None) -> None:
    # Rung-2 family materialization depends on the MS-0 seed surviving migration 0006.
    assert Category.objects.filter(slug="drive").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/db/test_resolution_models.py -q`
Expected: FAIL — `ImportError: cannot import name 'ListingResolution'`

- [ ] **Step 3: Implement the schema**

Append to `src/hw_radar/catalog/models/base.py` (after `RetentionClass`; `ResolutionGrain` lives here, NOT in resolution.py, because `market.Listing` needs it and `resolution.py` imports `market` — base.py breaks the cycle):

```python
class ResolutionGrain(models.TextChoices):
    """C.3.3 resolution grains. String values are shared verbatim with
    matching.types.Grain — the resolver maps between them by value."""

    NONE = "none", "Unresolved"
    FAMILY = "family", "Product family"
    MODEL = "model", "Product model"
    VARIANT = "variant", "Product variant"
```

In `src/hw_radar/catalog/models/identity.py`, extend `Condition` (N2 extracts `for-parts` per C.3.1; variant-on-demand needs the choice to exist):

```python
class Condition(models.TextChoices):
    NEW = "new", "New"
    RECERTIFIED = "recertified", "Recertified"
    REFURBISHED = "refurbished", "Refurbished"
    USED = "used", "Used"
    OPEN_BOX = "open_box", "Open box"
    FOR_PARTS = "for_parts", "For parts / not working"
    UNKNOWN = "unknown", "Unknown"
```

In `src/hw_radar/catalog/models/market.py`, add to `Listing` (after the existing `product_variant` field; import `ResolutionGrain` from `base` and reference identity models by string to keep import order unchanged):

```python
    # Denormalized CURRENT resolution (C.3.3): most-specific-wins, lower grains
    # NULL; refreshed ONLY by matching.resolver.CatalogResolver on accept. The
    # append-only audit trail lives in ListingResolution — these fields are a
    # read-path convenience, never the source of truth.
    product_family = models.ForeignKey(
        "catalog.ProductFamily",
        on_delete=models.SET_NULL,
        related_name="listings",
        null=True,
        blank=True,
    )
    product_model = models.ForeignKey(
        "catalog.ProductModel",
        on_delete=models.SET_NULL,
        related_name="listings",
        null=True,
        blank=True,
    )
    resolution_grain = models.CharField(
        max_length=10, choices=ResolutionGrain.choices, default=ResolutionGrain.NONE
    )
    resolution_confidence = models.FloatField(null=True, blank=True)
```

Create `src/hw_radar/catalog/models/resolution.py`:

```python
# pyright: reportIncompatibleVariableOverride=false
# django-types treats concrete nested Meta classes as incompatible with abstract
# base model Meta classes; Django's model metaclass handles this pattern.
"""Resolution state (spec C.3.3, ADR-0019 rule 6): the append-only
listing_resolution edge table + the unknown_model backfill view's unmanaged model.

Edges are NEVER updated or deleted; re-resolution appends a new edge and points
the prior current edge's superseded_by at it. Target FKs are most-specific-only
(lower grains NULL), mirroring Listing's denormalized rule. Identity targets are
PROTECT: edges are the audit trail (DR-010) — deleting a family/model/variant
that evidence points at must be blocked, matching ProductAlias's posture."""

from __future__ import annotations

from typing import ClassVar

from django.db import models
from django.utils import timezone

from hw_radar.catalog.models.base import ResolutionGrain
from hw_radar.catalog.models.identity import ProductFamily, ProductModel, ProductVariant
from hw_radar.catalog.models.market import Listing


class ResolutionMethod(models.TextChoices):
    """C.3.3 method enum; rung numbers are evidence, methods are schema."""

    SOURCE_ALIAS = "source_alias", "Rung 0 — re-observation"
    EXACT_ALIAS = "exact_alias", "Rung 1 — exact alias"
    MPN_DECODE = "mpn_decode", "Rung 2 — grammar decode"
    ATTRIBUTE_MATCH = "attribute_match", "Rung 3 — attribute match"
    MANUAL = "manual", "Rung 4 — manual"


class ListingResolution(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="resolutions")
    grain = models.CharField(
        max_length=10, choices=ResolutionGrain.choices, default=ResolutionGrain.NONE
    )
    product_family = models.ForeignKey(
        ProductFamily, on_delete=models.PROTECT, related_name="resolutions", null=True, blank=True
    )
    product_model = models.ForeignKey(
        ProductModel, on_delete=models.PROTECT, related_name="resolutions", null=True, blank=True
    )
    product_variant = models.ForeignKey(
        ProductVariant, on_delete=models.PROTECT, related_name="resolutions", null=True, blank=True
    )
    method = models.CharField(
        max_length=20, choices=ResolutionMethod.choices, blank=True, default=""
    )
    confidence = models.FloatField(null=True, blank=True)
    matcher_version = models.CharField(max_length=20)
    evidence: models.JSONField[dict[str, object]] = models.JSONField(default=dict, blank=True)
    resolved_at = models.DateTimeField(default=timezone.now)
    # is_current is the STATE flag (exactly one per listing, DB-enforced below);
    # superseded_by is the audit POINTER. They are split because a partial unique
    # constraint cannot be deferred in PostgreSQL and superseded_by points at the
    # NEW edge — the apply sequence is demote-old → insert-new → link-old, and the
    # uniqueness must hold at every statement (Codex CR-002).
    is_current = models.BooleanField(default=True)
    superseded_by = models.ForeignKey(
        "self", on_delete=models.PROTECT, related_name="supersedes", null=True, blank=True
    )

    class Meta:
        db_table = "listing_resolution"
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        grain="none",
                        product_family__isnull=True,
                        product_model__isnull=True,
                        product_variant__isnull=True,
                    )
                    | models.Q(
                        grain="family",
                        product_family__isnull=False,
                        product_model__isnull=True,
                        product_variant__isnull=True,
                    )
                    | models.Q(
                        grain="model",
                        product_family__isnull=True,
                        product_model__isnull=False,
                        product_variant__isnull=True,
                    )
                    | models.Q(
                        grain="variant",
                        product_family__isnull=True,
                        product_model__isnull=True,
                        product_variant__isnull=False,
                    )
                ),
                name="listing_resolution_grain_target_coherent",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(grain="none")
                    | (~models.Q(method="") & models.Q(confidence__isnull=False))
                ),
                name="listing_resolution_accept_carries_method",
            ),
            # DR-010/C.3.3: exactly ONE current resolution per listing, enforced
            # in the database, not by query discipline (Codex CR-002).
            models.UniqueConstraint(
                fields=["listing"],
                condition=models.Q(is_current=True),
                name="listing_resolution_one_current",
            ),
            models.CheckConstraint(
                condition=models.Q(is_current=False) | models.Q(superseded_by__isnull=True),
                name="listing_resolution_current_not_superseded",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["listing", "-resolved_at"], name="listing_res_recent"),
        ]

    def __str__(self) -> str:
        return f"listing {self.listing_id} → {self.grain} ({self.method or 'unresolved'})"
```

Export from `src/hw_radar/catalog/models/__init__.py` (add to imports and `__all__`, alphabetical): `ListingResolution`, `ResolutionGrain` (from `base`), `ResolutionMethod`.

Register in `src/hw_radar/catalog/admin.py` (read the file first; follow its existing registration style — the design doc names Django admin as the MS-1b review-queue inspection surface, so the edge table is read-only):

```python
@admin.register(ListingResolution)
class ListingResolutionAdmin(admin.ModelAdmin):
    list_display = (
        "listing", "grain", "method", "confidence", "matcher_version",
        "resolved_at", "superseded_by",
    )
    list_filter = ("grain", "method")
    ordering = ("-resolved_at",)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: ListingResolution | None = None
    ) -> bool:
        return False  # append-only audit trail (DR-010): admin is a window, not an editor

    def has_delete_permission(
        self, request: HttpRequest, obj: ListingResolution | None = None
    ) -> bool:
        return False
```

(`from django.http import HttpRequest` for the annotations, matching strict typing.)

- [ ] **Step 4: Generate and review the migration**

```bash
uv run python manage.py makemigrations catalog --name resolution
```

Review `src/hw_radar/catalog/migrations/0006_resolution.py` — expected operations, nothing more:
1. `AlterField` on `productvariant.condition` (new `for_parts` choice — choices-only, no DDL impact).
2. Four `AddField` on `listing` (`product_family`, `product_model`, `resolution_grain`, `resolution_confidence`) — all nullable-or-defaulted (expand/contract safe).
3. `CreateModel ListingResolution` + `AddConstraint` ×4 (grain/target coherence, accept-carries-method, **one-current unique**, current-not-superseded) + `AddIndex` ×1.

If makemigrations emits anything else (e.g. spurious `AlterField`s), investigate before committing.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/db/test_resolution_models.py tests/db/test_identity.py tests/db/test_migrations.py -q`
Expected: all PASS (existing migration tests must survive 0006).

- [ ] **Step 6: Fix pass, full gate, commit**

```bash
uv run ruff format . && uv run ruff check . --fix
uv run python -m scripts.check
git add src/hw_radar/catalog tests/db/test_resolution_models.py
git commit -m "feat(catalog): listing_resolution edge table + denormalized resolution fields (C.3.3)"
```

---

### Task 6: Match ladder rungs 0–2 (pure)

**Files:**
- Create: `src/hw_radar/matching/ladder.py`
- Test: `tests/unit/test_ladder.py`

**Interfaces:**
- Consumes: `types.*`, `vocab.ExtractedAttributes` shape.
- Produces: `ladder.HardAttrs`, `ladder.TargetRef`, `ladder.AliasHit`, `ladder.PriorResolution`, `ladder.Outcome`, `ladder.Verdict`, `ladder.contradictions(extracted, catalog) -> list[str]`, `ladder.brands_consistent(a, b) -> bool`, `ladder.decide(extracted, candidates, prior, alias_hits, decoded) -> Verdict`. Task 7's resolver consumes every one of these names exactly.

- [ ] **Step 1: Write the failing golden-table tests**

```python
# tests/unit/test_ladder.py
"""C.3.2 ladder golden verdict table — pure, no DB. Each case is one spec rule."""

from hw_radar.matching import ladder
from hw_radar.matching.types import (
    Attribute,
    DecodeResult,
    ExtractedAttributes,
    Grain,
    MpnCandidate,
    Provenance,
    TokenKind,
)

_TB = 1_000_000_000_000


def _attr[T](value: T) -> Attribute[T]:
    return Attribute(value=value, confidence=0.9, layer="test")


def _cand(token: str, kind: TokenKind = TokenKind.MANUFACTURER_MPN) -> MpnCandidate:
    return MpnCandidate(raw=token, normalized=token, kind=kind, confidence=0.9)


_MODEL_TARGET = ladder.TargetRef(grain=Grain.MODEL, family_id=1, model_id=10)
_SPEC_16TB = ladder.HardAttrs(capacity_bytes=16 * _TB, interface="sata")


def _model_hit(
    source_kind: str = "catalog_authoritative",
    alias_type: str = "mpn",
    brand: str = "seagate",
    hard: ladder.HardAttrs = _SPEC_16TB,
    target: ladder.TargetRef = _MODEL_TARGET,
    candidate_kind: TokenKind = TokenKind.MANUFACTURER_MPN,
    candidate_vendor: str = "seagate",
) -> ladder.AliasHit:
    return ladder.AliasHit(
        target=target, source_kind=source_kind, alias_type=alias_type,
        brand=brand, hard_attrs=hard,
        candidate_kind=candidate_kind, candidate_vendor=candidate_vendor,
    )


def test_rung0_clean_reobservation_inherits() -> None:
    prior = ladder.PriorResolution(target=_MODEL_TARGET, confidence=0.98, hard_attrs=_SPEC_16TB)
    extracted = ExtractedAttributes(capacity_bytes=_attr(16 * _TB))
    v = ladder.decide(extracted, [], prior, [], None)
    assert v.outcome is ladder.Outcome.ACCEPT
    assert v.rung == 0 and v.method == "source_alias"
    assert v.target == _MODEL_TARGET and v.confidence == 0.98


def test_rung0_contradiction_forces_review_survives_relist_abuse() -> None:
    prior = ladder.PriorResolution(target=_MODEL_TARGET, confidence=0.98, hard_attrs=_SPEC_16TB)
    extracted = ExtractedAttributes(capacity_bytes=_attr(14 * _TB))
    v = ladder.decide(extracted, [], prior, [], None)
    assert v.outcome is ladder.Outcome.REVIEW
    assert v.rung == 0
    assert v.evidence["veto"] == ["capacity"]


def test_rung1_exact_alias_accepts_at_alias_grain() -> None:
    extracted = ExtractedAttributes(
        brand=_attr("seagate"), capacity_bytes=_attr(16 * _TB)
    )
    v = ladder.decide(extracted, [_cand("st16000nm001g")], None, [_model_hit()], None)
    assert v.outcome is ladder.Outcome.ACCEPT
    assert v.rung == 1 and v.method == "exact_alias"
    assert v.grain is Grain.MODEL and v.confidence == 0.98


def test_rung1_capacity_contradiction_never_merges() -> None:
    extracted = ExtractedAttributes(capacity_bytes=_attr(14 * _TB))
    v = ladder.decide(extracted, [_cand("st16000nm001g")], None, [_model_hit()], None)
    assert v.outcome is ladder.Outcome.REVIEW
    assert v.evidence["veto"] == ["capacity"]


def test_rung1_capacity_tolerance_absorbs_rounding_only() -> None:
    almost = ExtractedAttributes(
        capacity_bytes=_attr(16_000_000_000_000 - 1_000_000)  # rounding noise
    )
    v = ladder.decide(almost, [_cand("st16000nm001g")], None, [_model_hit()], None)
    assert v.outcome is ladder.Outcome.ACCEPT


def test_rung1_conflicting_targets_go_to_review() -> None:
    other = ladder.TargetRef(grain=Grain.MODEL, family_id=2, model_id=20)
    v = ladder.decide(
        ExtractedAttributes(), [_cand("dellpn123")], None,
        [_model_hit(), _model_hit(target=other)], None,
    )
    assert v.outcome is ladder.Outcome.REVIEW


def test_rung1_oem_fanout_within_one_family_collapses_to_family() -> None:
    sibling = ladder.TargetRef(grain=Grain.MODEL, family_id=1, model_id=11)
    hits = [
        _model_hit(alias_type="oem_pn", source_kind="listing_derived"),
        _model_hit(alias_type="oem_pn", source_kind="listing_derived", target=sibling),
    ]
    v = ladder.decide(ExtractedAttributes(), [_cand("x477ar6", TokenKind.OEM_PN)], None, hits, None)
    assert v.outcome is ladder.Outcome.ACCEPT
    assert v.grain is Grain.FAMILY
    assert v.target is not None and v.target.family_id == 1


def test_rung1_brand_mismatch_filters_the_hit() -> None:
    extracted = ExtractedAttributes(brand=_attr("toshiba"))
    v = ladder.decide(extracted, [_cand("st16000nm001g")], None, [_model_hit()], None)
    assert v.outcome is ladder.Outcome.NONE  # hit filtered; no decode supplied


def test_rung1_brandless_unknown_code_collision_reviews_never_accepts() -> None:
    # CR-003: a bare normalized-text collision from an unknown-shaped token with
    # NO brand evidence must not enter the price history as an exact alias.
    hit = _model_hit(candidate_kind=TokenKind.UNKNOWN_CODE, candidate_vendor="")
    v = ladder.decide(
        ExtractedAttributes(), [_cand("abc123xyz99", TokenKind.UNKNOWN_CODE)], None, [hit], None
    )
    assert v.outcome is ladder.Outcome.REVIEW
    assert v.evidence["no_brand_evidence"] is True


def test_rung1_vendor_shaped_token_is_brand_evidence_without_title_brand() -> None:
    # 'ST16000NM001G' implies Seagate by shape — that satisfies the C.3.2
    # 'brand + MPN' trigger even when the title never says 'seagate'.
    v = ladder.decide(
        ExtractedAttributes(), [_cand("st16000nm001g")], None, [_model_hit()], None
    )
    assert v.outcome is ladder.Outcome.ACCEPT
    assert v.rung == 1


def test_brand_equivalence_wd_hgst_sandisk() -> None:
    assert ladder.brands_consistent("western_digital", "hgst")
    assert ladder.brands_consistent("hgst", "western_digital")
    assert not ladder.brands_consistent("seagate", "toshiba")
    assert ladder.brands_consistent(None, "seagate")  # unknown never vetoes


def test_rung2_decode_attaches_at_family_provisional() -> None:
    decoded = DecodeResult(
        vendor="seagate", family_name="exos", capacity_bytes=16 * _TB,
        generation="g", provenance=Provenance.CORROBORATED_COMMUNITY, rule="st:nm",
    )
    extracted = ExtractedAttributes(capacity_bytes=_attr(16 * _TB))
    v = ladder.decide(extracted, [_cand("st16000nm999x")], None, [], decoded)
    assert v.outcome is ladder.Outcome.ACCEPT
    assert v.rung == 2 and v.method == "mpn_decode"
    assert v.grain is Grain.FAMILY
    assert v.target is not None and v.target.family_key == ("seagate", "exos")
    assert v.confidence == 0.85
    assert v.evidence["provisional"] is True


def test_rung2_decoder_vs_title_capacity_conflict_reviews() -> None:
    decoded = DecodeResult(
        vendor="seagate", family_name="exos", capacity_bytes=16 * _TB,
        generation=None, provenance=Provenance.CORROBORATED_COMMUNITY, rule="st:nm",
    )
    extracted = ExtractedAttributes(capacity_bytes=_attr(14 * _TB))
    v = ladder.decide(extracted, [_cand("st16000nm999x")], None, [], decoded)
    assert v.outcome is ladder.Outcome.REVIEW


def test_no_signals_yields_none_with_hypothesis() -> None:
    v = ladder.decide(ExtractedAttributes(), [_cand("st16000nm001g")], None, [], None)
    assert v.outcome is ladder.Outcome.NONE
    assert v.grain is Grain.NONE
    assert v.evidence["mpn_hypothesis"] == "st16000nm001g"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_ladder.py -q`
Expected: FAIL — module not found

- [ ] **Step 3: Implement ladder.py**

```python
# src/hw_radar/matching/ladder.py
"""Match ladder rungs 0–2 + the hard-attribute contradiction veto (C.3.2) — pure.

The resolver feeds DB state in as plain data (PriorResolution / AliasHit /
HardAttrs); decide() does no I/O, so the golden verdict table runs without a
DB. Only rungs 0–2 auto-accept. The veto runs at EVERY rung — an exact alias
hit that contradicts extracted capacity goes to review, never into the price
history (ADR-0019: false merges poison the moat asymmetrically; missed matches
just queue).

Confidence constants are OQ-provisional tunables; ADR-0016 settings-row
versions arrive with the rung-3/occurrence thresholds at MS-1c."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from hw_radar.matching.types import (
    DecodeResult,
    ExtractedAttributes,
    Grain,
    MpnCandidate,
    Provenance,
    TokenKind,
)

CONFIDENCE_BY_SOURCE_KIND: dict[str, float] = {
    "catalog_authoritative": 0.98,
    "manual": 0.95,
    "listing_derived": 0.85,
}
CONFIDENCE_BY_PROVENANCE: dict[Provenance, float] = {
    Provenance.VENDOR_OFFICIAL: 0.92,
    Provenance.CORROBORATED_COMMUNITY: 0.85,
    Provenance.INFERRED: 0.75,
}
OEM_FAMILY_FANOUT_CONFIDENCE = 0.8
# Relative tolerance absorbing decimal-vs-marketing rounding (16TB vs 16000GB),
# NOT 14-vs-16 mislabels.
CAPACITY_TOLERANCE = 0.01

# One corporate lineage: WD absorbed HGST; the Jan-2026 "Optimus" rebrand moved
# WD-branded SSD lines under the SanDisk name with unchanged MPNs (spec C.3.1).
# Equivalence is a GATE only — it never merges without an MPN/alias hit.
_BRAND_EQUIV: tuple[frozenset[str], ...] = (
    frozenset({"western_digital", "hgst", "sandisk"}),
)


@dataclass(frozen=True)
class HardAttrs:
    """Catalog-side veto fields (from drive_spec / family agreement set).
    None = unknown on the catalog side → that field cannot veto."""

    capacity_bytes: int | None = None
    interface: str | None = None
    form_factor: str | None = None
    sector_format: str | None = None
    security: str | None = None


@dataclass(frozen=True)
class TargetRef:
    """Ladder-side identity reference. family_id is populated even for
    model/variant grains (enables the OEM family collapse); family_key names a
    not-yet-materialized provisional family for rung 2 — the resolver
    get_or_creates it (vendor, family_name)."""

    grain: Grain
    family_id: int | None = None
    model_id: int | None = None
    variant_id: int | None = None
    family_key: tuple[str, str] | None = None


@dataclass(frozen=True)
class AliasHit:
    target: TargetRef
    source_kind: str
    alias_type: str
    brand: str | None
    hard_attrs: HardAttrs
    # The candidate that produced this hit (Codex CR-003): rung-1 auto-accept is
    # 'brand + full normalized MPN' (C.3.2), so the ladder needs to know what
    # KIND of token collided and what vendor its shape implies.
    candidate_kind: TokenKind = TokenKind.MANUFACTURER_MPN
    candidate_vendor: str = ""
    candidate_structured: bool = False


@dataclass(frozen=True)
class PriorResolution:
    target: TargetRef
    confidence: float
    hard_attrs: HardAttrs


class Outcome(StrEnum):
    ACCEPT = "accept"
    REVIEW = "review"
    NONE = "none"


@dataclass(frozen=True)
class Verdict:
    outcome: Outcome
    grain: Grain
    rung: int | None = None
    method: str = ""
    target: TargetRef | None = None
    confidence: float | None = None
    evidence: dict[str, object] = field(default_factory=dict)


def contradictions(extracted: ExtractedAttributes, catalog: HardAttrs) -> list[str]:
    """Hard-attribute veto (C.3.2): fields where BOTH sides are known and disagree."""

    vetoed: list[str] = []
    if extracted.capacity_bytes is not None and catalog.capacity_bytes is not None:
        a, b = extracted.capacity_bytes.value, catalog.capacity_bytes
        if abs(a - b) > CAPACITY_TOLERANCE * max(a, b):
            vetoed.append("capacity")
    for name in ("interface", "form_factor", "sector_format", "security"):
        extracted_attr = getattr(extracted, name)
        catalog_value = getattr(catalog, name)
        if (
            extracted_attr is not None
            and catalog_value is not None
            and extracted_attr.value != catalog_value
        ):
            vetoed.append(name)
    return vetoed


def brands_consistent(extracted_brand: str | None, target_brand: str | None) -> bool:
    if not extracted_brand or not target_brand or extracted_brand == target_brand:
        return True
    return any(
        extracted_brand in group and target_brand in group for group in _BRAND_EQUIV
    )


def _hypothesis(candidates: Sequence[MpnCandidate]) -> str:
    for candidate in candidates:
        if candidate.kind is TokenKind.MANUFACTURER_MPN:
            return candidate.normalized
    return candidates[0].normalized if candidates else ""


def decide(
    extracted: ExtractedAttributes,
    candidates: Sequence[MpnCandidate],
    prior: PriorResolution | None,
    alias_hits: Sequence[AliasHit],
    decoded: DecodeResult | None,
) -> Verdict:
    evidence: dict[str, object] = {"mpn_hypothesis": _hypothesis(candidates)}
    if decoded is not None:
        evidence["vendor_hint"] = decoded.vendor

    # Rung 0 — re-observation: inherit after RE-RUNNING the veto (survives
    # relist/edit abuse — C.3.2 requires the check on every re-observation).
    if prior is not None:
        veto = contradictions(extracted, prior.hard_attrs)
        if veto:
            return Verdict(
                Outcome.REVIEW, Grain.NONE, rung=0, evidence={**evidence, "veto": veto}
            )
        return Verdict(
            Outcome.ACCEPT,
            prior.target.grain,
            rung=0,
            method="source_alias",
            target=prior.target,
            confidence=prior.confidence,
            evidence=evidence,
        )

    # Rung 1 — exact alias against grain-tagged product_alias. The C.3.2 trigger
    # is 'brand + full normalized MPN': a bare text collision is NOT enough
    # (Codex CR-003). Brand evidence = extracted brand, OR a vendor-shaped MPN
    # token whose implied vendor agrees with the target, OR a structured-field
    # MPN (merchant-asserted). Absent all three → review, never auto-accept.
    brand = extracted.brand.value if extracted.brand is not None else None
    viable = [h for h in alias_hits if brands_consistent(brand, h.brand)]
    if viable:

        def has_brand_evidence(hit: AliasHit) -> bool:
            if brand is not None:
                return True  # extracted brand, already filtered consistent
            if hit.candidate_structured:
                return True
            return bool(hit.candidate_vendor) and brands_consistent(
                hit.candidate_vendor, hit.brand
            )

        targets = {
            (h.target.grain, h.target.family_id, h.target.model_id, h.target.variant_id)
            for h in viable
        }
        if len(targets) == 1:
            best = max(
                viable, key=lambda h: CONFIDENCE_BY_SOURCE_KIND.get(h.source_kind, 0.5)
            )
            veto = contradictions(extracted, best.hard_attrs)
            if veto:
                return Verdict(
                    Outcome.REVIEW, Grain.NONE, rung=1, evidence={**evidence, "veto": veto}
                )
            if not has_brand_evidence(best):
                return Verdict(
                    Outcome.REVIEW,
                    Grain.NONE,
                    rung=1,
                    evidence={**evidence, "no_brand_evidence": True},
                )
            return Verdict(
                Outcome.ACCEPT,
                best.target.grain,
                rung=1,
                method="exact_alias",
                target=best.target,
                confidence=CONFIDENCE_BY_SOURCE_KIND.get(best.source_kind, 0.5),
                evidence=evidence,
            )
        families = {h.target.family_id for h in viable}
        if (
            len(families) == 1
            and None not in families
            and all(h.alias_type == "oem_pn" for h in viable)
        ):
            # OEM N:N fan-out inside one family → attach at family grain (the
            # OEM cross-reference verdict: an OEM PN can never assert a model).
            clean = [h for h in viable if not contradictions(extracted, h.hard_attrs)]
            if clean:
                family_id = next(iter(families))
                return Verdict(
                    Outcome.ACCEPT,
                    Grain.FAMILY,
                    rung=1,
                    method="exact_alias",
                    target=TargetRef(grain=Grain.FAMILY, family_id=family_id),
                    confidence=OEM_FAMILY_FANOUT_CONFIDENCE,
                    evidence={**evidence, "oem_fanout": len(viable)},
                )
        return Verdict(
            Outcome.REVIEW,
            Grain.NONE,
            rung=1,
            evidence={**evidence, "conflicting_targets": len(targets)},
        )

    # Rung 2 — valid grammar decode, no catalog hit → family grain, provisional.
    if decoded is not None and decoded.family_name:
        if (
            extracted.capacity_bytes is not None
            and decoded.capacity_bytes is not None
            and abs(extracted.capacity_bytes.value - decoded.capacity_bytes)
            > CAPACITY_TOLERANCE
            * max(extracted.capacity_bytes.value, decoded.capacity_bytes)
        ):
            return Verdict(
                Outcome.REVIEW,
                Grain.NONE,
                rung=2,
                evidence={
                    **evidence,
                    "veto": ["capacity"],
                    "decoder_capacity": decoded.capacity_bytes,
                },
            )
        return Verdict(
            Outcome.ACCEPT,
            Grain.FAMILY,
            rung=2,
            method="mpn_decode",
            target=TargetRef(
                grain=Grain.FAMILY, family_key=(decoded.vendor, decoded.family_name)
            ),
            confidence=CONFIDENCE_BY_PROVENANCE[decoded.provenance],
            evidence={
                **evidence,
                "provisional": True,
                "provenance": decoded.provenance,
                "rule": decoded.rule,
            },
        )

    return Verdict(Outcome.NONE, Grain.NONE, evidence=evidence)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_ladder.py -q`
Expected: all PASS

- [ ] **Step 5: Fix pass and commit**

```bash
uv run ruff format . && uv run ruff check . --fix
uv run basedpyright src/hw_radar/matching tests/unit/test_ladder.py
git add src/hw_radar/matching/ladder.py tests/unit/test_ladder.py
git commit -m "feat(matching): rung 0-2 conservative ladder with contradiction veto (C.3.2)"
```

---

### Task 7: CatalogResolver + FR-003 upgrade + parity test

**Files:**
- Create: `src/hw_radar/matching/resolver.py`
- Test: `tests/db/test_resolver.py`
- Modify: `tests/db/test_identity.py` (upgrade `test_recert_and_new_are_one_model_two_variants` in place — the spec §20 traceability matrix names this exact test path, so it must not move)

**Interfaces:**
- Consumes: everything from Tasks 1–6 plus `Listing`, `ListingResolution`, `ProductAlias`, `Category` (slug `drive`, seeded in 0001).
- Produces: `resolver.CatalogResolver` implementing `acquisition.contracts.ListingResolver` (`resolve_listing(listing_id: int) -> None`). Task 9 wires it into the poller.

- [ ] **Step 1: Write the failing tests**

```python
# tests/db/test_resolver.py
"""CatalogResolver end-to-end: rung flows, veto, no-spam re-observation, variant
on demand, provisional families, lazy aliases, error path, and the ADR-0019
rule-1 normalizer PARITY test (the CI guard for the single-normalizer invariant)."""

import pytest

from hw_radar.catalog.models import (
    AliasSourceKind,
    AliasType,
    Condition,
    DriveSpec,
    Listing,
    ListingResolution,
    Manufacturer,
    MediaType,
    ProductAlias,
    ProductFamily,
    ProductModel,
    ProductVariant,
    ResolutionGrain,
    ResolutionMethod,
    RetentionClass,
    SourceSite,
)
from hw_radar.matching import vocab
from hw_radar.matching.normalize import normalize_alias_text
from hw_radar.matching.resolver import CatalogResolver


@pytest.fixture
def site(db: None) -> SourceSite:
    return SourceSite.objects.create(name="Demo Recert", normalized_name="demorecert")


@pytest.fixture
def seagate(db: None) -> Manufacturer:
    return Manufacturer.objects.create(name="Seagate", normalized_name="seagate")


@pytest.fixture
def exos_16tb(seagate: Manufacturer) -> ProductModel:
    model = ProductModel.objects.create(
        manufacturer=seagate,
        model_number="ST16000NM001G",
        normalized_model_number="st16000nm001g",
    )
    DriveSpec.objects.create(
        product_model=model, media_type=MediaType.HDD, capacity_tb="16.000", interface="SATA 6Gb/s"
    )
    # Catalog alias seeded THROUGH the shared normalizer, from a deliberately
    # messy catalog-side rendering — this is the parity contract in action.
    ProductAlias.objects.create(
        alias_type=AliasType.MPN,
        normalized_alias_text=normalize_alias_text("ST16000NM-001G "),
        product_model=model,
        source_kind=AliasSourceKind.CATALOG_AUTHORITATIVE,
    )
    return model


def _listing(site: SourceSite, key: str, title: str) -> Listing:
    return Listing.objects.create(
        source_site=site,
        source_listing_key=key,
        canonical_url=f"https://example.test/{key}",
        url_hash=key,
        title_raw=title,
        retention_class=RetentionClass.MERCHANT_FACT,
    )


def test_rung1_parity_exact_alias_resolves_to_variant_on_demand(
    site: SourceSite, exos_16tb: ProductModel
) -> None:
    listing = _listing(
        site, "l1", "Seagate Exos X16 16TB ST16000NM001G Factory Recertified SATA"
    )
    CatalogResolver().resolve_listing(listing.pk)
    listing.refresh_from_db()
    # Model grain + known condition → variant created on demand (C.3.3).
    assert listing.resolution_grain == ResolutionGrain.VARIANT
    assert listing.product_variant is not None
    assert listing.product_variant.product_model == exos_16tb
    assert listing.product_variant.condition == Condition.RECERTIFIED
    assert listing.product_family is None and listing.product_model is None  # lower grains NULL
    edge = listing.resolutions.get(superseded_by__isnull=True)
    assert edge.method == ResolutionMethod.EXACT_ALIAS
    assert edge.grain == ResolutionGrain.VARIANT
    assert listing.title_normalized  # N1 output persisted


def test_recert_and_new_listings_make_one_model_two_variants(
    site: SourceSite, exos_16tb: ProductModel
) -> None:
    # FR-003 MS-1 acceptance, resolver-driven (also upgraded in test_identity.py).
    resolver = CatalogResolver()
    a = _listing(site, "a", "Seagate Exos 16TB ST16000NM001G Factory Recertified")
    b = _listing(site, "b", "Seagate Exos 16TB ST16000NM001G Brand New Sealed")
    resolver.resolve_listing(a.pk)
    resolver.resolve_listing(b.pk)
    assert ProductModel.objects.count() == 1
    assert ProductVariant.objects.filter(product_model=exos_16tb).count() == 2


def test_rung0_reobservation_appends_no_duplicate_edge(
    site: SourceSite, exos_16tb: ProductModel
) -> None:
    listing = _listing(site, "l2", "Seagate Exos 16TB ST16000NM001G Recertified")
    resolver = CatalogResolver()
    resolver.resolve_listing(listing.pk)
    resolver.resolve_listing(listing.pk)  # routine re-poll: veto re-runs, NO new edge
    assert listing.resolutions.count() == 1


def test_capacity_contradiction_goes_to_review_not_price_history(
    site: SourceSite, exos_16tb: ProductModel
) -> None:
    listing = _listing(site, "l3", "Seagate 14TB ST16000NM001G Recertified")
    CatalogResolver().resolve_listing(listing.pk)
    listing.refresh_from_db()
    assert listing.resolution_grain == ResolutionGrain.NONE
    assert listing.product_variant is None
    edge = listing.resolutions.get()
    assert edge.grain == ResolutionGrain.NONE
    assert edge.evidence["outcome"] == "review"
    assert edge.evidence["veto"] == ["capacity"]


def test_rung2_decode_materializes_provisional_family_once(
    site: SourceSite, seagate: Manufacturer
) -> None:
    resolver = CatalogResolver()
    a = _listing(site, "l4", "Seagate 20TB ST20000NM007D Recertified Enterprise")
    b = _listing(site, "l5", "Seagate 20TB ST20000NM007D Renewed")
    resolver.resolve_listing(a.pk)
    resolver.resolve_listing(b.pk)
    a.refresh_from_db()
    assert a.resolution_grain == ResolutionGrain.FAMILY
    assert a.product_family is not None and a.product_family.normalized_name == "exos"
    assert ProductFamily.objects.filter(normalized_name="exos").count() == 1  # reused
    edge = a.resolutions.get(superseded_by__isnull=True)
    assert edge.method == ResolutionMethod.MPN_DECODE
    assert edge.evidence["provisional"] is True


def test_dual_labeled_listing_emits_learned_oem_alias(
    site: SourceSite, seagate: Manufacturer
) -> None:
    hgst = Manufacturer.objects.create(name="HGST", normalized_name="hgst")
    model = ProductModel.objects.create(
        manufacturer=hgst,
        model_number="HUS724040ALS640",
        normalized_model_number="hus724040als640",
    )
    ProductAlias.objects.create(
        alias_type=AliasType.MPN,
        normalized_alias_text="hus724040als640",
        product_model=model,
        source_kind=AliasSourceKind.CATALOG_AUTHORITATIVE,
    )
    listing = _listing(site, "l6", "NetApp X477A-R6 4TB 7.2K SAS HDD HUS724040ALS640")
    CatalogResolver().resolve_listing(listing.pk)
    learned = ProductAlias.objects.get(
        alias_type=AliasType.OEM_PN, normalized_alias_text="x477ar6"
    )
    assert learned.product_model == model  # model grain max — never variant (rule 7)
    assert learned.source_kind == AliasSourceKind.LISTING_DERIVED


def test_matcher_crash_writes_error_edge_and_never_raises(
    site: SourceSite, monkeypatch: pytest.MonkeyPatch
) -> None:
    listing = _listing(site, "l7", "whatever 16TB")

    def boom(title: str) -> object:
        raise RuntimeError("vocab exploded")

    monkeypatch.setattr(vocab, "extract", boom)
    CatalogResolver().resolve_listing(listing.pk)  # must not raise (C.3)
    edge = listing.resolutions.get()
    assert edge.grain == ResolutionGrain.NONE
    assert "error" in edge.evidence


def test_unresolved_repoll_appends_no_duplicate_none_edge(site: SourceSite) -> None:
    listing = _listing(site, "l8", "mystery enterprise drive")
    resolver = CatalogResolver()
    resolver.resolve_listing(listing.pk)
    resolver.resolve_listing(listing.pk)
    assert listing.resolutions.count() == 1  # unchanged NONE outcome: no spam


def test_crash_after_accepted_resolution_records_error_without_demotion(
    site: SourceSite, exos_16tb: ProductModel, monkeypatch: pytest.MonkeyPatch
) -> None:
    listing = _listing(site, "l9", "Seagate Exos 16TB ST16000NM001G Recertified")
    resolver = CatalogResolver()
    resolver.resolve_listing(listing.pk)
    listing.refresh_from_db()
    assert listing.resolution_grain == ResolutionGrain.VARIANT

    def boom(title: str) -> object:
        raise RuntimeError("transient matcher bug")

    monkeypatch.setattr(vocab, "extract", boom)
    resolver.resolve_listing(listing.pk)
    listing.refresh_from_db()
    # CR-001: the crash is IN the ledger, the accepted state is NOT demoted.
    assert listing.resolution_grain == ResolutionGrain.VARIANT
    assert listing.product_variant is not None
    current = listing.resolutions.get(is_current=True)
    assert "error" in current.evidence
    assert current.evidence["denorm_preserved"] is True
    assert listing.resolutions.count() == 2


def test_repeated_identical_crash_does_not_spam_error_edges(
    site: SourceSite, monkeypatch: pytest.MonkeyPatch
) -> None:
    listing = _listing(site, "l10", "whatever 16TB")

    def boom(title: str) -> object:
        raise RuntimeError("same bug every poll")

    monkeypatch.setattr(vocab, "extract", boom)
    resolver = CatalogResolver()
    resolver.resolve_listing(listing.pk)
    resolver.resolve_listing(listing.pk)
    assert listing.resolutions.count() == 1  # identical error: no spam (CR-001)


def test_apply_failure_falls_back_to_error_edge(
    site: SourceSite, exos_16tb: ProductModel, monkeypatch: pytest.MonkeyPatch
) -> None:
    # CR-001: a failure INSIDE the write path still leaves a ledger trace via
    # the fallback error-edge write (which skips _materialize by design).
    from hw_radar.matching import resolver as resolver_module

    listing = _listing(site, "l11", "Seagate Exos 16TB ST16000NM001G Recertified")

    def broken_materialize(extracted: object, verdict: object) -> object:
        raise RuntimeError("materialize exploded")

    monkeypatch.setattr(resolver_module, "_materialize", broken_materialize)
    CatalogResolver().resolve_listing(listing.pk)  # must not raise
    edge = listing.resolutions.get(is_current=True)
    assert edge.grain == ResolutionGrain.NONE
    assert "error" in edge.evidence


def test_veto_on_reobservation_demotes_and_keeps_one_current(
    site: SourceSite, exos_16tb: ProductModel
) -> None:
    # CR-002 + C.3.2 relist/edit abuse: the transition appends exactly one new
    # current edge and the evidence-based demotion clears the denorm state.
    listing = _listing(site, "l12", "Seagate Exos 16TB ST16000NM001G Recertified")
    resolver = CatalogResolver()
    resolver.resolve_listing(listing.pk)
    Listing.objects.filter(pk=listing.pk).update(
        title_raw="Seagate Exos 14TB ST16000NM001G Recertified"
    )
    resolver.resolve_listing(listing.pk)
    listing.refresh_from_db()
    assert listing.resolution_grain == ResolutionGrain.NONE
    assert listing.product_variant is None
    assert listing.resolutions.count() == 2
    assert listing.resolutions.filter(is_current=True).count() == 1
    current = listing.resolutions.get(is_current=True)
    assert current.evidence["outcome"] == "review"
```

Also upgrade the FR-003 test **in place** in `tests/db/test_identity.py` — replace the body of `test_recert_and_new_are_one_model_two_variants` (keep the name and file; the spec traceability matrix points at this path):

```python
def test_recert_and_new_are_one_model_two_variants(exos_16tb: ProductModel) -> None:
    # FR-003 MS-1 acceptance, resolver-driven since MS-1b: a recert and a new
    # listing of the same drive resolve to ONE product_model, TWO variants.
    from hw_radar.catalog.models import (
        AliasSourceKind,
        AliasType,
        DriveSpec,
        Listing,
        MediaType,
        ProductAlias,
        RetentionClass,
        SourceSite,
    )
    from hw_radar.matching.resolver import CatalogResolver

    DriveSpec.objects.create(
        product_model=exos_16tb, media_type=MediaType.HDD, capacity_tb="16.000"
    )
    ProductAlias.objects.create(
        alias_type=AliasType.MPN,
        normalized_alias_text="st16000nm001g",
        product_model=exos_16tb,
        source_kind=AliasSourceKind.CATALOG_AUTHORITATIVE,
    )
    site = SourceSite.objects.create(name="FR3", normalized_name="fr3")
    resolver = CatalogResolver()
    for key, title in (
        ("r", "Seagate Exos 16TB ST16000NM001G Factory Recertified"),
        ("n", "Seagate Exos 16TB ST16000NM001G Brand New"),
    ):
        listing = Listing.objects.create(
            source_site=site,
            source_listing_key=key,
            canonical_url=f"https://example.test/{key}",
            url_hash=key,
            title_raw=title,
            retention_class=RetentionClass.MERCHANT_FACT,
        )
        resolver.resolve_listing(listing.pk)
    assert ProductModel.objects.count() == 1
    assert ProductVariant.objects.filter(product_model=exos_16tb).count() == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/db/test_resolver.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'hw_radar.matching.resolver'`

- [ ] **Step 3: Implement resolver.py**

```python
# src/hw_radar/matching/resolver.py
"""DB-facing resolver service (spec C.3.3): runs the pure ladder against catalog
state and writes append-only listing_resolution edges. Implements
acquisition.contracts.ListingResolver; the poller injects it from MS-1b on.

Invariants:
- NEVER gates ingestion: any internal failure — ladder OR apply/DB — becomes a
  grain=none error edge (fallback write in a fresh transaction); pipeline
  .run_source keeps its belt-and-braces catch as the last resort.
- Error edges never demote: a matcher crash appends an audit edge but PRESERVES
  the listing's denormalized accepted state; evidence-based review/none
  outcomes clear it (the veto's job is keeping the listing out of the trusted
  read path).
- Exactly one current edge per listing, DB-enforced (is_current unique) and
  serialized via select_for_update on the listing row; the apply order is
  demote-old → insert-new → link-old.
- No per-poll edge spam: unchanged rung-0 accepts, unchanged misses, and
  REPEATED IDENTICAL errors write no new edge; distinct new errors do.
- Rung 0 prior = the listing's denorm fields (last accepted state): MS-1a
  persist upserts on (source_site, source_listing_key), so a re-observation IS
  the same row.
- Single normalizer: all alias joins ride matching.normalize (ADR-0019 rule 1).
- Lazy alias learning (rule 7): dual-labeled listings emit listing_derived OEM
  aliases at MODEL grain max; house SKUs become source-local aliases."""

from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from hw_radar.catalog.models import (
    AliasSourceKind,
    AliasType,
    Category,
    DriveSpec,
    Listing,
    ListingResolution,
    Manufacturer,
    Packaging,
    ProductAlias,
    ProductFamily,
    ProductModel,
    ProductVariant,
    RecertChannel,
    ResolutionGrain,
    WarrantyChannel,
)
from hw_radar.matching import MATCHER_VERSION, ladder, mpn, vocab
from hw_radar.matching.grammars import decode
from hw_radar.matching.normalize import canonicalize_title
from hw_radar.matching.types import (
    DecodeResult,
    ExtractedAttributes,
    Grain,
    MpnCandidate,
    TokenKind,
)

logger = logging.getLogger(__name__)

_TB = Decimal(1_000_000_000_000)
_ALIAS_KINDS = (
    TokenKind.MANUFACTURER_MPN,
    TokenKind.OEM_PN,
    TokenKind.HOUSE_SKU,
    TokenKind.UNKNOWN_CODE,
)


def _spec_of(model: ProductModel | None) -> DriveSpec | None:
    if model is None:
        return None
    try:
        return model.drive_spec
    except DriveSpec.DoesNotExist:
        return None


def _hard_attrs_from_spec(spec: DriveSpec | None) -> ladder.HardAttrs:
    if spec is None:
        return ladder.HardAttrs()
    interface_text = spec.interface.casefold()
    interface = next(
        (k for k in ("nvme", "sas", "sata", "scsi", "usb") if k in interface_text), None
    )
    form_text = spec.form_factor.casefold()
    form_factor = next((k for k in ("3.5", "2.5", "m.2") if k in form_text), None)
    return ladder.HardAttrs(
        capacity_bytes=int(spec.capacity_tb * _TB) if spec.capacity_tb is not None else None,
        interface=interface,
        form_factor=form_factor,
        sector_format=spec.sector_format.casefold() or None,
        security="sed" if spec.sed else None,
    )


def _family_agreement_attrs(family_id: int | None) -> ladder.HardAttrs:
    """C.3.2 agreement set: a family-grain target vetoes only on fields where
    ALL known specs under the family agree; disagreeing fields stay unknown."""

    if family_id is None:
        return ladder.HardAttrs()
    specs = [
        _hard_attrs_from_spec(spec)
        for spec in DriveSpec.objects.filter(product_model__product_family_id=family_id)
    ]
    if not specs:
        return ladder.HardAttrs()

    def agreed[T](values: set[T | None]) -> T | None:
        return next(iter(values)) if len(values) == 1 else None

    return ladder.HardAttrs(
        capacity_bytes=agreed({a.capacity_bytes for a in specs}),
        interface=agreed({a.interface for a in specs}),
        form_factor=agreed({a.form_factor for a in specs}),
        sector_format=agreed({a.sector_format for a in specs}),
        security=agreed({a.security for a in specs}),
    )


def _structured_mpn(listing: Listing) -> str | None:
    attrs = (
        listing.snapshots.order_by("-observed_at").values_list("attrs_json", flat=True).first()
    )
    if isinstance(attrs, dict):
        value = attrs.get("mpn")
        if isinstance(value, str) and value.strip():
            return value
    return None


def _current_edge(listing: Listing, *, for_update: bool = False) -> ListingResolution | None:
    queryset = listing.resolutions.filter(is_current=True)
    if for_update:
        queryset = queryset.select_for_update()
    return queryset.first()


def _prior_from_listing(listing: Listing) -> ladder.PriorResolution | None:
    """Rung-0 prior = the listing's DENORM fields — the last *accepted* state.

    Deliberately not the current edge: after a review/none/error edge the denorm
    is the accepted-state memory (error edges preserve it, evidence-based misses
    clear it — see _apply), so denorm-as-prior gives rung 0 exactly the C.3.2
    'already resolved' semantics."""

    if listing.resolution_grain == ResolutionGrain.NONE:
        return None
    if listing.product_variant_id is not None:
        model = listing.product_variant.product_model
        target = ladder.TargetRef(
            grain=Grain.VARIANT,
            family_id=model.product_family_id,
            model_id=model.pk,
            variant_id=listing.product_variant_id,
        )
        hard = _hard_attrs_from_spec(_spec_of(model))
    elif listing.product_model_id is not None:
        target = ladder.TargetRef(
            grain=Grain.MODEL,
            family_id=listing.product_model.product_family_id,
            model_id=listing.product_model_id,
        )
        hard = _hard_attrs_from_spec(_spec_of(listing.product_model))
    elif listing.product_family_id is not None:
        target = ladder.TargetRef(grain=Grain.FAMILY, family_id=listing.product_family_id)
        hard = _family_agreement_attrs(listing.product_family_id)
    else:
        return None
    return ladder.PriorResolution(
        target=target,
        confidence=listing.resolution_confidence or 0.5,
        hard_attrs=hard,
    )


# CR-003: an alias hit only counts when the ALIAS TYPE is compatible with the
# KIND of token that collided — a house SKU must not satisfy an MPN alias, an
# ASIN/other alias must never satisfy anything but its own kind. UNKNOWN_CODE
# may look up identifier-ish types but the ladder still demands brand evidence.
_COMPATIBLE_ALIAS_TYPES: dict[TokenKind, frozenset[str]] = {
    TokenKind.MANUFACTURER_MPN: frozenset({"mpn", "retail_pn", "region_pn"}),
    TokenKind.OEM_PN: frozenset({"oem_pn"}),
    TokenKind.HOUSE_SKU: frozenset({"other", "retail_pn"}),
    TokenKind.UNKNOWN_CODE: frozenset({"mpn", "oem_pn", "retail_pn", "region_pn"}),
}


def _alias_hits(
    candidates: list[MpnCandidate], source_site_id: int
) -> list[ladder.AliasHit]:
    by_key = {c.normalized: c for c in candidates if c.kind in _ALIAS_KINDS}
    if not by_key:
        return []
    rows = (
        ProductAlias.objects.filter(normalized_alias_text__in=list(by_key))
        .filter(Q(source_site__isnull=True) | Q(source_site_id=source_site_id))
        .select_related(
            "product_variant__product_model__manufacturer",
            "product_variant__product_model__product_family",
            "product_model__manufacturer",
            "product_model__product_family",
            "product_family__manufacturer",
        )
    )
    hits: list[ladder.AliasHit] = []
    for row in rows:
        candidate = by_key[row.normalized_alias_text]
        if row.alias_type not in _COMPATIBLE_ALIAS_TYPES.get(candidate.kind, frozenset()):
            continue
        if row.product_variant is not None:
            model = row.product_variant.product_model
            target = ladder.TargetRef(
                grain=Grain.VARIANT,
                family_id=model.product_family_id,
                model_id=model.pk,
                variant_id=row.product_variant.pk,
            )
            brand: str | None = model.manufacturer.normalized_name
            hard = _hard_attrs_from_spec(_spec_of(model))
        elif row.product_model is not None:
            target = ladder.TargetRef(
                grain=Grain.MODEL,
                family_id=row.product_model.product_family_id,
                model_id=row.product_model.pk,
            )
            brand = row.product_model.manufacturer.normalized_name
            hard = _hard_attrs_from_spec(_spec_of(row.product_model))
        else:
            target = ladder.TargetRef(grain=Grain.FAMILY, family_id=row.product_family_id)
            brand = (
                row.product_family.manufacturer.normalized_name
                if row.product_family is not None
                else None
            )
            hard = _family_agreement_attrs(row.product_family_id)
        hits.append(
            ladder.AliasHit(
                target=target,
                source_kind=row.source_kind,
                alias_type=row.alias_type,
                brand=brand,
                hard_attrs=hard,
                candidate_kind=candidate.kind,
                candidate_vendor=candidate.vendor_hint,
                candidate_structured=candidate.from_structured_field,
            )
        )
    return hits


def _first_decode(candidates: list[MpnCandidate]) -> DecodeResult | None:
    for candidate in candidates:
        if candidate.kind is TokenKind.OEM_PN:
            continue
        result = decode(candidate.normalized)
        if result is not None:
            return result
    return None


def _run_ladder(
    listing: Listing,
) -> tuple[str, ExtractedAttributes, list[MpnCandidate], ladder.Verdict]:
    canonical = canonicalize_title(
        f"{listing.title_raw} {listing.condition_label_raw}".strip()
    )
    extracted = vocab.extract(canonical)
    candidates = mpn.extract_candidates(
        canonical,
        structured_mpn=_structured_mpn(listing),
        source_key=listing.source_site.normalized_name,
    )
    verdict = ladder.decide(
        extracted,
        candidates,
        _prior_from_listing(listing),
        _alias_hits(candidates, listing.source_site_id),
        _first_decode(candidates),
    )
    return canonical, extracted, candidates, verdict


def _materialize(
    extracted: ExtractedAttributes, verdict: ladder.Verdict
) -> tuple[str, ProductFamily | None, ProductModel | None, ProductVariant | None, bool]:
    """Turn an ACCEPT verdict's TargetRef into live rows. Returns
    (grain, family, model, variant, variant_created_on_demand)."""

    if verdict.outcome is not ladder.Outcome.ACCEPT or verdict.target is None:
        return ResolutionGrain.NONE, None, None, None, False
    target = verdict.target
    family: ProductFamily | None = None
    model: ProductModel | None = None
    variant: ProductVariant | None = None
    if target.family_key is not None:
        vendor, family_name = target.family_key
        manufacturer, _ = Manufacturer.objects.get_or_create(
            normalized_name=vendor,
            defaults={"name": vendor.replace("_", " ").title()},
        )
        family, _ = ProductFamily.objects.get_or_create(
            manufacturer=manufacturer,
            normalized_name=canonicalize_title(family_name),
            defaults={
                "category": Category.objects.get(slug="drive"),
                "name": family_name.title(),
            },
        )
    elif target.grain is Grain.FAMILY and target.family_id is not None:
        family = ProductFamily.objects.get(pk=target.family_id)
    if target.model_id is not None:
        model = ProductModel.objects.get(pk=target.model_id)
    if target.variant_id is not None:
        variant = ProductVariant.objects.get(pk=target.variant_id)
    grain: str = ResolutionGrain(target.grain.value)
    on_demand = False
    if grain == ResolutionGrain.MODEL and model is not None and extracted.condition is not None:
        # C.3.3: variant rows are created on demand once model grain + normalized
        # condition are both known — the sellable identity materializes here.
        variant, _created = ProductVariant.objects.get_or_create(
            product_model=model,
            condition=extracted.condition.value,
            packaging=(
                extracted.packaging.value if extracted.packaging else Packaging.UNKNOWN
            ),
            recert_channel=(
                extracted.recert_channel.value
                if extracted.recert_channel
                else RecertChannel.UNKNOWN
            ),
            warranty_channel=(
                extracted.warranty_channel.value
                if extracted.warranty_channel
                else WarrantyChannel.UNKNOWN
            ),
        )
        grain = ResolutionGrain.VARIANT
        on_demand = True
    return grain, family, model, variant, on_demand


def _emit_learned_aliases(
    listing: Listing, candidates: list[MpnCandidate], model_id: int | None
) -> None:
    if model_id is None:
        return
    has_manufacturer_token = any(
        c.kind is TokenKind.MANUFACTURER_MPN for c in candidates
    )
    for candidate in candidates:
        if candidate.kind is TokenKind.OEM_PN and has_manufacturer_token:
            # Dual-labeled listing: OEM token + resolved MPN → learned alias at
            # MODEL grain max (the N:N verdict, ADR-0019 rule 7).
            ProductAlias.objects.get_or_create(
                alias_type=AliasType.OEM_PN,
                normalized_alias_text=candidate.normalized,
                source_site=None,
                product_model_id=model_id,
                product_family=None,
                defaults={"source_kind": AliasSourceKind.LISTING_DERIVED},
            )
        elif candidate.kind is TokenKind.HOUSE_SKU:
            ProductAlias.objects.get_or_create(
                alias_type=AliasType.OTHER,
                normalized_alias_text=candidate.normalized,
                source_site=listing.source_site,
                defaults={
                    "product_model_id": model_id,
                    "source_kind": AliasSourceKind.LISTING_DERIVED,
                },
            )


def _error_verdict(exc: Exception) -> ladder.Verdict:
    return ladder.Verdict(
        outcome=ladder.Outcome.NONE, grain=Grain.NONE, evidence={"error": repr(exc)}
    )


@transaction.atomic
def _apply(
    listing: Listing,
    canonical: str,
    extracted: ExtractedAttributes,
    candidates: list[MpnCandidate],
    verdict: ladder.Verdict,
) -> None:
    # CR-002: serialize concurrent resolutions of one listing — lock the listing
    # row, then the current edge, inside this transaction.
    locked = (
        Listing.objects.select_for_update().select_related("source_site").get(pk=listing.pk)
    )
    current = _current_edge(locked, for_update=True)
    is_error = "error" in verdict.evidence
    # An unchanged rung-0 accept skips the write — UNLESS the current edge is an
    # error edge, in which case the clean re-accept must supersede it so the
    # ledger's current converges back to the accepted state.
    unchanged_accept = (
        verdict.outcome is ladder.Outcome.ACCEPT
        and verdict.rung == 0
        and current is not None
        and "error" not in current.evidence
    )
    unchanged_miss = (
        verdict.outcome is not ladder.Outcome.ACCEPT
        and not is_error
        and current is not None
        and current.grain == ResolutionGrain.NONE
        and "error" not in current.evidence
        and current.evidence.get("outcome") == verdict.outcome
    )
    unchanged_error = (
        is_error
        and current is not None
        and current.evidence.get("error") == verdict.evidence.get("error")
    )
    if unchanged_accept or unchanged_miss or unchanged_error:
        # Routine re-poll with an unchanged outcome: no edge spam
        # (append-only ≠ append-always). Distinct NEW errors DO append (CR-001).
        if canonical and locked.title_normalized != canonical:
            locked.title_normalized = canonical
            locked.save(update_fields=["title_normalized"])
        return
    accepted = verdict.outcome is ladder.Outcome.ACCEPT
    if accepted:
        grain, family, model, variant, on_demand = _materialize(extracted, verdict)
    else:
        # Non-accept (incl. error) edges never materialize identity rows — this
        # also keeps the CR-001 fallback error-write free of _materialize.
        grain, family, model, variant, on_demand = ResolutionGrain.NONE, None, None, None, False
    evidence: dict[str, object] = {**verdict.evidence, "outcome": verdict.outcome}
    if verdict.rung is not None:
        evidence["rung"] = verdict.rung
    if on_demand:
        evidence["variant_on_demand"] = True
    if is_error and locked.resolution_grain != ResolutionGrain.NONE:
        evidence["denorm_preserved"] = True
    # CR-002 ordering: demote-old → insert-new → link-old. The one-current
    # unique constraint must hold at every individual statement.
    if current is not None:
        current.is_current = False
        current.save(update_fields=["is_current"])
    edge = ListingResolution.objects.create(
        listing=locked,
        grain=grain,
        product_family=family if grain == ResolutionGrain.FAMILY else None,
        product_model=model if grain == ResolutionGrain.MODEL else None,
        product_variant=variant if grain == ResolutionGrain.VARIANT else None,
        method=verdict.method if accepted else "",
        confidence=verdict.confidence if accepted else None,
        matcher_version=MATCHER_VERSION,
        evidence=evidence,
        resolved_at=timezone.now(),
    )
    if current is not None:
        current.superseded_by = edge
        current.save(update_fields=["superseded_by"])
    # Denorm refresh (C.3.3 "refreshed on accept"), by outcome:
    #  accept       → point at the target;
    #  review/none  → CLEAR — an evidence-based miss (incl. veto trip) must pull
    #                 the listing out of the trusted-resolution read path;
    #  error        → PRESERVE the last accepted state — a matcher crash says
    #                 nothing about the listing; the edge records the failure
    #                 (CR-001: audit trail without demotion).
    locked.title_normalized = canonical or locked.title_normalized
    if is_error:
        locked.save(update_fields=["title_normalized"])
        return
    locked.resolution_grain = grain
    locked.resolution_confidence = edge.confidence
    locked.product_family = edge.product_family
    locked.product_model = edge.product_model
    locked.product_variant = edge.product_variant
    locked.save(
        update_fields=[
            "title_normalized",
            "resolution_grain",
            "resolution_confidence",
            "product_family",
            "product_model",
            "product_variant",
        ]
    )
    if accepted:
        resolved_model_id = (
            edge.product_model_id
            if edge.product_model_id is not None
            else (variant.product_model_id if variant is not None else None)
        )
        _emit_learned_aliases(locked, candidates, resolved_model_id)


class CatalogResolver:
    """The ADR-0019 resolver service. Stateless — safe to construct per call."""

    def resolve_listing(self, listing_id: int) -> None:
        listing = Listing.objects.select_related("source_site").get(pk=listing_id)
        try:
            canonical, extracted, candidates, verdict = _run_ladder(listing)
        except Exception as exc:  # ladder failure → error verdict (C.3)
            logger.exception("matcher crashed for listing %s", listing_id)
            canonical, extracted, candidates = "", ExtractedAttributes(), []
            verdict = _error_verdict(exc)
        try:
            _apply(listing, canonical, extracted, candidates, verdict)
        except Exception as exc:
            # CR-001: an apply/materialize/DB failure must still leave a trace in
            # the resolution ledger — fall back to a bare error edge in a fresh
            # transaction. If even THAT fails, propagate: pipeline.run_source
            # counts it as a resolver_error and never blocks ingestion.
            logger.exception("resolution apply failed for listing %s", listing_id)
            _apply(listing, canonical, ExtractedAttributes(), [], _error_verdict(exc))
```

Typing note: `_materialize`'s `grain: str = ResolutionGrain(...)` — declare the return slot as `str` and assign `ResolutionGrain` members (TextChoices members are `str` subclasses); if BasedPyright complains about the tuple element type, annotate the return as `tuple[str, ...]` exactly as written above.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/db/test_resolver.py tests/db/test_identity.py -q`
Expected: all PASS. Iteration likely on: `ST20000NM007D` must decode (`st` + `20000` + `nm` + `007` + `d` — fits the grammar); the review-edge evidence keys; the `x477ar6` OEM gate (title contains "netapp").

- [ ] **Step 5: Fix pass, full gate, commit**

```bash
uv run ruff format . && uv run ruff check . --fix
uv run python -m scripts.check
git add src/hw_radar/matching/resolver.py tests/db/test_resolver.py tests/db/test_identity.py
git commit -m "feat(matching): CatalogResolver — ladder against the DB, append-only edges (FR-003)"
```

---

### Task 8: `unknown_model_backfill` view + unmanaged model

**Files:**
- Create: `src/hw_radar/catalog/migrations/0007_backfill_view.py` (hand-written)
- Modify: `src/hw_radar/catalog/models/resolution.py` (add `UnknownModelBackfill`)
- Modify: `src/hw_radar/catalog/models/__init__.py`, `src/hw_radar/catalog/admin.py`
- Test: `tests/db/test_backfill_view.py`

**Interfaces:**
- Consumes: `listing.resolution_grain`, current (unsuperseded) `listing_resolution` edges, the `evidence->>'mpn_hypothesis'` / `'vendor_hint'` keys written by Task 7.
- Produces: `UnknownModelBackfill` (unmanaged, read-only): `hypothesis_key` (pk, `<vendor>:<hypothesis|listing:id>`), `mpn_hypothesis`, `vendor_hint`, `occurrences`, `family_grain_count`, `first_seen`, `last_seen`. MS-1c's occurrence-triggered discovery loop reads `occurrences` from here. **Scope (deliberate):** occurrence-only at MS-1b — the C.3.4 deal-attractiveness prioritization column requires scoring and lands with MS-3.

- [ ] **Step 1: Write the failing tests**

```python
# tests/db/test_backfill_view.py
"""C.3.4: the backfill queue is a VIEW over listings below model grain plus the
rung-2 decoded-but-unknown set — no second source of truth. Occurrence counts
group by decoded hypothesis so MS-1c's discovery loop has a trigger signal."""

import pytest

from hw_radar.catalog.models import (
    Listing,
    RetentionClass,
    SourceSite,
    UnknownModelBackfill,
)
from hw_radar.matching.resolver import CatalogResolver


@pytest.fixture
def site(db: None) -> SourceSite:
    return SourceSite.objects.create(name="BF", normalized_name="bf")


def _resolve(site: SourceSite, key: str, title: str) -> Listing:
    listing = Listing.objects.create(
        source_site=site,
        source_listing_key=key,
        canonical_url=f"https://example.test/{key}",
        url_hash=key,
        title_raw=title,
        retention_class=RetentionClass.MERCHANT_FACT,
    )
    CatalogResolver().resolve_listing(listing.pk)
    return listing


def test_same_decoded_hypothesis_groups_across_listings(site: SourceSite) -> None:
    _resolve(site, "b1", "Seagate 20TB ST20000NM007D Recertified")
    _resolve(site, "b2", "Seagate 20TB ST20000NM007D Renewed")
    row = UnknownModelBackfill.objects.get(mpn_hypothesis="st20000nm007d")
    assert row.occurrences == 2
    assert row.family_grain_count == 2  # both attached at family grain (rung 2)
    assert row.first_seen <= row.last_seen


def test_unresolved_listing_without_hypothesis_gets_its_own_row(site: SourceSite) -> None:
    listing = _resolve(site, "b3", "mystery enterprise drive")
    # No vendor → empty vendor prefix in the composite key.
    row = UnknownModelBackfill.objects.get(hypothesis_key=f":listing:{listing.pk}")
    assert row.mpn_hypothesis is None
    assert row.occurrences == 1


def test_same_text_hypothesis_from_different_vendors_never_collapses(
    site: SourceSite,
) -> None:
    # CR-005: vendor_hint is part of the grouping key.
    from hw_radar.catalog.models import ListingResolution, ResolutionGrain

    for key, vendor in (("bv1", "seagate"), ("bv2", "toshiba")):
        listing = Listing.objects.create(
            source_site=site,
            source_listing_key=key,
            canonical_url=f"https://example.test/{key}",
            url_hash=key,
            title_raw="collision fixture",
            retention_class=RetentionClass.MERCHANT_FACT,
        )
        ListingResolution.objects.create(
            listing=listing,
            grain=ResolutionGrain.NONE,
            matcher_version="test",
            evidence={"outcome": "none", "mpn_hypothesis": "zz99zz99", "vendor_hint": vendor},
        )
    assert UnknownModelBackfill.objects.filter(mpn_hypothesis="zz99zz99").count() == 2


def test_model_grain_listings_are_not_in_the_queue(site: SourceSite) -> None:
    # A fully resolved listing must not appear (view covers BELOW model grain).
    from hw_radar.catalog.models import (
        AliasSourceKind,
        AliasType,
        Manufacturer,
        ProductAlias,
        ProductModel,
    )

    mfr = Manufacturer.objects.create(name="Seagate", normalized_name="seagate")
    model = ProductModel.objects.create(
        manufacturer=mfr,
        model_number="ST16000NM001G",
        normalized_model_number="st16000nm001g",
    )
    ProductAlias.objects.create(
        alias_type=AliasType.MPN,
        normalized_alias_text="st16000nm001g",
        product_model=model,
        source_kind=AliasSourceKind.CATALOG_AUTHORITATIVE,
    )
    _resolve(site, "b4", "Seagate 16TB ST16000NM001G Recertified")
    assert not UnknownModelBackfill.objects.filter(
        mpn_hypothesis="st16000nm001g"
    ).exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/db/test_backfill_view.py -q`
Expected: FAIL — `ImportError: cannot import name 'UnknownModelBackfill'`

- [ ] **Step 3: Implement the view + model**

Append to `src/hw_radar/catalog/models/resolution.py`:

```python
class UnknownModelBackfill(models.Model):
    """C.3.4 backfill queue — a database VIEW (migration 0007), not a table:
    listings below model grain + the rung-2 decoded-but-unknown set, grouped by
    decoded hypothesis with occurrence counts. Read-only; the deal-signal
    ordering column arrives with scoring (MS-3), the occurrence-triggered
    discovery loop with MS-1c."""

    hypothesis_key = models.CharField(primary_key=True, max_length=300)
    mpn_hypothesis = models.CharField(max_length=200, null=True)
    vendor_hint = models.CharField(max_length=50, null=True)
    occurrences = models.BigIntegerField()
    family_grain_count = models.BigIntegerField()
    first_seen = models.DateTimeField()
    last_seen = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "unknown_model_backfill"
```

Create `src/hw_radar/catalog/migrations/0007_backfill_view.py`:

```python
"""C.3.4 unknown_model backfill queue as a VIEW — no second source of truth.

Grouping key: (vendor_hint, decoded mpn_hypothesis) from the current edge when
present, else a per-listing synthetic key ('listing:<id>') so hypothesis-less
unresolved listings still surface individually. Vendor is IN the grouping key
so equal token text from different vendors never collapses into one queue row
(Codex CR-005). MS-1b scope is occurrence-only: the C.3.4 deal-attractiveness
signal needs scoring (MS-3) and is deliberately absent. Reversible: DROP VIEW.

SeparateDatabaseAndState (Codex CR-NEW-001): Django's autodetector tracks
UNMANAGED models in migration state — RunSQL alone would leave the model
stateless and the repo's makemigrations --check gate (tests/db/
test_migrations.py) would fail. The CreateModel below is state-only; the
managed=False option makes database_forwards skip it, so the view SQL is the
sole DDL."""

from django.db import migrations, models

CREATE_VIEW = """
CREATE VIEW unknown_model_backfill AS
WITH current_res AS (
    SELECT lr.listing_id,
           NULLIF(lr.evidence->>'mpn_hypothesis', '') AS mpn_hypothesis,
           COALESCE(lr.evidence->>'vendor_hint', '') AS vendor_hint
    FROM listing_resolution lr
    WHERE lr.is_current
),
below_model AS (
    SELECT l.id AS listing_id,
           cr.mpn_hypothesis,
           COALESCE(cr.vendor_hint, '') AS vendor_hint,
           l.resolution_grain AS grain,
           l.first_seen,
           l.last_seen
    FROM listing l
    LEFT JOIN current_res cr ON cr.listing_id = l.id
    WHERE l.resolution_grain IN ('none', 'family')
)
SELECT vendor_hint || ':' || COALESCE(mpn_hypothesis, 'listing:' || listing_id::text)
           AS hypothesis_key,
       mpn_hypothesis,
       NULLIF(vendor_hint, '') AS vendor_hint,
       COUNT(*) AS occurrences,
       COUNT(*) FILTER (WHERE grain = 'family') AS family_grain_count,
       MIN(first_seen) AS first_seen,
       MAX(last_seen) AS last_seen
FROM below_model
GROUP BY vendor_hint, COALESCE(mpn_hypothesis, 'listing:' || listing_id::text), mpn_hypothesis;
"""


class Migration(migrations.Migration):
    dependencies = [("catalog", "0006_resolution")]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=CREATE_VIEW, reverse_sql="DROP VIEW unknown_model_backfill;"
                ),
            ],
            state_operations=[
                migrations.CreateModel(
                    name="UnknownModelBackfill",
                    fields=[
                        (
                            "hypothesis_key",
                            models.CharField(max_length=300, primary_key=True, serialize=False),
                        ),
                        ("mpn_hypothesis", models.CharField(max_length=200, null=True)),
                        ("vendor_hint", models.CharField(max_length=50, null=True)),
                        ("occurrences", models.BigIntegerField()),
                        ("family_grain_count", models.BigIntegerField()),
                        ("first_seen", models.DateTimeField()),
                        ("last_seen", models.DateTimeField()),
                    ],
                    options={"db_table": "unknown_model_backfill", "managed": False},
                ),
            ],
        ),
    ]
```

Export `UnknownModelBackfill` from `catalog/models/__init__.py`; register a read-only admin (same `has_add/change/delete_permission → False` pattern as `ListingResolutionAdmin`, `list_display = ("hypothesis_key", "mpn_hypothesis", "vendor_hint", "occurrences", "family_grain_count", "last_seen")`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/db/test_backfill_view.py tests/db/test_migrations.py -q`
Expected: all PASS

- [ ] **Step 5: Fix pass, full gate, commit**

```bash
uv run ruff format . && uv run ruff check . --fix
uv run python -m scripts.check
git add src/hw_radar/catalog tests/db/test_backfill_view.py
git commit -m "feat(catalog): unknown_model_backfill queue view (C.3.4)"
```

---

### Task 9: Poller wiring, spec reconciliation, closeout, PR

**Files:**
- Modify: `src/hw_radar/poller/service.py` (NullResolver → CatalogResolver)
- Modify: `tests/db/test_poller_jobs.py`
- Modify: `docs/specs/hw-radar-master-spec.md` (FR-003 traceability row + revision row)
- Modify: `docs/handoff.md`, `TODO.md` (local-only — never commit)

**Interfaces:**
- Consumes: `CatalogResolver` (Task 7).
- Produces: the live MS-1b system; the `dev→main` PR.

- [ ] **Step 1: Swap the resolver in the poller**

In `src/hw_radar/poller/service.py`, replace the import:

```python
from hw_radar.acquisition.contracts import NullResolver
```

with:

```python
from hw_radar.matching.resolver import CatalogResolver
```

and both call sites (`run_source(factory(), NullResolver())` and `run_source(factory(), NullResolver(), run_kind=RunKind.PROBE)`) with `CatalogResolver()`. Keep `NullResolver` itself in `acquisition/contracts.py` — tests still use it as the C.3 isolation stub, and its docstring should be updated from "MS-1b installs the ADR-0019 resolver" to "the poller wires matching.resolver.CatalogResolver; this stub remains for pipeline tests".

- [ ] **Step 2: Add the wiring regression test**

In `tests/db/test_poller_jobs.py`, add (adapt the fixture/setup style to what the file already uses — read it first; the assertion below is the contract):

```python
def test_poller_wires_the_catalog_resolver() -> None:
    # MS-1b: scheduled polls must resolve through the ADR-0019 resolver, not the
    # MS-1a NullResolver stub. Import-level tripwire + type check.
    from hw_radar.matching.resolver import CatalogResolver
    from hw_radar.poller import service

    assert service.CatalogResolver is CatalogResolver
    assert not hasattr(service, "NullResolver")
```

Run: `uv run pytest tests/db/test_poller_jobs.py tests/db/test_pipeline_demo.py -q`
Expected: all PASS (the demo pipeline test keeps using `NullResolver` explicitly and is unaffected).

- [ ] **Step 3: Reconcile the spec traceability matrix**

In `docs/specs/hw-radar-master-spec.md` §20 (verification matrix, around line 756): change the FR-003 row status from `Verified (resolver lands MS-1)` to `Verified (resolver-driven since MS-1b)`. Check the revision table's current highest version number first, then append the next revision row (expected `0.14` — verify), dated today, e.g.:

```markdown
| 0.14 | 2026-07-05 | Claude (MS-1b implementation) | MS-1b matching layer landed (matching/ library, listing_resolution, backfill view, resolver wired into the poller). Traceability: FR-003 row upgraded to the resolver-driven test; DR-010 listing_resolution now implemented. No design change — C.3/ADR-0019 implemented as specified. |
```

Also update the DR-010 row's status text if it still says the resolution table "lands MS-1".

- [ ] **Step 4: Full gate**

```bash
uv run python -m scripts.check
```

Expected: every stage green (format, lint, basedpyright 0 errors, pytest all pass, coverage ≥ 85% branch, pip-audit clean). Do not proceed on any failure.

- [ ] **Step 5: Commit and push dev**

```bash
git add src/hw_radar/poller/service.py src/hw_radar/acquisition/contracts.py \
        tests/db/test_poller_jobs.py docs/specs/hw-radar-master-spec.md
git commit -m "feat(poller): wire CatalogResolver into scheduled runs; spec traceability reconciled"
git push origin dev
```

- [ ] **Step 6: Update local session docs (never commit these)**

`docs/handoff.md`: new top section — MS-1b complete (what landed, MATCHER_VERSION, the rung-0/no-spam guard, provisional-family note for MS-1c dedup awareness, next step = MS-1c per the design doc). `TODO.md`: no MS-1b items should remain open; the ADR-0019 ratification item stays (it is MS-1e's gate); note that `HOUSE_SKU_PREFIXES` is empty pending MS-1d, that MS-1c must import `normalize_alias_text` for catalog aliases, and add a tracked MS-1c item: **verify the WD↔SanDisk Optimus equivalence against seeded catalog aliases** (SSD-line rebrand confirmed externally; split the brand key if the catalog contradicts the mapping — Codex CR-004).

- [ ] **Step 7: Open the MS-1b PR (dev→main)**

```bash
gh pr create --base main --head dev \
  --title "MS-1b: ADR-0019 matching layer — extraction stack, rung 0-2 ladder, resolver, backfill view" \
  --body "$(cat <<'EOF'
## Summary
- `hw_radar.matching`: pure extraction library (N1 canonicalize, N2 vocab, N3 MPN/OEM/house-SKU candidates, N4 provenance-tiered vendor grammars) + rung 0-2 conservative ladder with the hard-attribute contradiction veto (spec C.3, ADR-0019)
- `listing_resolution` append-only edge table + denormalized current-resolution fields on `listing` (migration 0006); `unknown_model_backfill` view (migration 0007)
- `CatalogResolver` wired into the poller (replaces the MS-1a `NullResolver` stub); variant-on-demand creation; lazy OEM/house-SKU alias learning; single-normalizer parity CI test
- FR-003 acceptance test upgraded to resolver-driven; spec traceability reconciled (v0.14)

## Test plan
- [ ] CI `check` green (gate: ruff, basedpyright strict, pytest + 85% branch coverage, pip-audit)
- [ ] `dependency-review` green (no dependency changes expected — stdlib-only feature)
EOF
)"
```

Wait for CI (`gh pr checks --watch`), then merge with a **merge commit** (repo convention — never squash):

```bash
gh pr merge --merge
```

Note: the merge deploys as a **behavioral near-no-op** (all sources still `disabled`; the demo source resolves to `grain = none`). The `production` environment gate may hold the deploy for owner approval — report it, don't force it.

---

## Self-review notes (author pass, 2026-07-05)

1. **Spec coverage check (design doc §MS-1b bullet by bullet):** N1–N4 → Tasks 1–4 ✅; ladder rungs 0–2 + veto → Task 6 ✅; rungs 3–4 as explicit review outcomes → `Outcome.REVIEW` edges with evidence (no scoring — correct for MS-1b) ✅; `ListingResolution` + listing denorm FKs migration → Task 5 ✅; variant-on-demand → Task 7 `_materialize` ✅; backfill view → Task 8 ✅; golden corpus / decoder vectors / idempotence property / **parity test** → Tasks 1–4, 6, 7 ✅; FR-003 upgrade → Task 7 (in place, traceability-safe) ✅; exit criteria (gate green, golden verdicts, FR-003 resolver-driven) → Tasks 6/7/9 ✅.
2. **Known simplifications, deliberate:** (a) same-target-different-grain alias hits (variant + model alias for one string) go to REVIEW rather than most-specific-wins — conservative, rare before MS-1c seeds variant aliases, and a veto-side error is recoverable (review) while a merge error is not; (b) `security` veto compares `sed`-only from `DriveSpec.sed` vs extracted `sed|fips|ise` — a FIPS-labeled listing on a SED-only spec goes to review, which is the conservative direction; (c) provisional rung-2 families ("exos") may need reconciliation with MS-1c's authoritative family names — noted in the handoff for the MS-1c plan.
3. **Type-consistency pass:** `Grain`/`ResolutionGrain` share string values by construction (Task 5 comment); `ladder.decide` signature identical in Task 6 definition and Task 7 usage; `TargetRef(grain=..., family_id=..., model_id=..., variant_id=..., family_key=...)` consistent across Tasks 6–7; evidence keys (`mpn_hypothesis`, `vendor_hint`, `outcome`, `veto`, `provisional`) written by Task 7 exactly as Task 8's view SQL reads them.
4. **Placeholder scan:** clean — no TBDs, no "similar to Task N", every code step shows the code. A strict-typing fix pass was applied during self-review: optional-attribute access in tests goes through typed `_value`/`_attr` helpers, `_family_agreement_attrs` uses a generic `agreed()` instead of ignores, and the boilerplate strip was reordered before noise-stripping so `l@@k`-class patterns are reachable.
5. **Migration safety:** 0006 is additive (AddField nullable/defaulted + CreateModel + choices-only AlterField); 0007 is a reversible view. Both run under the existing pytest `--create-db` flow.

## Codex audit round 1 — response ledger (2026-07-05)

Audit: `docs/codex-reviews/2026-07-05-095442-codex-plan-review-round1.md` (verdict: needs major correction; CR-001..CR-006). All three blocking findings were verified against the plan and accepted; revisions applied in place:

- **CR-001 (accepted, fixed):** resolver failures could escape `_apply` or vanish in the never-demote guard. Now: `resolve_listing` wraps BOTH `_run_ladder` and `_apply`; apply failures fall back to a bare error-edge write in a fresh transaction (materialize-free by construction); error edges always append to the ledger but PRESERVE denorm (`denorm_preserved` evidence); repeated identical errors are deduped, distinct errors append; a clean rung-0 re-accept supersedes a standing error edge (ledger converges). Four new regression tests (`test_crash_after_accepted…`, `test_repeated_identical_crash…`, `test_apply_failure_falls_back…`, `test_veto_on_reobservation…`).
- **CR-002 (accepted, fixed):** one-current is now a DB `UniqueConstraint(fields=["listing"], condition=Q(is_current=True))`. `is_current` (state flag) was split from `superseded_by` (audit pointer) because a partial unique index cannot be deferred in PostgreSQL and `superseded_by` points at the NEW edge — apply order is demote-old → insert-new → link-old, valid at every statement. `select_for_update` on the listing row + current edge serializes concurrent resolver calls. New schema tests (`test_two_current_edges…`, `test_current_edge_cannot_be_superseded`).
- **CR-003 (accepted, fixed):** rung 1 now enforces the C.3.2 `brand + full normalized MPN` trigger: alias-type ↔ candidate-kind compatibility map in the resolver (`_COMPATIBLE_ALIAS_TYPES`), and a brand-evidence gate in the ladder (extracted brand ∨ vendor-shaped token consistent with the target ∨ structured-field MPN) — no evidence → REVIEW, never accept. `AliasHit` carries `candidate_kind/candidate_vendor/candidate_structured`. New golden cases (brandless unknown-code → review; vendor-shaped token counts as brand evidence).
- **CR-004 (partially accepted):** the sandisk→western_digital mapping STAYS — it is mandated verbatim by spec C.3.1 (repo ground truth outranks the audit's inconclusive web pass), and brand equivalence is only a gate (never merges without MPN evidence). Documented in `vocab.py` with an MS-1c re-verification note against seeded catalog aliases.
- **CR-005 (accepted, fixed):** view scope honestly labeled occurrence-only (deal signal needs MS-3 scoring); `vendor_hint` added to the grouping key + composite `hypothesis_key`; collision regression test added.
- **CR-006 (accepted, fixed):** `podman rm -f` marked destructive-dev-only (fixture data); image tag cross-referenced to `compose.yaml`/CI with a verify-before-substitute note.

## Codex audit round 2 — response ledger (2026-07-05)

Audit: `docs/codex-reviews/2026-07-05-100843-codex-plan-review-round2.md` (CR-001/002/003/005/006 resolved; CR-004 partial; new blocker CR-NEW-001).

- **CR-NEW-001 (accepted, fixed):** migration `0007` now uses `SeparateDatabaseAndState` — the view SQL as `database_operations`, a state-only `CreateModel(options={"managed": False, ...})` as `state_operations` — because Django's autodetector tracks unmanaged models in migration state and the repo's `tests/db/test_migrations.py` gate (`makemigrations --check --dry-run`) would otherwise fail. `database_forwards` skips unmanaged models, so the view SQL remains the sole DDL.
- **CR-004 (closed):** the "SanDisk fronts WD HDDs" wording was mine and wrong — corrected in both `vocab.py` and `ladder.py` comments to the externally verified scope (WD-branded **SSD lines** → SanDisk Optimus, unchanged MPNs, per spec C.3.1). The `sandisk → western_digital` brand key stays (gate-only semantics; merges always require an MPN/alias hit), with a **tracked MS-1c TODO item** to verify against seeded catalog aliases and split the key if contradicted.

