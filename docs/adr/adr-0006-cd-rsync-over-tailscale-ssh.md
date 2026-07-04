---
schema_version: '1.1'
id: 'adr-0006-disk-search-cd-rsync-over-tailscale-ssh'
title: 'ADR 0006: CD via GitHub-hosted runner + rsync over Tailscale SSH'
description: 'Deploy from a GitHub-hosted runner that joins the tailnet ephemerally and rsyncs to the private CT over Tailscale SSH, rather than running a self-hosted runner on the box — because a public repo must not expose infrastructure to untrusted fork code.'
doc_type: 'adr'
status: 'active'
created: '2026-07-03'
updated: '2026-07-03'
reviewed: null
owner: ''
consumer: 'mix'
tags:
  - 'adr'
  - 'ci-cd'
  - 'deployment'
  - 'tailscale'
  - 'github-actions'
aliases: []
related:
  - 'docs/adr/README.md'
  - 'docs/specs/disk-search.md'
  - 'docs/gap-analysis.md'
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

# ADR 0006: CD via GitHub-hosted runner + rsync over Tailscale SSH

MADR status: **accepted**.

## Context and Problem Statement

The spec states "GitHub Actions → automatic deployment on merge to main" — the _what_, never the _how_: the transport, how CI reaches a **non-public** target (admin access is Tailscale-only; no public SSH port), and how the app runs as a service. The repo is **public**, and GitHub advises against self-hosted runners on public repos because a fork's pull request can execute untrusted code on the runner's infrastructure.

## Considered Options

- **Option 1 — Self-hosted runner on the deployment host**, deploying locally.
- **Option 2 — GitHub-hosted `ubuntu-latest` runner + `rsync` over Tailscale SSH** to the private CT. (chosen)
- **Option 3 — Docker registry/image-based deploy** (build image in CI, pull on the host).

## Decision Outcome

Chosen option: **Option 2 — GitHub-hosted runner, then `rsync` over Tailscale SSH.**

A GitHub-hosted `ubuntu-latest` runner builds and tests (nothing to harden; torn down after each run). The deploy job **joins the tailnet ephemerally** (`tailscale/github-action` with an OAuth client or a short-TTL pre-authorized ephemeral auth key), `rsync`s the checked-out source (or a `uv`-built artifact) to the CT, and triggers the remote restart over `tailscale ssh`. No public SSH port; no persistent runner.

**Trigger + secret discipline:** deploy only on `push` / `workflow_dispatch` to `main` (never `pull_request`/`pull_request_target`); put the deploy job behind a GitHub **Environment with a required reviewer**; store the Tailscale auth key + deploy SSH key as **Environment secrets** so PR-triggered runs can't read them; scope the tailnet ACL so the ephemeral runner node can reach **only** the disk-search CT's SSH.

**Build & release mechanics:** build the venv **on the CT** (`uv sync --frozen`) to avoid arch/path skew; run migrations **before** restart using **expand/contract** (backward-compatible with the still-running old code). **Service topology (systemd):** a **web** unit (gunicorn + uvicorn workers, `ExecReload=kill -HUP $MAINPID`) and **worker** unit(s) (`Restart=on-failure`) under a **dedicated non-root user** with `ProtectSystem=strict`/`NoNewPrivileges`; periodic scrapes run under **systemd timers**, not an in-process scheduler. Avoid `Type=notify` — plain gunicorn never calls `sd_notify()` and the unit would time out.

Option 1 was rejected outright: a public repo should not run a self-hosted runner where fork code could reach the box — a risk best avoided rather than fenced by trigger discipline alone. Option 3 was rejected because a registry/image build buys nothing for a single-CT fleet — pure overhead.

### Consequences

- **Good** — no infrastructure to harden or patch (ephemeral hosted runner), no public SSH port, no persistent runner, and no untrusted-fork code path to the box.
- **Good** — building the venv on the CT eliminates arch/path skew; expand/contract migrations avoid a broken window during restart.
- **Bad** — each deploy performs an ephemeral tailnet join, adding moving parts (auth-key/OAuth lifecycle, ACL scoping) versus a local runner.
- **Neutral** — no container image artifact; the release unit is source + an on-CT venv, consistent with the single-CT deployment (ADR 0003).

### Confirmation

gap-analysis gap #4 records this decision (superseding the earlier self-hosted-runner proposal). Confirmed when the workflow deploys on merge with zero manual steps, holds no OpenBao credential (secrets are templated on the CT by the local Agent — gap #2), and a rollback to the previous SHA is demonstrated.

## Open Question

The **ephemeral-runner tailnet auth mechanism** — Tailscale **OAuth client** (preferred: scoped, auto-rotating) vs a pre-generated ephemeral auth key — is not yet fixed; it depends on what the existing tailnet ACL setup supports (gap-analysis Open-Question #5). This ADR's decision holds regardless of which is chosen.

## More Information

- Research: [`github-actions-cd-private-debian-vm`](../research/2026-07-03-github-actions-cd-private-debian-vm.md) §1–4.
- Related: ADR 0003 (deploy target is a CT — this ADR's "CT" replaces the spec's original "VM"), gap #2 (runtime secrets via a local OpenBao Agent; CI holds no OpenBao credential).
