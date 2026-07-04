# Open Questions — `hw-radar.md`

## Important Notes

- **Document Handling Rules and Guidelines:** [How to maintain this document](#how-to-maintain-this-document)
- **Terminology:**
  - _open question_ (`OQ#`) is a decision still to be made — the primary unit of this document.
  - _resolved question_ (`RQ#`, already settled) and the original _gaps_ (`gap #`, the twelve spec-audit findings that seeded these questions) are settled provenance and live in the companion file [`resolved-questions.md`](resolved-questions.md).

## Table of Contents

- [Open Questions — `hw-radar.md`](#open-questions--hw-radarmd)
  - [Important Notes](#important-notes)
  - [Table of Contents](#table-of-contents)
  - [Open questions](#open-questions)
    - [OQ16 — SSD cohort-key endurance dimension (DWPD)](#oq16--ssd-cohort-key-endurance-dimension-dwpd)
    - [OQ17 — Heartbeat-grain retention & storage policy](#oq17--heartbeat-grain-retention--storage-policy)
    - [OQ18 — Recovery-time objective (RTO) for v1](#oq18--recovery-time-objective-rto-for-v1)
    - [OQ19 — Accessibility & i18n declaration](#oq19--accessibility--i18n-declaration)
    - [OQ20 — OSS license-compliance posture](#oq20--oss-license-compliance-posture)
  - [How to maintain this document](#how-to-maintain-this-document)

## Open questions

Five questions (OQ16–OQ20), all raised by the **2026-07-04 spec gap analysis** run after the ADR 0015–0017 reconciliation. None are blocking; each names the milestone it must precede. Previously-open questions are settled and relocated to [`resolved-questions.md`](resolved-questions.md) — most recently **OQ3** and **OQ15**, both resolved 2026-07-04.

### OQ16 — SSD cohort-key endurance dimension (DWPD)

**From:** spec↔ADR consistency review (2026-07-04 gap analysis). **Decision needed:** the spec's glossary and EC-008 define the SSD price-scoring cohort key as capacity · tier · interface/form · condition **+ DWPD endurance class**, but [ADR 0011](adr/adr-0011-composite-deal-score.md)'s ratified cohort key stops at condition — no endurance dimension. Ratify the DWPD extension (amend ADR 0011 or record a superseding note) or drop it from the spec so SSDs cohort on the four-part key alone. Needed before SSD scoring lands (M2).

#### Agent notes

- The DWPD dimension traces to the [suitability taxonomy research](research/machine-usable-drive-suitability-taxonomy-for-24-7-nas-and-server-scoring.md) (`dwpd` is already a typed `drive_spec` column), so the data to cohort on it will exist either way — the question is only whether it partitions the price cohort.
- Trade-off: including DWPD prevents comparing a read-intensive SSD's `$/TB` against mixed-use peers (EC-008's intent), but **thins cohorts further** — and thin cohorts already force the ADR 0011 warm-up/relaxation machinery. A middle path: fold DWPD into the *fitness* subscore instead of the cohort key.
- Both spec sites (glossary "Cohort" row; EC-008) are marked _provisional — OQ16_ pending this call.

#### My Comments

_(owner — pending)_

### OQ17 — Heartbeat-grain retention & storage policy

**From:** [ADR 0015](adr/adr-0015-availability-heartbeat-grain-volatility-scheduling.md)'s accepted-consequence list ("its own retention") via the 2026-07-04 gap analysis. **Decision needed:** `availability_heartbeat_observation` rows have **no retention class or TTL** — DR-001's class list doesn't cover the new grain, and fast-lane polling at p95 ≤ 3 min generates ~500 rows/source/day of mostly-`unchanged` heartbeats. Decide: (a) how long each decision class is kept (e.g. drop `unchanged` quickly / aggregate to a daily count, keep `transition_detected`/`ambiguous`/`failed` longer for SLO measurement and fingerprint tuning), and (b) whether the table is a TimescaleDB hypertable with compression/retention policies like `offer_snapshot`. Needed before the first fast-lane source (eBay, M1+).

#### Agent notes

- The retention choice is coupled to two consumers ADR 0015 creates: **p95 transition-to-alert SLO measurement** (needs enough heartbeat history to compute per-source percentiles) and **fingerprint tuning** (mis-tuned fingerprints are diagnosed from `ambiguous`/`failed` runs). Keeping only transitions would starve both.
- DR-008 carries the _(heartbeat retention/TTL undecided — OQ17)_ marker in the spec.
- This is a **retention/ops tunable riding on an already-ratified grain** — likely resolvable without a new ADR (record in `resolved-questions.md` + spec DR-008), unless the answer changes the schema shape.

#### My Comments

_(owner — pending)_

### OQ18 — Recovery-time objective (RTO) for v1

**From:** spec §18.6 ("RTO: not stated in sources") via the 2026-07-04 gap analysis. **Decision needed:** OQ3 ratified the RPO (≤1 h) but no one has stated how long the tool may stay **down** after a CT loss — the bound on acceptable rebuild time (re-provision CT + restore TimescaleDB-aware dump + re-wire secrets/backups). A lax RTO (days) keeps the current manual-runbook posture; a tight one (hours) would force provisioning automation (e.g. the ansible scaffold ADR 0009 notes is not yet built). Needed before production entry.

#### Agent notes

- Suggested default given the product's shape: **best-effort, ~1 business day** — deals missed during an outage are unrecoverable either way; the durable asset (price history, protected by RPO) is what matters. The cost of a tight RTO is real (automation work); the benefit is small for a single-user tool.
- Whatever the number, §18.6 should state it and the restore-test discipline should verify it once (a timed restore is already an M5 acceptance item).

#### My Comments

_(owner — pending)_

### OQ19 — Accessibility & i18n declaration

**From:** spec §11's `<placeholder-guidance>` block ("state the target … or explicitly declare it out of scope with a reason") via the 2026-07-04 gap analysis. **Decision needed:** the template requires an explicit statement and no repo source makes one. Options: declare **out of scope for v1** (single sighted user, English-only — consistent with "Engineered to Needs"), or set a lightweight target (e.g. semantic-HTML/keyboard-navigable, no formal WCAG audit). Needed by M3 (UI build) — retrofitting is costlier than declaring intent now.

#### Agent notes

- Server-rendered Django templates + HTMX (ADR 0004) are naturally close to semantic-HTML/keyboard-navigable, so the lightweight target is nearly free if adopted at build time.
- i18n: strings-externalized-but-single-locale is the usual cheap hedge; also probably unnecessary for v1 (owner-only, extensibility principle already covers "later users" structurally).

#### My Comments

_(owner — pending)_

### OQ20 — OSS license-compliance posture

**From:** spec §16's unchecked box ("OSS license compatibility of dependencies — not systematically recorded … to be covered by the standard toolchain's audit practices") via the 2026-07-04 gap analysis. **Decision needed:** the cited coverage doesn't exist — **pip-audit checks CVEs, not licenses**; nothing in the gate inspects dependency licenses. For a public repo, decide: (a) one-time manual review at v1 + on new deps (cheap; the current stack is permissively-licensed mainstream), (b) add an automated license check to the gate (e.g. `licensecheck`/`pip-licenses` with an allowlist), or (c) accept the risk and re-word §16 to say so honestly. Needed before the v1 release.

#### Agent notes

- The realistic exposure is low: Django/Scrapy/APScheduler/psycopg etc. are BSD/MIT/Apache; the sharper cases are TimescaleDB (**TSL license for some features** — community edition self-hosted use is fine, but worth recording which feature set the deploy relies on) and any future managed-unblocker SDK.
- Whichever option wins, the §16 checklist line should be re-worded to match reality (it currently promises toolchain coverage that isn't there).

#### My Comments

_(owner — pending)_

## How to maintain this document

These rules govern **both** files: this one (open) and its companion [`resolved-questions.md`](resolved-questions.md) (settled).

- Read **[Open questions](#open-questions)** for anything that still needs a call. Everything settled lives in [`resolved-questions.md`](resolved-questions.md) — you should not have to read it to know what's outstanding.
- When a question is settled, move it to [`resolved-questions.md`](resolved-questions.md). If a question is partially settled, move the decided half there and leave a focused open question here covering _only_ the remaining fork.
- Once an ADR is written for a settled question, the resolved decision can be safely removed from `resolved-questions.md` to control its size. The ADR is the canonical record of the decision. (This is why the ADR-backed OQs in [`resolved-questions.md`](resolved-questions.md) are condensed to a one-line pointer + ADR link, while the OQs with no ADR retain their full decided substance there.)

**Rules:**

1. **Open questions first, distilled.** Each open question states _only_ the unresolved decision — not the history behind it. The history lives in `resolved-questions.md` and in the research reports.
2. **When a question is settled, move it to `resolved-questions.md`.** Relocate its substance there (record the decision + any ADR) and remove it from this file. Never leave a settled item in Open questions.
3. **Split partially-settled items.** If a gap is half-decided, move the decided half to `resolved-questions.md` and leave a focused open question here covering _only_ the remaining fork. (This is how the OQs in `resolved-questions.md` were produced from the twelve gaps.)
4. **Two comment layers per open question, kept separate:**
   - `#### Agent notes` — research/reconciliation context, maintained by the assistant.
   - `#### My Comments` — the owner's notes and decisions; **the assistant does not edit this block.** (When an OQ is relocated to `resolved-questions.md`, its owner comments are preserved verbatim.)
5. **Cross-reference by stable ID.** `OQ#` = open question, `RQ#` = resolved question, `gap #` = original gap. ADRs, the spec, and TODO link here by those IDs — keep them stable. The `#oq#` / `#gap#` **anchors** derive from heading _text_, so they survive a move between files — **but a link that names the file (`open-questions.md#oq…`) breaks when the item moves to `resolved-questions.md`; update every referring ADR/TODO/spec/research link to the new file in the same change.** If you must renumber, update the referencing docs in the same change.
6. **Not a log:** Do not append a log of routine maintenance or administrative changes. This is a _decision record_, not a change log. Use the Git history for that and `docs/handoff.md` and/or `TODO.md` where appropriate.
