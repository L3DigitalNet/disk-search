# TODO

Human-facing work queue. The project builder owns the first section; agents maintain the second section from handoff docs, plans, reviews, and session work.

## User Tracked Tasks

## Agent Tracked Tasks

- [ ] **SanDisk↔WD real-corpus alias verification:** run against seeded catalog aliases before the first WD/SanDisk SSD family seed (plan D7; brand-equivalence descriptor machinery landed at MS-1c).
- [ ] **MS-1d connector must-dos (residual):** DONE — `expires_at` threaded through `run_source` (B3), per-item raw payload rows (B4), `httpx.TransportError`→TRANSIENT (B0), fast-lane flags for WD (C3; Seagate/eBay pending their tasks). STILL OPEN — enable sources deliberately at go-live (operational, gated by the E3 SA-004 ops gate; eBay additionally blocked on the delist path below), wire heartbeat *scheduling* in the poller (D1), and revisit Scrapy diagnostics after the `run_spider` `settings_override` change (C2).
- [ ] **WD enterprise recert facet (MS-1d+):** the WD connector's `query=recertified` OCC sweep surfaces WD *consumer* recert (My Book/Elements/My Passport), not the enterprise Gold/Red/Ultrastar recert catalog (recon 2026-07-06; in-code `TODO(MS-1d+)` marker at `sources/wd.py`). The consumer sweep is a valid MS-1 walking connector (per-source gate needs only ≥1 listing); enumerate the enterprise recert facet/category param and prefer it before MS-2 coverage expectations apply.
- [ ] **ADR-0019 ratification:** hand-label a real listing corpus, require at least 99.5% precision on auto-accepted rungs 0-2, measure model-grain coverage, then update ADR-0019 and the spec qualifiers if the validation passes.
- [ ] **Recorded test debt (residual):** distinct-consecutive-error dedup, error-edge recovery, admin permission methods, rung-2 decoder-capacity veto, pure-ladder `oem_fanout`, conflicting-targets / no-brand-evidence REVIEW paths, and WD/HGST/SanDisk brand-equivalence coverage are now pinned. Still open — add a DB-level family-agreement-set veto regression when touching resolver family agreement inheritance.
- [ ] **eBay delete-on-delist soft-delete path (spec IR-002):** the append-only / `PROTECT` ledger posture is owner-confirmed **intentional** (2026-07-05) — `Listing.delete()` is deliberately blocked and pinned by `test_listing_delete_is_blocked_by_supersede_chain`; hard delete is never the path. When the eBay connector lands (MS-1d+), implement listing removal as a Listing-grain soft-delete / terminal state (mirroring `RetentionGoverned` + `is_current`) to satisfy the eBay delete-on-delist obligation, **without** relaxing the resolution-edge `superseded_by` `PROTECT`.

## Maintenance Notes

- Keep open work here; move completed outcomes to `STATUS.md`.
- Preserve the separation between user-owned and agent-tracked tasks.
- Do not store secrets, private hostnames, private IPs, or credential values in this file.
