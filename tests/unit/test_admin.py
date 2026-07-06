"""Permission-method coverage for the two inspection-only admin surfaces.

Both classes are deliberately read-only: `listing_resolution` is an append-only
audit trail (DR-010) and `unknown_model_backfill` is a database VIEW (C.3.4), so
add/change/delete must be refused unconditionally — the overrides ignore the
request, which is exactly why these are pure unit checks with no DB access."""

from django.contrib import admin
from django.test import RequestFactory

from hw_radar.catalog.admin import ListingResolutionAdmin, UnknownModelBackfillAdmin
from hw_radar.catalog.models import ListingResolution, UnknownModelBackfill


def test_listing_resolution_admin_refuses_all_mutations(rf: RequestFactory) -> None:
    admin_obj = ListingResolutionAdmin(ListingResolution, admin.site)
    request = rf.get("/admin/")
    assert admin_obj.has_add_permission(request) is False
    assert admin_obj.has_change_permission(request) is False
    assert admin_obj.has_change_permission(request, None) is False
    assert admin_obj.has_delete_permission(request) is False
    assert admin_obj.has_delete_permission(request, None) is False


def test_unknown_model_backfill_admin_refuses_all_mutations(rf: RequestFactory) -> None:
    admin_obj = UnknownModelBackfillAdmin(UnknownModelBackfill, admin.site)
    request = rf.get("/admin/")
    assert admin_obj.has_add_permission(request) is False
    assert admin_obj.has_change_permission(request) is False
    assert admin_obj.has_change_permission(request, None) is False
    assert admin_obj.has_delete_permission(request) is False
    assert admin_obj.has_delete_permission(request, None) is False
