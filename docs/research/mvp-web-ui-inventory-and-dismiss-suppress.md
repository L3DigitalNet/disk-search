---
schema_version: '1.1'
id: mvp-web-ui-inventory-and-dismiss-suppress
title: MVP Web-UI Page Inventory, Dismiss-to-Suppress Model, and Purchase-Tracking Scope
description: Validates the proposed MVP page inventory against CamelCamelCamel, Keepa, changedetection.io, and Slickdeals; recommends a per-listing permanent-suppress model for "dismiss" that reuses the existing watch_match_state row, and recommends deferring purchase-tracking/realized-savings analytics to post-v1.
doc_type: research
status: active
created: '2026-07-04'
updated: '2026-07-04'
reviewed: null
owner: chris
tags:
- ui
- ux
- alerting
- dismiss
- suppress
- purchase-tracking
- django
aliases: []
related:
- opinionated-core-stack-recommendations-for-a-python-drive-price-monitor
- designing-a-low-noise-alerting-layer-for-a-hard-drive-deal-monitor
source: []
confidence: medium
visibility: private
license: null
---

# MVP Web-UI Page Inventory, Dismiss-to-Suppress Model, and Purchase-Tracking Scope

## Bottom line

The proposed MVP page inventory is **confirmed, no additions needed**. For dismiss→suppress, the right model is a **permanent, per-listing suppression flag** — not a TTL, not drive-model-scoped by default — implemented as a new terminal value on the *existing* `watch_match_state.current_state` enum rather than a new table. For purchase tracking, **defer the analytics** (realized-savings, spend history) to post-v1; ship only a lightweight `purchased` status flag with two optional nullable fields (price, date) as scaffolding, because none of the closest comparable tools model savings analytics at all, and the ones that model "purchased" use it purely to stop tracking, not to report on spend.

The evidence for both calls comes from the same place: every comparable tool at this scale — CamelCamelCamel, Keepa, changedetection.io (the closest architectural cousin: self-hosted, single-maintainer-friendly, Python, per-entity watch model), and Slickdeals — treats "I'm done with this" as a **binary, permanent, per-item** action, never a scoped/TTL suppression system. That is a strong signal to keep the design simple rather than inventing a more elaborate suppression model than the domain has ever needed.

## Page inventory validation

| Proposed page | Verdict | Why |
| --- | --- | --- |
| Dashboard (filterable ranked deals) | **Confirmed** | Matches every comparable's core screen — CamelCamelCamel's watch list, Keepa's tracked-products view, changedetection.io's watch table. |
| Listing detail (score breakdown + "why it matched") | **Confirmed** | No comparable tool exposes an explainable score (CCC/Keepa show raw price history only), but this is a deliberate differentiator already settled by the alerting research's "why it matched" email block — reusable as a page, not a new design. |
| Watches / alert-rules manager (hard filters separate from thresholds; no free-text title matching) | **Confirmed** | Directly matches the already-settled `watch` / `watch_selector` schema in the alerting research. No comparable tool exposes rule-authoring UI this rich (CCC/Keepa watches are single-threshold), which is expected — this app's multi-marketplace, multi-tier scope needs more structure than a single-retailer tracker. |
| Price-history view (time-series per drive model) | **Confirmed** | This is CamelCamelCamel's and Keepa's signature feature — validated as core, not optional. |
| Listing-state controls (interested / purchased / dismissed / snoozed) | **Confirmed, with one semantic fix** | See the dismiss→suppress section below — `dismissed` needs a defined effect, not just a label. |
| Django admin as internal back-office | **Confirmed** | Consistent with the stack research's framing of Django admin as an internal tool, never the user-facing surface. |

No comparable tool suggested an MVP page this design is missing. The one thing worth flagging as **explicitly post-MVP, not required now**: a standalone "notification history / sent-alerts log" page. changedetection.io and Alertmanager both expose one, but the already-designed `notification_event` ledger table gives the same auditability via direct DB query or the Django admin — a dedicated page is a nice-to-have once the admin becomes cumbersome, not a v1 requirement.

## Dismiss → suppress model

### What comparable tools actually do

- **CamelCamelCamel** has no concept of "dismiss" independent of the watch itself. The mechanism is binary: a price watch exists (you get alerted) or it's deleted (you don't). Its own wishlist-importer feature makes this pattern explicit — quoting its docs, the importer "will even delete those products marked in your wishlist as purchased." Purchase is treated as **cause for permanent removal**, not a separate suppression state layered on top of an active watch.
- **Keepa** follows the same shape: per-product price-watch thresholds that a user edits or deletes; there is no separate "mute but keep watching" toggle documented or discussed in user forums.
- **changedetection.io** — the closest architectural cousin to this project (self-hosted, single-maintainer-oriented, Python, per-entity watch rows) — models this with a single boolean, `notification_muted`, directly on the watch record (visible in its public API schema: `GET /api/v1/watch` returns `"notification_muted": false` per watch). No TTL, no scope parameter — muting is a permanent per-watch flag until manually unmuted.
- **Slickdeals** (per a historical beta-feature announcement) shipped an **"I Bought This"** button alongside "Report as Expired" — a one-way, per-deal-post tag with no reporting layer built on top of it. It marks the *post* as resolved for that user; it does not feed any savings ledger.
- **Ops-alerting systems** (Alertmanager, PagerDuty) *do* have a richer three-way vocabulary worth borrowing the shape of, even though they're not consumer deal trackers: PagerDuty's **Acknowledge** (temporary — stops re-paging while someone works the issue, but the incident is still open), **Snooze** (an explicit bounded TTL — "remind me again in N hours"), and **Resolve** (permanent close) are three distinct primitives. The useful takeaway isn't to import incident-management complexity wholesale — it's that **"temporary/bounded" and "permanent/done" are different concepts and should not share one flag.**

### Recommendation

Treat **dismiss** and **snooze** as the two primitives, matching the Acknowledge/Snooze/Resolve split above, and keep them at the granularity the alerting research already chose:

1. **Dismiss = permanent, listing-scoped, no TTL.** Add `dismissed` as a new terminal value on the existing `watch_match_state.current_state` enum (today: `none / pending / firing / cooling / digested`). Because that table is already primary-keyed on `(watch_id, listing_fingerprint)`, dismissing a listing under a given watch is a single-row update — no new table, no new suppression-flag plumbing. A listing is suppressed for *that specific offer from that specific seller*, matching CCC's and changedetection.io's precedent of binary, un-timed, per-item suppression. **Do not** default-scope dismiss to the drive model: a user dismissing an overpriced or sketchy-seller listing of a 16TB Exos X18 should not silence a fairly-priced listing of the same drive from a different, reputable seller — that would throw away exactly the cross-marketplace comparison this tool exists to do.
2. **Snooze stays watch-scoped and TTL-bound**, exactly as already designed in the alerting research (`watch.snoozed_until`, plus the email action links `snooze_24h` / `snooze_7d`). This is the bounded-duration lever; dismiss is the permanent one. Keep them visually and semantically distinct in the UI (e.g., "Dismiss this listing" vs. "Snooze this watch for 24h/7d") — the existing alerting-email action list already has both, so this is confirmation of an existing design, not new surface.
3. **No cross-scope default.** Don't offer a "dismiss this drive model everywhere" action as the default dismiss button — if wanted, expose it as a clearly separate, explicit secondary action (mirroring how the email template already separates "Snooze this listing for 7d" from "Stop this watch"). This keeps the common case (one bad listing) cheap and the rare case (genuinely done with this whole model) opt-in and explicit.

This costs nothing beyond one enum value and a state-transition rule ("dismissed is terminal until the listing_fingerprint reappears as a *new* observation, which starts a fresh row") — it does not require inventing a suppression-scope/TTL data model the research hadn't already produced.

## Purchase tracking / realized savings

### What comparable tools do

None of the four comparables ship anything resembling a savings ledger:

- CamelCamelCamel's only purchase-adjacent behavior is using "purchased" as a *deletion trigger* during wishlist sync — not a tracked, reportable state.
- Keepa has no purchase-tracking feature.
- changedetection.io has no purchase concept at all (it's a general change monitor, not a marketplace tool).
- Slickdeals' "I Bought This" (per the historical beta announcement) is a one-way social/expiry signal on a deal post — it closes out that user's interest in that post; it does not carry a price paid, a savings-vs-list-price computation, or any personal spend history.

The complete absence of this feature across every comparable — including the two (CCC, Keepa) whose entire product is Amazon price tracking, where a "total saved" feature would be a natural, high-visibility marketing hook if it worked well — is itself informative. If it were cheap and valuable to build well, at least one of the market leaders would likely have shipped it by now.

### Recommendation: defer the analytics, ship only the flag

**Include:** the `purchased` status is already in the proposed listing-state controls — keep it, because it's needed regardless (once a user buys a drive, the listing should stop generating alerts, which is a natural consequence of the dismiss mechanism above: mark `purchased` and set `current_state = dismissed` on that listing row in the same action). Attach two **optional, nullable** fields to that state transition — `purchase_price` and `purchased_at` — purely as low-cost scaffolding for a future feature, with no UI built on top of them yet (no totals, no "money saved vs. baseline," no reporting page).

**Defer:** any realized-savings computation, spend-history view, or "total saved this year" summary. Rationale:

- **No precedent to validate the UX against.** Every comparable either doesn't have the feature or reduces it to a one-way tag. There's no existing design to adapt, which means building it now would mean designing an entirely new UI pattern speculatively rather than adapting a validated one — exactly the kind of scope this project's MVP should avoid per the spec's phasing intent.
- **The "savings vs. what" question is unresolved and non-trivial.** A meaningful realized-savings number needs a baseline (savings vs. list price? vs. the $/TB baseline the scoring model already tracks? vs. the price at first-alerted?) — that's a design decision this project hasn't made and doesn't need to make for v1, since the scoring subsystem (OQ11) is still being ratified and a savings feature would want to reuse its baseline machinery once stable.
- **Low cost to add later if the flag + two fields exist now.** Because `purchased_at`/`purchase_price` cost nothing to capture at the point of marking a listing purchased, deferring the *reporting* layer doesn't foreclose it — it just avoids building a UI and a savings-math decision speculatively.

## Sources

- CamelCamelCamel: [Features](https://camelcamelcamel.com/features), [Support](https://camelcamelcamel.com/support), wishlist-importer description (via [Amazon Sellers Club summary](https://amazonsellersclub.co/listing/camelcamelcamel/), which quotes the site's own wishlist-import copy).
- changedetection.io: [public API docs](https://changedetection.io/docs/api_v1/index.html) (`notification_muted` field on the watch object).
- Slickdeals: historical beta-feature announcement, ["New Feature in Beta Testing — Deal Display"](https://groups.google.com/g/dealshome/c/Z1Ly-tWI9l0) (Google Groups), describing "I Bought This" and "Report as Expired" buttons.
- PagerDuty: [Edit Incidents](https://support.pagerduty.com/main/docs/edit-incidents), [Mobile App docs](https://support.pagerduty.com/main/docs/mobile-app) (Acknowledge → Snooze button behavior; Snooze vs. Resolve distinction).
- Internal: [`designing-a-low-noise-alerting-layer-for-a-hard-drive-deal-monitor.md`](designing-a-low-noise-alerting-layer-for-a-hard-drive-deal-monitor.md) (existing `watch_match_state` schema, snooze/stop email actions — reused rather than redesigned here); [`opinionated-core-stack-recommendations-for-a-python-drive-price-monitor.md`](opinionated-core-stack-recommendations-for-a-python-drive-price-monitor.md) (Django admin as internal back-office).

## Confidence and caveats

Confidence is **medium**, not high: CamelCamelCamel's and Keepa's internal suppression mechanics are not publicly documented in detail (inferred from support docs, forum discussion, and third-party reviews rather than source code or an admitted internals doc), and the Slickdeals "I Bought This" feature is sourced from a single historical beta announcement rather than current product documentation — it may since have changed or been removed. changedetection.io's `notification_muted` field is the most solidly sourced claim (direct from its public API schema). These are all directional, comparable-tool signals to design against, not load-bearing specifications — the recommendation stands on the reasoning (reuse the existing schema, avoid an unproven speculative feature) more than on any single comparable's exact implementation.
