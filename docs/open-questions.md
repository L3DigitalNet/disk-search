# Open Questions — `hw-radar.md`

**Document Handling Rules and Guidelines:** [How to maintain this document](#how-to-maintain-this-document)

**Terminology:** an **open question** (`OQ#`) is a decision still to be made — the primary unit of this document. A **resolved question** (`RQ#`, already settled) and the original **gaps** (`gap #`, the twelve spec-audit findings that seeded these questions) are settled provenance and live in the companion file **[`resolved-questions.md`](resolved-questions.md)**.

**Two-file layout (split 2026-07-04):** this file holds only what is still **open** (currently just **OQ3**) plus the maintenance rules; every **settled** item — RQ1–RQ6, the 12-gap analysis, and the resolved OQ write-ups (OQ1–OQ2, OQ4–OQ14) — is in [`resolved-questions.md`](resolved-questions.md).

## Table of Contents

- [Open Questions — `hw-radar.md`](#open-questions--hw-radarmd)
  - [Table of Contents](#table-of-contents)
  - [Open questions](#open-questions)
    - [OQ3 — DB RPO acceptance (+ TimescaleDB dump handling)](#oq3--db-rpo-acceptance--timescaledb-dump-handling)
      - [Agent notes](#agent-notes)
      - [My Comments](#my-comments)
  - [How to maintain this document](#how-to-maintain-this-document)

---

## Open questions

**Only OQ3 remains genuinely open** (awaiting the owner's sign-off on the backup-requirements doc's §7). Every other OQ is settled — see [`resolved-questions.md`](resolved-questions.md) for the one-line resolutions (ADR-backed) or full decided substance (no ADR).

### OQ3 — DB RPO acceptance (+ TimescaleDB dump handling)

**From:** gap #5 (resolved CT path, [ADR 0003](adr/adr-0003-deploy-as-lxc-container.md)). **Decision needed:** is the inherited **≤1 h RPO / no PITR** (hourly logical dumps) acceptable for the accumulating price-history moat, or must **pgBackRest + WAL archiving** be layered **inside the CT**?

A second driver is coupled to this: TimescaleDB ([ADR 0007](adr/adr-0007-datastore-postgresql-timescaledb.md)) means the inherited logical `pg_dump` needs **TimescaleDB-aware** dump/restore (`timescaledb_pre_restore()` / `post_restore()`, compression state not preserved), so **physical** backup may be preferable for _correctness_, not only for RPO. Decide both together.

#### Agent notes

- **Owner direction (2026-07-03):** don't pick an RPO in the abstract — **first author a backup-requirements doc** (RPO, PITR, and the TimescaleDB dump/restore constraints) for hw-radar in the private **`homelab` repo**, coordinated with the existing Hetzner backup strategy; then evaluate the inherited **≤1 h RPO / no-PITR** against those documented requirements and expand only if they demand it. **Non-blocking** — can land in parallel with or after deploy, **but must precede the first backup being taken.**
- **Requirements doc written (2026-07-04):** `homelab/docs/plans/2026-07-04-hw-radar-backup-requirements.md` (verified live against `backup-dumps.sh`/`backup-restic.sh`). **Headline finding:** hw-radar is the fleet's **first TimescaleDB consumer**, but every existing dump is plain `pg_dump --format=custom` with no hypertable awareness → a naïve allowlist entry **restores incorrectly**. So the real work is **TimescaleDB-correct dumps + wiring coverage, not tighter RPO** — the inherited **≤1 h RPO / no-PITR is accepted for v1** (revisit if OQ9 sets sub-hourly polling). Own-CT Postgres (OQ4) matches the CT 109/112/114 pattern. _(OQ3 stays open pending the owner's confirmation of the doc's §7 decisions — RPO, join-B2-tier-1, logical-vs-physical — and the provisioning-time wiring.)_
- **Fallback design if tighter RPO/PITR is wanted:** pgBackRest physical backup + continuous WAL archiving on-CT (`repo1`) with a second repo (`repo2`) on S3-compatible storage (Backblaze B2 or Hetzner Storage Box), pgBackRest AES-256 encryption → PITR + offsite 3-2-1. Supplement with a weekly `pg_dumpall`.
- TimescaleDB: **physical** backups (pgBackRest / `pg_basebackup`) need no special handling; only logical (`pg_dump`) backups carry hypertable caveats — prefer physical.
- Keep the **monthly restore-test** discipline regardless — an untested backup is a hope. **Patch PostgreSQL/tooling** (recent `pg_dump`/`pg_basebackup`/`pg_rewind` CVEs live in the tools).
- Independent of the CT decision. Research: [`postgresql-backup-disaster-recovery-single-vm.md`](research/2026-07-03-postgresql-backup-disaster-recovery-single-vm.md).

#### My Comments

Create a document of all backup requirements and constraints, including RPO, PITR, and TimescaleDB considerations. Evaluate the current backup strategy against these requirements and determine if the current ≤1 h RPO is acceptable or if a more robust solution is needed. Go into the `homelab` repo and create appropriate documentation for hw-radar and document it's backup needs there. The backup strategy will have to be coordinated with the existing Hetzner backup strategy and any other relevant infrastructure. We can expand/improve as necessary, but the first step is to document the requirements and constraints. This is not a blocker, it can be completed in parallel or after the project is deployed, but it should be done before the first backup is taken.

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
