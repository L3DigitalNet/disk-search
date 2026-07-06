# **Workflow:** Enforce Consistency and Mitigate Drift Exposures

Run a **workflow** to:

- _Enforce consistency_ between the Hardware Radar master spec (`docs/specs/hw-radar-master-spec.md`), ADRs, resolved questions, open questions, and active milestone design/plan docs.
- _Mitigate drift exposures_ by ensuring that all information is in its canonical location and not duplicated across documents.

## Goals

- The Hardware Radar master spec is **100%** internally consistent and reflects the current accepted architecture.
- Each ADR is **100%** internally consistent, unambiguous, indexed in `docs/adr/README.md`, and accurately summarized or referenced in the spec.
- There are **zero** contradictions or ambiguities between ADRs.
- There are **zero** contradictions or ambiguities between any ADR and the Hardware Radar master spec.
- Any resolved questions in `docs/resolved-questions.md` found to be inconsistent with the spec or ADRs are downgraded to open questions and relocated to `docs/open-questions.md` for further research and resolution.
- Active milestone design and plan docs under `docs/superpowers/` are consistent with the spec and ADRs, or explicitly identify any plan updates still needed.

## Additional Guidelines

**Workflow parameters:**

- _Workers:_ Use Sonnet subagents for routine worker-level tasks when the harness supports them.
- _Complex tasks:_ Use Opus for complex synthesis or high-risk architectural conflicts.
- _Avoid:_ Haiku and Fable subagents for source-of-truth reconciliation.
- Use as many subagents as needed to achieve a successful outcome.
- You are empowered to expand the workflow with additional steps if needed to fill gaps or address issues that I may have missed.

**Resolving inconsistencies:**

- _Source-of-truth order:_ Accepted ADRs own costly architectural decisions; the master spec owns requirements, milestones, data contracts, and acceptance criteria; `open-questions.md` / `resolved-questions.md` own decision state before ADR graduation; `docs/research/` owns evidence and dated recommendations; `docs/superpowers/` owns milestone decomposition and execution details.
- _Repo level sources:_ Research reports in `docs/research/`, active designs/plans in `docs/superpowers/`, `STATUS.md`, `TODO.md`, and `docs/handoff/specs-plans.md`.
- _Internet research:_ Use `/qdev:research` when a decision depends on current external behavior, pricing, terms, APIs, laws, service limits, or software versions.
- _Deep research escalation:_ If still unresolved, escalate to a deep-research prompt in `docs/further-research-needed-prompts.md` for further investigation.
- _Public-repo hygiene:_ Do not add secrets, credential values, private hostnames, private IP addresses, or internal infrastructure details.

**Reduce drift exposure:**

- _Deduplication:_ Avoid duplicating information across documents where possible. Comprehensive structured information belongs in its single canonical location (e.g., ADRs, spec, question records, or research reports). Use links/pointers/references to the canonical source instead of restating when it must be referenced elsewhere.
- _Reference; don't repeat:_ Do not verbosely restate ADRs in the spec; the spec should summarize the critical points and reference the ADRs for details.
- _Promote and remove:_ When a piece of information is promoted, ensure it is removed from the original location to avoid duplication and potential drift. A link may be left in the original location to point to the new canonical source, but the original content should be removed to prevent drift.
- _Research index:_ Do not hand-edit `docs/research/index.md`; it is generated.

## References

- [Hardware Radar Master Spec](../specs/hw-radar-master-spec.md)
- [Resolved Questions](../resolved-questions.md)
- [Open Questions](../open-questions.md)
- [Architecture Decision Records](../adr)
- [Research Reports](../research)
- [Further Research Prompts](../further-research-needed-prompts.md)
- [MS-1 Ingestion Design](../superpowers/specs/2026-07-05-ms1-ingestion-design.md)
- [Specs And Plans Index](../handoff/specs-plans.md)
