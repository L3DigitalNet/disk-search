# **Workflow:** Hardware Radar Gap Analysis

## Goals

Perform a comprehensive gap analysis of the Hardware Radar project.

## Instructions

- Run a **workflow** using Sonnet workers and Opus where complexity is high. Do not use Haiku or Fable.
- The workflow should comprehensively review the Hardware Radar spec and overall project, identifying gaps in functionality, documentation, research, implementation plans, ADR coverage, testing, deployment, operations, and public-repo hygiene.
- Review the master spec, ADRs, open/resolved question files, active `docs/superpowers/` design and plan files, `STATUS.md`, `TODO.md`, and the handoff specs/plans index.
- Document each identified gap in `docs/open-questions.md` and `docs/further-research-needed-prompts.md` as appropriate following the guidelines in those files.
- Perform follow-up internet research using `/qdev:research` to provide evidence-backed recommendations for each gap, and document findings in `docs/research/` as well as summaries in `open-questions.md` and `further-research-needed-prompts.md` when applicable.
- Where deeper research is required or warranted I will use ChatGPT Deep Research. Create prompts for each justified deep-research candidate in `docs/further-research-needed-prompts.md`.
- Provide your analysis of the research findings and present recommendations for each gap and open question in `docs/open-questions.md`. Include an analysis of potential downstream impacts of each recommendation on Hardware Radar milestones, ADRs, tests, operations, and public docs.
- Assign each gap and open question a priority level (High, Medium, Low) based on its impact on the project and the urgency of addressing it.
- If a gap reveals a significant architectural decision that is settled in practice but not recorded, recommend an ADR candidate. Do not write the ADR unless explicitly asked.
- Do not hand-edit `docs/research/index.md`; it is generated.
- Keep the repo public-safe. Do not add secrets, credential values, private hostnames, private IP addresses, or internal infrastructure details.

## Resources and References

- [Hardware Radar Master Spec](../specs/hw-radar-master-spec.md)
- [Open Questions](../open-questions.md)
- [Resolved Questions](../resolved-questions.md)
- [Further Research Prompts](../further-research-needed-prompts.md)
- [Research Reports](../research)
- [Architecture Decision Records](../adr)
- [MS-1 Ingestion Design](../superpowers/specs/2026-07-05-ms1-ingestion-design.md)
- [Specs And Plans Index](../handoff/specs-plans.md)
