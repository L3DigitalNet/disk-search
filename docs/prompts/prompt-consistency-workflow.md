# **Workflow:** Enforce Hardware Radar Spec Consistency and Reduce Drift

Run a **workflow** to reconcile the Hardware Radar documentation graph and
remove drift between the master spec, ADRs, decision records, research reports,
implementation plans, and current repo state.

## Goals

- The master spec (`docs/specs/hw-radar-master-spec.md`) is internally
  consistent and reflects the current accepted architecture.
- Each ADR is internally consistent, status-correct, indexed in
  `docs/adr/README.md`, and accurately summarized or referenced by the spec.
- Accepted ADRs do not contradict each other, the spec, or the settled decision
  record in `docs/resolved-questions.md`.
- `docs/open-questions.md` contains only unresolved decisions; settled decisions
  are moved to `docs/resolved-questions.md` or an ADR, as appropriate.
- Active milestone docs under `docs/superpowers/` agree with the spec and ADRs,
  or explicitly identify any plan/design updates still needed.
- Duplicated facts are reduced to links or short summaries that point to the
  canonical source.

## Source-Of-Truth Order

Use this order when two documents disagree:

1. Accepted ADRs own costly architectural decisions.
2. The master spec owns product requirements, milestones, data contracts, and
   implementation acceptance criteria.
3. `open-questions.md` and `resolved-questions.md` own decision state before a
   decision graduates to an ADR.
4. `docs/research/` owns evidence and dated recommendations, not current policy
   by itself.
5. `docs/superpowers/specs/` and `docs/superpowers/plans/` own milestone
   decomposition and execution details, constrained by the spec and ADRs.
6. `STATUS.md`, `TODO.md`, and `docs/handoff/` own current work state, not
   architectural truth.

If the source-of-truth order is insufficient, flag the conflict instead of
guessing.

## Checks

### Spec Consistency

- Check the spec for contradictions, stale TODO language, obsolete milestone
  status, unresolved placeholders, broken links, and duplicate explanations.
- Verify that requirement IDs, decision IDs, milestone IDs, and appendix
  references stay stable.
- Ensure implementation claims in the spec are backed by code, tests, deploy
  artifacts, or explicitly documented acceptance evidence.

### ADR Consistency

- Verify each ADR's status, frontmatter, supersession fields, related links, and
  index row.
- Check that accepted ADRs are summarized in the spec only where necessary.
  Keep detailed rationale in the ADR.
- Identify resolved questions or recurring conventions that should become ADRs,
  but do not create a new ADR unless explicitly asked.

### Question Record

- Confirm `docs/open-questions.md` lists only unresolved decisions.
- When settling or reopening a question, preserve stable `OQ#` anchors and
  update links from the spec, ADRs, research reports, TODO, and plans.
- Do not edit the owner's `#### My Comments` blocks except when relocating the
  whole question verbatim according to the file's own rules.

### Research And Prompt Ledger

- Use `docs/research/` for evidence. Treat dated claims as time-sensitive and
  re-verify when the decision depends on current external behavior, pricing,
  terms, APIs, laws, or service limits.
- Do not hand-edit `docs/research/index.md`; it is generated.
- If more research is needed, add a focused prompt to
  `docs/further-research-needed-prompts.md` and link it from the relevant open
  question or plan.

### Drift Reduction

- Keep comprehensive structured detail in one canonical place.
- In the spec, summarize decisions and link to ADRs or research instead of
  restating long rationale.
- When promoting content into an ADR, spec section, or resolved question, remove
  the redundant copy from the old location or replace it with a short pointer.
- Keep public-repo hygiene: do not add secrets, credential values, private
  hostnames, private IP addresses, or internal infrastructure details.

## Workflow Parameters

- Use subagents for independent scans when the harness supports them.
- Use stronger models for synthesis or high-risk architectural conflicts.
- Avoid low-capability workers for source-of-truth reconciliation.
- Expand the workflow when needed to cover gaps not listed here.

## References

- [Master Spec](../specs/hw-radar-master-spec.md)
- [ADR Index](../adr/README.md)
- [Open Questions](../open-questions.md)
- [Resolved Questions](../resolved-questions.md)
- [Research Reports](../research/README.md)
- [Further Research Prompts](../further-research-needed-prompts.md)
- [MS-1 Ingestion Design](../superpowers/specs/2026-07-05-ms1-ingestion-design.md)
- [Specs And Plans Index](../handoff/specs-plans.md)
