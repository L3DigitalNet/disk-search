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

# Unicode dash variants (HYPHEN, DASH, FIGURE DASH, EN DASH, EM DASH, HORIZONTAL BAR,
# MINUS SIGN) → ASCII hyphen so MPNs like "MZ‑77E1T0B/AM" keep their separator through  # noqa: RUF003
# canonicalization (NFKC alone leaves U+2011 untouched).
_DASHES: dict[int, str] = dict.fromkeys(
    (0x2010, 0x2011, 0x2012, 0x2013, 0x2014, 0x2015, 0x2212), "-"
)
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
