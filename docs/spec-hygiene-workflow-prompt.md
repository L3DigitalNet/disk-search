# Major Spec Drift Check, Polish, Consistency, and ADR Validation Workflow

## Workflow General Guidelines

- Use Sonnet and/or Opus subagents as appropriate for the task/step.
- Do not use Fable subagents or Haiku subagents for routine work.
- Fable should be used for the final synthesis.

## Minimum Requirements

At a minimum, the following checks should be performed on the spec and ADRs (perform additional checks as needed to ensure the spec is consistent, complete, and up-to-date):

### ADR Validation

Ensure that ADRs are:

- internally consistent
- do not contradict each other
- do not contradict the spec
- up-to-date with the current state of the project
- properly linked and referenced in the spec
- summarized in the spec where applicable, with clear references to the full ADRs

### Spec Consistency and Completeness

The spec should be checked for:

- internal consistency
- completeness and coverage of all relevant topics
- clarity and readability
- the content in each section is within the scope/purpose of the section
- up-to-date with the current state of the project
- The spec should point/link to ADRs where applicable. Do not regurgitate the content of the ADRs in the spec; instead, provide a summary and clear references to them.

### Resolved Questions and Decisions

- Check that any resolved questions do not contradict the current ADRs. ADRs are the source of truth; conflicting 'resolved questions' should be flagged for review and downgraded to 'open questions' for follow-up.
- Identify resolved questions and other non-ADR locked decisions that would make good ADR candidates.

### Miscellaneous Checks

Add any additional checks that are missing from above as determined necessary, relevant, useful, polish, or helpful to ensure the spec and ADRs are consistent, complete, and up-to-date.
