# MS-1e — Validation corpus + ADR-0019 ratification: Design

> Brainstorm output (2026-07-06, owner-approved). Instantiates master-spec §19 "MS-1
> close" and the `docs/superpowers/specs/2026-07-05-ms1-ingestion-design.md` §MS-1e
> sub-milestone: the labeled-corpus evaluation that ratifies ADR-0019. Introduces no
> new matching architecture — the resolver, ladder, normalizer, and catalog are all
> fixed by ADR-0019 / master-spec Appendix C.3 and already implemented (MS-1a–d). This
> document records the *evaluation harness + harvest tooling* design and the owner scope
> decision taken 2026-07-06 (build the deterministic harness + harvest tooling now; the
> live harvest, label audit, and ratification run are a deferred owner-in-the-loop step).

**Goal:** a repeatable, deterministic **evaluation harness** that runs a versioned,
hand-labeled corpus of real listings through the **production** rung-0–2 resolver
(`CatalogResolver().resolve_listing`) and computes a tri-state ratification verdict —
`PASS` (≥ 99.5% auto-accept precision on a ≥ 100-decision denominator), `INSUFFICIENT_CORPUS`
(< 100 auto-accepted decisions), or `FAIL` (< 99.5%) — plus the reported per-source
model-grain coverage, the per-source ≥ 1-family-grain resolution floor (an MS-1 gate),
and the OEM dual-label spot-check rate. Ships with the harness proven against a synthetic
fixture in CI; the real-corpus ratification test is skip-guarded until the live harvest lands.

## 1. Owner scope decisions (2026-07-06)

These settle what the MS-1e sub-milestone left to plan time:

| # | Decision | Consequence |
| --- | --- | --- |
| E-1 | **Build the deterministic evaluation harness + harvest tooling in this milestone; defer the live harvest, label drafts, owner audit, and ratification run to a scheduled owner-in-the-loop follow-up.** | MS-1e merges with the harness proven on a synthetic fixture and the real-corpus test skip-guarded. Ratification (ADR flip) happens later, out of this PR, when a real corpus has been harvested and audited. No fake green. |
| E-2 | **Eval architecture = Approach A (full production path).** Each corpus title is normalized + `upsert_listing`-ed into a rolled-back test-DB transaction, then run through the real `CatalogResolver().resolve_listing`; the harness reads back the denorm grain + target FK + resolution-edge rung. | The gate certifies exactly the code path that writes to price history. No proxy/second-code-path drift (the ADR-0019 rule 1 hazard). Rung 0 self-bypasses on first observation, so the measured decisions are genuinely rung-1/2 auto-accepts. |
| E-3 | **`expected_target` is a grain-addressed natural key (brand/family/model/variant strings), never a catalog PK.** | The committed corpus outlives any DB seed; the eval maps each *predicted* target PK back to its natural key and compares strings. The fixture doubles as a durable post-`matcher_version`-bump regression asset. |
| E-4 | **The real labeled corpus is committed to this public repo** — `title` + a curated subset of extraction-consumed structured attributes only; **never** full raw payloads. | Titles + curated attrs are public marketplace data (repo-safe per AGENTS.md Public-Repo Rule); full payloads (seller handles/URLs) stay transient in the harvest staging file, uncommitted. |
| E-5 | **Labeling per ingestion-design S-5**: Claude drafts every label; owner audits a random ~20% sample + **every** entry where the label disagrees with the matcher prediction. | Bounded owner time while keeping the ratification gate meaningfully independent. Audit status is tracked per entry. |

## 2. Module layout

New code under `src/hw_radar/`, plus a Django management command and test fixtures:

```
hw_radar/
├── matching/
│   └── eval/                        # MS-1e — corpus evaluation (pure orchestration over the resolver)
│       ├── __init__.py
│       ├── corpus.py                # Pydantic: CorpusEntry, CorpusMeta, GroundTruthLabel, TargetKey; load + validate JSONL
│       ├── evaluate.py              # Approach A: per entry → upsert Listing → resolve_listing → Prediction; aggregate → EvalReport
│       └── report.py                # EvalReport + tri-state Verdict; precision / coverage / per-source floor / OEM-rate math
├── catalog/
│   └── management/commands/
│       └── harvest_corpus.py        # manual harvest: drives each adapter directly, bypasses scheduler + enabled flag
│                                    # (catalog app hosts commands — acquisition is a plain package, not an installed app;
│                                    #  sits beside the existing import_refdata command)
tests/
├── fixtures/matching_corpus/
│   ├── synthetic.jsonl              # ~10 hand-built entries with known outcomes (always-on harness unit tests)
│   ├── synthetic.meta.json
│   ├── corpus.jsonl                 # the real harvested + labeled corpus (added by the deferred ratification step)
│   └── corpus.meta.json
├── unit/test_corpus_eval.py         # harness math on the synthetic fixture (no live data)
├── unit/test_corpus_schema.py       # Pydantic validation invariants
├── unit/test_harvest_corpus.py      # command drives a fake adapter → JSONL; eBay-creds-absent → eBay-only skip
└── db/test_ratification_corpus.py   # the executable ratification gate; skip-guarded until the real corpus exists
```

The eval module is deliberately thin: it *orchestrates* the existing resolver and owns only
the corpus I/O, the metrics math, and the tri-state verdict. It contains **no matching logic**
— that would be the second-code-path drift E-2 exists to prevent.

## 3. Corpus fixture — schema & versioning

A JSONL corpus plus a sidecar manifest under `tests/fixtures/matching_corpus/`.

**`corpus.jsonl`** — one object per listing:

```json
{
  "id": "spd-0001",
  "source": "serverpartdeals",
  "title": "Seagate Exos X18 ST18000NM000J 18TB SATA Recertified Enterprise HDD",
  "raw_attributes": {
    "capacity_text": "18TB", "condition": "recertified",
    "mpn_field": "ST18000NM000J", "oem_field": null,
    "price": "199.00", "currency": "USD"
  },
  "label": {
    "expected_grain": "model",
    "expected_target": {
      "brand": "Seagate", "family": "Exos X18",
      "model": "ST18000NM000J", "variant": null
    },
    "oem_dual_label": false,
    "audit_status": "claude_draft",
    "notes": ""
  }
}
```

- **`source`** ∈ the five connector keys (`serverpartdeals`, `goharddrive`, `wd`, `seagate`, `ebay`).
- **`raw_attributes`** carries only the curated fields extraction consumes (E-4). `mpn_field`/`oem_field`
  are the connector-provided structured fields, distinct from what extraction parses out of `title`.
- **`label.expected_grain`** ∈ `none | family | model | variant`.
- **`label.expected_target`** is the natural key (E-3). Grain/key consistency is a validated invariant:
  `variant` grain requires a non-null `variant`; `model` requires `model`; `family` requires `family`;
  `none` requires all of family/model/variant null (a listing that *should not* auto-accept — e.g. a
  genuinely unresolvable or contradiction case).
- **`label.oem_dual_label`** — the OEM-token-AND-MPN spot-check flag (ADR-0019 rule 7 / consequence);
  measured against ServerPartDeals + eBay listings.
- **`label.audit_status`** ∈ `claude_draft | owner_confirmed | owner_corrected`.

**`corpus.meta.json`** — `corpus_version` (string), `harvested_at` range, per-source counts,
`matcher_version` at labeling time, and an audit rollup (counts by `audit_status`).

## 4. Harvest command — `manage.py harvest_corpus`

A Django management command that harvests real listings **without touching go-live gates**:
it instantiates each connector adapter directly and calls `await adapter.fetch()` →
`adapter.parse(batch) → list[ParsedListing]`, bypassing the poller scheduler and the
`SourceConfig.enabled` flag entirely (it is a manual tool, not a scheduled job).

- **Flags:** `--source {serverpartdeals,goharddrive,wd,seagate,ebay} | --all`, `--limit N`
  (per-source cap), `--out PATH` (staging JSONL).
- **Isolation (NFR-001):** one source failing never halts the others; each source's outcome is
  logged and the sweep continues.
- **eBay creds:** the connector reads `EBAY_CLIENT_ID` / `EBAY_CLIENT_SECRET` (production keyset in
  OpenBao at `secret/api-keys/commerce/ebay`, verified live per ingestion-design S-4; Buy-API access
  is eBay-mutable — re-run the token-mint + one-search smoke at harvest time, never print the token).
  If the env vars are absent the command **skips eBay only** and harvests the other four.
- **Robots:** honors the existing `acquisition/http.py` robots preflight.
- **Output:** *unlabeled* staging entries (`id`, `source`, `title`, `raw_attributes`) with an optional
  `oem_dual_label` heuristic pre-fill. Labeling is the separate S-5 step; the command never invents labels.

## 5. Evaluation harness — `src/hw_radar/matching/eval/`

For each corpus entry, the harness (Approach A, E-2):

1. Builds a normalized listing from `title` + `raw_attributes` via the production normalizer and
   `upsert_listing`, in a rolled-back test-DB transaction against the seeded catalog.
2. Calls `CatalogResolver().resolve_listing(listing.pk)` — the exact production resolver.
3. Reads back a `Prediction(grain, target_natural_key, rung, outcome)` from the denorm fields + the
   current `listing_resolution` edge (rung/method live in the edge evidence).

`report.py` aggregates predictions into an `EvalReport` with a tri-state verdict:

| Metric | Rule |
| --- | --- |
| **Auto-accepts** | predictions where `outcome == ACCEPT and rung ∈ {1, 2}` (rung 0 self-bypasses on a first observation, so it never enters the denominator) |
| **Precision** | `correct_auto_accepts / total_auto_accepts`; *correct* ⇔ predicted grain **and** natural-key target match the label at that grain (rung-2 family attach checked at family grain) |
| **Verdict** | `total_auto_accepts < 100` → **INSUFFICIENT_CORPUS**; else `precision ≥ 0.995` → **PASS**; else **FAIL** |
| **Coverage** (reported, not gated) | per-source % of listings resolved at model grain or better (MS-2's ≥ 80% expectation) |
| **Per-source floor** (MS-1 gate) | every one of the 5 sources resolves ≥ 1 listing at family grain or better; a source stuck at `grain = none` fails MS-1 (surfaces a catalog/extraction gap) |
| **OEM dual-label rate** (reported) | % of ServerPartDeals + eBay listings printing both an OEM token and an MPN |

The `100` auto-accept floor is a named constant (Codex SA-003: the gate must not be passable on
trivially few matches or `grain = none` rows). A corpus that resolves 12 lucky matches reports
`INSUFFICIENT_CORPUS`, **never** `PASS`.

## 6. Ratification procedure (deferred, owner-in-the-loop)

Documented as a runbook; executed after MS-1e merges, not in its PR:

1. `manage.py harvest_corpus --all --limit …` (live, manual) → staging JSONL of ~150–200 titles
   spanning all 5 sources.
2. Claude drafts `label` for every entry → labeled `corpus.jsonl` + `corpus.meta.json`.
3. Owner audits a random ~20% sample **plus every entry where the label disagrees with the matcher
   prediction** (S-5); corrections set `audit_status = owner_corrected`.
4. Run `tests/db/test_ratification_corpus.py`.
5. **PASS** (≥ 99.5% on ≥ 100 auto-accepts) → flip ADR-0019 MADR status `proposed → accepted`, record
   the result in its **Confirmation** section, drop the D-019 / C.3 "(proposed)" qualifiers in the
   master spec, update the ADR-index row, and close the TODO ratification item.
6. **FAIL** → veto-rule fix + `matcher_version` bump + re-run (master-spec C.3.5 loop). **The gate is
   never loosened.**

MS-1 close additionally requires (ingestion-design §MS-1e): the FR-003 acceptance case green as a
resolver-driven test (a recert + a new listing of the same drive → one `product_model`, two
`product_variant`s), the per-source resolution floor (§5), and the coverage report emitted for MS-2.

## 7. Testing strategy

- **Always-on harness unit tests** (`tests/unit/test_corpus_eval.py`) drive `synthetic.jsonl`
  (~10 hand-built entries with known outcomes): precision math; the tri-state boundaries (a `< 100`
  case must yield `INSUFFICIENT_CORPUS`, **not** `PASS`; a `99.4%` case must `FAIL`); coverage; the
  per-source floor (a source stuck at `none` fails); the OEM rate; and a deliberate
  capacity-contradiction entry that must land in review, **not** auto-accept (the poison case
  ADR-0019 rule 1 is built to stop).
- **Schema-validation tests** (`tests/unit/test_corpus_schema.py`): grain/target-key consistency,
  malformed-entry rejection, unknown-source rejection.
- **Harvest-command test** (`tests/unit/test_harvest_corpus.py`): a fake adapter → asserts JSONL
  shape and staging fields; eBay-creds-absent → eBay-only skip, other sources still harvested.
- **Ratification test** (`tests/db/test_ratification_corpus.py`): loads the real corpus if present;
  `pytest.skip("corpus not yet harvested / below floor")` when absent or below the denominator floor,
  so CI stays green pre-harvest. Once the real corpus lands it asserts `PASS`. This *is* the executable
  ratification gate.
- **Full gate** (`uv run python -m scripts.check`) green at every commit: ruff format + check,
  basedpyright, pytest + coverage, pip-audit.

## 8. Risks / open edges

| Risk | Posture |
| --- | --- |
| Live endpoints drifted since the 2026-07-04 recon; harvest yields too few titles for a source | Harvest is manual/plan-time (never CI); a thin source surfaces its catalog/extraction gap via the §5 per-source floor — that is a finding MS-1 must expose, not hide |
| eBay Buy-API access regressed (terms are eBay-mutable) | Re-run the two-step smoke at harvest time; if regressed, harvest the other four and raise an OQ (defer-eBay decision is the owner's) — the harness tolerates a missing source |
| Corpus precision misses 99.5% | Master-spec C.3.5 loop: veto fix + `matcher_version` bump + re-run; never loosen the gate |
| Synthetic fixture diverges from real matcher behavior | The synthetic fixture tests only the *harness math*, not matcher quality; the real gate is Approach A against the production resolver — the two never substitute for each other |

## 9. Execution process

`superpowers:writing-plans` plan doc (`docs/superpowers/plans/2026-07-06-ms1e-…`) → execution with the
verification gate → `dev → main` PR (merge commit, CI + dependency-review green). The live harvest,
label audit, and ratification (§6) are a **separate, later** owner-in-the-loop step, not part of this
PR. Deviations from this design or the spec go to the spec Deviations Log / OQ process.
