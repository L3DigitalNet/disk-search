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
        provenance=(Provenance.CORROBORATED_COMMUNITY if family else Provenance.VENDOR_OFFICIAL),
        rule=f"st:{m.group(2)}",
    )
