# Hardware Radar

A search-and-monitoring tool that watches ~20 online marketplaces — manufacturer
recertified stores, storage-specialist resellers, eBay/Amazon/Newegg, business VARs,
and refurbished-server sellers — for hard disk drives (HDDs) and solid-state drives
(SSDs), and scores each listing (0–100) to surface the best deals for a
homelab/small-business buyer who favors **enterprise/NAS-grade** and **recertified**
drives. It alerts on availability and price drops.

Personal/business use; single maintainer.

## Status

**Scaffolded — toolchain live, features not started.** The Python verification gate
(uv · Ruff · BasedPyright strict · pytest + coverage · pip-audit) is green locally
and in CI; `src/hw_radar/` is a version-only skeleton. All design substance lives in
the spec, ADRs, and research corpus below.

## Documentation

| Doc | What it is |
| --- | --- |
| [`docs/specs/hw-radar-master-spec.md`](docs/specs/hw-radar-master-spec.md) | The master specification — requirements, architecture, scoring, deployment, milestones. |
| [`docs/adr/`](docs/adr/) | Architecture Decision Records (MADR) — the authoritative record of significant decisions. |
| [`docs/open-questions.md`](docs/open-questions.md) · [`docs/resolved-questions.md`](docs/resolved-questions.md) | Decision backlog (open) and settled provenance. |
| [`docs/research/index.md`](docs/research/index.md) | Generated index of the research corpus (in-depth context behind decisions). |
| [`AGENTS.md`](AGENTS.md) | The toolchain/agent contract (verification gate, dependency/typing/testing rules). |

## Development

```bash
uv sync --all-groups            # create the env from uv.lock
uv run python -m scripts.check  # full verification gate (fmt · lint · types · test · cov · audit)
uv run ruff format . && uv run ruff check . --fix   # fix pass
```

**Branching:** `main` is protected — no direct pushes. `dev` is the long-lived integration branch; do work on `dev` or short-lived `feature/*` branches off `dev`, merging features into `dev`. To release, open a pull request from `dev` into `main` and **merge with a merge commit** (not squash — this keeps the long-lived branch in sync with `main` and preserves history). Merges require the CI checks to pass and a signed-commit history.

## Decided stack

Python · Scrapy (HTTP-first / structured-data-first / browser-last) · PostgreSQL +
TimescaleDB · Django + server-rendered templates + HTMX · APScheduler in one
systemd-supervised poller · deployed to a dedicated Debian LXC container · NGINX +
Let's Encrypt · GitHub Actions CD. See the master spec §8.3 for the ADR-backed
rationale behind each choice.
