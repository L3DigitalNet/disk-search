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

    source_kind: Literal["first_party_datasheet", "first_party_manual", "first_party_page"]
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
