"""C.3.4 discovery loop: decoded-but-unknown MPNs crossing the occurrence
threshold become ReferenceFetchRequest rows — the ADR-0018 'unmatched listings
are the discovery signal for catalog gaps' made operational. Threshold is an
ADR-0016 settings row (RefdataConfig). Synthetic 'listing:<id>' hypothesis keys
(no decoded MPN) never enqueue — there is nothing targeted to fetch."""

from __future__ import annotations

from hw_radar.catalog.models import (
    RefdataConfig,
    ReferenceFetchRequest,
    UnknownModelBackfill,
)


def scan_backfill_queue() -> int:
    config = RefdataConfig.current()
    created = 0
    rows = UnknownModelBackfill.objects.filter(
        occurrences__gte=config.discovery_occurrence_threshold,
        mpn_hypothesis__isnull=False,
    )
    for row in rows:
        _, was_created = ReferenceFetchRequest.objects.get_or_create(
            hypothesis_key=row.hypothesis_key,
            defaults={
                "mpn_hypothesis": row.mpn_hypothesis or "",
                "vendor_hint": row.vendor_hint or "",
                "occurrences_at_enqueue": int(row.occurrences),
            },
        )
        created += int(was_created)
    return created
