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
