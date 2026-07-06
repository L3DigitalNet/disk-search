# TODO

Human-facing work queue. The project builder owns the first section; agents maintain the second section from handoff docs, plans, reviews, and session work.

## User Tracked Tasks

## Agent Tracked Tasks

- [ ] **SanDisk↔WD real-corpus alias verification:** run against seeded catalog aliases before the first WD/SanDisk SSD family seed (plan D7; brand-equivalence descriptor machinery landed at MS-1c).
- [ ] **MS-1d connector must-dos:** enable sources deliberately, wire heartbeat adapters, keep fast-lane to WD/Seagate/eBay, pass `expires_at` through `run_source`, store per-item raw payload rows, revisit Scrapy diagnostics, and classify `httpx.TransportError` as transient before non-USD/API sources go live.
- [ ] **ADR-0019 ratification:** hand-label a real listing corpus, require at least 99.5% precision on auto-accepted rungs 0-2, measure model-grain coverage, then update ADR-0019 and the spec qualifiers if the validation passes.
- [ ] **Recorded test debt:** add coverage for distinct consecutive resolver errors, resolver prior/family branches, and admin permission methods when touching those areas.
- [ ] **eBay delete-on-delist soft-delete path (spec IR-002):** the append-only /
  `PROTECT` ledger posture is owner-confirmed **intentional** (2026-07-05) —
  `Listing.delete()` is deliberately blocked and pinned by
  `test_listing_delete_is_blocked_by_supersede_chain`; hard delete is never the
  path. When the eBay connector lands (MS-1d+), implement listing removal as a
  Listing-grain soft-delete / terminal state (mirroring `RetentionGoverned` +
  `is_current`) to satisfy the eBay delete-on-delist obligation, **without**
  relaxing the resolution-edge `superseded_by` `PROTECT`.

## Maintenance Notes

- Keep open work here; move completed outcomes to `STATUS.md`.
- Preserve the separation between user-owned and agent-tracked tasks.
- Do not store secrets, private hostnames, private IPs, or credential values in this file.
