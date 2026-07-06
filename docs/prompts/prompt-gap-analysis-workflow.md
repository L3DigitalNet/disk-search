# **Workflow:** Hardware Radar Gap Analysis

## Goal

Perform a comprehensive gap analysis of the Hardware Radar project, covering the
product spec, ADRs, research corpus, milestone plans, implementation state, and
operational readiness.

## Scope

Look for gaps in:

- Product requirements, milestone boundaries, and acceptance criteria.
- Data acquisition, entity resolution, scoring, alerting, and UI workflows.
- Research evidence, especially dated or external facts that may have changed.
- ADR coverage for significant, hard-to-reverse decisions.
- Implementation-plan coverage under `docs/superpowers/`.
- Tests, verification gates, deployment, backup, monitoring, and runbooks.
- Public-repo hygiene, credential references, and private-infrastructure
  boundaries.

## Instructions

- Run a workflow using subagents for independent review tracks when the harness
  supports them. Use stronger models for synthesis or high-risk design calls.
- Start from the current repo state; do not assume old prompt text or archived
  docs are current.
- Read the master spec, ADR index, open/resolved question files, active
  `docs/superpowers/` design and plan files, `STATUS.md`, `TODO.md`, and the
  handoff specs/plans index.
- Treat `docs/research/` as the evidence base. Re-verify time-sensitive claims
  before making a recommendation that depends on current pricing, APIs, terms,
  law, software versions, or service limits.
- For each gap, record:
  - Stable ID or proposed ID.
  - Priority: High, Medium, or Low.
  - Evidence and source documents.
  - Why it matters to Hardware Radar.
  - Downstream impact on milestones, ADRs, tests, operations, or public docs.
  - Recommended next action.
- If a gap is an unresolved decision, add or update an entry in
  `docs/open-questions.md` following that file's rules.
- If a gap needs external research, add a focused prompt to
  `docs/further-research-needed-prompts.md`.
- If the research can be completed during the workflow, write the report under
  `docs/research/` and summarize the decision impact in the relevant open
  question or plan. Do not hand-edit `docs/research/index.md`; it is generated.
- If the gap reveals an architectural decision that is already settled in
  practice but not recorded, recommend an ADR candidate. Do not write the ADR
  unless explicitly asked.
- Keep the repo public-safe. Do not add secrets, credential values, private
  hostnames, private IP addresses, or internal infrastructure details.

## Output

Produce a gap-analysis report with:

- Executive summary.
- Prioritized gap table.
- Detailed findings with evidence and recommended action.
- Proposed updates to `open-questions.md`,
  `docs/further-research-needed-prompts.md`, or ADR candidates.
- A short section for items reviewed and found adequate, so future passes do not
  re-litigate them without new evidence.

## Resources

- [Master Spec](../specs/hw-radar-master-spec.md)
- [Open Questions](../open-questions.md)
- [Resolved Questions](../resolved-questions.md)
- [ADR Index](../adr/README.md)
- [Research Reports](../research/README.md)
- [Further Research Prompts](../further-research-needed-prompts.md)
- [MS-1 Ingestion Design](../superpowers/specs/2026-07-05-ms1-ingestion-design.md)
- [Specs And Plans Index](../handoff/specs-plans.md)
