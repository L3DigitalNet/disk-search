from datetime import UTC, datetime, timedelta

import pytest
from django.db import connection, transaction
from django.db.utils import IntegrityError

from hw_radar.catalog.models import (
    AvailabilityHeartbeatEvent,
    AvailabilityHeartbeatObservation,
    HeartbeatDecision,
    RetentionClass,
    SourceSite,
)

pytestmark = pytest.mark.django_db


def _site() -> SourceSite:
    return SourceSite.objects.get(normalized_name="serverpartdeals")  # migration-0005 seed


def test_bounded_class_requires_expires_at() -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        AvailabilityHeartbeatObservation.objects.create(
            source_site=_site(),
            source_sku="SKU1",
            observed_at=datetime.now(UTC),
            decision=HeartbeatDecision.UNCHANGED,
            fingerprint="a" * 64,
            retention_class=RetentionClass.AVAILABILITY_HEARTBEAT,
            expires_at=None,  # violates TTL-coherent
        )


def test_observation_persists_with_expiry() -> None:
    now = datetime.now(UTC)
    obs = AvailabilityHeartbeatObservation.objects.create(
        source_site=_site(),
        source_sku="SKU1",
        observed_at=now,
        decision=HeartbeatDecision.UNCHANGED,
        fingerprint="a" * 64,
        retention_class=RetentionClass.AVAILABILITY_HEARTBEAT,
        expires_at=now + timedelta(days=30),
    )
    assert obs.pk is not None


def test_event_persists_with_365d_expiry() -> None:
    now = datetime.now(UTC)
    evt = AvailabilityHeartbeatEvent.objects.create(
        source_site=_site(),
        source_sku="SKU1",
        observed_at=now,
        decision=HeartbeatDecision.TRANSITION_DETECTED,
        fingerprint="a" * 64,
        retention_class=RetentionClass.AVAILABILITY_HEARTBEAT_EVENT,
        expires_at=now + timedelta(days=365),
    )
    assert evt.pk is not None


def test_observation_table_is_hypertable() -> None:
    with connection.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM timescaledb_information.hypertables "
            "WHERE hypertable_name = 'availability_heartbeat_observation';"
        )
        assert cur.fetchone() is not None


def test_event_table_is_not_a_hypertable() -> None:
    with connection.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM timescaledb_information.hypertables "
            "WHERE hypertable_name = 'availability_heartbeat_event';"
        )
        assert cur.fetchone() is None
