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
