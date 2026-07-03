# Designing a Low-Noise Alerting Layer for a Hard-Drive Deal Monitor

## Bottom line

For this kind of deal monitor, the right mental model is **stateful alerting**, not “send a message every time a poll matches a predicate.” The useful architectures in monitoring systems all converge on the same controls: deduplicate repeated detections of the same condition, wait briefly so short-lived or conflicting signals can settle, batch related notifications, use separate enter and recovery thresholds to prevent flapping, and cap repeat frequency. Prometheus Alertmanager explicitly centers grouping, deduplication, routing, silencing, `group_wait`, `group_interval`, and `repeat_interval`; FireHydrant does the same with idempotency keys and configurable dedup windows; Splunk documents both per-field throttling and suppression groups for families of similar alerts; and Datadog documents recovery thresholds specifically to reduce flapping.

For your use case, the best default is:

- **Email as the guaranteed channel**, but sent through a transactional provider API rather than direct SMTP from a Hetzner VM.
- **A second, cheaper “high-urgency personal push” channel** before SMS. Pushover is the cleanest hobby-scale paid option; ntfy and Telegram are strong if you want self-host / hackable options.
- **Instant alerts only for state transitions that matter**: newly available, first threshold crossing, or a materially better price than the last-alerted state.
- **Digest everything else**: minor price improvements, repeated sightings, and “still available” confirmations.

My strongest recommendation is to **not send raw mail directly from the Hetzner VM to destination MX hosts** unless you intentionally want email-delivery engineering as a separate project. Hetzner blocks outbound ports 25 and 465 by default on cloud servers and recommends using port 587 with external mail delivery services instead. Gmail and Yahoo expect authentication, DNS correctness, TLS, and low complaint rates; Gmail also calls out reverse DNS and the reputation impact of shared IPs, while Spamhaus emphasizes that IP/domain reputation is foundational to inbox placement. On a small sender with a fresh datacenter IP, an external provider is the lower-noise, higher-reliability path.

## Noise-resistant alerting patterns

The cleanest design is to treat each incoming observation as an input to a **per-watch, per-listing state machine**. A notification is emitted only when that state machine crosses a meaningful boundary.

A good default event taxonomy is:

- `became_available`
- `crossed_price_threshold`
- `crossed_price_per_tb_threshold`
- `crossed_score_threshold`
- `material_improvement_since_last_alert`
- `entered_digest_queue`

This maps well to the alerting patterns used by operational systems. Alertmanager’s `group_wait` exists precisely because immediate notification can be worse than waiting a short time for related alerts or inhibiting conditions to arrive; if an alert resolves before `group_wait` expires, no notification is sent, which directly reduces flapping noise. Its `group_interval` and `repeat_interval` then separate “new information in the same group” from “same old thing, remind me later.”

### Deduplication

Use **two fingerprints**, not one:

1. **Listing fingerprint**  
   Stable identity for “this marketplace listing / offer.”  
   Prefer marketplace-native IDs. Fall back to a canonical hash of normalized URL path, marketplace, seller, normalized model, capacity, and condition.

2. **Alert fingerprint**  
   Stable identity for “this watch was alerted for this reason on this listing.”  
   Example: `sha256(watch_id | listing_fingerprint | reason_code | threshold_bucket)`.

That gives you the equivalent of FireHydrant’s `idempotency_key`: duplicates of the same condition collapse into one alert record, while a new reason or meaningfully different state can still generate a new signal. FireHydrant’s guidance is exactly the right shape here: the key should be unique per condition, consistent across repeat occurrences, and must not include random values or timestamps.

Practical rules:

- If the **same alert fingerprint** reappears inside the dedup window, increment a counter and update `last_seen_at`, but do not re-notify.
- If the **listing fingerprint** is the same but the reason changed from `entered_digest_queue` to `crossed_price_threshold`, allow the stronger event to supersede the weaker one.
- If the supplier republishes the same offer under a new URL, use a second-pass similarity key so obvious reposts do not bypass dedup.

### Debouncing and cooldowns

Debounce before first send. In operational alerting, short waits eliminate a lot of false-positive churn; in your domain, a listing that appears once and vanishes on the next poll is often not worth an instant email. Prometheus documents this exact effect with `group_wait`. Splunk’s throttling guidance also supports a field-based suppression concept: once an alert has triggered for a particular result key, subsequent events with the same values are suppressed for the throttling period.

A strong default policy is:

| Condition | Initial debounce | Cooldown | Re-alert bypass |
|---|---:|---:|---|
| Newly available and meets thresholds | 2 consecutive polls or 2–5 min stable | 12 h | Price improves by max($10, 5%) or score improves materially |
| First price threshold crossing | 1 consecutive poll if availability confirmed; else 2 polls | 12 h | Another threshold bucket crossed |
| Minor repeated sightings | none | digest only | never instant |
| “Still available” confirmations | none | off by default | n/a |

That gives you the right asymmetry: **rare, meaningful transitions notify immediately; ongoing sameness becomes digest material**.

### Thresholds and hysteresis

This is the single most important anti-noise feature after dedup.

Datadog’s recovery-threshold documentation is directly applicable: use **one threshold to enter** an alert condition and a stricter one to recover from it, so the system does not oscillate around a single boundary. The same logic works for price, $/TB, score, and even availability confidence.

Recommended hysteresis rules:

- **Absolute price**  
  Fire when `price <= target_price`.  
  Recover only when `price >= target_price + max($5, target_price * 0.03)`.

- **$/TB**  
  Fire when `price_per_tb <= target_price_per_tb`.  
  Recover only when `price_per_tb >= target_price_per_tb * 1.03`.

- **Score**  
  Fire when `score >= min_score`.  
  Recover only when `score <= min_score - 3`.

- **Availability**  
  Fire when availability is `in_stock` for 2 consecutive polls, or when the source is high-confidence.  
  Recover only after 2–3 consecutive `out_of_stock` / `gone` observations.

This avoids the classic “$199.99 / $200.01 / $199.98 / $200.03” spam loop.

### Digesting and rate caps

Alertmanager separates “new information in the same group” from “repeat reminder” with `group_interval` and `repeat_interval`; Splunk suppression groups suppress whole families of similar alerts when one of them fires. Those are good models for per-watch digests and rate caps.

A practical strategy:

- **Instant lane**
  - first time a listing becomes available and matches
  - first threshold crossing
  - materially better price than already-alerted state

- **Hourly digest**
  - multiple matching listings for the same watch
  - repeated sightings of already-alerted listings
  - small improvements that do not justify another instant notification

- **Daily roundup**
  - “best current deals for each active watch”
  - stale-but-still-good items
  - score/price trend summary if you collect history

Per-watch caps should exist at two levels:

- **Instant cap per watch**: for example, max 3 instant alerts in 6 hours, max 8 per day.
- **Global user cap**: for example, max 12 total instant messages per day across all watches, after which anything else is digest-only.

That is conceptually similar to Splunk’s per-result throttling plus suppression groups: suppress the same thing repeatedly, and suppress clusters of similar things when one representative signal already told the story.

## Watch model and matching engine

The clean rule model is **structured criteria + delivery policy + state**, not a monolithic boolean expression blob.

The core design choice is this: **normalize observations hard, keep watches simple, and make matching mostly data-driven**. In other words, do the messy parsing once when an observation arrives, rather than forcing every alert rule to compensate for bad titles and marketplace weirdness.

A minimal relational sketch:

```sql
-- User-facing rule
watch (
    id uuid primary key,
    user_id uuid not null,
    name text not null,
    enabled boolean not null default true,

    -- hard matching scope
    model_id uuid null,               -- exact model if known
    family_id uuid null,              -- Exos X18 / Ultrastar / IronWolf, etc.
    min_capacity_tb numeric null,
    max_capacity_tb numeric null,
    tier text[] null,                 -- enterprise, nas, desktop, refurb, etc.
    marketplace_allowlist text[] null,
    marketplace_denylist text[] null,

    -- threshold predicates
    max_price numeric null,
    max_price_per_tb numeric null,
    min_score numeric null,

    -- delivery policy
    channel_policy jsonb not null,    -- email instant, push instant, sms critical-only
    instant_enabled boolean not null default true,
    digest_mode text not null default 'hourly',   -- off/hourly/daily
    debounce_polls integer not null default 2,
    cooldown_minutes integer not null default 720,
    hysteresis jsonb not null,        -- e.g. {"price_abs":5,"price_pct":0.03,"score":3}
    rate_caps jsonb not null,         -- e.g. {"instant_6h":3,"instant_day":8}

    snoozed_until timestamptz null,
    created_at timestamptz not null,
    updated_at timestamptz not null
);

-- Canonical parsed observation
observation (
    id uuid primary key,
    observed_at timestamptz not null,
    marketplace text not null,
    external_listing_id text null,
    canonical_url text not null,
    seller_id text null,
    model_id uuid null,
    family_id uuid null,
    capacity_tb numeric null,
    tier text[] null,
    score numeric null,
    price numeric null,
    price_per_tb numeric null,
    availability text not null,       -- in_stock / maybe / out / gone
    raw_payload jsonb not null
);

-- Per-watch, per-listing evaluation state
watch_match_state (
    watch_id uuid not null,
    listing_fingerprint text not null,
    current_state text not null,      -- none / pending / firing / cooling / digested
    reason_code text null,
    first_matched_at timestamptz null,
    last_seen_at timestamptz null,
    last_notified_at timestamptz null,
    last_notified_price numeric null,
    last_notified_score numeric null,
    consecutive_match_count integer not null default 0,
    consecutive_miss_count integer not null default 0,
    digest_bucket_at timestamptz null,
    occurrence_count integer not null default 0,
    primary key (watch_id, listing_fingerprint)
);

-- Sent notifications / dedup ledger
notification_event (
    id uuid primary key,
    watch_id uuid not null,
    listing_fingerprint text not null,
    alert_fingerprint text not null unique,
    channel text not null,
    reason_code text not null,
    sent_at timestamptz not null,
    payload_hash text not null,
    provider_message_id text null
);
```

The important modeling choice is to keep **hard filters** separate from **thresholds**:

- Hard filters determine candidate applicability: model, family, capacity range, tier, marketplace.
- Thresholds determine whether the candidate is “interesting enough”: max price, max $/TB, min score.

That matters because it lets you narrow candidate watches efficiently before evaluating thresholds.

### Efficient matching

For hobby scale, a relational matcher is enough if you normalize observations well. For larger scale, use an inverted index.

A practical two-stage matcher:

```text
normalize observation
→ derive match keys
→ fetch candidate watches by selective keys
→ evaluate hard predicates
→ evaluate thresholds
→ update watch_match_state
→ enqueue instant or digest
```

Recommended candidate keys:

- `model_id`
- `family_id`
- capacity bucket, e.g. `12TB`, `14TB`, `16TB`
- tier token
- marketplace token

You can materialize these in a helper table like:

```sql
watch_selector (
    watch_id uuid not null,
    selector_type text not null,   -- model, family, capacity_bucket, tier, marketplace
    selector_value text not null,
    primary key (watch_id, selector_type, selector_value)
);
```

Then candidate matching becomes:

1. pull the union of watches matching any high-selectivity key on the observation,
2. intersect with enabled / not-snoozed,
3. evaluate remaining hard predicates,
4. evaluate thresholds.

That keeps matching work proportional to **candidate watches**, not **all watches**.

A design point worth being explicit about: do **not** make free-text marketplace titles part of your rule model. Use them only in normalization. Watches should target normalized fields like `model_id`, `family_id`, and `capacity_tb`; otherwise, rule complexity grows as fast as marketplace messiness.

### A cleaner user-facing watch shape

If you want a durable API surface, this is the shape I would expose:

```json
{
  "name": "16TB enterprise drives under $12/TB",
  "criteria": {
    "model_ids": [],
    "family_ids": ["exos-x18", "ultrastar-dc-hc550"],
    "capacity_tb": {"min": 16, "max": 16},
    "tier_any": ["enterprise", "datacenter"],
    "marketplaces_any": ["ebay", "serverpartdeals"]
  },
  "thresholds": {
    "max_price": 192.00,
    "max_price_per_tb": 12.00,
    "min_score": 82
  },
  "delivery": {
    "instant": {"email": true, "push": true, "sms": false},
    "digest": {"mode": "hourly"},
    "debounce_polls": 2,
    "cooldown_minutes": 720,
    "rate_caps": {"watch_6h": 3, "watch_day": 8},
    "hysteresis": {"price_abs": 5, "price_pct": 0.03, "score": 3}
  }
}
```

That is expressive without becoming a mini rules language.

## Email delivery and sender choice

### Why direct send from a Hetzner VM is the wrong default

Hetzner’s own cloud FAQ says outbound ports 25 and 465 are blocked by default, can only be unblocked after you have been with them for a month and paid the first invoice, and explicitly recommends using port 587 with external mail delivery services instead. That is already a strong signal that “DIY SMTP from a cloud VM” is the exception path, not the normal path.

Even if you do unblock direct SMTP, inbox providers still expect the fundamentals. Gmail requires authentication, forward and reverse DNS, TLS, standards-compliant messages, and low spam rates; for higher-volume senders it also requires DMARC and alignment. Yahoo likewise calls for SPF, DKIM, DMARC, one-click unsubscribe for subscribed/marketing mail, low complaint rates, and valid forward/reverse DNS. Gmail also notes that shared IP reputation affects delivery, and Spamhaus emphasizes that IP/domain reputation is central to deliverability.

So the root cause is not “Hetzner is bad at email.” The root cause is that **deliverability is identity + DNS + infrastructure reputation + recipient behavior**, and a small fresh sender from a datacenter IP starts with very little trust. Using a transactional provider moves you onto already-managed mail infrastructure and makes domain authentication, event tracking, and suppression handling much easier.

### Transactional-email provider comparison

For your monitor, I would pick **Postmark** if your top priority is “alerts should just land,” or **SES** if your top priority is “pay almost nothing and I’m fine with AWS overhead.” **Resend** is very attractive if DX matters and you like modern tooling. **Mailgun** is mature and feature-rich but broader and less minimalist. **AgentMail** is most interesting if you also want programmable inboxes, threading, or inbound agent workflows; for pure outbound alerts, it is probably more product than you need.

| Provider | Best fit | Cost signal | Strengths | Main caveat |
|---|---|---|---|---|
| **Postmark** | Reliability-first transactional alerts | Starts at **$15/mo**; dedicated IPs **$50/mo** and only for senders at **300,000+/mo** | Purpose-built transactional model, separate Message Streams for transactional vs broadcast, inbound processing via webhook, bounce/spam-complaint webhooks | Pricing is not the absolute cheapest; dedicated IP is irrelevant at hobby scale |
| **Amazon SES** | Cheapest serious option if AWS complexity is acceptable | **$0.10 per 1,000 outbound emails**; optional deliverability tooling extra | Very low usage cost, verified identities, Easy DKIM/BYODKIM, custom MAIL FROM, event publishing / feedback handling | More setup friction, sandbox/identity gating, weaker out-of-box ergonomics for a small hobby project |
| **Resend** | Best DX / modern API ergonomics | Free **3,000/mo** with **100/day**; Pro from **$20/mo for 50,000**; dedicated IP add-on **$30/mo** on Scale, for **>3,000/day** senders | API + SMTP relay, webhooks, receiving support, recommends subdomains, built-in deliverability insights | Still more “developer platform” than “transactional-email specialist,” and low-volume deliverability claims are newer than Postmark/SES’s long operational history |
| **Mailgun** | Mature, feature-rich platform | Free **100/day**; Basic starts at **$15/mo for 10,000** | HTTP API + SMTP, webhooks, inbound routes, analytics; Mailgun explicitly recommends the HTTP API over SMTP for application use | Broader platform surface than you need for a simple monitor; hobby simplicity is not its strongest angle |
| **AgentMail** | If you also want programmable inboxes, threads, receiving, and agent workflows | Developer tier **$20/mo**, **10 inboxes**, **10,000 emails/mo**; custom domains, SMTP relay, webhooks, DKIM/SPF/DMARC support | Real inbox primitive, custom domains, receiving, pods/multi-tenancy, signed webhooks; good fit if replies or inbound processing matter later | For pure outbound deal alerts it is likely overkill compared with Postmark/SES/Resend |

### Deliverability setup checklist

Use a **dedicated sending subdomain** such as `alerts.example.com` or `deals.example.com`, rather than your apex/root domain. Resend explicitly recommends subdomains for reputation isolation and transparency, and Mailgun recommends using a sending subdomain off the principal/root domain.

Then configure the basics in this order:

- **Verify the sending domain with your provider and enable DKIM**. Gmail recommends SPF, DKIM, and DMARC for best delivery; SES, Postmark, Resend, Mailgun, and AgentMail all document domain verification and authentication paths.
- **Publish exactly one SPF record for the hostname and merge includes rather than creating multiple SPF TXT records**. Gmail requires SPF or DKIM for all senders and recommends including all senders in SPF; Mailgun explicitly warns that multiple SPF records on one hostname must be merged.
- **Publish DMARC**, starting with `p=none` plus `rua=` reporting while you validate alignment. Gmail requires DMARC for bulk senders and recommends DMARC reports; Yahoo strongly urges or requires DMARC and recommends `rua` reporting.
- **If your provider supports it, configure custom MAIL FROM / Return-Path** so SPF alignment is cleaner. SES documents custom MAIL FROM requirements; Postmark documents custom Return-Path and DKIM setup.
- **Use HTTPS API delivery or provider SMTP on port 587**, not direct-to-MX delivery from the VM. Hetzner explicitly recommends the port-587-to-external-service path.
- **Wire bounce, complaint, and suppression handling back into your app.** SES supports feedback/event publishing; Postmark exposes bounce and spam-complaint webhooks; Resend has modular webhooks and suppression lists; Mailgun has webhooks intended for bounce/complaint/unsubscribe hygiene.
- **Keep alert traffic and any digest/broadcast traffic logically separate.** Postmark’s Message Streams and Yahoo’s “segregate email types” guidance both point the same way: separate transactional/user mail from bulk-like traffic so the reputations do not contaminate each other.
- **If you send digest-like or subscribed summaries, implement List-Unsubscribe and one-click unsubscribe headers.** Gmail requires RFC 8058-style one-click unsubscribe for subscribed/marketing mail over the bulk threshold, and Yahoo highly recommends the POST method while requiring easy unsubscribe handling.

The practical implication for your project is simple: **for small volume, use shared provider infrastructure and your authenticated domain; do not chase dedicated IPs.** The providers themselves reserve dedicated-IP options for materially larger senders, which is a good hint that hobby-scale alert mail should stay on managed shared pools.

## SMS and push channel tradeoffs

For a personal deal monitor, **push is the right second channel before SMS**. SMS is worth it only for the truly time-sensitive subset, such as “rare high-score drive became available now,” and only after you have already tamed the noise in email/push. Twilio’s US SMS pricing is still inexpensive in isolation, but it is charged per segment, may involve number and carrier/onboarding fees, and is operationally noisier than push. By contrast, Pushover is extremely cheap for one user, ntfy is open-source and script-friendly, and Telegram bots are free to use if you already live in Telegram.

| Channel / service | Cost signal | Effort | Best parts | Weak points | Recommendation |
|---|---|---|---|---|---|
| **Email via transactional ESP** | Usually cheapest serious “guaranteed” channel; SES is **$0.10/1k**, Postmark starts **$15/mo**, Resend has a free tier, Mailgun free **100/day** | Moderate, mostly DNS/auth setup | Rich context, links, explanations, digests, searchable history | Too easy to overuse if you do not dedup/cool down | **Primary channel** |
| **Twilio SMS** | US long-code outbound SMS starts around **$0.0083** per message, charged per segment; extra carrier/onboarding fees may apply | Moderate | Highest urgency, best for scarce-item availability | Cost, compliance friction, and the easiest channel to make annoying | **Use only for the rarest / highest-value instant alerts** |
| **Pushover** | **$4.99 one-time per platform** for personal use, **10,000 messages/month free** to send via API | Low | Excellent hobby-scale personal push, simple API, receipt/callback support | Closed ecosystem; recipient needs the app | **Best personal push default** |
| **ntfy** | Open-source, can use public `ntfy.sh` or self-host; simple HTTP publish/subscribe, click actions, auth tokens supported | Low to moderate | Extremely hackable, native apps + PWA, easy self-hosting | Self-hosting introduces mobile-edge cases and topic/auth hygiene responsibilities; docs note some iOS/self-host caveats | **Best if you want self-hostable push** |
| **Telegram bot** | Bot API is free to use; Telegram says Bot API / Telegram API are free of charge | Low | Free, easy HTTP interface, buttons/links, good personal chat workflow | Bot/user must both be in Telegram; broadcast limits exist unless you pay for higher throughput | **Great if Telegram is already in your daily flow** |

If it were my build, I would run:

- **Email instant + hourly digest**
- **Pushover or Telegram for urgent instant alerts**
- **No SMS initially**

That gives you one durable channel and one interruptive channel without paying the operational tax of SMS too early.

## Actionable email design

An alert email should answer four questions in the first screenful:

1. **What is it?**
2. **Why did I get this?**
3. **How good is it right now?**
4. **What can I do with one click?**

The subject line should therefore be dense but stable. Something like:

```text
[Drive Alert] $179.99 • $11.25/TB • score 88 • Exos X18 16TB • eBay
```

That is better than “A watched item matched” because it lets you triage directly from the inbox.

The body should be organized around **facts first, explanation second**:

```text
Exos X18 16TB is available on eBay from seller xyz.

Current:
- Price: $179.99
- $/TB: $11.25
- Score: 88
- Availability: In stock
- Marketplace: eBay
- Seller: xyz
- Link: [Open listing]

Why it matched:
- Max price watch: $190.00 → passed by $10.01
- Max $/TB watch: $12.00 → passed by $0.75/TB
- Min score watch: 82 → exceeded by 6

Actions:
- Open listing
- Snooze this watch for 24h
- Snooze this listing for 7d
- Stop this watch
```

The “why it matched” block matters more than most implementations realize. It is what keeps an alert from feeling arbitrary. You want the user to see the specific thresholds crossed, not just the current values.

### Per-watch snooze and unsubscribe

For email-side actions, use **signed, single-purpose links** carrying:

- `watch_id`
- `target` (`watch` or `listing`)
- `action` (`snooze_24h`, `snooze_7d`, `unsubscribe_watch`)
- `exp`
- `nonce`
- HMAC signature

Do not embed raw database IDs without signing, and do not make “unsubscribe all” the primary control. For a monitor like this, the natural unit of opt-out is the **watch**, not the sender identity as a whole.

If you send digest-like or subscribed emails, also add standards-based unsubscribe headers. Gmail says one-click unsubscribe requires both `List-Unsubscribe` and `List-Unsubscribe-Post`, and its FAQ clarifies that a `mailto:` link alone does not satisfy the one-click requirement; the RFC 8058 mechanism exists specifically to let mailbox providers trigger a secure one-click POST without relying on body links. Yahoo similarly recommends/accepts this model and asks senders to honor unsubscribes within two days.

For this application, the right interpretation is:

- **Instant transactional alerts**: body actions are the main thing; RFC 8058 headers are optional but still useful if you want native mailbox unsubscribe affordances.
- **Hourly/daily digests**: treat each watch as a per-topic subscription and include List-Unsubscribe headers so the mailbox can expose a native unsubscribe control. SES explicitly documents subscription-management headers, and Postmark documents List-Unsubscribe support as well.

### Recommended notification strategy

This is the concrete strategy I would ship first:

| Event | Email | Push | SMS | Notes |
|---|---|---|---|---|
| First time listing becomes available and passes thresholds | Instant | Instant | Off | Most valuable signal |
| First threshold crossing on existing listing | Instant | Instant | Off | Only on state transition |
| Material improvement after prior alert | Instant if improvement is large; else digest | Instant if large | Off | Bypass cooldown only for meaningful change |
| Repeated sightings / still available | Hourly digest | Off | Off | Avoid noise |
| Listing vanished / went out of stock | Off by default or digest-only | Off | Off | Usually negative-value noise |

That design preserves the scarce thing in any alerting system: **the user’s willingness to trust the next message**.