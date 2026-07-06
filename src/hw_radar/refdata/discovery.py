"""C.3.4 discovery loop: decoded-but-unknown MPNs crossing the occurrence
threshold become ReferenceFetchRequest rows — the ADR-0018 'unmatched listings
are the discovery signal for catalog gaps' made operational. Threshold is an
ADR-0016 settings row (RefdataConfig). Synthetic 'listing:<id>' hypothesis keys
(no decoded MPN) never enqueue — there is nothing targeted to fetch."""

from __future__ import annotations

import logging

from hw_radar.catalog.models import (
    RefdataConfig,
    ReferenceFetchRequest,
    UnknownModelBackfill,
)

logger = logging.getLogger(__name__)

# ReferenceFetchRequest column caps (must match resolution.py).
_HYPOTHESIS_KEY_MAX = 300
_MPN_HYPOTHESIS_MAX = 200


def scan_backfill_queue() -> int:
    config = RefdataConfig.current()
    created = 0
    rows = UnknownModelBackfill.objects.filter(
        occurrences__gte=config.discovery_occurrence_threshold,
        mpn_hypothesis__isnull=False,
    )
    for row in rows:
        # mpn_hypothesis is merchant-controlled (structured attrs_json mpn has no
        # length cap) and the view is an unmanaged read, so an over-length value
        # reaches here uncaught. Skip rather than truncate — a truncated
        # hypothesis is not a valid fetch target and truncation could collide
        # dedup keys. MS-1d hardening: cap the token at decode time instead.
        if len(row.hypothesis_key) > _HYPOTHESIS_KEY_MAX or (
            row.mpn_hypothesis is not None and len(row.mpn_hypothesis) > _MPN_HYPOTHESIS_MAX
        ):
            logger.warning("skipping over-length backfill hypothesis: %s", row.hypothesis_key[:80])
            continue
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
