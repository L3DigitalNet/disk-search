"""N1 canonicalization + the single-normalizer alias key (ADR-0019 rule 1, C.3)."""

import random
import string

from hw_radar.matching.normalize import canonicalize_title, normalize_alias_text

# Test data intentionally contains unicode dash variants for normalization testing
GOLDEN_TITLES = [
    "Seagate Exos X16 16TB ST16000NM001G Factory Recertified Enterprise HDD",
    "WD Red Plus 12TB WD120EFBX NAS Hard Drive – NEW ✅ FREE SHIPPING",  # noqa: RUF001
    'Toshiba MG08ACA16TE 16TB 7200RPM SATA 512e CMR 3.5" L@@K!!',
    "NetApp X477A-R6 4TB 7.2K SAS HDD WD4001FYYG server pull",
    'SAMSUNG MZ‑77E1T0B/AM 870 EVO 1TB 2.5" SSD lot of 4',  # noqa: RUF001
    "HGST Ultrastar HUS724040ALS640 4TB SAS  ships fast  us seller",
    "goHardDrive白ラベル 8TB — white label",
]


def test_canonicalize_casefolds_and_unifies_separators() -> None:
    out = canonicalize_title("SAMSUNG MZ‑77E1T0B/AM 870 EVO")  # noqa: RUF001
    assert out == "samsung mz-77e1t0b/am 870 evo"


def test_canonicalize_strips_boilerplate_but_keeps_condition_words() -> None:
    out = canonicalize_title("WD 12TB NEW ✅ FREE SHIPPING L@@K brand new sealed")
    assert "free shipping" not in out
    assert "l@@k" not in out
    assert "brand new" in out  # condition signal is N2's job, never stripped


def test_canonicalize_collapses_whitespace() -> None:
    assert canonicalize_title("  a   b\t c ") == "a b c"


def test_alias_key_strips_all_separators() -> None:
    for raw in ("MZ-77E1T0B/AM", "mz 77e1t0b/am", "MZ‑77E1T0B/AM", "mz_77e1t0b.am"):  # noqa: RUF001
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
    alphabet = string.ascii_letters + string.digits + " -_/.\"'!★✅–—‑@#TBtb"  # noqa: RUF001
    for _ in range(500):
        s = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 60)))
        once = canonicalize_title(s)
        assert canonicalize_title(once) == once
        key = normalize_alias_text(s)
        assert normalize_alias_text(key) == key
