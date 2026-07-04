---
schema_version: '1.1'
id: automated-test-policy-for-a-low-volume-scrapy-price-monitor
title: Automated Test Policy for a Low-Volume Scrapy Price Monitor
description: Build-time test-strategy finalization for a low-volume Scrapy price monitor — per-extraction-tier canary cadence and degradation alerts, a per-source real-vs-synthetic cassette commit policy, vcrpy PII-scrubbing, a parser-rot-vs-anti-bot failure-classification tree, and GitHub Actions CI wiring. Answers open-questions OQ8 (deep-research prompt #13).
doc_type: research
status: active
created: '2026-07-03'
updated: '2026-07-03'
reviewed: null
owner: chris
tags:
- testing
- web-scraping
- scrapy
- vcrpy
- syrupy
- pydantic
- ci-cd
- canary
- anti-bot
aliases:
- scraper test policy
- vcrpy cassette policy
related: []
source: []
confidence: high
visibility: private
license: null
---

# Automated Test Policy for a Low-Volume Scrapy Price Monitor

## Recommended operating posture

The strongest recommendation is this: keep **real captured HTTP traffic out of a public repository** for the named commercial sources, and use **synthetic or heavily reduced fixtures** for public tests. For your monitoring and parser-development loop, use live traffic only in controlled environments, store only what you need, and let CI stay fully offline with VCR replay in `record_mode="none"`. That recommendation is not just a privacy preference; it follows from a mix of explicit API/storage restrictions, anti-automation clauses, broad copyright/content restrictions, and seller/customer-data exposure on marketplace pages. Amazon’s Product Advertising / Associates terms are especially restrictive on storage and use of Program Content; Google Programmable Search forbids caching or non-transitory storage of results; eBay API terms only allow limited intermediate copies and impose personal-information limits; Newegg, Seagate, and ServerPartDeals each publish anti-automation or similar use restrictions; and WD and goHardDrive reserve site content for restricted, non-commercial use and prohibit broader reproduction/distribution.

Your chosen stack is a good fit for this model. VCR.py’s documented `none` record mode guarantees that no new HTTP requests are made during replay; its request/response filtering hooks are specifically designed to scrub sensitive values before cassettes are written; Syrupy’s normal update path is `pytest --snapshot-update`; Pydantic v2’s model validation gives a hard failure when output no longer conforms to your declared shape; and Scrapy’s selectors are explicitly HTML-structure-dependent, which is why they should be treated as the highest-risk extraction tier.

## Canary cadence and degradation alerts

The defensible monitoring model for a low-volume service is a **tier-weighted canary**, not a uniform cadence. JSON-LD is explicitly intended as structured, machine-readable markup, and Google recommends JSON-LD because it is easier to implement and maintain at scale. By contrast, Scrapy selectors work by binding to HTML structure through CSS/XPath, which is exactly the layer most likely to drift when front-end markup changes. Hidden bootstrap JSON sits between those extremes: it is machine-readable, but usually implementation-detail data for the current front end rather than a stability-promoted contract.

The concrete cadence I would ship for ~20 sources is below. These are **operational recommendations**, not vendor-mandated intervals. They are based on the relative stability of the data source class, the low-volume nature of your monitor, and the fact that the real cost to you is not raw uptime but **undetected bad parses or silent fallbacks**. The volume remains modest even at these frequencies.

| Extraction tier | Stability rationale | Recommended canary frequency | Alert signal |
| --- | --- | --: | --- |
| JSON-LD / schema.org | Machine-readable layer intended for downstream consumers; Google recommends JSON-LD as easier to maintain and less error-prone. | **Every 24 hours** | Alert if primary tier disappears for **2 consecutive runs**, or if required-field coverage drops below **90%** of expected shape while a lower tier succeeds. |
| First-party platform JSON | More stable than DOM selectors because it is application data, but often still a front-end contract rather than a public compatibility promise. | **Every 12 hours** | Alert if endpoint content-type/body shape changes, or if extractor drops to a lower tier for **2 consecutive runs**. |
| Hidden bootstrap / hydration JSON | Still machine-readable, but typically implementation-detail data tied to the current site bundle/layout. | **Every 8 hours** | Alert on any tier downgrade persisting for **2 consecutive runs**, or if field coverage drops by **20%+** against the 30-day median. |
| HTML selectors | Most presentation-coupled and therefore most brittle; Scrapy selectors are directly tied to HTML structure. | **Every 4 hours** | Alert on first hard failure after one retry, and on any sustained zero-result or missing-field condition. |

The key thing you asked about—**silent degradation**—should be treated as a first-class signal independent of “did parsing still work.” The canary needs to emit at least these fields per source and per URL class: `selected_tier`, `expected_best_tier`, `required_fields_present_pct`, `record_count`, `content_type`, `body_bytes`, and a small set of extractor-specific booleans such as `jsonld_found`, `platform_json_found`, and `html_selector_used`. If the parse still validates but `selected_tier` is worse than `expected_best_tier`, that is a **degradation event**, not success. Pydantic is useful here because it gives you a hard contract for the normalized record, but it will not by itself tell you that a source dropped from JSON-LD to HTML and merely happened to remain parseable.

A good default alert rule is:

```text
degradation_alert =
    actual_tier_rank > expected_tier_rank
    AND (
        consecutive_degraded_runs >= 2
        OR degraded_runs_in_last_5 >= 3
    )
```

Then add a second quality rule:

```text
quality_alert =
    model_valid
    AND required_fields_present_pct < max(0.90, rolling_30d_median - 0.20)
```

That splits “hard break” from “still working, but worse than before,” which is exactly the distinction you need for a tiered extractor. This is an engineering recommendation inferred from the stability differences above, not something directly prescribed by the libraries.

If you want a simple source-level formula instead of hardcoded intervals, use:

```text
interval_hours = max(4, min(24, 24 / tier_risk_weight / source_business_weight))
```

with `tier_risk_weight = {jsonld: 1, platform_json: 2, bootstrap_json: 3, html: 6}` and `source_business_weight = 1` for normal sources, `2` for sources that dominate your alerting value or buying decisions. That reproduces the table above for ordinary sources while letting you tighten only the few high-value domains. This formula is a recommendation, not a documented standard.

## Public cassette commit policy

For a **public Git repository**, the conservative answer is that **raw real cassettes from the named sources should be treated as synthetic-only**. The reason is not just one clause from one vendor; it is the cumulative combination of indefinite public redistribution, captured copyrighted page bodies, embedded media, cookies/session artifacts, seller or marketplace metadata, and explicit storage or automation limits on many of the sites you named.

### Decision table

| Source | Terms / retention signal | Public repo decision |
| --- | --- | --- |
| **Amazon Product Advertising / Associates content** | Associates Operating Agreement updated **October 15, 2025**; Amazon Program Content is licensed and not yours, and the broader Amazon Conditions of Use prohibit commercial copying, collection and use of listings/descriptions/prices, and data-mining/robots. | **Synthetic only** |
| **Amazon retail HTML / embedded JSON** | Amazon Conditions of Use prohibit collection/use of product listings, descriptions, and prices for commercial purposes and bar robots/data-mining tools. | **Synthetic only** |
| **Google Programmable Search / Custom Search JSON** | Google’s Programmable Search terms say you may not frame, cache, modify, or in any non-transitory manner store or cache results; the Custom Search JSON API overview also notes the service transition deadline of **January 1, 2027** for existing customers. | **Synthetic only** |
| **Serper-derived SERP data** | Serper ToS updated **May 29, 2024** are more permissive than Google’s direct PSE terms, but still say returned data can contain third-party content whose IP rights remain with the owners, and you may not mirror materials “as-is with no-value-added.” | **Synthetic only** |
| **eBay API content** | eBay API License allows only limited intermediate copies as necessary, requires deletion when no longer required, and imposes personal-information restrictions; the current license page also defines eBay Content and Personal Information broadly. | **Synthetic only** |
| **eBay listing pages / storefronts** | Marketplace pages routinely expose seller identities/feedback and dynamic listing metadata; eBay’s API terms are already restrictive, and raw page bodies are a poor public-fixture choice even aside from API use. | **Synthetic only** |
| **Newegg site** | Newegg terms page, last updated **September 24, 2024**, prohibits automated access, scripts, or web crawlers, and reserves site content for personal, non-commercial use. | **Synthetic only** |
| **ServerPartDeals** | Current Terms of Service prohibit automated use and explicitly say not to scrape, spider, or crawl the service, or bypass robot-exclusion headers. | **Synthetic only** |
| **Seagate site / recert pages** | Seagate Website Use Terms updated **July 24, 2024** restrict use to personal, non-commercial purposes and prohibit use of robots, spiders, site-search/retrieval apps, and data-mining. | **Synthetic only** |
| **Seagate recertified eBay storefront** | Seagate announced its recertified storefront on eBay in **September 2024**; that means the eBay constraints apply even if the seller is the OEM. | **Synthetic only** |
| **WD / Western Digital store** | WD Terms of Use reserve site materials for personal, non-commercial use and prohibit copying/reproduction/distribution without permission. The accessible search result did not surface a clean anti-bot clause, but the reproduction restriction alone makes public raw cassettes a bad fit. | **Synthetic only** |
| **goHardDrive** | goHardDrive Terms reserve site content, allow download/print only for your own non-commercial use or ordering, and prohibit other reproduction/distribution/transmission without authorization. | **Synthetic only** |
| **Generic specialist refurb/server seller** | Unless you have explicit written redistribution rights, a raw cassette is still a copied third-party commercial page. Public accessibility is not the same as redistribution permission; photographs and page content are ordinarily protected. | **Synthetic only by default** |

The practical decision rule is simple:

```text
For a PUBLIC repo, commit a real cassette only if ALL are true:
1) you own or clearly license the captured content for redistribution;
2) the source terms do not prohibit automation, caching, copying, or redistribution;
3) the fixture contains no third-party images, media, cookies, auth, or user/seller PII;
4) the recorded body is reduced to the minimum non-substitutable material needed for the test.

If any condition fails, use a synthetic fixture.
```

For the sources you named, that rule lands on **synthetic only** nearly every time. The safer compromise is to keep **real cassettes private**, keep them short-lived where terms require it, and derive **public synthetic fixtures** from the normalized records your parser emits. That gives you deterministic offline tests without publicly redistributing vendor content.

Product images deserve a bright-line rule of their own: do **not** commit them unless the license explicitly allows redistribution. The U.S. Copyright Office states that copyright protects original photographs, and the rightsholder controls copying and public display absent permission or a valid defense. ServerPartDeals’ own terms also say its manufacturer images are used under license, which is exactly why you should not republish them in your fixtures.

## Scrubbing requirements and vcrpy sketch

The cassette scrubber should assume that **anything request-scoped or user-scoped is hostile to long-term storage**. At minimum, strip authentication headers, cookies, CSRF tokens, session identifiers, API keys, signed query parameters, account IDs, request IDs, geo/shipping context, and any marketplace seller/buyer identifiers that are not part of the normalized public product facts you actually test. VCR.py’s documented mechanisms for this are `filter_headers`, `filter_query_parameters`, `filter_post_data_parameters`, `before_record_request`, and `before_record_response`; and if you enable `decode_compressed_response=True`, decompression happens before your response filter runs.

A good scrub checklist for your use case is:

| Area | Strip or rewrite |
| --- | --- |
| Request headers | `authorization`, `cookie`, `x-api-key`, `x-amz-*`, `x-csrf-token`, bearer/basic auth, signed tracing headers, anything unique-per-session. |
| Request query params | `api_key`, `key`, `token`, `signature`, `sig`, `expires`, `awsAccessKeyId`, session IDs, tracking IDs, marketplace account params. |
| Request body / form data | login credentials, email, postal code, address, CSRF, checkout or cart inputs, hidden auth tokens. |
| Response headers | `set-cookie`, `x-set-cookie`, signed redirect locations, transient IDs, anti-bot cookies/headers, request tracing noise. |
| Response body | customer/seller names, emails, addresses, seller handles, phone numbers, account/order state, anti-bot challenge markup, signed CDN URLs, image URLs, inline base64 images, shipping-destination echoes, ZIP/postal code context. |
| Stored media | Product images, thumbnails, `srcset`, Open Graph / Twitter image tags, downloadable assets. |

A compact VCR.py configuration sketch for this looks like:

```python
import json
import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

import vcr

SENSITIVE_HEADERS = [
    ("authorization", "REDACTED"),
    ("cookie", None),
    ("set-cookie", None),
    ("x-api-key", "REDACTED"),
    ("x-csrf-token", "REDACTED"),
]

SENSITIVE_QUERY_KEYS = [
    ("api_key", "REDACTED"),
    ("key", "REDACTED"),
    ("token", "REDACTED"),
    ("signature", "REDACTED"),
    ("sig", "REDACTED"),
    ("expires", "REDACTED"),
]

BODY_PATTERNS = [
    # emails
    (re.compile(rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), b"redacted@example.invalid"),
    # US ZIP-like strings in explicit shipping contexts
    (re.compile(rb'("zip"|\"postalCode\"|\"postcode\")\s*[:=]\s*"?[0-9A-Za-z -]{3,10}"?', re.I), b'"zip":"REDACTED"'),
    # likely seller/buyer handles in marketplace fragments
    (re.compile(rb'("seller(Name|Id|Username)"\s*:\s*")[^"]+(")', re.I), rb'\1REDACTED\3'),
    # image URLs
    (re.compile(rb'https?://[^"\']+\.(?:png|jpg|jpeg|webp)(?:\?[^"\']*)?', re.I), b"https://example.invalid/redacted-image"),
]

ANTI_BOT_MARKERS = [
    b"/cdn-cgi/challenge-platform/",
    b"cf-mitigated",
    b"captcha",
    b"geo.captcha-delivery.com",
    b"datadome",
    b"just a moment",
]

def _scrub_uri(uri: str) -> str:
    parts = urlsplit(uri)
    params = parse_qsl(parts.query, keep_blank_values=True)
    cleaned = []
    for k, v in params:
        kl = k.lower()
        if kl in {"api_key", "key", "token", "signature", "sig", "expires"}:
            cleaned.append((k, "REDACTED"))
        elif kl in {"session", "sessionid", "sid", "phpsessid"}:
            continue
        else:
            cleaned.append((k, v))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(cleaned), ""))

def before_record_request(request):
    request.uri = _scrub_uri(request.uri)

    # Never record auth/cart/checkout/account flows
    blocked_paths = ("/login", "/signin", "/account", "/cart", "/checkout", "/orders")
    if any(request.path.lower().startswith(p) for p in blocked_paths):
        return None

    return request

def before_record_response(response):
    headers = {k.lower(): v for k, v in response["headers"].items()}

    # Drop response entirely if it is obviously an anti-bot interstitial
    body = response["body"]["string"] or b""
    body_l = body.lower()
    if any(marker in body_l for marker in ANTI_BOT_MARKERS):
        return None

    # Remove cookies and noisy per-request headers
    for h in ["set-cookie", "x-set-cookie", "cf-ray", "x-request-id", "traceparent", "baggage"]:
        headers.pop(h, None)
    response["headers"] = headers

    # Scrub body
    for pattern, repl in BODY_PATTERNS:
        body = pattern.sub(repl, body)

    # Optional: if body is JSON, drop image-ish fields recursively
    ctype = b"".join(headers.get("content-type", [])).lower()
    if b"json" in ctype:
        try:
            data = json.loads(body.decode("utf-8"))
            def walk(x):
                if isinstance(x, dict):
                    return {
                        k: walk(v)
                        for k, v in x.items()
                        if k.lower() not in {"image", "images", "imageurl", "thumbnail", "srcset"}
                    }
                if isinstance(x, list):
                    return [walk(v) for v in x]
                return x
            body = json.dumps(walk(data), separators=(",", ":"), sort_keys=True).encode("utf-8")
        except Exception:
            pass

    response["body"]["string"] = body
    return response

my_vcr = vcr.VCR(
    cassette_library_dir="tests/cassettes",
    decode_compressed_response=True,
    filter_headers=SENSITIVE_HEADERS,
    filter_query_parameters=SENSITIVE_QUERY_KEYS,
    filter_post_data_parameters=[("password", "REDACTED"), ("csrf", "REDACTED")],
    before_record_request=before_record_request,
    before_record_response=before_record_response,
    record_on_exception=False,
    drop_unused_requests=True,
)
```

That sketch stays inside the documented VCR.py hook model: header/query/post-data filters for the obvious secrets, request/response callbacks for the custom redaction and dropping logic, compressed-response decoding before scrub, `record_on_exception=False` so failed updates do not persist garbage, and `drop_unused_requests=True` so old interactions do not accumulate inside cassettes.

## Failure classification

What you want operationally is not “test failed,” but a **triageable class**: parser rot, anti-bot, or transient. Those are materially different incidents. Cloudflare explicitly documents that challenge responses carry `cf-mitigated: challenge` and that challenge pages are `text/html` regardless of the requested resource type. DataDome documents device-check / CAPTCHA / block response pages and uses a `datadome` cookie to track whether the user has passed the challenge. Those are strong, codable anti-bot signals.

### Decision tree

```text
If network exception / timeout / DNS / TLS / 5xx / 408:
    classify TRANSIENT
Else if anti-bot fingerprint present:
    classify ANTI_BOT
Else if authentic page shape present but extraction or validation fails:
    classify PARSER_ROT
Else if model validates but tier worsened or quality cratered:
    classify DEGRADATION
Else:
    classify UNKNOWN and escalate
```

### Codable signals

| Class | Signals you can code |
| --- | --- |
| **Anti-bot protected** | HTTP in `{401, 403, 429, 503}`; **or** header `cf-mitigated=challenge`; **or** request for JSON/API endpoint returns `text/html`; **or** body contains Cloudflare challenge markers such as `/cdn-cgi/challenge-platform/`, `Just a moment`, or CAPTCHA text; **or** `Set-Cookie` / response body includes `datadome` or DataDome challenge assets. |
| **Parser rot** | HTTP 200/OK; expected content-type; body size within normal band; page contains authentic page markers such as canonical/product title/price tokens or known product-page scaffolding; no anti-bot fingerprints; but required extractor paths fail or Pydantic raises `ValidationError` / missing required fields. |
| **Silent degradation** | Pydantic still validates, but `selected_tier` worsens from baseline, required-field percentage drops materially, record count collapses, or high-confidence fields move from structured sources to CSS/XPath-only extraction for repeated runs. |
| **Transient** | Timeout, DNS/TLS exception, 5xx, connection reset, short-lived 429 with retry semantics, or empty/truncated body that resolves on retry and lacks challenge fingerprints. |

A compact implementation model is:

```python
def classify(resp, model_ok, anti_bot_markers, expected_json=False):
    status = getattr(resp, "status", None)
    ctype = resp.headers.get("Content-Type", b"").decode("latin1").lower()
    body = (resp.text or "").lower()

    if status in {408, 500, 502, 503, 504}:
        return "transient"

    if "cf-mitigated" in {k.lower() for k in resp.headers.keys()} and \
       resp.headers.get("cf-mitigated", b"").decode("latin1").lower() == "challenge":
        return "anti_bot"

    if expected_json and "json" not in ctype and "html" in ctype:
        return "anti_bot"

    if any(m in body for m in anti_bot_markers):
        return "anti_bot"

    if not model_ok:
        return "parser_rot"

    return "ok"
```

The **rolling checks** matter as much as per-response signals. Use a rolling baseline for `body_bytes`, `record_count`, and `required_fields_present_pct`. If a source suddenly returns zero valid records across multiple sampled URLs in two consecutive runs, and the raw body is HTML interstitials or challenge text, that is anti-bot. If a single source keeps returning authentic-looking product pages but your selectors or JSON pathing start missing required fields, that is parser rot. If it validates but falls from JSON-LD to HTML for three of the last five canaries, that is silent degradation and should alert before it becomes a hard break. This is an operational inference layered on top of the vendor-documented challenge fingerprints and Pydantic’s validation model.

## GitHub Actions wiring

The cleanest GitHub Actions setup is to split your system into **three separate workflows**:

| Workflow | Trigger | Network policy | Required for PR merge? |
| --- | --- | --- | --- |
| **Offline test** | `pull_request`, `push` | **No live calls**; VCR replay only with `record_mode=none` | **Yes** |
| **Snapshot refresh** | `workflow_dispatch` | Live calls allowed only here, in a trusted/manual path | **No** |
| **Production canary** | `schedule` on default branch | Live calls allowed; alerting path | **No** |

GitHub documents that scheduled workflows run on the latest commit on the default branch, support cron scheduling, and can now use an IANA timezone string; the shortest interval is five minutes, though your proposed cadences are much slower. GitHub also documents that **required status checks** are what gate merges, so the way to keep a broken production canary from blocking unrelated PRs is simply to make the **offline test workflow** required and keep the scheduled canary **separate and non-required**.

### Recommended wiring

For the **offline test workflow**, use VCR replay only and snapshot assertions only:

```yaml
name: tests-offline
on:
  pull_request:
  push:
jobs:
  test:
    runs-on: ubuntu-latest
    env:
      VCR_RECORD_MODE: none
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -e ".[test]"
      - run: pytest -q
```

That aligns with VCR.py’s documented `none` mode, which guarantees no new HTTP requests will be made.

For the **snapshot refresh workflow**, use `workflow_dispatch`, run trusted live recordings, and allow Syrupy updates with `pytest --snapshot-update`. Syrupy’s README documents that as the normal approval/update path and notes that the generated snapshot files should be committed with test code.

For the **production canary**, use `schedule` and keep it entirely separate from required PR checks. On failure, do all three of these in the same workflow: fail the job, produce a concise machine-readable summary, and open or update a GitHub issue. `actions/github-script` is a straightforward way to call the GitHub API from a workflow, and GitHub’s workflow syntax docs show that `issues: write` is the permission you need to work with issues.

A minimal permissions block for that workflow is:

```yaml
permissions:
  contents: read
  issues: write
```

And the key policy choice is this: **do not** add the canary workflow to your branch protection / ruleset as a required check. GitHub’s required-status-check documentation is explicit that required checks are what block merges, and skipped required workflows can leave PRs pending. Keeping the canary as a separate scheduled workflow avoids that failure mode entirely.

## Open questions and limitations

The highest-confidence conclusion is the public-repo one: for the named marketplaces and commercial storefronts, **public raw cassettes are not a good legal or operational fit**. The only realistic “commit to public Git” path is **synthetic fixtures** or fixtures reduced so far that they are effectively your own authored test artifacts.

Two source-specific nuances are worth calling out. WD’s accessible terms evidence was weaker than Seagate/Newegg/ServerPartDeals because the fetched Terms page was not easy to inspect in English lines, but the search result still clearly surfaced a personal, non-commercial use restriction and a no-copy/no-distribution restriction, which is already enough for a conservative synthetic-only recommendation for public fixtures. goHardDrive’s terms, by contrast, were accessible and did **not** surface an explicit no-scraping clause in the fetched text, but they still prohibit broader reproduction/distribution of site content, which is why the public-fixture recommendation remains synthetic-only there as well.

Everything above is a risk-control recommendation, not legal advice. If you later obtain written permission from a specific seller, or a source publishes a redistribution-friendly test-data policy, that should override the conservative defaults here.
