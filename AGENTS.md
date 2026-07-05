# Hardware Radar — Agent Instructions

Cross-agent entry point for this repository — the canonical, tracked instruction source for any coding agent (Claude Code, Codex CLI, others) or human contributor. `CLAUDE.md` is a thin Claude Code-specific wrapper that imports this file (`@AGENTS.md`) and adds only session-ritual notes on top; do not duplicate this file's content there. `docs/handoff.md` and `TODO.md` are git-ignored, local-only, and **absent on a fresh clone** — do not rely on them.

> **Public repository.** Do not put secrets, internal hostnames/IPs, or infrastructure addresses in this file, in docs, or in commits. Runtime secrets are resolved from OpenBao (paths are referenced in the spec); a local `.env` is for development only.

## Project status: MS-0 foundation built & deployed — MS-1+ features not started

MS-0 is **implemented and live on the Hetzner CT** (see [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml)): a **Django 6** project carrying the **ADR-0010 identity ladder** (migrations run through the `offer_snapshot` **TimescaleDB hypertable**), the `accounts` / `web` (healthz · session login · dashboard) / `poller` (**APScheduler** heartbeat) apps, `deploy/` (systemd units + nginx), and **CD via GitHub Actions** over Tailscale SSH. The verification gate below is **live and green** (uv · Ruff · BasedPyright strict · pytest + coverage · pip-audit). What is **not** built yet is the MS-1+ product surface — the `fetch → parse → normalize → entity-resolve → score → alert` pipeline, the marketplace connectors, and scoring — for which **the spec and research remain the design source**. Build MS-1+ features under the `src/` layout below, adding real deps with `uv add`.

```bash
uv sync --all-groups          # set up the env (creates .venv, reads uv.lock)
podman compose up -d db       # dev TimescaleDB from compose.yaml (docker works too)
uv run python manage.py migrate    # apply migrations to the dev DB
uv run python manage.py runserver  # serve the web app locally
uv run python -m scripts.check # the full verification gate (fmt/lint/type/test/cov/audit)
uv run ruff format . && uv run ruff check . --fix   # fix pass
uv add <pkg> / uv add --dev <pkg>   # add deps (never hand-edit pyproject/uv.lock)
```

**Gotchas:**

- **`tests/db/*` need a live TimescaleDB** (they use the Django `django_db` fixture) — bring the DB up with `podman compose up -d db` first, or those tests error instead of skipping. `tests/unit/*` run without a DB.
- **DB connection is env-driven** — `HW_RADAR_DB_{NAME,USER,PASSWORD,HOST,PORT}` (`settings.py`); `compose.yaml` publishes `127.0.0.1:5432`, matching the `HW_RADAR_DB_PORT` default of `5432`. Override the port env var if 5432 is already taken on your host.

### Where the code lives now

The "Planned architecture" section below is the _design_; this is the _current_ layout under the `src/` package (`hw_radar`):

| Path | What's there |
| --- | --- |
| `src/hw_radar/{settings,urls,wsgi}.py` | Django project core (`DJANGO_SETTINGS_MODULE = hw_radar.settings`). |
| `src/hw_radar/catalog/models/{base,identity,market,evidence}.py` | The **ADR-0010** data model, split by grain — `identity.py` is the category→…→variant ladder; `market.py`/`evidence.py` are listings/offers/observations. Migrations `0001`–`0003` (`0003` = `offer_snapshot` hypertable). |
| `src/hw_radar/accounts/` · `web/` · `poller/` | Auth stub · healthz/login/dashboard views + templates · APScheduler heartbeat (`python -m hw_radar.poller`, systemd-supervised in prod). |
| `deploy/` | `nginx/hw-radar.conf`, `systemd/hw-radar-{web,poller}.service`, `deploy-remote.sh` (on-CT deploy). |
| `tests/{db,unit}/` | `db/` = DB-backed (needs the live DB, above); `unit/` = pure. |
| `manage.py` · `compose.yaml` · `scripts/check.py` | Django CLI · dev DB · the verification gate. |

## What this project is

A search-and-monitoring tool that watches ~20 online marketplaces (manufacturer recert stores, storage-specialist resellers, eBay/Amazon/Newegg, refurb server sellers) for HDDs and SSDs, and scores each listing to surface the best deals for a homelab/small-business buyer who favors **enterprise/NAS-grade** and **recertified** drives. It alerts on availability and price drops. Personal/business use; single maintainer.

## Key documents — read these to understand the system

| Doc | Role |
| --- | --- |
| [`docs/specs/hw-radar-master-spec.md`](docs/specs/hw-radar-master-spec.md) | **The spec — source of truth.** Full SPEC-0000 master spec: requirements, marketplace tiering, scoring, architecture, stack, deployment, milestones. Decisions settled without an ADR are marked _provisional_ in-text. |
| [`docs/open-questions.md`](docs/open-questions.md) | **Open engineering/design decisions** — read for what's still undecided. Carries the shared "How to maintain this document" rules. |
| [`docs/resolved-questions.md`](docs/resolved-questions.md) | **Settled decisions** — companion to `open-questions.md`. Kept for provenance and to keep ADR/spec cross-refs resolvable. |
| [`docs/further-research-needed-prompts.md`](docs/further-research-needed-prompts.md) | Queued deep-research prompts for undecided **domain** areas (drive grading, scoring math, legal/ToS, entity resolution, …). Each maps to a spec gap. |
| [`docs/research/`](docs/research/) | Completed research reports (dated, frontmatter'd markdown). |
| [`docs/research/index.md`](docs/research/index.md) | **Generated** index of the research reports — do **not** hand-edit; regenerated by the research tooling. |
| [`docs/adr/`](docs/adr/) | Architecture Decision Records (MADR format). Significant, hard-to-reverse decisions. See [`docs/adr/README.md`](docs/adr/README.md). |

## Planned architecture (the big picture)

The design is spread across the spec and the research reports; this is the synthesis worth knowing before touching any of it.

- **Acquisition is tiered by source, not uniform.** Prefer official APIs (eBay Browse/Feed, Amazon SP-API where authorized, Newegg is seller-side only) → machine-readable structured data (JSON-LD / hidden JSON) → headless scrape → skip. The ~20 marketplaces are **ranked by trust posture** in the spec; the recert specialists (WD/Seagate recert stores, ServerPartDeals, goHardDrive) are the primary value targets. Search APIs (Serper/Brave/Tavily) are for **discovery**, not authoritative state.
- **Pipeline stages:** `fetch → parse → normalize → entity-resolve → score → persist → alert`. Stages should be independently testable and re-runnable.
- **Canonical-entity model (critical, fixed by ADR-0010):** identity is a multi-grain ladder — `category → product_family → product_model` (the **physical, condition-free** canonical entity) `→ product_variant` (the **sellable** identity: condition/packaging/warranty-channel) `→ listing → offer_snapshot` (time-series observations), plus an orthogonal `drive_unit` (serial/SMART) grain. External identifiers (GTIN/MPN/ASIN/ePID) are `product_alias` rows, **not** columns; drive attributes live in the typed `drive_spec` satellite. Do **not** model a retail page as "the product" and do not simplify back to the two-level model/snapshot shape. See [`docs/adr/adr-0010-canonical-data-model.md`](docs/adr/adr-0010-canonical-data-model.md) + [`docs/research/database-architecture.md`](docs/research/database-architecture.md).
- **Scoring:** a 0–100 composite from price (**USD per TB**, ideally relative to a moving baseline), availability, cross-marketplace-normalized seller reputation, and fitness-for-purpose (enterprise/NAS grade, warranty, condition). Scores should stay **explainable** (a listing can show _why_ it scored what it did). The scoring math is **fixed by ADR-0011**: a weighted geometric mean (price 0.50 · fitness 0.25 · seller 0.15 · availability 0.10) with three non-compensatory veto caps and `λ = min(1, n_eff/30)` warm-up shrinkage, validated against mock data before ratification.
- **Decided stack** (all ADR-backed; see master spec §8.3): **Python**; **Scrapy** with the HTTP-first/structured-data-first/browser-last escalation ladder, `curl_cffi`/Playwright deferred to MS-5 (ADR-0014); **PostgreSQL + TimescaleDB** (ADR-0007); **Django + server-rendered templates + HTMX** (ADR-0004); **APScheduler 3.11.x** in one systemd-supervised poller (ADR-0012); **uv** (ADR-0002); **NGINX + Let's Encrypt**; deployed to a dedicated **Debian 13 LXC container** on Hetzner (ADR-0003); **GitHub Actions** CD via rsync over Tailscale SSH (ADR-0006); email alerts via **M365 Graph** with AgentMail free fallback (ADR-0013); runtime secrets via a local **OpenBao Agent** (ADR-0009). New decisions go through the ADR/OQ process, then the spec.

## Operating model

Use the existing project structure and tools. Do not replace the tooling stack unless explicitly instructed. Read `pyproject.toml`, the relevant spec/ADRs, and any existing tests before editing.

## Fix pass (mutating — run first when changing Python code)

```bash
uv run ruff format .
uv run ruff check . --fix
```

## Verification gate (non-mutating — run before claiming completion)

```bash
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
uv run coverage run -m pytest
uv run coverage report
uv run pip-audit
```

Do not claim completion if any command fails. `scripts/check.py` (`uv run python -m scripts.check`) runs this sequence, and `.github/workflows/check.yml` runs it in CI on every push to `main` or `dev`, on all pull requests, and via `workflow_call` from `deploy.yml`. `dependency-review.yml` is **PR-only** and **required** on `main` — a dev-only commit gets the full gate but no license/dependency scan until the `dev→main` PR.

## Dependency rules

- `uv add <package>` for runtime deps; `uv add --dev <package>` for dev deps; `uv remove <package>` to drop.
- Do not manually edit `uv.lock`; commit it when dependencies change.
- No dependency for trivial standard-library functionality; every runtime dep needs a reason.
- Mention any dependency added or removed in your final response.

## Typing rules (strict for `src/`)

- All public functions/methods/constructors are fully annotated; `None` is explicit as `T | None`.
- Parameterized collections (`list[str]`, `dict[str, int]`); no vague `dict`/`list`/`tuple` on public interfaces.
- Prefer Pydantic models at external I/O boundaries; dataclasses for internal records; `Protocol` for behavior interfaces; `Literal`/`Enum` over boolean flags.
- Avoid implicit `Any` and broad `# type: ignore`; if unavoidable, give the exact rule and reason.

## Testing rules

- New behavior requires tests; bug fixes require a regression test that fails without the fix.
- Tests assert behavior, not implementation. Do not weaken or delete tests to make the suite pass.
- Branch coverage is on; default threshold is 85%.

## Style rules

- Ruff owns formatting, linting, and import sorting. Do not add Black, isort, Flake8, Pylint, or mypy.
- Do not fight formatter output.

## VS Code

`.vscode/` is git-ignored in this repo (public-repo hygiene) but the standard tasks apply locally: `check`, `fix`, `test`, `typecheck`, `audit`. Do not edit `.vscode/settings.json` to bypass the gate; do not add personal editor preferences.

## Git & decision-making conventions

- **Resolving decisions:** [`docs/open-questions.md`](docs/open-questions.md) and the master spec's §21 table are the open-question backlog; ADRs are the authoritative decision record. Domain questions are answered by running the queued deep-research prompts; operational questions are `OQ#` open questions, backed by reports under `docs/research/`. When an `OQ#` is settled, move it to [`docs/resolved-questions.md`](docs/resolved-questions.md) per the maintenance rules (and update every referring link that names the file). When new research lands, **reconcile findings back into the spec** rather than leaving them only in the report; when a provisional (no-ADR) position gets ratified, drop its _provisional_ markers in the spec.
- **Cross-document links are relative.** The spec lives at `docs/specs/hw-radar-master-spec.md`; docs elsewhere link to it as `specs/hw-radar-master-spec.md` (from within `docs/`). Keep links working when moving files.
- **Time-sensitive facts** in research reports (US import de-minimis / tariff status, tool CVEs, library maintenance status) are **dated** — re-verify before relying on them; several were in active flux as of the report dates.
- **Git:** solo-developer repo on a **branched, PR-gated** model. `main` is stable and **protected** — no direct pushes (branch protection requires a PR, the CI `check` status to pass, signed commits, and includes admins). **Commit directly to `dev`** (the long-lived working branch — no PR needed); use a `feature/*` branch only when you want isolation. `main` advances only via a PR from `dev`, **merged with a merge commit** once CI is green (0 approvals required — solo self-merge; merge commits, not squash, keep `dev` in sync with `main`). Conventional commit messages; all commits are GPG-signed.
- **Decisions:** significant, hard-to-reverse decisions are recorded as ADRs under [`docs/adr/`](docs/adr/), per the Python Tooling Standard §20. This repo deliberately does **not** adopt the Markdown Frontmatter Standard (**ADR-0001**). **ADR-0002** keeps `.vscode/` git-ignored (its deferred-gate deviation was retired at scaffold; the `CLAUDE.md` half of that deviation was retired 2026-07-05h — `CLAUDE.md` is now tracked).
