---
schema_version: '1.1'
id: 'adr-0008-disk-search-currency-landed-cost-normalization'
title: 'ADR 0008: Currency & landed-cost normalization'
description: 'Normalize every listing price to USD via a daily ECB-anchored Frankfurter rate stamped on each observation, fold known domestic shipping (and tax where known) into the $/TB score, and flag cross-border listings rather than applying a fixed international overhead haircut or computing exact duty.'
doc_type: 'adr'
status: 'active'
created: '2026-07-03'
updated: '2026-07-03'
reviewed: null
owner: ''
consumer: 'mix'
tags:
  - 'adr'
  - 'currency'
  - 'fx'
  - 'scoring'
  - 'normalization'
  - 'data-model'
aliases: []
related:
  - 'docs/adr/README.md'
  - 'docs/specs/disk-search.md'
  - 'docs/open-questions.md'
  - 'docs/research/2026-07-03-currency-conversion-and-landed-cost-estimation-for-cross-border-drive-price-scoring.md'
supersedes: []
superseded_by: null
source: []
confidence: 'high'
visibility: 'public'
license: null
project:
  decision_makers:
    - 'chris'
  consulted: []
  informed: []
---

# ADR 0008: Currency & landed-cost normalization

MADR status: **accepted**.

## Context and Problem Statement

The core ranking metric is **USD per TB**, but several of the ranked merchants (ETB Technologies, Bargain Hardware) are UK/EU resellers pricing in **GBP/EUR**, and the buyer is US-based. A cross-border listing scored on its raw foreign price — or on item price alone, ignoring shipping — is ranked on a false basis, which corrupts the one number the whole tool exists to produce.

Two coupled questions fall out of this and must be answered together, because both feed the same `$/TB` computation and the same `observation` schema (ADR 0007):

- **FX** — which rate source normalizes foreign prices to USD, and how is it recorded so a historical score stays reproducible and auditable as rates drift?
- **Landed cost** — how much of the _real_ cost of acquiring a drive (foreign-exchange risk, shipping, import duty, VAT handling) is baked into the score versus surfaced to the buyer as a flag? A precise landed-cost figure is tempting but rests on volatile, jurisdiction-specific inputs.

The research report [`currency-conversion-and-landed-cost-estimation…`](../research/2026-07-03-currency-conversion-and-landed-cost-estimation-for-cross-border-drive-price-scoring.md) analyzes the FX sources and the US import regime directly.

## Considered Options

- **Option 1 — Frankfurter FX → USD stamped per observation; fold known domestic shipping into `$/TB`; flag cross-border cost rather than estimate it.** (chosen)
- **Option 2 — Same FX, but apply a fixed "international overhead" percentage haircut** to cross-border listings so a single comparable number is produced.
- **Option 3 — Compute exact landed cost** (FX + shipping + duty + VAT) per cross-border listing.
- **Option 4 — Score on item price alone**, ignore shipping, leave FX ad hoc.

## Decision Outcome

Chosen option: **Option 1.** Owner-accepted 2026-07-03 (with changes), resolving open-questions.md gaps #3 and #11.

**FX.** Use **Frankfurter** — ECB-anchored, free, no API key, MIT-licensed, self-hostable — refreshed once per day. Normalize every price to USD, and store `fx_rate`, `fx_pair`, `fx_rate_date`, and `fx_source` **on each `observation`** (ADR 0007), not just on the current listing. Stamping the rate per observation is what makes a historical score reproducible and auditable: re-deriving last month's `$/TB` uses the rate that was actually applied, not today's.

**Landed cost is flagged, not estimated.** Normalize the price to USD, then **flag** cross-border listings (e.g. `"international — extra shipping/duty likely; verify before buying"`) and let the buyer decide, rather than encoding a fixed overhead. **Known domestic shipping (and tax where known) _is_ folded into `$/TB`** (gap #11); when shipping is unknown, apply a penalty or flag rather than silently scoring as if free. So the split is: _domestic, knowable_ costs enter the number; _cross-border, volatile_ costs become a flag.

Option 2 was rejected: a hardcoded percentage is **false precision** — the real cross-border surcharge (shipping + potential customs) varies too much to compress into one constant, and a wrong constant silently mis-ranks. Option 3 was rejected because its inputs are in active legal flux and would go stale: as of 2026-07-03 the US **de-minimis exemption is suspended indefinitely** and the add-on tariff rate for UK/EU goods is unsettled; HDDs classify under **HTS 8471.70 at a 0% base (MFN) rate**, so the volatile part is precisely the surcharge the flag defers to the buyer — computing an "exact" duty would manufacture a number that is wrong the moment policy shifts. Option 4 was rejected as the original defect: it misranks a cheap drive with high shipping even domestically.

### Consequences

- **Good** — a single, honest comparison basis: all scores are USD, and domestic listings fold in their real knowable cost.
- **Good** — historical scores are **reproducible and auditable** because the applied FX rate + date live on each observation; no silent retroactive re-pricing when rates move.
- **Good** — no stale hardcoded tariff/overhead constant to maintain against a shifting trade regime; the flag ages gracefully where a number would rot.
- **Good** — Frankfurter adds no API key, no cost, and no vendor lock-in (self-hostable, MIT).
- **Bad (accepted)** — cross-border listings are **not fully comparable**: the buyer must manually weigh the flagged extra cost. This is deliberate — the tool's own analysis is that a cross-border purchase is rarely worthwhile, so surfacing the risk beats fabricating precision.
- **VAT footgun (must be handled in ingestion)** — UK/EU VAT should be **zero-rated on export**, but many storefronts display **VAT-inclusive** shelf prices pre-checkout. The scraper must not treat a VAT-inclusive shelf price as the export price, or it will over-state the true USD cost of an international listing.
- **Neutral** — this ADR fixes the _normalization contract_, not the deal-score math (cohort percentile, warm-up, cohort key) — that is a separate, still-to-be-folded scoring decision (open-questions.md gap #12).

### Confirmation

The spec's `$/TB` scoring and cross-border handling reflect this decision, and gaps #3 and #11 in open-questions.md are recorded settled. Implementation-time confirmation (M1/M2): every non-USD listing carries a stored `fx_rate` + `fx_rate_date` and a normalized USD price; international listings are flagged; domestic listings with known shipping fold it into `$/TB`; a VAT-inclusive foreign shelf price is not mistaken for the export price.

## More Information

- Research: [`currency-conversion-and-landed-cost-estimation…`](../research/2026-07-03-currency-conversion-and-landed-cost-estimation-for-cross-border-drive-price-scoring.md) — FX-source comparison, US de-minimis/tariff status (dated 2026-07-03 — re-verify before relying on the tariff specifics), and the VAT-on-export footgun.
- Related: **ADR 0007** (the `observation` schema these FX fields live on), open-questions.md **gap #3** (currency) and **gap #11** (shipping in `$/TB`), and the still-open scoring math (**gap #12**) that consumes the normalized USD price.
- **Time-sensitive:** the de-minimis-suspended / tariff-in-flux facts carry a 2026-07-03 date — re-verify before shipping any UI copy that quotes duty status.
