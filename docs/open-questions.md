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
    - [OQ15 — Amazon acquisition path after PA-API deprecation](#oq15--amazon-acquisition-path-after-pa-api-deprecation)
      - [Agent notes](#agent-notes)
      - [My Comments](#my-comments)
  - [How to maintain this document](#how-to-maintain-this-document)

## Open questions

### OQ15 — Amazon acquisition path after PA-API deprecation

**From:** the [polling-cadence reconciliation](research/2026-07-04-polling-cadence-reconciliation.md) §6 (surfaced by the ChatGPT Deep Research run). **Decision needed:** the Amazon **Product Advertising API (PA-API 5)** `GetItems` documentation now carries a **2026-05-15 deprecation notice** directing developers to the **Creators API**. This invalidates an assumption in the settled Amazon acquisition/retention path (Amazon = display/discovery, ASIN-persistable, offers via PA-API/SP-API — [DR-001](specs/hw-radar-master-spec.md), the acquisition + [legal](resolved-questions.md) research). Choose the replacement path — migrate to the Creators API, rely on SP-API where authorized, or drop Amazon to **discovery-only** via the search APIs — **after verifying the deprecation and its timeline live** (dated fact; API timelines shift). **Non-blocking:** Amazon is _churning_, exposes no cheap availability signal, and is not a fast-lane/primary value source (reconciliation §1/§4); needed before the Amazon connector is built (~M5).

#### Agent notes

- **Time-sensitive:** the 2026-05-15 date is the ChatGPT run's read of `webservices.amazon.com/paapi5/documentation/get-items.html`; **re-verify live** before acting — do not treat as fixed.
- **Retention is transport-independent:** whichever API path wins, [DR-001](specs/hw-radar-master-spec.md) already governs storage (Amazon = ASIN identifier indefinite, all else ephemeral 24 h, no image bytes — from the legal research). The deprecation changes _how_ Amazon data is fetched, not _what_ may be kept.
- **Coupled docs to update once decided:** the Amazon rows in [`resolved-questions.md`](resolved-questions.md), the acquisition research report, and any Amazon interface row (IR) in the spec.

#### My Comments

**Task for Claude:** /qdev:research the Creators API and SP-API to determine which is the best replacement for PA-API 5 `GetItems` for our use case. Provide a recommendation with pros and cons for each option, including any limitations or restrictions that may affect our ability to acquire and retain Amazon data. Once a decision is made, update the relevant documentation accordingly.

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
