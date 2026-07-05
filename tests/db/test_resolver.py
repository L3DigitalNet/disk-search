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


# django-types has no stub for the `resolutions` reverse-FK related manager
# (Listing carries no such attribute in its stubs — related_name is runtime-only
# Django metaclass magic; see the identical precedent in test_resolution_models.py).
# A bare inline ignore on the `.get(...)`/`.count()` call still leaves the
# RETURNED value's own type Unknown, so every downstream `.grain`/`.evidence`
# read would need its own ignore too — these two typed helpers are the function
# return-type boundary that actually stops that propagation (verified empirically:
# a declared variable annotation alone does not).
def _edge(listing: Listing, **filters: object) -> ListingResolution:
    return listing.resolutions.get(**filters)  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType, reportUnknownArgumentType, reportAttributeAccessIssue]


def _edge_count(listing: Listing, **filters: object) -> int:
    return listing.resolutions.filter(  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType, reportUnknownArgumentType, reportAttributeAccessIssue]
        **filters
    ).count()


def test_rung1_parity_exact_alias_resolves_to_variant_on_demand(
    site: SourceSite, exos_16tb: ProductModel
) -> None:
    listing = _listing(site, "l1", "Seagate Exos X16 16TB ST16000NM001G Factory Recertified SATA")
    CatalogResolver().resolve_listing(listing.pk)
    listing.refresh_from_db()
    # Model grain + known condition → variant created on demand (C.3.3).
    assert listing.resolution_grain == ResolutionGrain.VARIANT
    assert listing.product_variant is not None
    assert listing.product_variant.product_model == exos_16tb
    assert listing.product_variant.condition == Condition.RECERTIFIED
    assert listing.product_family is None and listing.product_model is None  # lower grains NULL
    edge = _edge(listing, superseded_by__isnull=True)
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
    assert _edge_count(listing) == 1


def test_capacity_contradiction_goes_to_review_not_price_history(
    site: SourceSite, exos_16tb: ProductModel
) -> None:
    listing = _listing(site, "l3", "Seagate 14TB ST16000NM001G Recertified")
    CatalogResolver().resolve_listing(listing.pk)
    listing.refresh_from_db()
    assert listing.resolution_grain == ResolutionGrain.NONE
    assert listing.product_variant is None
    edge = _edge(listing)
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
    edge = _edge(a, superseded_by__isnull=True)
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
    learned = ProductAlias.objects.get(alias_type=AliasType.OEM_PN, normalized_alias_text="x477ar6")
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
    edge = _edge(listing)
    assert edge.grain == ResolutionGrain.NONE
    assert "error" in edge.evidence


def test_unresolved_repoll_appends_no_duplicate_none_edge(site: SourceSite) -> None:
    listing = _listing(site, "l8", "mystery enterprise drive")
    resolver = CatalogResolver()
    resolver.resolve_listing(listing.pk)
    resolver.resolve_listing(listing.pk)
    assert _edge_count(listing) == 1  # unchanged NONE outcome: no spam


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
    current = _edge(listing, is_current=True)
    assert "error" in current.evidence
    assert current.evidence["denorm_preserved"] is True
    assert _edge_count(listing) == 2


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
    assert _edge_count(listing) == 1  # identical error: no spam (CR-001)


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
    edge = _edge(listing, is_current=True)
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
    assert _edge_count(listing) == 2
    assert _edge_count(listing, is_current=True) == 1
    current = _edge(listing, is_current=True)
    assert current.evidence["outcome"] == "review"
