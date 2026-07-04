---
schema_version: '1.1'
id: 'adr-0009-disk-search-secrets-runtime-openbao-agent'
title: 'ADR 0009: Secrets runtime — local OpenBao Agent on the CT'
description: 'Resolve runtime secrets via a local OpenBao Agent on the disk-search CT that AppRole-auto-auths against the Hetzner-local bao-services store and templates to tmpfs, delivered by a persistent CIDR-bound SecretID issued operator-to-CT; the public-repo CD job holds no OpenBao credential.'
doc_type: 'adr'
status: 'active'
created: '2026-07-03'
updated: '2026-07-03'
reviewed: null
owner: ''
consumer: 'mix'
tags:
  - 'adr'
  - 'secrets'
  - 'openbao'
  - 'security'
  - 'deployment'
aliases: []
related:
  - 'docs/adr/README.md'
  - 'docs/specs/disk-search.md'
  - 'docs/open-questions.md'
  - 'docs/research/2026-07-03-github-actions-cd-private-debian-vm.md'
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

# ADR 0009: Secrets runtime — local OpenBao Agent on the CT

MADR status: **accepted**.

> **Public repository.** This ADR records the _decision and its shape only_. Concrete infrastructure specifics — container IDs, private addresses, the SecretID's CIDR bind, and exact script/unit paths — live in the private `homelab` repo (`infrastructure/servers/hetzner-dedicated/bao-agent/`), following the ADR 0003 disclosure boundary.

## Context and Problem Statement

The org standard is **OpenBao as the credential store**; the spec, however, originally said secrets live in a committed-excluded `.env`, and never answered the load-bearing question: **how does the deployed app obtain secrets at runtime** without a plaintext secret at rest? The contradiction is sharpened by two facts already decided:

- disk-search deploys as an **LXC container**, which has **no per-container vTPM** (shared host kernel), so `systemd-creds --with-key=tpm2` hardware-bound storage is unavailable (ADR 0003; open-questions.md RQ3/RQ5).
- CD runs from a **GitHub-hosted runner on a public repo** (ADR 0006), so **CI can hold no OpenBao credential** — anything the workflow can read, the public world's threat model must assume is reachable.

So the app needs live secrets, the container can't hardware-bind them, and the delivery pipeline can't carry them. What resolves secrets at runtime, and how does the bootstrap credential (the AppRole `secret_id`) reach the box?

The research report [`github-actions-cd-private-debian-vm`](../research/2026-07-03-github-actions-cd-private-debian-vm.md) §3 covers the runtime-injection pattern; the live pattern was verified against the Hetzner infrastructure while resolving open-questions.md OQ1.

## Considered Options

- **Option 1 — Local OpenBao Agent on the CT as the next `bao-services` consumer**, AppRole auto-auth, templating secrets to tmpfs; SecretID delivered operator→CT and stored persistent + CIDR-bound. (chosen)
- **Option 2 — The CD job fetches a response-wrapped `secret_id`** and injects it during deploy.
- **Option 3 — Plaintext `.env` at rest** on the CT, provisioned once by hand.
- **Option 4 — `systemd-creds` TPM2-bound** secret storage.

## Decision Outcome

Chosen option: **Option 1.** Settled and **verified against the live infrastructure** while resolving open-questions.md OQ1 — disk-search onboards as the _next_ `bao-services` consumer, the exact pattern already running for the LiteLLM service (the wave-1 reference consumer).

**Runtime path.** A local **OpenBao Agent** (`bao-agent`) runs on the disk-search CT under its own hardened systemd unit. It **AppRole-auto-auths** against the **Hetzner-local `bao-services` store** (not a remote store reached over the tailnet) and **templates secrets to a tmpfs render path** (convention: `/run/bao-agent/disk-search.env`, root-owned, app-group-readable, gone on reboot). App services depend on that unit via `After=`. There is **no plaintext `.env` at rest** and no secret baked into a unit file. The `role_id` ships in the CT config-management; it is not a secret.

**SecretID delivery.** The bootstrap `secret_id` is delivered **operator→CT** (a short-lived response-wrapped token pushed to the container by the issuer script), then unwrapped and stored at a root-only path. It is **persistent** (`remove_secret_id_file_after_reading=false`) so an agent restart re-reads it, and the consumer AppRole is **long-lived** (`num_uses=0, ttl=0`). The active security control is a **CIDR bind on the SecretID**, not a TTL treadmill — the credential is only usable from the container's own address. Rotation is a re-run of the issuer, not a scheduled renewal.

**CD holds nothing.** Because CD is `rsync` over Tailscale from a GitHub-hosted runner (ADR 0006), the public-repo workflow carries **no OpenBao credential**: it ships code and triggers `systemctl restart`; the already-running Agent has templated the secrets the restarted services read.

Option 2 was **rejected (and explicitly withdrawn from the spec)**: it would place an OpenBao-reachable credential inside a public-repo CI job, exactly the exposure the whole model avoids — and it couples secret delivery to the deploy pipeline, which ADR 0006 deliberately keeps credential-free. Option 3 was rejected: a plaintext secret at rest directly violates the OpenBao standard and forfeits rotation/audit. Option 4 was rejected: a CT has no per-container TPM, so TPM2 binding degrades to host-key-only encryption — no real hardware binding (RQ3/RQ5). The Agent is therefore the only viable secrets path for a CT.

> **Supersedes two earlier assumptions in the spec/plan** (not prior ADRs): (a) the spec's `remove_secret_id_file_after_reading=true` — it **breaks restart safety**, because a single-use wrap token means any agent restart fails; the live pattern uses a persistent, CIDR-bound SecretID instead. (b) The "CD job fetches a response-wrapped `secret_id`" mechanism (Option 2) — withdrawn, because CI holds no OpenBao credential.

### Consequences

- **Good** — **no plaintext secret at rest** and **no OpenBao credential in public-repo CI**; the two exposure surfaces that motivated the decision are both closed.
- **Good** — maximal reuse of a **battle-tested, already-running pattern** (`bao-services` + `bao-agent`, wave-1 on the LiteLLM consumer): a documented onboarding runbook and issuer script already exist.
- **Good** — **no renewal treadmill**: a persistent, long-lived, CIDR-bound SecretID means the agent survives restarts unattended; rotation is a deliberate operator action.
- **Bad (accepted)** — security rests on the **CIDR bind + host file permissions**, not on a short TTL. Acceptable given the single-host, Tailscale-only, physically-controlled environment, but it means a compromise _of that container's network identity_ is the threat to guard, and the SecretID file's `0600` root ownership is load-bearing.
- **Bad (operational)** — onboarding is a **manual wave-2 step** (issue SecretID, drop the agent config/unit); it is not yet automated in the ansible scaffold. An implementation task, not a design gap.
- **Spec reconciliation (follow-ups):** the spec still references the withdrawn `/run/disk-search/secrets.env` path and a GMK-direct store — reconcile to `/run/bao-agent/disk-search.env` and the Hetzner-local `bao-services` store; ensure the consumer AppRole's CIDR bind includes the disk-search CT's address (value kept in the `homelab` repo).

### Confirmation

open-questions.md **OQ1** is recorded settled (verified live), and gap #2 records the runtime-injection decision. Provisioning-time confirmation (M0): the web service serves an authenticated page and **reads at least one secret sourced from OpenBao** with **no plaintext `.env` on the CT**; the `bao-agent` unit is `Active`, renders to the tmpfs path, and survives a container restart without re-issuing the SecretID.

## More Information

- **Findings that forced the decision:** open-questions.md **OQ1** (SecretID delivery, verified live), **gap #2** (`.env` → OpenBao runtime injection), and **RQ3/RQ5** (no per-container vTPM → Agent is the only path).
- **Depends on / interacts with:** **ADR 0003** (CT deployment — the vTPM consequence) and **ADR 0006** (credential-free CD from a public-repo runner).
- **Live infrastructure specifics** — container IDs, the SecretID CIDR value, the `bao-issue-secret-id.sh` issuer, agent config and systemd unit paths — live in the **private `homelab` repo** under `infrastructure/servers/hetzner-dedicated/bao-agent/`, deliberately kept out of this public repo.
