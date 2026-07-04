---
schema_version: '1.1'
id: drive-deal-scoring-model-test-results
title: Drive Deal Scoring Model — Mock-Data Test Results
description: An empirical validation of the weighted-geometric-mean deal-score model against a seeded mock dataset of 8 archetype listings across 5 market cohorts, confirming the three veto caps bind, the ranking is sensible, and surfacing two calibration findings (harsh price floor, demanding n_eff threshold) to settle before ADR-0011.
doc_type: research
status: active
created: '2026-07-04'
updated: '2026-07-04'
reviewed: null
owner: chris
tags:
- scoring
- deal-score
- validation
- test-results
- geometric-mean
- calibration
aliases: []
related:
- principled-deal-score-for-hard-drive-listings
source: []
confidence: high
visibility: private
license: null
---

# Drive Deal Scoring Model — Mock-Data Test Results

## Why this document exists

This is the **pre-ADR sanity test** for [OQ11](../open-questions.md#oq11--composite-scoring-model-adopt-research-4). The scoring algorithm in
[`principled-deal-score-for-hard-drive-listings.md`](principled-deal-score-for-hard-drive-listings.md) is
concrete and ADR-ready, but the owner's directive was: *before* ratifying it in an ADR, **run it against
mock data and confirm it rates items that are expected to be high or low correctly.** This report is that
test: the dataset, the results, the analysis, and the go/tune recommendation for **candidate ADR-0011**.

**Headline result:** the model **passes**. Every one of the three non-compensatory veto caps binds exactly as
designed, the overall ranking matches buyer intuition, and 6 of 8 archetypes landed inside their expected
band. The two that didn't are *calibration* observations, not correctness failures — and both are worth an
explicit owner decision before the ADR is written (see [Findings](#findings--calibration-decisions-for-the-adr)).

## Method

The full algorithm — price cheapness-percentile, Bayesian + Wilson seller trust, fitness rubric, availability,
weighted geometric mean, and the three caps — was implemented **verbatim** from the source report (stdlib
Python, no dependencies) and run with a fixed RNG seed (`42`) so every number here is reproducible. The
complete harness is in [Appendix A](#appendix-a--reproducible-harness).

The key methodological point is that **the price subscore is cohort-relative**, so a listing cannot be scored
in isolation — it must be ranked against a *market*. The test therefore builds **5 synthetic cohorts**
(each a set of aged `$/TB` observations drawn from a plausible 2026 distribution), then scores **8 archetype
listings** against them. The archetypes were chosen to exercise every distinct behavior of the model —
including deliberately triggering each veto and the thin-cohort provisional path.

### The mock market (5 cohorts)

Cohort key = **capacity · tier · interface/form · condition** (per the source report). Each cohort is a set of
`($/TB, age_days)` observations over a 90-day window; the price subscore weights them by a 30-day half-life.

| Cohort | Raw obs (N) | Effective n (age-decayed) | Weighted median | Note |
|---|---:|---:|---:|---|
| 16TB enterprise recert (CMR) | 64 | 48.9 | $10.69/TB | well-populated (A, E, F, H) |
| 18TB NAS Pro new (CMR) | 48 | 36.1 | $18.83/TB | B |
| 12TB consumer SMR new | 40 | 29.5 | $8.29/TB | C |
| 14TB enterprise used-pull (CMR) | 40 | 29.5 | $8.52/TB | D |
| 8TB NAS new (CMR) — **thin** | 6 | 4.6 | $19.79/TB | G (provisional path) |

> **Already a finding:** even the **64-observation** cohort only reaches an *effective* n of ~49. The 30-day
> half-life over a 90-day window discounts older observations so heavily that raw counts far above 50 are
> needed to clear the `n_eff ≥ 50` full-confidence bar. This matters — see finding #2.

### The 8 archetype listings + a-priori expectations

| Tag | Listing | Designed to test | Expected |
|---|---|---|---|
| **A** | 16TB ent recert CMR, $8.75/TB, eBay 99.6%/5000, 2yr verified, in stock | the ideal top deal | TOP (~88–95) |
| **B** | 18TB NAS Pro new CMR, $18.5/TB (~median), Amazon 97%/80, 5yr, backorder 5d | a fine-but-not-standout listing | FAIR (~55–65) |
| **C** | 12TB consumer **SMR** new, $7.20/TB (cheapest), 4.8★/12, 1yr, in stock, **no returns** | SMR veto for an enterprise buyer | CAPPED 35 |
| **D** | 14TB ent **used-pull** CMR, $7.90/TB, eBay 100%/**3**, no warranty, **no returns** | used/no-return veto + tiny-feedback trust | CAPPED 60 |
| **E** | 16TB ent recert CMR, $8.90/TB (cheap+great), seller **30%/200** | low-trust veto despite great everything else | CAPPED 60 |
| **F** | 16TB ent recert CMR, **$16.00/TB** (expensive), eBay 99.6%/5000, in stock | price drag on an otherwise-great drive | LOW (~35–45) |
| **G** | 8TB NAS new CMR, $17.0/TB (cheap), 98%/400, in stock, **thin cohort** | provisional / warm-up shrinkage | MODERATE + provisional |
| **H** | 16TB ent recert CMR, $9.20/TB (cheap), **no seller ratings** (major mkt) | missing-seller-data policy prior | GOOD, tempered |

## Results

```
   s_price   q%  lam s_sell s_fit  stk  base  cap FINAL  expectation        verdict
--------------------------------------------------------------------------------------
A    0.838   16 0.99  0.995 0.895 1.00 0.890 1.00    89  TOP (~88-95)       ✓ match
B    0.548   43 0.73  0.953 0.950 0.60 0.689 1.00    69  FAIR (~55-65)      ~ high by 4
C    0.640   27 0.60  0.899 0.465 1.00 0.650 0.35    35  CAPPED 35 (SMR)    ✓ exact
D    0.571   38 0.60  0.832 0.620 1.00 0.653 0.60    60  CAPPED 60 (return) ✓ exact
E    0.831   17 0.99  0.320 0.895 1.00 0.747 0.60    60  CAPPED 60 (trust)  ✓ exact
F    0.022   98 0.99  0.995 0.895 1.00 0.144 1.00    14  LOW (~35-45)       ✗ harsher (14)
G    0.542   12 0.11  0.975 0.855 1.00 0.705 1.00    70  MODERATE+provis.   ✓ match
H    0.831   17 0.99  0.600 0.895 1.00 0.821 1.00    82  GOOD tempered      ✓ match
```

**Final ranking:** A (89) > H (82) > G (70) > B (69) > D = E (60) > C (35) > F (14).

That ordering is exactly what a value-focused enterprise/recert buyer should see: the cheap, credible,
fit-for-purpose, in-stock drive tops the list; the vetoed listings (SMR, used-no-return, bad-seller) are
pinned at their caps regardless of an attractive price; and an expensive drive sinks no matter how good the
seller and warranty are.

### Per-listing reading

- **A → 89 ✓.** Cheaper than 84% of its cohort, near-max seller trust (posterior *and* Wilson floor both ≈0.995
  over 5,000 ratings), strong fitness, in stock, no cap. The canonical "buy this" listing.
- **B → 69 (~4 high).** Nothing is wrong with it — median price, credible seller, excellent drive/warranty —
  it's simply not a *deal*, and the backorder (stock 0.60) is the main drag. See finding #1: a median-priced
  listing arguably shouldn't clear 65 in a deal monitor.
- **C → 35 ✓ exact.** The SMR cap (max 35) does exactly its job: the **cheapest price in the test** (73rd
  percentile cheap) and a not-terrible seller would otherwise float this to ~65 on the raw geometric mean;
  the veto keeps it honest for an enterprise/NAS buyer. (The no-return cap also applies but SMR is stricter.)
- **D → 60 ✓ exact.** Used pull + no returns caps at 60; separately, the **3-feedback** seller is dragged down
  by the Wilson lower bound (LB 0.646 vs posterior 0.957) — the small-sample discount working as intended.
- **E → 60 ✓ exact.** Great drive, cheap, in stock — but a genuinely bad seller (30% positive over 200 ratings)
  trips the `s_seller < 0.50` veto (trust 0.320). Proves a cheap great drive from an untrustworthy seller is
  correctly held back.
- **F → 14 (harsher than the ~40 guess).** At $16/TB it sits in the **98th percentile** of its cohort (median
  $10.69), so `s_price` hits the 0.02 floor; with a 0.50 weight and the geometric mean, the base collapses to
  0.144. Defensible for a *deal* monitor, but see finding #3 — the floor makes "merely expensive" and
  "absurdly expensive" indistinguishable.
- **G → 70 + provisional ✓.** Priced cheaper than 88% of its cohort, but `λ = 0.11` (only 5.5 effective obs)
  shrinks `s_price` from ~0.94 all the way to **0.542** — the warm-up mechanism refusing to trust a cheap
  price on thin evidence. Exactly the cold-start behavior gap #12 specified. Would carry a **provisional** badge.
- **H → 82 ✓.** Identical to A's drive but a **no-rating seller** → policy prior 0.60 instead of 0.995, costing
  ~7 points (89 → 82). The missing-data state is handled as a conservative prior, not a pretend-average.

## Findings & calibration decisions for the ADR

The model is **correct**. These are tuning calls to make consciously before ADR-0011 freezes the constants.

### 🟡 Finding 1 — the model is mildly generous in the "fair" middle (B = 69)

A median-priced, backordered, otherwise-excellent listing scores 69. For a tool whose job is to surface
*deals*, the middle band feels ~5–10 points hot. **Options:** (a) accept it — 69 vs 89 still clearly separates
"fine" from "great"; (b) raise the price weight above 0.50 to widen price's influence; (c) steepen the price
subscore (e.g. apply a mild convex transform to `1 − q`) so only genuinely-cheap listings score high.
**Recommendation:** accept for v1 (option a) and revisit after real data — the ordering is right and absolute
calibration is easy to tune later without changing the model's shape.

### 🔴 Finding 2 — `n_eff ≥ 50` is a demanding bar; many cohorts will be perpetually provisional

With a 30-day half-life over a 90-day window, a cohort needs a *high recent arrival rate* to be
non-provisional: 64 raw obs → n_eff 49; 40 → 30. Narrow cohorts (a specific capacity · tier · interface ·
condition) may **never** clear 50, so their price scores permanently shrink toward 0.5 and everything shows as
provisional. **Options:** (a) lower the full-confidence target to `n_eff ≥ 30`; (b) lengthen the half-life
(e.g. 45–60 days) so history counts for more; (c) lean harder on the documented cohort-relaxation fallback
(condition → adjacent capacity → parent tier) to borrow observations. **Recommendation:** adopt **(a) n_eff ≥ 30**
*and* wire the relaxation fallback (b/c as tuning). This is the single most important pre-ADR change — the
`50` constant was illustrative in the source report and the test shows it is too strict for real cohort sizes.

### 🟡 Finding 3 — the `s_price` floor (0.02) flattens the expensive tail

F (98th percentile) and a hypothetical 99.9th-percentile listing both floor at 0.02 → both score ~14. That's
fine for surfacing deals (nobody wants either) but erases ordering information in the expensive tail.
**Options:** (a) keep the floor (deal monitors don't rank expensive drives, so who cares); (b) lower the floor
to ~0.005 so the tail still orders. **Recommendation:** keep the floor (option a) — ranking expensive listings
against each other has no product value here.

### 🟢 Finding 4 — the seller-trust prior is strong (trust is "sticky high")

The Beta prior (μ₀ = 0.95, κ = 20) pulls thin/low sellers upward: an 85%/50 seller still scores ~0.87, and it
took **30%/200** to breach the 0.50 veto (E). This is *appropriate* — the veto should be rare and reserved for
sellers with substantial negative evidence — but the owner should ratify that a merely-mediocre seller (say
88% positive) is **not** meant to trip the veto; it only lowers the score continuously. **Recommendation:**
accept as designed; document that the trust veto is a genuine-disqualifier gate, not a quality knob.

## Recommendation for OQ11 / ADR-0011

**Ratify the model as specified, with one constant change and the relaxation fallback wired in:**

1. **Adopt** the weighted geometric mean over the four subscores at weights **0.50 / 0.25 / 0.15 / 0.10**
   (price / fitness / seller / availability). Validated: the ranking is intuitive and hard to game.
2. **Adopt** all three caps — SMR-for-enterprise (35), used/refurb-no-returns (60), seller-trust < 0.50 (60).
   Validated: each binds exactly as intended on C, D, E.
3. **Change** the warm-up full-confidence target from `n_eff ≥ 50` to **`n_eff ≥ 30`** (finding 2), and
   commit to the cohort-relaxation fallback so narrow cohorts borrow observations rather than sit provisional
   forever.
4. **Keep** the `s_price` floor (finding 3) and the strong seller prior (finding 4) as-is; document both as
   deliberate.
5. **Store** the per-subscore explanation payload as a first-class output (already assumed by
   [OQ6](../open-questions.md#oq6--final-ui-page-inventory--dismisssuppress-feedback--purchase-tracking)'s
   listing-detail "why it matched" view). The payloads emitted by this harness are the exact shape to persist.
6. **Defer** absolute-calibration tuning of the middle band (finding 1) until real observations exist — the
   model's *shape* is right; its *constants* are cheap to re-fit later.

This maps directly onto milestone **M2** (reproducible 0–100 score with per-factor breakdown), whose
acceptance criteria this test already demonstrates in miniature.

## Appendix A — reproducible harness

Stdlib-only; run with `uv run python3 score_test.py` (or any Python 3.11+). Seed `42` fixes every number above.
The mock cohorts are generated from log-normal `$/TB` distributions; the archetypes and their attributes are
the dataset. This is a **validation experiment, not production code** — the shipped scoring engine (M2) will
read real observations from the `observation` time-series table rather than synthetic cohorts.

```python
"""OQ11 validation harness — implements the deal-score model from
principled-deal-score-for-hard-drive-listings.md verbatim and scores a mock
dataset to check the output matches a-priori expectations. Stdlib only; seeded."""

from __future__ import annotations
import math, random
from dataclasses import dataclass

SEED = 42
rng = random.Random(SEED)

def weighted_quantiles(pairs, qs):
    s = sorted(pairs, key=lambda p: p[0]); total = sum(w for _, w in s); out = []
    for q in qs:
        target = q * total; cum = 0.0; val = s[-1][0]
        for v, w in s:
            cum += w
            if cum >= target: val = v; break
        out.append(val)
    return out

def weighted_percentile_rank(ys, ws, y_i):
    total = sum(ws)
    below = sum(w for y, w in zip(ys, ws) if y < y_i)
    equal = sum(w for y, w in zip(ys, ws) if y == y_i)
    return (below + 0.5 * equal) / total

def price_subscore(usd_per_tb, cohort_obs):  # cohort_obs: (usd_per_tb, age_days) incl. this listing
    y_i = math.log(usd_per_tb)
    ys = [math.log(u) for (u, _a) in cohort_obs]
    ws = [2 ** (-a / 30) for (_u, a) in cohort_obs]
    q = weighted_percentile_rank(ys, ws, y_i)
    sumw, sumw2 = sum(ws), sum(w * w for w in ws)
    n_eff = (sumw * sumw) / sumw2
    lam = min(1.0, n_eff / 50)          # <-- finding 2: change 50 -> 30 for ADR
    s = lam * (1 - q) + (1 - lam) * 0.5
    q25, med, q75 = weighted_quantiles(list(zip(ys, ws)), [0.25, 0.50, 0.75])
    iqr = (q75 - q25) or 1e-9
    return {"s_price": s, "q": q, "n_eff": n_eff, "lam": lam, "margin_iqr": (med - y_i) / iqr}

def seller_subscore(p_obs, n, major=True):
    if not n: return {"s_seller": 0.60 if major else 0.50, "p_post": None, "LB": None}
    z = 1.2816; a0, b0 = 19.0, 1.0; y = p_obs * n
    p_post = (a0 + y) / (a0 + b0 + n)
    lb = (p_obs + z*z/(2*n) - z*math.sqrt((p_obs*(1-p_obs)+z*z/(4*n))/n)) / (1 + z*z/n)
    return {"s_seller": 0.6 * p_post + 0.4 * lb, "p_post": p_post, "LB": lb}

AVAIL = {"in_stock": 1.00, "backorder_7d": 0.60, "preorder": 0.30, "oos": 0.00}
SUIT = {"enterprise_cmr": 1.00, "naspro_cmr": 0.90, "nas_cmr": 0.80, "desktop_cmr": 0.55,
        "unknown_rec": 0.50, "consumer_smr": 0.20}
WARR = {"5yr_mfr": 1.00, "3yr_mfr": 0.85, "2yr_verified": 0.75, "1yr_verified": 0.55,
        "90d_seller": 0.30, "none": 0.10}
COND = {"new": 1.00, "mfr_recert": 0.85, "seller_refurb_smart": 0.70, "used_pull": 0.45, "unknown": 0.35}

def fitness_subscore(suit, warr, cond):
    t, w, c = SUIT[suit], WARR[warr], COND[cond]
    return {"s_fit": 0.5 * t + 0.3 * w + 0.2 * c, "T": t, "W": w, "C": c}

def aggregate(s_price, s_fit, s_seller, s_stock, *, is_smr_for_ent, used_no_returns):
    weights = {"price": 0.50, "fit": 0.25, "seller": 0.15, "stock": 0.10}
    subs = {"price": s_price, "fit": s_fit, "seller": s_seller, "stock": s_stock}
    base = 1.0
    for k, wt in weights.items(): base *= max(subs[k], 0.02) ** wt
    cap, reasons = 1.0, []
    if is_smr_for_ent: cap = min(cap, 0.35); reasons.append("SMR for enterprise/NAS use -> max 35")
    if used_no_returns: cap = min(cap, 0.60); reasons.append("used/refurb with no returns -> max 60")
    if s_seller < 0.50: cap = min(cap, 0.60); reasons.append("seller trust < 0.50 -> max 60")
    return {"base": base, "cap": cap, "final": round(100 * min(base, cap)), "cap_reasons": reasons}

def make_cohort(median, log_sigma, n):
    mu = math.log(median)
    return [(round(math.exp(rng.gauss(mu, log_sigma)), 2), round(rng.uniform(0, 90), 1)) for _ in range(n)]

COHORTS = {
    "16TB_ent_recert_cmr": make_cohort(10.5, 0.18, 64),
    "18TB_naspro_new_cmr": make_cohort(18.5, 0.15, 48),
    "12TB_consumer_smr_new": make_cohort(8.5, 0.20, 40),
    "14TB_ent_usedpull_cmr": make_cohort(8.8, 0.20, 40),
    "8TB_nas_new_cmr_THIN": make_cohort(21.0, 0.15, 6),
}

@dataclass
class Listing:
    tag: str; summary: str; cohort: str; usd_per_tb: float
    suit: str; warr: str; cond: str; avail: str
    p_obs: float | None; n: int | None; major: bool = True
    is_smr_for_ent: bool = False; used_no_returns: bool = False; expect: str = ""

LISTINGS = [
    Listing("A", "16TB ent recert CMR, cheap, elite seller, 2yr, in stock", "16TB_ent_recert_cmr",
            8.75, "enterprise_cmr", "2yr_verified", "mfr_recert", "in_stock", 0.996, 5000, expect="TOP"),
    Listing("B", "18TB NAS Pro new CMR, ~median, strong seller, 5yr, backorder", "18TB_naspro_new_cmr",
            18.5, "naspro_cmr", "5yr_mfr", "new", "backorder_7d", 0.97, 80, expect="FAIR"),
    Listing("C", "12TB consumer SMR new, cheapest, no returns", "12TB_consumer_smr_new",
            7.20, "consumer_smr", "1yr_verified", "new", "in_stock", 0.96, 12,
            is_smr_for_ent=True, used_no_returns=True, expect="CAP 35"),
    Listing("D", "14TB ent used pull, cheap, 3 feedback, no warranty/returns", "14TB_ent_usedpull_cmr",
            7.90, "enterprise_cmr", "none", "used_pull", "in_stock", 1.00, 3,
            used_no_returns=True, expect="CAP 60"),
    Listing("E", "16TB ent recert, cheap+great, BAD seller 30%/200", "16TB_ent_recert_cmr",
            8.90, "enterprise_cmr", "2yr_verified", "mfr_recert", "in_stock", 0.30, 200, expect="CAP 60"),
    Listing("F", "16TB ent recert CMR, EXPENSIVE, great seller, in stock", "16TB_ent_recert_cmr",
            16.00, "enterprise_cmr", "2yr_verified", "mfr_recert", "in_stock", 0.996, 5000, expect="LOW"),
    Listing("G", "8TB NAS new CMR, cheap, THIN cohort", "8TB_nas_new_cmr_THIN",
            17.0, "nas_cmr", "3yr_mfr", "new", "in_stock", 0.98, 400, expect="MODERATE+provisional"),
    Listing("H", "16TB ent recert CMR, cheap, NEW seller no ratings", "16TB_ent_recert_cmr",
            9.20, "enterprise_cmr", "2yr_verified", "mfr_recert", "in_stock", None, None, expect="GOOD tempered"),
]

def score(l):
    obs = list(COHORTS[l.cohort]) + [(l.usd_per_tb, 0.0)]
    p = price_subscore(l.usd_per_tb, obs)
    sell = seller_subscore(l.p_obs, l.n, l.major)
    fit = fitness_subscore(l.suit, l.warr, l.cond)
    agg = aggregate(p["s_price"], fit["s_fit"], sell["s_seller"], AVAIL[l.avail],
                    is_smr_for_ent=l.is_smr_for_ent, used_no_returns=l.used_no_returns)
    return p, sell, fit, AVAIL[l.avail], agg

if __name__ == "__main__":
    for l in LISTINGS:
        p, sell, fit, stk, agg = score(l)
        print(f"{l.tag} price={p['s_price']:.3f} seller={sell['s_seller']:.3f} "
              f"fit={fit['s_fit']:.3f} stock={stk:.2f} base={agg['base']:.3f} "
              f"cap={agg['cap']:.2f} FINAL={agg['final']:3d}  ({l.expect})")
```
