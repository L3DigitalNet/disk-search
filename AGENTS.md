# disk-search — Agent Instructions

Cross-agent entry point for this repository. It follows the **Python Tooling SSOT Standard**
(uv · Ruff · BasedPyright strict · pytest + coverage · pip-audit). This file is the
canonical, tracked instruction source; `CLAUDE.md` and `docs/handoff.md` exist locally for
Claude Code sessions but are **git-ignored and absent on a fresh clone** — do not rely on them.

## Project status: scaffolded — toolchain live, feature implementation not started

The repo is scaffolded and the verification gate below is **live and green**. `src/disk_search`
is a version-only skeleton — no features yet. Build features from here under the `src/` layout,
adding real deps with `uv add`. Standard deviations are recorded in `docs/adr/` (ADR-0002).

The planned stack (see `docs/specs/disk-search.md` and `docs/gap-analysis.md`): **Django** +
server-rendered templates + HTMX, PostgreSQL (+ TimescaleDB), Scrapy, deployed to a single VM.

## Operating model

Use the existing project structure and tools. Do not replace the tooling stack unless explicitly
instructed. Read `pyproject.toml`, the relevant spec/ADRs, and any existing tests before editing.

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

Do not claim completion if any command fails. `scripts/check.py`
(`uv run python -m scripts.check`) runs this sequence, and `.github/workflows/check.yml` runs it
in CI on every push/PR to `main`.

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

`.vscode/` is git-ignored in this repo (public-repo hygiene) but the standard tasks apply locally:
`check`, `fix`, `test`, `typecheck`, `audit`. Do not edit `.vscode/settings.json` to bypass the
gate; do not add personal editor preferences.

## Decisions

Significant, hard-to-reverse decisions are recorded as ADRs under `docs/adr/`. This repo
deliberately does **not** adopt the Markdown Frontmatter Standard (see `docs/adr/adr-0001-*`).
Record standard deviations as ADRs (`docs/adr/`), per the Python Tooling Standard §20.
