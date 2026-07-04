---
schema_version: '1.1'
id: 'adr-0003-disk-search-deploy-as-lxc-container'
title: 'ADR 0003: Deploy as a dedicated LXC container (not a VM)'
description: 'Deploy disk-search as a dedicated Proxmox LXC container rather than a VM, to reuse the existing Hetzner CT backup/monitoring infrastructure and honor the homelab dedicated-LXC standard; the trade-off is no vTPM.'
doc_type: 'adr'
status: 'active'
created: '2026-07-03'
updated: '2026-07-03'
reviewed: null
owner: ''
consumer: 'mix'
tags:
  - 'adr'
  - 'deployment'
  - 'infrastructure'
  - 'backup'
  - 'monitoring'
aliases: []
related:
  - 'docs/adr/README.md'
  - 'docs/specs/disk-search.md'
  - 'docs/open-questions.md'
supersedes: []
superseded_by: null
source: []
confidence: 'high'
visibility: 'public'
license: null
project:
  decision_makers:
    - 'chris'
  consulted: []
  informed: []
---

# ADR 0003: Deploy as a dedicated LXC container (not a VM)

MADR status: **accepted**.

## Context and Problem Statement

The spec originally specified the deployment target as a **VM in Proxmox** on the Hetzner dedicated server. disk-search's compounding value is its **accumulating price-history database**, so backup coverage and operational monitoring of the deployment are load-bearing, not afterthoughts.

A 2026-07-03 inspection of the _live_ Hetzner infrastructure (SSH, verified against the private `homelab` repo) established that the existing backup/monitoring pipeline is **CT-shaped**:

- **Backup is file-level restic over host + LXC-container ZFS-subvolume paths.** There is **no scheduled `vzdump`/PBS** job at all. A VM's virtual disks are therefore invisible to the pipeline; the one VM protected today backs up only a small config directory via a bespoke Tailscale-SSH file-staging step — not a database.
- **Monitoring auto-discovers containers.** The twice-daily fleet-digest health check enumerates CTs from `pct list`, so a new **container** is monitored automatically; a VM would get only a coarse up/down probe.
- **The homelab standard mandates a dedicated LXC per service** — a VM-direct deployment requires explicit prior approval and a recorded exception.

Given that the deployment target is significant and costly to reverse once provisioned, backed up, and accumulating history: **VM or LXC container?**

## Considered Options

- **Option 1 — Standalone VM** (as originally spec'd), with the database inside the VM.
- **Option 2 — Dedicated LXC container**, with the database on a container Postgres. (chosen)

## Decision Outcome

Chosen option: **Option 2 — deploy as a dedicated LXC container.**

It maximizes reuse of the existing, battle-tested Hetzner infrastructure and aligns with the homelab dedicated-LXC standard (so no approved exception is needed). A VM would have fallen **entirely outside** the current backup coverage (no `vzdump`, and restic cannot see VM disks) and would have required building a dedicated backup pipeline from scratch — cost with no offsetting benefit for this workload.

Option 1 was rejected because it defeats the primary reason the deployment target matters (protecting the price-history moat): it inherits neither the file-level restic pipeline nor monitoring auto-discovery, and it contradicts the homelab standard without a justifying need.

**The database lives on a container Postgres.** Whether that is a Postgres inside the disk-search CT (self-contained) or the shared datastores CT (centralized, already in the dump pipeline) is a deferred sub-decision (open-questions.md OQ4); both are compatible with this ADR.

### Consequences

- **Good** — monitoring is automatic: the fleet-digest health check auto-discovers the new CT; no per-service monitoring config to hand-maintain.
- **Good** — backup reuses the mature local + offsite restic pipeline (retention 48h/14d/8w/6m) and the hourly logical-dump machinery, rather than a from-scratch VM pipeline.
- **Good** — honors the homelab "every service in a dedicated LXC" standard; no exception record required.
- **Bad (accepted trade-off)** — a CT has **no per-container vTPM** (containers share the host kernel), so `systemd-creds --with-key=tpm2` hardware-bound secret storage is unavailable. Secrets resolve via a **local OpenBao Agent** instead (open-questions.md gap #2). Acceptable because the app is designed to hold no in-app secrets and the static-secret set is small.
- **Bad (mitigable)** — backup coverage is a **hardcoded allowlist, not auto-discovery**: provisioning **must** wire the CT's data paths into `backup-restic.sh` and its DB into `backup-dumps.sh` (+ mirror config per the homelab "Maintenance" checklist), or the CT is silently unprotected. A fail-loud guard catches a _disappearing_ declared path, but not a _never-added_ one. **Because the DB uses TimescaleDB (ADR 0007), a plain `pg_dump` allowlist entry is not sufficient** — the dump/restore must be TimescaleDB-aware (`timescaledb_pre_restore()`/`post_restore()`; native-compression state not preserved), or in-CT physical backup must be added (open-questions.md OQ3).
- **Neutral** — the inherited database RPO is **≤1 h with no PITR** (hourly logical dumps). Whether that is sufficient for the price-history moat, or pgBackRest + WAL archiving must be layered inside the CT, is tracked as open-questions.md OQ3 — independent of this container-vs-VM decision.
- **Neutral** — shared-kernel isolation (LXC) rather than full virtualization; acceptable for this single-maintainer workload and consistent with every other service on the host.

### Confirmation

The spec's Server Configuration section states "Dedicated LXC container … (not a VM)" and carries a dedicated Backup & Monitoring bullet; open-questions.md resolved question RQ5 records the **dedicated LXC container** decision, with the vTPM consequence reflected in gap #2. Provisioning-time confirmation: the CT appears in `pct list` (→ auto-monitored) and its paths/DB appear in `backup-restic.sh`/`backup-dumps.sh` (→ backed up).

## More Information

- **Findings that forced the decision:** open-questions.md [`#5` (backup) and `#6` (observability)](../open-questions.md) "Live-state findings" blocks, and resolved question **RQ5** (CT-vs-VM).
- **Downstream consequences tracked as open questions:** OQ3 (DB-RPO acceptance), OQ4 (own-PG-in-CT vs shared datastores CT), and gap #2 (secrets via local OpenBao Agent).
- **Live infrastructure specifics** (container IDs, script paths, addresses) live in the **private `homelab` repo** under `infrastructure/servers/hetzner-dedicated/` — deliberately kept out of this public repo.
