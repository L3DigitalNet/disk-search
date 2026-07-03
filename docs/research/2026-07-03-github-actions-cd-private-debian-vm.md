---
schema_version: '1.0'
id: 2026-07-03-github-actions-cd-private-debian-vm
title: GitHub Actions CD to a private Debian 13 VM with systemd + OpenBao secret injection
description: Recommended stack for deploying a FastAPI/Django app plus background workers from GitHub Actions to a single Tailscale-only Debian 13 VM, covering runner topology, systemd service patterns, OpenBao AppRole secret injection, and deployment mechanics.
doc_type: research
status: active
created: '2026-07-03'
updated: '2026-07-03'
reviewed: '2026-07-03'
owner: chris
tags:
- github-actions
- ci-cd
- systemd
- openbao
- vault
- tailscale
- debian
- deployment
aliases:
- gh actions private vm deploy
- openbao systemd secret injection
- self-hosted runner public repo risk
related: []
source:
- https://docs.github.com/en/actions/reference/security/secure-use
- https://tailscale.com/docs/integrations/github/github-action
- https://openbao.org/docs/agent-and-proxy/agent
- https://systemd.io/CREDENTIALS
confidence: high
visibility: private
license: null
---

# GitHub Actions CD to a private Debian 13 VM with systemd + OpenBao secret injection

## Context

Single Debian 13 VM (Proxmox on Hetzner dedicated), NGINX + Let's Encrypt in front, PostgreSQL co-located, single maintainer. Python web app (FastAPI or Django) plus long-running background workers (scrapers/scheduler). Repo is **public**. Org secret store is OpenBao, reachable only via Tailscale, AppRole auth. An existing self-hosted Ubuntu runner is available. Goal: auto-deploy on merge to `main`.

## Recommended default stack (one-liners)

| Layer | Recommendation | Why |
| --- | --- | --- |
| Runner topology | **Push-only self-hosted runner, isolated to this repo, no `pull_request` trigger, ephemeral/JIT config** | Only viable low-effort path to a Tailscale-only VM; the fork-PR attack requires a `pull_request`/`pull_request_target` trigger, which the deploy workflow doesn't need [official] |
| Runner isolation | Dedicated runner user, `--ephemeral`, restricted to this one repo (not org-wide), environment with required reviewer as a backstop | Limits blast radius if a workflow file is ever mis-triggered [official] |
| Secret store auth | **OpenBao Agent with AppRole, response-wrapped `secret_id` delivered by the CD job, `role_id` baked into the VM image/config** | Solves Secret Zero without a static long-lived credential on disk [official][community] |
| Secret delivery to service | **`systemd` `LoadCredential=`/socket-activated credential fetch, agent renders to a root-only tmpfs file, app reads via `$CREDENTIALS_DIRECTORY` or the rendered file** | No `.env` on disk in plaintext at rest; avoids baking secrets into the unit file (`SetCredential=` is world-readable) [official] |
| Process manager | `systemd` units per service (web, worker, scheduler), `Type=simple` + `Restart=on-failure`, socket-activated web tier | Predictable restart/ordering semantics without Docker overhead for a single-VM deploy [community, corroborated] |
| Scheduler | **`systemd` timers** for periodic jobs, in-app scheduler only for jobs needing sub-minute precision or job-parameter fan-out | Timers get journal logging, resource limits, and independent restart semantics for free; avoids a second in-process scheduler thread that silently dies [community] |
| Packaging | **`uv sync --frozen` into a venv on the box**, not Docker | Matches "small-scale, single maintainer, already has a VM" — Docker adds an image-build/registry step with no payoff here; `uv` is fast enough that a full resync during deploy is cheap [community] |
| Deploy transport | Runner has local filesystem access (it's the same VM) — **`rsync`/git checkout + `systemctl restart`**, no SSH hop needed | Runner-on-target collapses "deploy mechanics" to a local script; if you later move the runner off-box, fall back to SSH deploy key over Tailscale |
| DB migrations | **Migrate before restart, additive/backward-compatible migrations only (expand-contract)** | Old code must tolerate the new schema during the restart window [community, corroborated] |

## ⚠ Existing solution note

Coolify/Dokploy/Kamal cover "push-to-deploy on a VPS" out of the box but are Docker-first PaaS layers; adopting one would mean containerizing the app and workers, which is a bigger change than requested. Worth a look only if you're open to Docker — otherwise the systemd-native path above is the better fit for this repo's constraints.

## 1. Reaching a Tailscale-only VM from GitHub Actions

**Options compared:**

| Option | How it works | Fit here |
| --- | --- | --- |
| Self-hosted runner **on the target VM** | Runner polls GitHub outbound over HTTPS; job executes locally | **Recommended.** You already have one. Deploy step is just local `systemctl`/`rsync` — no network hop, no extra secret (Tailscale OAuth client) needed. |
| `tailscale/github-action` on a GitHub-hosted runner | Ephemeral, ACL-scoped Tailscale node spun up per job; runner then SSHes into the VM over the tailnet [official](https://tailscale.com/docs/integrations/github/github-action) | Good alternative if you don't want any code executing on GitHub-controlled-but-owned-by-you infra, or want the runner off the production box entirely. Adds a Tailscale OAuth client secret to manage. |
| SSH deploy key to a public IP | Classic; requires exposing SSH | **Rejected** — VM is intentionally not publicly reachable; would mean opening a port specifically for this. |
| Pull-based (VM polls a queue/webhook receiver) | VM runs a small listener (e.g., a webhook container) that reacts to a signed ping and pulls+deploys | Valid pattern (see `tymscar.com` blog using a Cloudflare Tunnel + webhook container), but for a single VM that already runs the target service, it just re-implements what a self-hosted runner already gives you, with extra moving parts (tunnel, webhook auth) for no security gain since the runner is push-not-pull-triggered here. |

**Recommendation:** keep the existing self-hosted Ubuntu runner, but:
- Scope it to **this repository only** (not an org-wide runner group), and register it with **JIT config or `--ephemeral`** so a compromised job can't leave a persistent runner process to attack later jobs.
- The deploy workflow must trigger only on `push`/`workflow_dispatch` to `main` — **never `pull_request` or `pull_request_target`**. This is the actual security boundary, not the runner's network location.
- As defense-in-depth, put the deploy job behind a GitHub **Environment with a required reviewer** (`production`) even though you're the only approver — it's a free extra gate and prevents a rogue workflow-file edit merged via a compromised token from silently deploying (`docs.github.com/actions/deployments-and-environments`) [official].

### Security implications of self-hosted + public repo (footgun, corroborated)

- GitHub's own docs: "self-hosted runners should almost never be used for public repositories... any user can open pull requests against the repository and compromise the environment" — corroborated by StepSecurity, Sysdig, and multiple community discussions describing the exact attack (`pull_request_target` + malicious workflow file in a fork PR) [official](https://docs.github.com/en/actions/reference/security/secure-use), corroborated by [community](https://github.com/orgs/community/discussions/26722), [blog](https://www.stepsecurity.io/blog/defend-your-github-actions-ci-cd-environment-in-public-repositories), [blog](https://www.sysdig.com/blog/how-threat-actors-are-using-self-hosted-github-actions-runners-as-backdoors).
- The mitigating factor that makes this safe **in this specific setup**: the risk is entirely a function of trigger type, not runner location. A workflow triggered only by `push` to `main` (which only repo collaborators, not fork authors, can do) cannot be reached by a forked PR at all — confirmed by GitHub staff in [community discussion #26722] and independently in the StackOverflow thread analyzing the exact same scenario.
- Residual risk to flag: any *other* workflow file in the same repo that uses `pull_request`/`pull_request_target` and shares the same runner label pool would still expose the runner. Audit all workflow files for `runs-on: self-hosted` + PR-triggering events, not just the deploy workflow.
- GitHub is enforcing a minimum self-hosted runner version (pre-2.329 runners exposed a runner-escape class of vulnerability); full enforcement on github.com began rolling out through 2026 — keep the runner binary current [official](https://github.blog/changelog/2026-06-12-github-actions-minimum-version-enforcement-timeline-for-self-hosted-runners/).

## 2. Service topology: systemd units

**Recommendation:** one unit per logical process (web, worker(s), scheduler), dedicated non-root system user, socket activation for the web tier only.

```ini
# /etc/systemd/system/myapp-web.socket
[Unit]
Description=myapp web socket
[Socket]
ListenStream=/run/myapp/web.sock
SocketUser=myapp
SocketGroup=myapp
SocketMode=0660
[Install]
WantedBy=sockets.target
```

```ini
# /etc/systemd/system/myapp-web.service
[Unit]
Description=myapp web (gunicorn/uvicorn)
Requires=myapp-web.socket
After=network-online.target myapp-secrets.service
Wants=network-online.target
[Service]
Type=simple
User=myapp
Group=myapp
WorkingDirectory=/opt/myapp
ExecStart=/opt/myapp/.venv/bin/gunicorn myapp.asgi:app \
  --worker-class uvicorn_worker.UvicornWorker \
  --bind fd://3 --workers 4 --timeout 120
ExecReload=/bin/kill -s HUP $MAINPID
Restart=on-failure
RestartSec=2
# secrets rendered by openbao-agent@myapp; read from CREDENTIALS_DIRECTORY / rendered file
EnvironmentFile=-/run/myapp/secrets.env
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/myapp/var /run/myapp
PrivateTmp=true
LimitNOFILE=65536
[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/myapp-worker.service
[Unit]
Description=myapp background worker (scrapers)
After=network-online.target myapp-secrets.service postgresql.service
[Service]
Type=simple
User=myapp
Group=myapp
WorkingDirectory=/opt/myapp
ExecStart=/opt/myapp/.venv/bin/python -m myapp.worker
Restart=on-failure
RestartSec=5
EnvironmentFile=-/run/myapp/secrets.env
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/opt/myapp/var
[Install]
WantedBy=multi-user.target
```

Key decisions:
- **`Type=notify` footgun:** plain `gunicorn` does **not** call `sd_notify()` — setting `Type=notify` on a gunicorn unit causes it to time out on start, a confirmed open behavior corroborated by the gunicorn maintainers' issue tracker and an independent StackOverflow report of the same symptom on the systemd watchdog side. Use `Type=simple` unless you add explicit `sd_notify` calls in an app startup hook (e.g., via the `sdnotify` PyPI package) — corroborated: [community](https://github.com/benoitc/gunicorn/issues/2165), [community](https://stackoverflow.com/questions/63945102/gunicorn-with-systemd-watchdog).
- **Socket activation** on the web tier gives you the actual zero-downtime win: systemd holds the listening socket open across a service restart, so client connections queue instead of getting ECONNREFUSED during a deploy — corroborated by [community](https://blog.alphabravo.io/systemd-zero-to-hero-part-5-advanced-features-sandboxing-and-security-best-practices) and a dedicated 2026 walkthrough [blog](https://www.hostmycode.com/blog/systemd-socket-activation-fastapi-vps-zero-downtime-restarts-2026). Workers don't need this (no inbound connections to preserve).
- **Reload vs restart:** `ExecReload=/bin/kill -HUP $MAINPID` triggers gunicorn's graceful worker replacement (new workers spawn, finish in-flight requests on old workers, no dropped connections) — this is the actual zero-downtime mechanism, more important than socket activation for a *code* deploy; combine both.
- **Timers vs in-app scheduler:** use `systemd` timers (`OnCalendar=`, `Persistent=true`, `RandomizedDelaySec=`) for scrapes/cron-shaped jobs. Reasons: independent journal logging per run, independent `Restart=`/resource limits, and — critically — a timer-triggered oneshot service can't silently die inside a long-running worker process the way an in-process `APScheduler`/thread can. Reserve an in-app scheduler only if jobs need sub-minute cadence or dynamic per-tenant schedules that a static timer can't express.

## 3. Runtime secret injection from OpenBao without a static `.env`

**Recommended pattern:** OpenBao Agent (the `bao agent` binary, OpenBao's own fork of Vault Agent — same HCL config surface) running as a small systemd unit, using **AppRole auto-auth with response-wrapped `secret_id`**, templating secrets to a root-owned, `0640`, app-group-readable file under `/run/myapp/` (tmpfs, gone on reboot), which the app service depends on via `After=`.

```ini
# /etc/systemd/system/myapp-secrets.service
[Unit]
Description=OpenBao agent for myapp secrets
Before=myapp-web.service myapp-worker.service
[Service]
Type=simple
User=myapp
Group=myapp
RuntimeDirectory=myapp
RuntimeDirectoryMode=0750
ExecStart=/usr/bin/bao agent -config=/etc/myapp/openbao-agent.hcl
Restart=always
RestartSec=5
NoNewPrivileges=true
ProtectSystem=strict
CapabilityBoundingSet=
[Install]
WantedBy=multi-user.target
```

```hcl
# /etc/myapp/openbao-agent.hcl
vault { address = "https://openbao.internal.tailnet:8200" }

auto_auth {
  method "approle" {
    mount_path = "auth/approle"
    config = {
      role_id_file_path = "/etc/myapp/role_id"          # static, non-secret, checked in via config mgmt
      secret_id_file_path = "/run/myapp/secret_id.wrapped"
      secret_id_response_wrapping_path = "auth/approle/role/myapp/secret-id"
      remove_secret_id_file_after_reading = true
    }
  }
  sink "file" { config = { path = "/run/myapp/.bao-token" } }
}

template {
  source      = "/etc/myapp/secrets.env.tmpl"
  destination = "/run/myapp/secrets.env"
  perms       = "0640"
}
```

**The AppRole bootstrap problem ("Secret Zero") and how it resolves here:**

`role_id` is not secret (it's a static UUID scoped to one AppRole/policy) and can live in the VM's config-management state or repo. The `secret_id`, however, *is* the actual credential-granting artifact — writing it to disk unprotected recreates the `.env`-in-plaintext problem one layer down. The standard resolution, confirmed across HashiCorp's own validated pattern and independent write-ups, is **response wrapping**: a trusted orchestrator (here: the CD pipeline itself, which already authenticates to OpenBao with its own narrowly-scoped AppRole/CI token) calls `bao write -f auth/approle/role/myapp/secret-id`, receives a **single-use, short-TTL wrapping token** instead of the raw `secret_id`, and drops only that wrapping token onto the VM (e.g., via the CD job's existing filesystem access, since the runner is on-box). OpenBao Agent unwraps it on startup, authenticates, and deletes the wrapped file. If the wrapped token is intercepted in transit, it can only be unwrapped once — a replay attempt gets an error and (with `disable_unauthed_rekey_endpoints`/audit logging) becomes a detectable canary — corroborated: [official pattern](https://developer.hashicorp.com/validated-patterns/vault/vault-agent-approle), [community walkthrough](https://tekanaid.com/posts/secret-zero-problem-solved-for-hashicorp-vault).

Practical flow for this project:
1. CD job authenticates to OpenBao with a CI-scoped AppRole (its own Secret Zero, solved once via a GitHub Actions secret holding a narrowly-scoped, periodically-rotated `secret_id` for the *CI* role — acceptable because GitHub Actions secrets are already the trust boundary for this pipeline).
2. CD job requests a wrapped `secret_id` for the **app's** AppRole and places it at `/run/myapp/secret_id.wrapped` on the VM (local copy, since runner == target).
3. `systemctl restart myapp-secrets.service` (or the agent's file-watch on the sink triggers re-auth) — agent unwraps, authenticates, renders the template, and the app services (which depend on it via `After=`) pick up fresh values on their own restart.
4. Consider a short `secret_id_ttl`/`secret_id_num_uses` on the AppRole role definition so a leaked wrapped token has a small blast-radius window.

**Alternative considered — `systemd` native `LoadCredential=`/`ImportCredential=`:** viable for *static* secrets (e.g., a signing key rotated rarely) using `systemd-creds encrypt --with-key=host`, but does not solve dynamic secret rotation or renewal the way the agent's templating loop does, and on a KVM/Proxmox guest without a **vTPM configured**, `systemd-creds` falls back to the host-key-only encryption mode (`/var/lib/systemd/credential.secret`), which only protects against a stolen-disk scenario if that key file itself is separately safeguarded — not a distinct security boundary from file permissions alone. Confirm whether the Proxmox VM has a vTPM device attached before relying on `--with-key=tpm2+host`; if not, this reduces to host-key encryption, which is still worthwhile for defense-in-depth but not TPM-hardware-bound — corroborated: [official](https://systemd.io/CREDENTIALS), [community](https://smallstep.com/blog/systemd-creds-hardware-protected-secrets).

**`envconsul`:** effectively superseded by the templating engine built into Vault/OpenBao Agent (`env_template` + `exec` stanzas in "process supervisor mode") for new setups; don't introduce a second tool where the agent's built-in `exec` mode already covers "render env vars, then exec my app" — [official](https://openbao.org/docs/agent-and-proxy/agent/process-supervisor).

## 4. Deployment mechanics

- **Packaging:** `uv sync --frozen` against a committed `uv.lock` on the target VM, into a persistent `.venv` under `/opt/myapp`. At this scale, Docker's isolation/reproducibility benefit is outweighed by the extra registry/build-cache infrastructure it demands for a single VM that's already the whole fleet. Revisit if you ever need more than one app host.
- **Transport:** because the runner already lives on the target VM, "deploy" is a local script: `git fetch && git checkout <sha>` (or `rsync` from the runner's checkout dir) into a release directory, `uv sync --frozen`, run migrations, `systemctl restart myapp-web myapp-worker`. No SSH hop, no deploy key to manage. If the runner is ever moved off-box (e.g., switching to the Tailscale-GitHub-Action pattern), replace this step with `rsync -e ssh` or `tailscale ssh` over the tailnet — do **not** open a public SSH port for this.
- **Zero-ish-downtime restart:** socket activation (connections queue) + gunicorn `SIGHUP` graceful reload (workers replaced without dropping in-flight requests) together get you close to zero-downtime for the web tier without a blue-green setup. Workers can just `Restart=on-failure` — a scraper mid-run getting killed and restarted is generally an acceptable trade at this scale; make jobs idempotent/resumable rather than engineering worker blue-green.
- **Migration ordering — the actual footgun:** run migrations **before** restarting the app, and make every migration **backward-compatible with the currently-running (old) code** during the restart window (expand/contract pattern: add-nullable-column now, backfill, switch reads in a later deploy, drop old column in a third deploy). Never combine "add NOT NULL column" and "restart to code that requires it" in one deploy step if you want to avoid a request-failure window — corroborated: [blog](https://www.massivegrid.com/blog/zero-downtime-deployment-ubuntu-vps), [blog](https://www.deployhq.com/blog/database-migration-strategies-for-zero-downtime-deployments-a-step-by-step-guide). This is a process discipline, not a tool — Django/Alembic migrations don't enforce it for you.

## Version-sensitive flags

- **OpenBao 2.5.x** (Feb 2026, Linux Foundation governance) is current as of this research; `bao agent` config syntax mirrors Vault Agent but check `openbao.org/docs/agent-and-proxy` for the OpenBao-specific stanza names (`env_template`, `process-supervisor` mode) rather than assuming 1:1 parity with HashiCorp Vault docs going forward — the projects are diverging gradually [official](https://openbao.org).
- **Debian 13 (trixie)**, released Aug 2025, ships kernel 6.12 LTS and current systemd; verify the installed systemd version supports the specific `LoadCredentialEncrypted=`/`ImportCredential=` syntax used above (these are fully present in the systemd shipped with trixie, but confirm before scripting against RHEL-9-era examples which sometimes lag or diverge slightly).
- **GitHub Actions self-hosted runner minimum-version enforcement** is actively rolling out through H2 2026 — pin the runner update mechanism so it doesn't silently stop registering.
- Tavily `search_depth=fast` returned empty results during this research — used `basic`/`advanced` throughout per the known 2026 quirk.

## Open Questions

| # | Question | Why unresolved |
| --- | --- | --- |
| 1 | Does the Proxmox VM have a vTPM device attached? | Determines whether `systemd-creds --with-key=tpm2` is available or whether the org falls back to host-key-only encryption for any static systemd-native credentials. |
| 2 | Is Django or FastAPI the actual target framework? | Migration tooling (`manage.py migrate` vs Alembic) and ASGI/WSGI worker class differ; unit sketch above assumes an ASGI app behind gunicorn+uvicorn workers. |
| 3 | What is the CI AppRole's own Secret Zero rotation cadence? | Research covered the pattern; the org's specific rotation policy for the CI-facing `secret_id` stored as a GitHub Actions secret wasn't in scope here. |

## Handoff

Persisted at `/home/chris/projects/disk-search/docs/research/2026-07-03-github-actions-cd-private-debian-vm.md`. Downstream skills that may consume it:

- `superpowers:brainstorming` — feed Open Questions (vTPM availability, framework choice) into a design conversation
- `feature-dev:feature-dev` — start implementing the systemd units + OpenBao agent config from this background

## Sources

| URL | Title | Date | Authority |
| --- | --- | --- | --- |
| https://docs.github.com/en/actions/reference/security/secure-use | Secure use reference - GitHub Docs | 2026 | official |
| https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments | Deployments and environments - GitHub Docs | 2026 | official |
| https://github.blog/changelog/2026-06-12-github-actions-minimum-version-enforcement-timeline-for-self-hosted-runners/ | Minimum version enforcement timeline for self-hosted runners | 2026-06-12 | official |
| https://github.com/orgs/community/discussions/26722 | Self-hosted runner security with public repositories | 2020-2026 | community |
| https://www.stepsecurity.io/blog/defend-your-github-actions-ci-cd-environment-in-public-repositories | Defend Your GitHub Actions CI/CD Environment in Public Repositories | 2026 | blog |
| https://www.sysdig.com/blog/how-threat-actors-are-using-self-hosted-github-actions-runners-as-backdoors | How threat actors are using self-hosted GitHub Actions runners as backdoors | 2026 | blog |
| https://stackoverflow.com/questions/77179987 | Is it really unsafe to use a GitHub self-hosted runner on a public repo | 2023-2026 | community |
| https://tailscale.com/docs/integrations/github/github-action | Tailscale GitHub Action | 2026 | official |
| https://tailscale.com/docs/solutions/connect-github-CICD-workflows-to-private-infrastructure-without-public-exposure | Connect GitHub CI/CD workflows to private infrastructure | 2026 | official |
| https://aaronstannard.com/docker-compose-tailscale | Deploying Docker Compose Applications with Tailscale and GitHub Actions | 2025-04-23 | blog |
| https://blog.tymscar.com/posts/privategithubcicd | How I deploy private GitHub projects to local self-hosted servers | 2026 | blog |
| https://openbao.org/docs/agent-and-proxy/agent | What is OpenBao Agent? | 2026 | official |
| https://openbao.org/docs/agent-and-proxy/agent/process-supervisor | OpenBao agent's process supervisor mode | 2026 | official |
| https://openbao.org/docs/agent-and-proxy/autoauth/methods/approle | OpenBao Auto-Auth AppRole method | 2026 | official |
| https://openbao.org/docs/auth/approle | AppRole auth method - OpenBao | 2026 | official |
| https://endoflife.date/openbao | OpenBao release schedule | 2026-06-17 | community |
| https://developer.hashicorp.com/validated-patterns/vault/vault-agent-approle | Integrate brownfield applications with Vault Agent and AppRole | 2026 | official |
| https://tekanaid.com/posts/secret-zero-problem-solved-for-hashicorp-vault | Secret Zero Problem Solved for HashiCorp Vault | 2026 | community |
| https://systemd.io/CREDENTIALS | System and Service Credentials - Systemd | 2026 | official |
| https://smallstep.com/blog/systemd-creds-hardware-protected-secrets | The magic of systemd-creds | 2022-2026 | blog |
| https://github.com/systemd/systemd/issues/23566 | systemd-creds: allow to store host private key in RAM | 2026 | community |
| https://www.hostmycode.com/blog/systemd-socket-activation-fastapi-vps-zero-downtime-restarts-2026 | Systemd Socket Activation for FastAPI on a VPS: 2026 guide | 2026 | blog |
| https://blog.alphabravo.io/systemd-zero-to-hero-part-5-advanced-features-sandboxing-and-security-best-practices | Systemd: Zero to Hero – Part 5 | 2026 | blog |
| https://github.com/benoitc/gunicorn/issues/2165 | gunicorn times out starting with systemd service Type=notify | ongoing | community |
| https://stackoverflow.com/questions/63945102/gunicorn-with-systemd-watchdog | gUnicorn with systemd Watchdog | 2026 | community |
| https://www.massivegrid.com/blog/zero-downtime-deployment-ubuntu-vps | Blue-Green and Rolling Deployments on Ubuntu VPS | 2026 | blog |
| https://www.deployhq.com/blog/database-migration-strategies-for-zero-downtime-deployments-a-step-by-step-guide | Database Migration Strategies for Zero-Downtime Deployments | 2026 | blog |
| https://haloy.dev/blog/self-hosted-deployment-tools-compared | Self-Hosted Deployment Tools Compared (2026) | 2026-03-22 | blog |
| https://getdeploying.com/guides/coolify-vs-dokploy | Coolify vs. Dokploy: Which is best in 2026? | 2026 | blog |
| https://lwn.net/Articles/1033474 | Lucky 13: a look at Debian trixie | 2025-08 | community |
| https://www.debian.org/releases/stable/release-notes | Release Notes for Debian 13 (trixie) | 2026 | official |
| https://lalatenduswain.medium.com/openbao-vs-hashicorp-vault-the-secrets-management-showdown-every-devops-team-needs-to-read-in-2026-458ae0d9a408 | OpenBao vs HashiCorp Vault 2026 | 2026-02 | blog |
