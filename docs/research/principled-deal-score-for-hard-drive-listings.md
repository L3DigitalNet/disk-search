# Principled Deal Score for Hard-Drive Listings

## Executive recommendation

For this use case, I would not use a plain weighted sum. The design I recommend is simpler and more defensible: score **price** relative to a recent comparable cohort using a **cheapness percentile**; convert seller reputation into a cross-marketplace **trust score** with **Bayesian shrinkage** and a **Wilson lower bound**; score **fitness-for-purpose** with an explicit rubric for enterprise/NAS suitability, warranty, and condition; keep **availability** as a bounded operational factor; and combine the four with a **weighted geometric mean**, then apply a small number of explicit **caps** for true veto conditions such as SMR-for-enterprise or used/no-returns. That gives you a score that is self-adjusting as market prices move, harder to game, and much easier to explain listing-by-listing than a black-box ranking or an undocumented weighted sum. Percentile-based normalization is a non-parametric alternative to average-based normalization for skewed distributions, and the weighted product model is the standard multiplicative MCDM analogue of a weighted geometric mean.

The most important design choice is this: treat **price as a relative signal**, not an absolute one. Hard-coded “good if below $X/TB” thresholds age badly in a falling market. A recent reference-set percentile for the same capacity/tier makes the score automatically track the market, which is exactly the logic percentile normalization was introduced for in other skewed, fast-moving domains.

My default weights for a **value-focused enterprise-drive buyer** are:

- **Price:** 0.50  
- **Fitness-for-purpose:** 0.25  
- **Seller trust:** 0.15  
- **Availability:** 0.10  

That weighting says “deal first,” but still makes it hard for a cheap, ill-suited, or risky listing to float to the top. The geometric mean enforces that more naturally than an arithmetic mean because weak dimensions cannot be fully washed out by one strong dimension.

## Normalizing heterogeneous signals

There are really two different normalization problems here. One is **statistical normalization** for continuous, messy variables like $/TB. The other is **semantic normalization** for already bounded or rubric-like variables such as stock state, warranty tier, or condition.

For raw continuous features, the standard options behave very differently. **Min-max scaling** is intuitive and bounded, but it depends directly on the current minimum and maximum, so one new extreme rescales every other listing. **Z-scoring** is the classical \((x-\mu)/\sigma\), but standardization relies on the mean and standard deviation and is explicitly sensitive to outliers. **Robust scaling** swaps those for the median and IQR, which makes it substantially more stable when the distribution is skewed or heavy-tailed. **Quantile transforms** go further: they use the empirical CDF to map values to a uniform or normal target distribution and reduce the impact of marginal outliers, but they are nonlinear and can distort linear relationships.

For **right-skewed positive variables** like $/TB, a **log transform** is the right first instinct. Both methodological summaries and applied examples note that logarithmic transformation is commonly used for positively skewed data and has a normalizing effect on positively skewed distributions. In other words, if you want a distance-from-typical metric, compute it on **log($/TB)**, not on raw $/TB.

That said, for the **actual price score**, I would not stop at log-then-z-score. I would use a **cohort-relative percentile rank**. Percentile/rank normalization is non-parametric, robust to skew, bounded by construction, and easy to explain: “this listing is cheaper than 88% of comparable recent listings.” If you want an auxiliary diagnostic for spacing, keep a **robust log-margin** alongside it: how many IQRs below the cohort median the listing sits. But the ranking signal should be percentile-based.

For bounded rubric variables, do not overcomplicate things. **Availability**, **condition**, **verified warranty tier**, and **enterprise/NAS suitability** are better treated as explicit 0–1 rubrics than as learned continuous transforms. That keeps them audit-friendly and avoids pretending that sparse categorical metadata is a smooth numeric distribution. Interpretable scoring systems are valuable precisely because humans can inspect the rules and see where the score came from.

## Making price relative to a moving baseline

The clean approach is to compute the price score against a **reference set of comparable listings**, not against all hard drives. In the bibliometrics literature, percentile normalization is explicitly defined relative to a **reference set** of similar items rather than to a single global mean; the same logic transfers well here. Your reference set should be as homogeneous as you can make it while still preserving enough sample size.

For hard drives, the default cohort key should be:

- **capacity class**  
- **tier / intended use**: enterprise, NAS-pro, NAS, desktop  
- **interface / form factor** when it materially changes comparability  
- **condition bucket**: new, manufacturer recertified, seller refurb, used pull  

I would maintain the cohort on a **rolling recent window** and decay observations by age so the baseline moves with the market. A practical default is a **90-day trailing window** with **30-day half-life** weights. If the cohort is too small, relax matching in a fixed fallback order that you document: condition first, then adjacent capacity, then parent tier. That gives you stable scores without freezing the market baseline in place.

Use this price subscore:

```text
x_i = USD_i / TB_i
y_i = ln(x_i)

w_j = 2^(-age_days_j / 30)

q_i = weighted_percentile_rank(y_i within cohort C(i), using weights w_j)
      # q_i in [0,1], where 0 = cheapest extreme, 1 = most expensive extreme

n_eff(i) = (Σ w_j)^2 / Σ (w_j^2)
λ_i = min(1, n_eff(i) / 50)

s_price(i) = λ_i * (1 - q_i) + (1 - λ_i) * 0.5
```

A few details matter here. The **sample-size shrinkage** toward 0.5 prevents a tiny cohort from giving an overconfident 99th-percentile score. The **rolling weighted cohort** is what makes the price score self-adjust as street prices fall. And because the score is percentile-based, it is naturally bounded and explainable. The log transform is still useful for your side-channel explanation metric:

```text
price_margin_i = (median_C(y) - y_i) / IQR_C(y)
```

That gives you a sentence like: “priced at the 12th percentile of recent 16TB enterprise-refurb listings, about 0.9 IQR below cohort median on log $/TB.”

If you are tempted to use raw min-max or raw z-scores here, that is where I would push back. Min-max is too hostage to window extremes, and raw z-scores are too sensitive to skew and outliers. Log-plus-percentile is the more durable design for used-storage marketplaces.

## Normalizing seller reputation across marketplaces

This is the hardest part conceptually, because marketplace reputation systems do not mean the same thing.

On **eBay**, the public signals include the **percentage of positive ratings**, the **overall feedback score**, and the **detailed seller ratings**. eBay states that the headline percentage under the username is the share of buyers who had a positive experience, and the bracketed score next to the username is how many buyers have left feedback. eBay also exposes detailed 1–5 star seller ratings for item description, communication, shipping time, and shipping charges.

On **Amazon seller feedback**, buyers use a **5-star system** in which **4 or 5 stars are positive, 3 is neutral, and 1 or 2 are negative**. Amazon also states that seller feedback scores are calculated for **30-day, 90-day, 365-day, and lifetime** windows, and that displayed percentages are rounded.

Those are not directly comparable, so the first step is to convert everything into a common latent quantity:

```text
p_obs = “positive-equivalent rate” in [0,1]
n     = effective count of rating observations
```

Use the following mappings:

```text
eBay:
  p_obs = positive_percent / 100
  n     = bracketed feedback count

Amazon seller feedback:
  p_obs = positive_percent / 100
  n     = count for the same displayed window when available
  prefer 365-day window if exposed and n is adequate; else fallback to lifetime

Star-only marketplaces:
  p_obs = (avg_stars - 1) / 4
  n     = rating count
```

That last mapping is not a platform definition; it is an engineering approximation that places average stars onto a 0–1 positive-equivalent scale. If, later, you accumulate outcome labels such as return rate, DOA rate, or dispute rate, you can replace that linear mapping with a marketplace-specific calibration curve.

Then do **Bayesian shrinkage** on \(p_{\text{obs}}\). In the Beta-Binomial model, a Beta prior stays Beta after observing binomial data, and the posterior mean is \((\alpha + y)/(\alpha+\beta+n)\). That gives you exactly the sample-size discount you want for thinly rated sellers.

Use:

```text
y = p_obs * n

Prior for established marketplaces:
  μ0 = 0.95
  κ  = 20
  α0 = μ0 * κ
  β0 = (1 - μ0) * κ

p_post = (α0 + y) / (α0 + β0 + n)
```

Now add a **Wilson lower bound** so the trust score is not just a posterior mean, but also reflects uncertainty conservatively. Brown, Cai, and DasGupta recommend Wilson among the closed-form alternatives and show that the standard Wald interval performs poorly, especially at small or extreme proportions.

Use the lower bound:

```text
LB = (
      p_obs + z^2/(2n)
      - z * sqrt((p_obs*(1-p_obs) + z^2/(4n))/n)
     ) / (1 + z^2/n)
```

with a practical default of **z = 1.2816** for a moderately conservative one-sided bound. Then combine central estimate and uncertainty floor:

```text
s_seller = 0.6 * p_post + 0.4 * LB
```

For **no rating available**, do not pretend the seller is average. Treat this as a distinct missing-data state. Estimate a marketplace-specific **new-seller prior** from your own history when you have it; until then, a reasonable default is:

```text
major marketplace, no visible ratings: s_seller = 0.60
other marketplace, no visible ratings: s_seller = 0.50
```

That is the one place where you should be explicit that you are using a conservative policy prior rather than hidden math.

One more practical point: score **verified warranty**, not just claimed warranty. WD states that no limited warranty is provided unless the drive was purchased from an authorized distributor or reseller, and Seagate states the same principle for consumer warranty coverage. WD also explicitly excludes products not sold as new and products not used for their intended function, including desktop drives used in an enterprise environment. That means warranty and suitability belong in your fitness rubric, but only when they are actually supportable from listing evidence.

## Combining factors without losing discipline

This is where the weighted geometric mean earns its keep.

A **weighted arithmetic mean** is fully compensatory: a massive price win can cancel a terrible seller or a fundamentally wrong drive class. That is often too forgiving for marketplace hardware. The **weighted product model**, by contrast, is explicitly multiplicative: it multiplies normalized criteria raised to their weights, so weak factors bite harder. That behavior is usually much closer to how an experienced buyer actually thinks about risky storage listings.

Use **hard caps sparingly**. Non-compensatory logic is appropriate when a factor is a real veto rather than a tradeoff variable. Munda’s work on non-compensatory composite indicators is the right conceptual reference here: some dimensions should be allowed to stop a ranking from going higher, rather than merely subtracting a few points.

For this domain, my default caps are:

- **SMR for an enterprise/NAS buyer:** max score **35**
- **Used or seller-refurbished drive with no returns accepted:** max score **60**
- **Seller trust below 0.50:** max score **60**

Everything else should stay soft. Stock state, moderate warranty differences, or a merely okay seller should lower the score continuously, not snap it off at the knees.

I would **not** use TOPSIS as the primary production score. TOPSIS is a ranking method over a finite set of alternatives, based on distance from a positive and negative ideal solution, and it can be useful when you are comparing a batch shortlist. But it is less suitable as a portable listing-level score because the result depends on the current candidate matrix, and the method has known ranking pathologies in multidimensional settings. For a deal monitor, you want a score that means roughly the same thing today, tomorrow, and across scans; a geometric-mean score with explicit rubrics does that better.

## Keeping the score explainable

Explainability here should come from the model structure, not from post-hoc interpretation.

An interpretable scoring system should let a user answer four questions immediately:

- **How cheap is this relative to comparable recent listings?**
- **How much should I trust this seller and why?**
- **Is the drive actually fit for my use case?**
- **Was the score capped by a veto condition?**

That is exactly why a glass-box scoring system is preferable here. Rudin’s work on scoring systems makes the broader point: where people need to inspect and trust a decision, interpretable models are not a cosmetic feature; they are the right model class.

So each listing should expose a structured explanation payload alongside the 0–100 score. A good presentation would be:

```text
Deal score: 93

Top drivers
- Price: cheaper than 92% of recent comparable listings
- Seller: 99.6% positive from 5,000 feedbacks → shrunk trust 0.995
- Fitness: enterprise-class + 2-year verified warranty + manufacturer recert
- Caps: none
```

If a cap applied, show that first:

```text
Cap applied: used drive with no returns → max score 60
```

That kind of explanation is better than a generic “AI ranked this highly” line because it tells the user what they can disagree with. If they are personally comfortable with used/no-return listings, they can override the policy. If they are never willing to touch SMR, they can make the cap stricter. That is the right kind of controllability.

## Recommended formula and worked example

Here is the concrete formula I would ship first.

### Final subscore definitions

```text
Price
  x_i = USD_i / TB_i
  y_i = ln(x_i)
  q_i = weighted_percentile_rank(y_i within recent comparable cohort)
  λ_i = min(1, n_eff / 50)
  s_price = λ_i * (1 - q_i) + (1 - λ_i) * 0.5

Seller trust
  if ratings available:
      y = p_obs * n
      p_post = (α0 + y) / (α0 + β0 + n), with α0 = 19, β0 = 1
      LB = Wilson lower bound with z = 1.2816
      s_seller = 0.6 * p_post + 0.4 * LB
  else:
      s_seller = 0.60 on major marketplaces, else 0.50

Availability
  in stock now                     -> 1.00
  backorder / ships within 7 days -> 0.60
  preorder / ETA unknown          -> 0.30
  out of stock                    -> 0.00

Fitness
  suitability T:
      enterprise / CMR            -> 1.00
      NAS Pro / CMR               -> 0.90
      NAS / CMR                   -> 0.80
      desktop / CMR               -> 0.55
      recording unknown           -> 0.50
      consumer / SMR              -> 0.20

  verified warranty W:
      5-year manufacturer         -> 1.00
      3-year manufacturer         -> 0.85
      2-year verified             -> 0.75
      1-year verified             -> 0.55
      90-day seller warranty      -> 0.30
      none                        -> 0.10

  condition C:
      new / sealed                -> 1.00
      manufacturer recert         -> 0.85
      seller refurb w/SMART proof -> 0.70
      used pull                   -> 0.45
      unknown                     -> 0.35

  s_fit = 0.5*T + 0.3*W + 0.2*C
```

### Final aggregation

```text
Weights
  w_price  = 0.50
  w_fit    = 0.25
  w_seller = 0.15
  w_stock  = 0.10

Base score
  base = Π_k max(s_k, 0.02) ^ w_k

Caps
  cap = 1.00
  if target_use is enterprise/NAS and drive is SMR:       cap = min(cap, 0.35)
  if condition in {used, seller_refurb} and no returns:   cap = min(cap, 0.60)
  if s_seller < 0.50:                                     cap = min(cap, 0.60)

Final
  deal_score = round(100 * min(base, cap))
```

This is a weighted product model with explicit non-compensatory caps. It aligns with the methodological literature on multiplicative MCDM, accommodates Wilson/Beta-Binomial trust estimation, and remains directly inspectable.

### Worked example

The table below uses four hypothetical listings for a value-focused enterprise-drive buyer.

| Listing | Summary | s_price | s_seller | s_fit | s_stock | Cap | Final score |
|---|---|---:|---:|---:|---:|---:|---:|
| A | 16TB enterprise, manufacturer recert, $8.75/TB, eBay 99.6% with 5,000 feedback, 2-year verified warranty, in stock | 0.92 | 0.995 | 0.895 | 1.00 | 1.00 | **93** |
| B | 18TB NAS Pro, new, $11.30/TB, Amazon 97% with 80 ratings, 5-year warranty, backorder ships in 5 days | 0.45 | 0.953 | 0.950 | 0.60 | 1.00 | **62** |
| C | 12TB consumer SMR, new, $7.20/TB, 4.8 stars with 12 ratings, 1-year warranty, in stock, no returns | 0.98 | 0.891 | 0.465 | 1.00 | 0.35 | **35** |
| D | 14TB enterprise used pull, $7.90/TB, eBay 100% with 3 feedback, no warranty, no returns, in stock | 0.95 | 0.832 | 0.620 | 1.00 | 0.60 | **60** |

A few notes on how those numbers were produced:

For **Listing A**, the seller trust is almost maxed out because both the posterior mean and the Wilson lower bound stay extremely high at 99.6% over 5,000 observations. The fitness score is also strong because manufacturer recertified condition and a verified 2-year warranty remain very compatible with a budget-conscious enterprise buyer. The result is exactly what you want a top-ranked deal to look like: cheap, credible, available, and fit-for-purpose.

For **Listing B**, nothing is wrong with the listing. It is simply not a standout deal. The seller is credible, the drive is appropriate, and the warranty is strong, but the price is only mildly attractive relative to its cohort and the listing is not immediately available. That is why it lands in the low 60s instead of the 80s.

For **Listing C**, the geometric mean alone would still give a deceptively decent score because the price is excellent and the seller is not obviously terrible. The **SMR cap** is what keeps the system honest for an enterprise/NAS buyer. This is exactly the kind of case where a soft penalty is not enough.

For **Listing D**, the raw multiplicative score would be much higher because the price is excellent. But a **used pull with no returns** is the canonical reason to apply a hard cap. The tiny feedback count also suppresses seller trust through the Wilson term. This produces a result that says, in effect, “interesting gamble, not a top-tier deal.”

### What I would use in production

If you want the shortest version of the recommendation:

- **Price:** weighted recent-cohort cheapness percentile  
- **Seller:** marketplace-normalized positive-equivalent rate, then Beta-Binomial shrinkage plus Wilson lower bound  
- **Fitness:** explicit rubric for target suitability, verified warranty, and condition  
- **Combination:** weighted geometric mean  
- **Vetoes:** only for real buyer disqualifiers  
- **Explanation:** always show percentile, seller evidence, fitness rubric pieces, and cap reason if any  

That is principled, stable, and easy to defend.