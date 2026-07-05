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
    capacity = (
        int(m.group(4)) * _TB  # '16t' → 16 TB
        if m.group(4) is not None
        else int(m.group(5)) * _TB  # '400' → leading digit is TB (MG04ACA400E → 4 TB)
    )
    return DecodeResult(
        vendor="toshiba",
        family_name=_FAMILIES[m.group(1)],
        capacity_bytes=capacity,
        generation=m.group(2),
        provenance=Provenance.VENDOR_OFFICIAL,
        rule=f"toshiba:{m.group(1)}",
    )
