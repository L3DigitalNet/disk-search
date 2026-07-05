# MS-0 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver spec §19 MS-0 — a deployable Django foundation: uv-managed Django project, the ADR-0010 canonical schema as initial migrations (with `offer_snapshot` as a TimescaleDB hypertable), the single-account Argon2id session login with a `users` stub, CD via GitHub-hosted runner → rsync over Tailscale SSH, and the systemd web/poller/bao-agent service contract.

**Architecture:** Single Django project under the existing `src/hw_radar` layout with three apps — `accounts` (users stub, ADR-0005), `catalog` (the full ADR-0010 identity spine + evidence tables), `web` (healthz + login + hello dashboard). A stub APScheduler poller proves the systemd supervision contract (ADR-0012). Deployment artifacts (systemd units, nginx config, deploy workflow, remote script) live in the repo; execution of the deploy is operator-gated on CT provisioning (Task 8).

**Tech Stack:** Python 3.14 (pinned) · Django 6.0 · psycopg 3.3 (`[binary]`) · PostgreSQL + TimescaleDB (Community/TSL edition) · gunicorn 26 · APScheduler 3.11.x · uv/Ruff/BasedPyright-strict/pytest+coverage/pip-audit (the live gate).

**Verified version facts (researched 2026-07-04; sources: official docs/PyPI):** Django 6.0 supports Python 3.12–3.14 (6.1 is beta — do not use). `CompositePrimaryKey` models **cannot be registered in Django admin** and relational fields cannot target composite-PK models (documented 6.0 limitation — see Task 4 notes). TimescaleDB 2.27+ supports PG 16/17/18; the classic `create_hypertable(table, time_col)` two-arg form is deprecated since 2.13 — use `by_range()`. **Debian's `postgresql-*-timescaledb` package is the Apache-2 edition and lacks compression/retention/continuous aggregates** — production must install the Community (TSL) packages from Timescale's packagecloud repo. psycopg 3.3.4 and pytest-django 4.12 are current; APScheduler 4.x is still explicitly not production-ready (ADR's `3.11.x` pin stands). `django-types` (0.24.0, active) is the pyright/basedpyright-compatible stubs package — `django-stubs` needs the mypy plugin we don't run.

## Global Constraints

Every task implicitly includes all of these. Copied from `AGENTS.md`, spec §8.5/§8.6, Appendix B, and repo git conventions.

- **Gate before every commit claim:** `uv run python -m scripts.check` must exit 0 (format → lint → basedpyright strict → pytest+coverage branch ≥85% → pip-audit). Fix pass first when editing: `uv run ruff format . && uv run ruff check . --fix`.
- **Local DB prerequisite for the gate:** tests hit PostgreSQL+TimescaleDB. Start it first: `podman compose up -d db` (or `docker compose up -d db`) from the repo root (compose file created in Task 1).
- **Dependencies only via `uv add` / `uv add --dev`** — never hand-edit `[project.dependencies]` or `uv.lock`. Allowed runtime deps for MS-0 (all in spec §8.6): `django[argon2]>=6.0,<6.1`, `psycopg[binary]>=3.3`, `gunicorn>=26.0`, `apscheduler>=3.11,<4` (**4.x prohibited**). Dev deps added: `pytest-django>=4.12`, `django-types>=0.24` — toolchain-adjacent additions recorded as a Deviations Log row in Task 7 (approved by owner approval of this plan).
- **Typing:** BasedPyright strict on `src/` + `tests/`, `failOnWarnings=true`. Generated `migrations/` are excluded from basedpyright + given a Ruff per-file-ignore (Task 1) — generated code, not a gate weakening. Any unavoidable ignore uses the exact rule id + a reason comment (AGENTS.md).
- **Git:** commit directly to `dev` (no PR needed); conventional commit messages; commits are GPG-signed automatically. `main` advances only via a `dev→main` PR with green CI — that PR merge is what triggers the first deploy (Task 8).
- **Public repo:** no secrets, internal hostnames, IPs, or CT IDs in any committed file. Deploy host/user names go in GitHub **Environment secrets** only. OpenBao *paths* are fine; values never.
- **Milestone discipline (Appendix B.1):** MS-0 only. No scrapers, no scoring, no watches, no FX fetching, no heartbeat tables (ADR-0015 lands MS-1). Migrations from now on are expand/contract.
- **Spec contract (Appendix B):** underspecified behavior → file an `OQ-` row with a proposed default, don't guess silently; divergences → `DEV-` row; keep §17.3 traceability current (Task 7); B.3 completion report at milestone end.
- **Naming:** explicit `db_table` names matching the spec's table vocabulary (`product_model`, `offer_snapshot`, …) so raw SQL in ADRs/research reads identically against the live schema.

## File Structure

```
manage.py                                  # new — Django entrypoint (root; not typechecked: outside src/tests)
compose.yaml                               # new — dev-only TimescaleDB
.env.example                               # new — documented dev env vars (values are dev-only defaults)
pyproject.toml                             # modified — pytest-django/coverage/ruff/basedpyright config
.gitignore                                 # modified — add RELEASE
.github/workflows/check.yml                # modified — workflow_call + dev push + TimescaleDB service
.github/workflows/deploy.yml               # new — CD per ADR-0006
src/hw_radar/settings.py                   # new — single env-driven settings module
src/hw_radar/urls.py                       # new
src/hw_radar/wsgi.py                       # new
src/hw_radar/accounts/{__init__,apps,models,admin}.py + migrations/   # users stub (ADR-0005)
src/hw_radar/web/{__init__,apps,views}.py + templates/                # healthz, login, dashboard
src/hw_radar/catalog/{__init__,apps,admin}.py
src/hw_radar/catalog/models/{__init__,base,identity,market,evidence}.py
src/hw_radar/catalog/migrations/           # 0001_initial, 0002_market_evidence, 0003_offer_snapshot_hypertable
src/hw_radar/poller/{__init__,__main__}.py # APScheduler heartbeat stub (ADR-0012)
deploy/systemd/hw-radar-web.service        # new
deploy/systemd/hw-radar-poller.service     # new
deploy/nginx/hw-radar.conf                 # new
deploy/deploy-remote.sh                    # new — runs on the CT
docs/runbooks/deploy-and-rollback.md       # new
docs/runbooks/provisioning.md              # new — operator checklist (public-safe; specifics in homelab repo)
tests/unit/test_settings.py, test_poller.py, test_wsgi.py
tests/db/test_accounts.py, test_web.py, test_identity.py, test_market.py, test_migrations.py
```

Design decisions this plan locks in (each traceable to a source):

1. **`offer_snapshot` PK = `CompositePrimaryKey("listing_id", "observed_at")`** — TimescaleDB requires the partition column in every unique constraint; a lone surrogate `id` PK is invalid on a hypertable. Consequences (documented Django 6.0 limitations): `OfferSnapshot` is **not registered in admin**, and MS-2's `listing_score` must reference snapshots by `(listing FK, observed_at)`, not a snapshot FK.
2. **`product_alias` is the full ADR-0010/ADR-0019/DR-010 shape from day one**: grain-addressed across model XOR family XOR variant (exactly-one check constraint), **marketplace-local and single-target** (identifier aliases — including `OTHER` — are unique per `(alias_type, text, source_site)`; the same ASIN on one site cannot point at two products), with **`OEM_PN` as the sole N:N exemption** (OEM↔MPN is many-to-many per the OEM cross-reference research; protected against exact per-target duplicates) **and structurally capped at family/model grain** (check constraint — an OEM PN cannot identify a sellable variant, ADR-0019), and **provenance-classed** (`source_kind`: `catalog_authoritative` / `listing_derived` / `manual`). Only `listing_resolution` edges + alias revocation land at MS-1. _(Codex CR-004, rounds 1–3.)_
3. **`expires_at` NULL = indefinite, tied to the class by check constraints** — indefinite classes (merchant_fact, amazon_identifier, tavily_extract, manufacturer_reference) must have `expires_at IS NULL`; bounded classes (ebay_listing_observation, amazon_ephemeral, transient_discovery) must have it `NOT NULL`. Recorded as **DEV-002** (Task 7): DR-001's literal "non-null `expires_at`" is unsatisfiable for indefinite classes. **Reference tables (`product_model`, `drive_spec`, `product_alias`) carry the retention columns from day one** (blank class = unclassified/manual until the MS-1 catalog ingest stamps `manufacturer_reference`, DR-009) so no expand/contract churn hits the costliest tables later. _(Codex CR-001.)_
4. **`search_observation` is IR-006-minimal**: it stores the discovered URL + our own query metadata only — **no `result_title`, `result_snippet`, or provider-payload columns exist**, guarded by a schema test (Serper/Brave forbid persisting snippets/JSON; Tavily-extracted *facts* flow through `raw_payload`/listing rows with `retention_class=tavily_extract`, not through this table). _(Codex CR-002.)_
5. **The deploy gate re-runs on the exact ref being deployed** — `check.yml` accepts a `ref` input via `workflow_call`, and `deploy.yml` passes `inputs.ref || github.sha`, so a rollback dispatch validates the SHA it ships (a reusable workflow otherwise runs on the caller's event ref). _(Codex CR-003.)_
6. **Poller at MS-0 is a heartbeat-only stub** — spec MS-0 says "install systemd web + poller units"; the stub proves supervision + the ADR-0012 job-defaults contract (including the spec-named resource limits on the unit); MS-1 fills in real jobs.
7. **Static files via `collectstatic` + nginx alias** — no whitenoise dep needed for a single-CT deployment.
8. **`check.yml` gains `workflow_call:` (reused by deploy.yml) and `push: dev`** so direct-to-dev commits are CI-checked. Residual: `dependency-review` runs only on PRs, so **every `uv add` in this plan is followed by a manual `uvx licensecheck` pass** against the dependency-review allowlist. _(Codex CR-005.)_

---

### Task 1: Dependencies, Django skeleton, users stub, dev/CI database

**Files:**
- Create: `manage.py`, `compose.yaml`, `.env.example`, `src/hw_radar/settings.py`, `src/hw_radar/urls.py`, `src/hw_radar/wsgi.py`, `src/hw_radar/accounts/__init__.py`, `src/hw_radar/accounts/apps.py`, `src/hw_radar/accounts/models.py`, `src/hw_radar/accounts/admin.py`, `src/hw_radar/accounts/migrations/` (generated `0001_initial.py`)
- Modify: `pyproject.toml` (tool config only — deps go through uv), `.github/workflows/check.yml`
- Test: `tests/unit/test_settings.py`, `tests/unit/test_wsgi.py`, `tests/db/test_accounts.py`, `tests/db/test_migrations.py`

**Interfaces:**
- Produces: `hw_radar.settings` (env contract: `HW_RADAR_ENV` = `dev`|`production`, `DJANGO_SECRET_KEY`, `HW_RADAR_DB_{NAME,USER,PASSWORD,HOST,PORT}`, `HW_RADAR_ALLOWED_HOSTS`, `HW_RADAR_STATIC_ROOT`); `accounts.User` (= `AUTH_USER_MODEL`, db_table `users`); dev DB at `127.0.0.1:5432` (`hw_radar`/`hw_radar`/`hw_radar`). Later tasks add apps to `INSTALLED_APPS` and paths to `urls.py`.

- [ ] **Step 1: Add dependencies**

```bash
uv add "django[argon2]>=6.0,<6.1" "psycopg[binary]>=3.3" "gunicorn>=26.0"
uv add --dev "pytest-django>=4.12" "django-types>=0.24"
# License gate (CR-005): runtime deps AND the dev group — --zero makes
# violations exit nonzero; --only-licenses takes SPACE-SEPARATED values
# (documented form: --only-licenses ONLY_LICENSES [ONLY_LICENSES ...]);
# -g dev includes the dev dependency group. Confirm flag names with
# `uvx licensecheck --help` if the tool errors (CLI flags drift).
uvx licensecheck --zero --only-licenses MIT BSD APACHE LGPL PYTHON ISC MPL UNLICENSE
uvx licensecheck --zero -g dev --only-licenses MIT BSD APACHE LGPL PYTHON ISC MPL UNLICENSE
```

Note: `django[argon2]` pulls `argon2-cffi` (Django's Argon2 hasher requires it; the hasher's default variant is Argon2**id** — Django docs).

License gate rationale (CR-005): `dependency-review` only runs on PRs, so direct-to-`dev` dependency adds bypass it until the `dev→main` PR — this manual pass is what the workflow's own header comment mandates. Every reported license must fall inside `dependency-review.yml`'s `allow-licenses` list. Expected here: Django BSD-3-Clause, psycopg LGPL-3.0, gunicorn MIT, argon2-cffi MIT, pytest-django BSD-3-Clause, django-types MIT. Anything outside the allowlist: stop and surface to the owner before committing.

- [ ] **Step 2: Dev database plumbing**

Create `compose.yaml`:

```yaml
# Local development/test database ONLY — production runs its own in-CT
# PostgreSQL+TimescaleDB (ADR-0003/0007). Community (TSL) image: the Apache-2
# build lacks compression/retention, which later milestones rely on.
services:
  db:
    image: timescale/timescaledb:2.27.0-pg17
    environment:
      POSTGRES_DB: hw_radar
      POSTGRES_USER: hw_radar
      POSTGRES_PASSWORD: hw_radar   # dev-only value; prod password comes from OpenBao (ADR-0009)
    ports:
      - "127.0.0.1:5432:5432"
    volumes:
      - db-data:/var/lib/postgresql/data
volumes:
  db-data:
```

Create `.env.example` (tracked; documents the dev contract — real `.env` stays git-ignored):

```bash
# Local development only. Production gets these from the bao-agent tmpfs render
# (/run/bao-agent/hw-radar.env) via systemd EnvironmentFile= — never a file at rest (ADR-0009).
HW_RADAR_ENV=dev
DJANGO_SECRET_KEY=dev-only-insecure-key
HW_RADAR_DB_NAME=hw_radar
HW_RADAR_DB_USER=hw_radar
HW_RADAR_DB_PASSWORD=hw_radar
HW_RADAR_DB_HOST=127.0.0.1
HW_RADAR_DB_PORT=5432
```

Start it: `podman compose up -d db` (or `docker compose up -d db`). Verify: `podman compose ps` shows the db service running.

- [ ] **Step 3: Write the failing tests**

`tests/unit/test_settings.py`:

```python
from django.conf import settings


def test_argon2id_is_primary_password_hasher() -> None:
    assert settings.PASSWORD_HASHERS[0] == "django.contrib.auth.hashers.Argon2PasswordHasher"


def test_hardened_cookie_flags() -> None:
    # ADR-0005: Secure+HttpOnly+SameSite=Lax. Secure is prod-only (dev runs http).
    assert settings.SESSION_COOKIE_HTTPONLY is True
    assert settings.SESSION_COOKIE_SAMESITE == "Lax"
    assert settings.CSRF_COOKIE_SAMESITE == "Lax"


def test_custom_user_model_is_the_stub() -> None:
    assert settings.AUTH_USER_MODEL == "accounts.User"


def test_strong_password_floor() -> None:
    min_length = next(
        v["OPTIONS"]["min_length"]
        for v in settings.AUTH_PASSWORD_VALIDATORS
        if v["NAME"].endswith("MinimumLengthValidator")
    )
    assert min_length >= 16
```

`tests/unit/test_wsgi.py`:

```python
def test_wsgi_application_loads() -> None:
    from hw_radar.wsgi import application

    assert application is not None
```

`tests/db/test_accounts.py`:

```python
import pytest

from hw_radar.accounts.models import User


@pytest.mark.django_db
def test_password_hash_is_argon2id() -> None:
    user = User.objects.create_user(username="owner", password="a-strong-password-123!")
    assert user.password.startswith("$argon2id$")
    assert user.check_password("a-strong-password-123!")


@pytest.mark.django_db
def test_users_table_name_matches_spec() -> None:
    assert User._meta.db_table == "users"
```

`tests/db/test_migrations.py`:

```python
from io import StringIO

from django.core.management import call_command


def test_no_missing_migrations() -> None:
    # Fails if any model change lacks a migration (keeps schema == migrations).
    call_command("makemigrations", "--check", "--dry-run", stdout=StringIO())
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `uv run coverage run -m pytest tests/unit/test_settings.py -v`
Expected: FAIL/ERROR — `hw_radar.settings` does not exist / pytest-django unconfigured.

- [ ] **Step 5: Create the Django project files**

`manage.py` (repo root):

```python
#!/usr/bin/env python
import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hw_radar.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
```

`src/hw_radar/settings.py` (complete file):

```python
"""Django settings for Hardware Radar.

Single env-driven module — no settings package, no per-env files.
Environment contract (see .env.example for dev values):
  HW_RADAR_ENV              "dev" (default) | "production"
  DJANGO_SECRET_KEY         REQUIRED in production (rendered from OpenBao, ADR-0009)
  HW_RADAR_DB_NAME/_USER/_PASSWORD/_HOST/_PORT
  HW_RADAR_ALLOWED_HOSTS    comma-separated override
  HW_RADAR_STATIC_ROOT      collectstatic target (prod: served by nginx)
Production values arrive via the bao-agent tmpfs render (systemd
EnvironmentFile=/run/bao-agent/hw-radar.env) — never a plaintext file at rest.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # repo root

ENV = os.environ.get("HW_RADAR_ENV", "dev")
IS_PRODUCTION = ENV == "production"
DEBUG = not IS_PRODUCTION

if IS_PRODUCTION:
    SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]  # KeyError = fail loud; no fallback in prod
else:
    SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key")

_default_hosts = "hw-radar.l3digital.net,localhost,127.0.0.1" if IS_PRODUCTION else "localhost,127.0.0.1"
ALLOWED_HOSTS = [h for h in os.environ.get("HW_RADAR_ALLOWED_HOSTS", _default_hosts).split(",") if h]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "hw_radar.accounts",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "hw_radar.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "hw_radar.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("HW_RADAR_DB_NAME", "hw_radar"),
        "USER": os.environ.get("HW_RADAR_DB_USER", "hw_radar"),
        "PASSWORD": os.environ.get("HW_RADAR_DB_PASSWORD", "hw_radar"),
        "HOST": os.environ.get("HW_RADAR_DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("HW_RADAR_DB_PORT", "5432"),
    }
}

AUTH_USER_MODEL = "accounts.User"

# ADR-0005: Argon2id first (argon2-cffi's default variant is argon2id).
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 16},  # ADR-0005 "strong password", single account
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = Path(os.environ.get("HW_RADAR_STATIC_ROOT", BASE_DIR / "staticfiles"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"

# ADR-0005 hardened cookies. Secure flags are prod-only (dev runs plain http).
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = IS_PRODUCTION
CSRF_COOKIE_SECURE = IS_PRODUCTION
X_FRAME_OPTIONS = "DENY"

if IS_PRODUCTION:
    # §13.6: CSRF origins confirmed at MS-0. No CORS policy needed — no
    # cross-origin API surface exists (server-rendered same-origin app, D-004).
    CSRF_TRUSTED_ORIGINS = ["https://hw-radar.l3digital.net"]
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")  # nginx sets it
```

`src/hw_radar/urls.py` (Task 2 extends this):

```python
from django.contrib import admin
from django.urls import URLPattern, URLResolver, path

urlpatterns: list[URLPattern | URLResolver] = [
    path("admin/", admin.site.urls),
]
```

`src/hw_radar/wsgi.py`:

```python
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hw_radar.settings")

application = get_wsgi_application()
```

`src/hw_radar/accounts/__init__.py`: empty file.

`src/hw_radar/accounts/apps.py`:

```python
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hw_radar.accounts"
    label = "accounts"
```

`src/hw_radar/accounts/models.py`:

```python
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Single-account stub (ADR-0005).

    No extra fields yet. The custom model exists so multi-user growth is
    additive — AUTH_USER_MODEL cannot be changed after the first migration.
    """

    class Meta:
        db_table = "users"
```

`src/hw_radar/accounts/admin.py`:

```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from hw_radar.accounts.models import User

admin.site.register(User, UserAdmin)
```

- [ ] **Step 6: Tool configuration in `pyproject.toml`**

Append `DJANGO_SETTINGS_MODULE` to `[tool.pytest.ini_options]` and exclude generated migrations from coverage/lint/typecheck (generated code — not a gate weakening):

```toml
[tool.pytest.ini_options]
minversion = "9.0"
testpaths = ["tests"]
DJANGO_SETTINGS_MODULE = "hw_radar.settings"
addopts = [
    "-ra",
    "--strict-markers",
    "--strict-config",
]
```

```toml
[tool.coverage.run]
branch = true
source = ["src"]
omit = ["*/migrations/*"]
```

Add to `[tool.ruff.lint.per-file-ignores]`:

```toml
"src/hw_radar/*/migrations/*.py" = [
    "RUF012", # generated migrations use mutable class attrs without ClassVar
]
```

Add to `[tool.basedpyright]`:

```toml
exclude = ["**/migrations"]
```

- [ ] **Step 7: Generate the accounts migration**

```bash
uv run python manage.py makemigrations accounts
```

Expected: `accounts/migrations/0001_initial.py` created (User model). Then verify migrations apply from empty:

```bash
uv run python manage.py migrate
```

Expected: all `contrib` + `accounts` migrations apply with no errors.

- [ ] **Step 8: Run the tests to verify they pass**

Run: `uv run coverage run -m pytest -v`
Expected: PASS (settings, wsgi, accounts, migrations tests; existing `test_version.py` still green).

Note on strict typing: `django-types` provides pyright-compatible stubs. If `basedpyright` reports unknown member types on ORM calls (e.g. `User.objects`), annotate explicitly (`objects: ClassVar[UserManager[Self]]`) rather than blanket-ignoring; if a stub gap is unavoidable, use the exact rule id with a reason comment (AGENTS.md).

- [ ] **Step 9: Update `check.yml` — service DB, dev push, reusable**

Modify `.github/workflows/check.yml`: replace the `on:` block, make the checkout ref-aware, and add `services:` to the `check` job:

```yaml
on:
  pull_request:
  push:
    branches: ["main", "dev"]
  workflow_call:
    inputs:
      ref:
        description: "Ref to check (deploy.yml passes the exact ref it will ship)"
        required: false
        type: string
        default: ""
```

Change the checkout step so a caller-supplied ref wins (empty string = the event's default ref, so `pull_request`/`push` behavior is unchanged):

```yaml
      - uses: actions/checkout@v7
        with:
          ref: ${{ inputs.ref }}
```

(CR-003: a same-repo reusable workflow runs on the **caller's** event ref — without this input, a rollback dispatch would gate `main` HEAD while deploying an older SHA.)

```yaml
    services:
      db:
        image: timescale/timescaledb:2.27.0-pg17
        env:
          POSTGRES_DB: hw_radar
          POSTGRES_USER: hw_radar
          POSTGRES_PASSWORD: hw_radar
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U hw_radar"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10
```

(Defaults in `settings.py` match the service, so no extra env vars are needed. `workflow_call:` lets `deploy.yml` reuse this gate; `push: dev` closes the unchecked-direct-commit gap.)

- [ ] **Step 10: Full gate, then commit**

```bash
uv run ruff format . && uv run ruff check . --fix
uv run python -m scripts.check
git add pyproject.toml uv.lock manage.py compose.yaml .env.example src/hw_radar tests .github/workflows/check.yml
git commit -m "feat(core): scaffold Django project with users stub and TimescaleDB dev/CI database"
```

Expected: gate exits 0. Coverage note: if `coverage report` falls below 85% at this intermediate point (settings-heavy, little logic), proceed to Task 2 in the same commit series only if the shortfall is real — the web app in Task 2 restores headroom; do not lower the threshold.

---

### Task 2: Web app — healthz, session login, authenticated hello

**Files:**
- Create: `src/hw_radar/web/__init__.py`, `src/hw_radar/web/apps.py`, `src/hw_radar/web/views.py`, `src/hw_radar/web/templates/base.html`, `src/hw_radar/web/templates/web/dashboard.html`, `src/hw_radar/web/templates/registration/login.html`
- Modify: `src/hw_radar/settings.py` (add `"hw_radar.web"` to `INSTALLED_APPS`), `src/hw_radar/urls.py`, `.gitignore` (add `RELEASE`)
- Test: `tests/db/test_web.py`

**Interfaces:**
- Consumes: `accounts.User` (Task 1).
- Produces: `GET /healthz` → JSON `{"status", "version", "release", "database"}`, 200 or 503 (deploy smoke-test + Uptime Kuma target; unauthenticated by design); `GET /` → login-required dashboard (`name="dashboard"`); `login`/`logout` URL names; optional `RELEASE` file at repo root (written by the deploy workflow, git-ignored) surfaces the deployed SHA for the rollback demo.

- [ ] **Step 1: Write the failing tests**

`tests/db/test_web.py`:

```python
import pytest
from django.test import Client

from hw_radar.accounts.models import User

PASSWORD = "a-strong-password-123!"


@pytest.fixture
def owner(db: None) -> User:
    return User.objects.create_user(username="owner", password=PASSWORD)


def test_healthz_ok(client: Client, db: None) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] is True
    assert body["version"]


def test_dashboard_requires_login(client: Client, db: None) -> None:
    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/accounts/login/")


def test_login_then_dashboard(client: Client, owner: User) -> None:
    assert client.login(username="owner", password=PASSWORD)
    response = client.get("/")
    assert response.status_code == 200
    assert b"Hardware Radar" in response.content


def test_wrong_password_rejected(client: Client, owner: User) -> None:
    assert not client.login(username="owner", password="wrong-password-000!")


def test_login_page_renders(client: Client, db: None) -> None:
    assert client.get("/accounts/login/").status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run coverage run -m pytest tests/db/test_web.py -v`
Expected: FAIL — 404s (no routes yet).

- [ ] **Step 3: Implement the web app**

`src/hw_radar/web/__init__.py`: empty. `src/hw_radar/web/apps.py`:

```python
from django.apps import AppConfig


class WebConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hw_radar.web"
    label = "web"
```

`src/hw_radar/web/views.py`:

```python
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import DatabaseError, connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render

from hw_radar import __version__


def _release() -> str:
    # RELEASE is written by the deploy workflow (git SHA); absent in dev.
    release_file = settings.BASE_DIR / "RELEASE"
    try:
        return release_file.read_text(encoding="utf-8").strip()
    except OSError:
        return "dev"


def healthz(request: HttpRequest) -> JsonResponse:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            db_ok = cursor.fetchone() == (1,)
    except DatabaseError:
        db_ok = False
    payload = {
        "status": "ok" if db_ok else "degraded",
        "version": __version__,
        "release": _release(),
        "database": db_ok,
    }
    return JsonResponse(payload, status=200 if db_ok else 503)


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    return render(request, "web/dashboard.html", {"version": __version__, "release": _release()})
```

`src/hw_radar/web/templates/base.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}Hardware Radar{% endblock %}</title>
</head>
<body>
  <main>{% block content %}{% endblock %}</main>
</body>
</html>
```

`src/hw_radar/web/templates/web/dashboard.html`:

```html
{% extends "base.html" %}
{% block content %}
  <h1>Hardware Radar</h1>
  <p>Hello, {{ user.get_username }}. Foundation is live (MS-0).</p>
  <p>Version {{ version }} · release {{ release }}</p>
  <form method="post" action="{% url 'logout' %}">
    {% csrf_token %}
    <button type="submit">Log out</button>
  </form>
{% endblock %}
```

`src/hw_radar/web/templates/registration/login.html`:

```html
{% extends "base.html" %}
{% block title %}Log in — Hardware Radar{% endblock %}
{% block content %}
  <h1>Log in</h1>
  {% if form.errors %}<p>Invalid credentials.</p>{% endif %}
  <form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">Log in</button>
  </form>
{% endblock %}
```

Update `src/hw_radar/urls.py` (full file):

```python
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import URLPattern, URLResolver, path

from hw_radar.web import views

urlpatterns: list[URLPattern | URLResolver] = [
    path("healthz", views.healthz, name="healthz"),
    path("", views.dashboard, name="dashboard"),
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("admin/", admin.site.urls),
]
```

Add `"hw_radar.web",` to `INSTALLED_APPS` in `settings.py` (after `"hw_radar.accounts"`). Append `RELEASE` on its own line to `.gitignore`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run coverage run -m pytest tests/db/test_web.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Gate and commit**

```bash
uv run ruff format . && uv run ruff check . --fix
uv run python -m scripts.check
git add src/hw_radar tests/db/test_web.py .gitignore
git commit -m "feat(web): healthz endpoint, session login, authenticated hello dashboard"
```

---

### Task 3: Catalog app — the identity ladder (ADR-0010)

**Files:**
- Create: `src/hw_radar/catalog/__init__.py`, `src/hw_radar/catalog/apps.py`, `src/hw_radar/catalog/admin.py`, `src/hw_radar/catalog/models/__init__.py`, `src/hw_radar/catalog/models/base.py`, `src/hw_radar/catalog/models/market.py` (SourceSite/SourceType only — Task 4 extends it), `src/hw_radar/catalog/models/identity.py`, `src/hw_radar/catalog/migrations/0001_initial.py` (generated, then hand-edited: extensions + seed)
- Modify: `src/hw_radar/settings.py` (add `"hw_radar.catalog"`)
- Test: `tests/db/test_identity.py`

**Interfaces:**
- Consumes: nothing app-level.
- Produces (used by Task 4 and MS-1): `RetentionClass` (TextChoices), `INDEFINITE_RETENTION_CLASSES`/`BOUNDED_RETENTION_CLASSES`, `retention_constraints(prefix)` (per-model constraint factory), abstract `RetentionGoverned` (fields `retention_class: CharField(max_length=40)`, `expires_at: DateTimeField(null=True)`), abstract `TimeStamped` (`created_at`/`updated_at`); models `SourceSite`, `Manufacturer`, `Category`, `ProductFamily`, `ProductModel`, `ProductVariant`, `DriveSpec`, `ProductAlias`, `DriveUnit`; enums `SourceType`, `Condition`, `Packaging`, `RecertChannel`, `WarrantyChannel`, `AliasType`, `AliasSourceKind`. All with explicit spec-vocabulary `db_table` names.
- `SourceSite` lives in Task 3 (not Task 4) because `ProductAlias.source_site` is part of the alias uniqueness key from day one — ASIN/ePID are marketplace-local (ADR-0010 rule 3, CR-004).

- [ ] **Step 1: Write the failing tests**

`tests/db/test_identity.py`:

```python
import pytest
from django.db import IntegrityError

from hw_radar.catalog.models import (
    AliasType,
    Category,
    Condition,
    DriveSpec,
    Manufacturer,
    MediaType,
    ProductAlias,
    ProductFamily,
    ProductModel,
    ProductVariant,
    RecertChannel,
)


@pytest.fixture
def seagate(db: None) -> Manufacturer:
    return Manufacturer.objects.create(name="Seagate", normalized_name="seagate")


@pytest.fixture
def exos_16tb(seagate: Manufacturer) -> ProductModel:
    return ProductModel.objects.create(
        manufacturer=seagate,
        model_number="ST16000NM001G",
        normalized_model_number="st16000nm001g",
    )


def test_drive_category_is_seeded(db: None) -> None:
    # ADR-0010: category is the extensibility axis; v1 ships only 'drive'.
    assert Category.objects.filter(slug="drive").exists()


def test_recert_and_new_are_one_model_two_variants(exos_16tb: ProductModel) -> None:
    # ADR-0010 confirmation criterion (rule 1 + 2).
    ProductVariant.objects.create(product_model=exos_16tb, condition=Condition.NEW)
    ProductVariant.objects.create(
        product_model=exos_16tb,
        condition=Condition.RECERTIFIED,
        recert_channel=RecertChannel.FACTORY,
    )
    assert ProductModel.objects.count() == 1
    assert exos_16tb.variants.count() == 2


def test_model_identity_anchor_is_unique(seagate: Manufacturer, exos_16tb: ProductModel) -> None:
    with pytest.raises(IntegrityError):
        ProductModel.objects.create(
            manufacturer=seagate,
            model_number="ST16000NM001G (OEM)",
            normalized_model_number="st16000nm001g",
        )


def test_duplicate_variant_rejected(exos_16tb: ProductModel) -> None:
    ProductVariant.objects.create(product_model=exos_16tb, condition=Condition.NEW)
    with pytest.raises(IntegrityError):
        ProductVariant.objects.create(product_model=exos_16tb, condition=Condition.NEW)


def test_drive_spec_is_one_to_one_satellite(exos_16tb: ProductModel) -> None:
    DriveSpec.objects.create(
        product_model=exos_16tb,
        media_type=MediaType.HDD,
        capacity_tb="16.000",
        spec_json={"helium": True},
    )
    assert exos_16tb.drive_spec.media_type == MediaType.HDD


def test_alias_requires_exactly_one_grain(
    seagate: Manufacturer, exos_16tb: ProductModel
) -> None:
    family = ProductFamily.objects.create(
        category=Category.objects.get(slug="drive"),
        manufacturer=seagate,
        name="Exos X16",
        normalized_name="exos x16",
    )
    # one grain: OK (ADR-0019: OEM part numbers attach at family/model grain only)
    ProductAlias.objects.create(
        alias_type=AliasType.OEM_PN,
        normalized_alias_text="wd-oem-0001",
        product_family=family,
        source_kind=AliasSourceKind.MANUAL,
    )
    with pytest.raises(IntegrityError):
        ProductAlias.objects.create(
            alias_type=AliasType.MPN,
            normalized_alias_text="st16000nm001g",
            product_model=exos_16tb,
            product_family=family,
            source_kind=AliasSourceKind.MANUAL,
        )


def test_alias_requires_at_least_one_grain(db: None) -> None:
    with pytest.raises(IntegrityError):
        ProductAlias.objects.create(
            alias_type=AliasType.GTIN,
            normalized_alias_text="0012345678905",
            source_kind=AliasSourceKind.MANUAL,
        )


def test_alias_supports_variant_grain(exos_16tb: ProductModel) -> None:
    # IR-007/ADR-0018: the manufacturer catalog persists the full
    # family→model→variant MPN matrix as aliases — variant grain is required.
    variant = ProductVariant.objects.create(
        product_model=exos_16tb, condition=Condition.RECERTIFIED, recert_channel=RecertChannel.FACTORY
    )
    alias = ProductAlias.objects.create(
        alias_type=AliasType.MPN,
        normalized_alias_text="st16000nm001g-recert-sku",
        product_variant=variant,
        source_kind=AliasSourceKind.CATALOG_AUTHORITATIVE,
    )
    assert alias.product_variant == variant


def test_alias_is_marketplace_local(exos_16tb: ProductModel) -> None:
    # ADR-0010 rule 3: ASIN/ePID are marketplace-local — the same alias text may
    # exist per source_site, but is unique within one.
    amazon = SourceSite.objects.create(
        name="Amazon", normalized_name="amazon", source_type=SourceType.MARKETPLACE
    )
    ebay = SourceSite.objects.create(
        name="eBay", normalized_name="ebay", source_type=SourceType.MARKETPLACE
    )
    for site in (amazon, ebay):
        ProductAlias.objects.create(
            alias_type=AliasType.ASIN,
            normalized_alias_text="b08x123456",
            product_model=exos_16tb,
            source_site=site,
            source_kind=AliasSourceKind.LISTING_DERIVED,
        )
    assert ProductAlias.objects.filter(normalized_alias_text="b08x123456").count() == 2
    with pytest.raises(IntegrityError):
        ProductAlias.objects.create(
            alias_type=AliasType.ASIN,
            normalized_alias_text="b08x123456",
            product_model=exos_16tb,
            source_site=amazon,
            source_kind=AliasSourceKind.LISTING_DERIVED,
        )


def test_identifier_alias_cannot_point_at_two_targets(
    seagate: Manufacturer, exos_16tb: ProductModel
) -> None:
    # Same ASIN on the same site must not resolve to two different products —
    # identifier aliases are single-target per marketplace (ADR-0010 rule 3).
    amazon = SourceSite.objects.create(
        name="Amazon2", normalized_name="amazon2", source_type=SourceType.MARKETPLACE
    )
    other_model = ProductModel.objects.create(
        manufacturer=seagate, model_number="ST18000NM000J", normalized_model_number="st18000nm000j"
    )
    ProductAlias.objects.create(
        alias_type=AliasType.ASIN,
        normalized_alias_text="b09y654321",
        product_model=exos_16tb,
        source_site=amazon,
        source_kind=AliasSourceKind.LISTING_DERIVED,
    )
    with pytest.raises(IntegrityError):
        ProductAlias.objects.create(
            alias_type=AliasType.ASIN,
            normalized_alias_text="b09y654321",
            product_model=other_model,
            source_site=amazon,
            source_kind=AliasSourceKind.LISTING_DERIVED,
        )


def test_oem_alias_may_map_to_multiple_models(seagate: Manufacturer, exos_16tb: ProductModel) -> None:
    # OEM PN ↔ MPN is N:N (OEM cross-reference research): the same OEM part
    # number legitimately maps to several models — exempt from single-target.
    other_model = ProductModel.objects.create(
        manufacturer=seagate, model_number="ST16000NM002G", normalized_model_number="st16000nm002g"
    )
    for model in (exos_16tb, other_model):
        ProductAlias.objects.create(
            alias_type=AliasType.OEM_PN,
            normalized_alias_text="dell-0f1w2x3",
            product_model=model,
            source_kind=AliasSourceKind.LISTING_DERIVED,
        )
    assert ProductAlias.objects.filter(normalized_alias_text="dell-0f1w2x3").count() == 2


def test_oem_alias_rejected_at_variant_grain(exos_16tb: ProductModel) -> None:
    # ADR-0019: OEM part numbers are capped at family/model grain — an OEM PN
    # is too coarse to identify a sellable variant.
    variant = ProductVariant.objects.create(product_model=exos_16tb, condition=Condition.NEW)
    with pytest.raises(IntegrityError):
        ProductAlias.objects.create(
            alias_type=AliasType.OEM_PN,
            normalized_alias_text="hp-mb016000gwxyz",
            product_variant=variant,
            source_kind=AliasSourceKind.LISTING_DERIVED,
        )


def test_reference_tables_carry_retention_columns(exos_16tb: ProductModel) -> None:
    # DR-009 (ADR-0018): catalog-seeded product_model/drive_spec/product_alias
    # rows carry retention_class=manufacturer_reference. The MS-1 ingest stamps
    # it; MS-0 guarantees the columns exist on the costliest-to-reshape tables.
    for model_cls in (ProductModel, DriveSpec, ProductAlias):
        field_names = {f.name for f in model_cls._meta.get_fields()}
        assert {"retention_class", "expires_at"} <= field_names, model_cls.__name__
```

Extend the import block at the top of the test file accordingly: add `AliasSourceKind`, `ProductVariant`, `SourceSite`, `SourceType` (and keep the rest).

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run coverage run -m pytest tests/db/test_identity.py -v`
Expected: FAIL — `hw_radar.catalog` does not exist.

- [ ] **Step 3: Implement the catalog identity models**

`src/hw_radar/catalog/__init__.py`: empty. `src/hw_radar/catalog/apps.py`:

```python
from django.apps import AppConfig


class CatalogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hw_radar.catalog"
    label = "catalog"
```

`src/hw_radar/catalog/models/base.py`:

```python
from django.db import models


class RetentionClass(models.TextChoices):
    """DR-001 retention classes (ADR-0010 rule 6; ADR-0018 added manufacturer_reference).

    ADR-0015's availability_heartbeat classes are added at MS-1 with their tables.
    """

    MERCHANT_FACT = "merchant_fact", "Merchant fact (indefinite)"
    EBAY_LISTING_OBSERVATION = "ebay_listing_observation", "eBay observation (≤6h, delete-on-delist)"
    AMAZON_EPHEMERAL = "amazon_ephemeral", "Amazon ephemeral (24h)"
    AMAZON_IDENTIFIER = "amazon_identifier", "Amazon identifier (indefinite)"
    TRANSIENT_DISCOVERY = "transient_discovery", "Search-provider discovery (TTL 0)"
    TAVILY_EXTRACT = "tavily_extract", "Tavily-extracted fact (indefinite)"
    MANUFACTURER_REFERENCE = "manufacturer_reference", "Manufacturer reference (indefinite, append-only)"


# DEV-002: DR-001's literal "non-null expires_at" is unsatisfiable for
# indefinite classes; the encoding is expires_at NULL = indefinite, and the
# class↔TTL coherence is enforced by retention_constraints() below.
# Adding a class at MS-1 (availability_heartbeat*) = extend one list here +
# a constraint migration — deliberate, so a new class can't dodge the rule.
INDEFINITE_RETENTION_CLASSES: tuple[RetentionClass, ...] = (
    RetentionClass.MERCHANT_FACT,
    RetentionClass.AMAZON_IDENTIFIER,
    RetentionClass.TAVILY_EXTRACT,
    RetentionClass.MANUFACTURER_REFERENCE,
)
BOUNDED_RETENTION_CLASSES: tuple[RetentionClass, ...] = (
    RetentionClass.EBAY_LISTING_OBSERVATION,
    RetentionClass.AMAZON_EPHEMERAL,
    RetentionClass.TRANSIENT_DISCOVERY,
)


def retention_constraints(prefix: str) -> list[models.CheckConstraint]:
    """DR-001 constraints for EVIDENCE models (call in each concrete Meta).

    Per-model because subclass Meta.constraints does not merge with an
    abstract parent's. Two rules: (1) retention_class must be set — Django
    CharFields default to '', which satisfies NOT NULL silently; (2) TTL
    coherence — indefinite classes carry no expires_at, bounded classes must.
    Reference/identity tables (product_model, drive_spec, product_alias) carry
    the columns WITHOUT these constraints: blank class = unclassified/manual
    row until the MS-1 catalog ingest stamps manufacturer_reference (DR-009).
    """
    return [
        models.CheckConstraint(
            condition=~models.Q(retention_class=""),
            name=f"{prefix}_retention_class_set",
        ),
        models.CheckConstraint(
            condition=(
                models.Q(
                    retention_class__in=[c.value for c in INDEFINITE_RETENTION_CLASSES],
                    expires_at__isnull=True,
                )
                | models.Q(
                    retention_class__in=[c.value for c in BOUNDED_RETENTION_CLASSES],
                    expires_at__isnull=False,
                )
            ),
            name=f"{prefix}_retention_ttl_coherent",
        ),
    ]


class RetentionGoverned(models.Model):
    """DR-001 retention governance fields (see retention_constraints)."""

    retention_class = models.CharField(max_length=40, choices=RetentionClass.choices, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True


class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
```

`src/hw_radar/catalog/models/identity.py`:

```python
from django.db import models

from hw_radar.catalog.models.base import TimeStamped


class Condition(models.TextChoices):
    NEW = "new", "New"
    RECERTIFIED = "recertified", "Recertified"
    REFURBISHED = "refurbished", "Refurbished"
    USED = "used", "Used"
    OPEN_BOX = "open_box", "Open box"
    UNKNOWN = "unknown", "Unknown"


class Packaging(models.TextChoices):
    RETAIL = "retail", "Retail"
    BULK = "bulk", "Bulk/OEM"
    UNKNOWN = "unknown", "Unknown"


class RecertChannel(models.TextChoices):
    FACTORY = "factory", "Manufacturer recertified"
    SELLER = "seller", "Seller refurbished"
    NONE = "none", "Not recertified"
    UNKNOWN = "unknown", "Unknown"


class WarrantyChannel(models.TextChoices):
    MANUFACTURER = "manufacturer", "Manufacturer"
    SELLER = "seller", "Seller"
    NONE = "none", "None"
    UNKNOWN = "unknown", "Unknown"


class MediaType(models.TextChoices):
    HDD = "hdd", "HDD"
    SSD = "ssd", "SSD"
    UNKNOWN = "unknown", "Unknown"


class RecordingTech(models.TextChoices):
    CMR = "cmr", "CMR"
    SMR_DEVICE_MANAGED = "smr_dm", "SMR (device-managed)"
    SMR_HOST_MANAGED = "smr_hm", "SMR (host-managed)"
    SMR_UNKNOWN = "smr_unknown", "SMR (type unknown)"
    UNKNOWN = "unknown", "Unknown"


class AliasType(models.TextChoices):
    GTIN = "gtin", "GTIN"
    UPC = "upc", "UPC"
    EAN = "ean", "EAN"
    ASIN = "asin", "ASIN"
    EPID = "epid", "eBay ePID"
    MPN = "mpn", "Manufacturer part number"
    OEM_PN = "oem_pn", "OEM part number"
    RETAIL_PN = "retail_pn", "Retail part number"
    REGION_PN = "region_pn", "Region/revision part number"
    OTHER = "other", "Other"


class AliasSourceKind(models.TextChoices):
    """DR-010 alias provenance: learned (listing_derived) aliases are revocable
    at MS-1; catalog_authoritative rows come from the ADR-0018 ingest."""

    CATALOG_AUTHORITATIVE = "catalog_authoritative", "Catalog authoritative"
    LISTING_DERIVED = "listing_derived", "Listing derived"
    MANUAL = "manual", "Manual"


class Manufacturer(TimeStamped):
    name = models.CharField(max_length=100)
    normalized_name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "manufacturer"

    def __str__(self) -> str:
        return self.name


class Category(TimeStamped):
    """The extensibility axis (ADR-0010): 'drive' in v1; later 'ram', 'gpu'."""

    slug = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)

    class Meta:
        db_table = "category"
        verbose_name_plural = "categories"

    def __str__(self) -> str:
        return self.slug


class ProductFamily(TimeStamped):
    """Watches and tier-lookup target this grain (e.g. 'Exos X18')."""

    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="families")
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.PROTECT, related_name="families")
    name = models.CharField(max_length=200)
    normalized_name = models.CharField(max_length=200)

    class Meta:
        db_table = "product_family"
        verbose_name_plural = "product families"
        constraints = [
            models.UniqueConstraint(
                fields=["manufacturer", "normalized_name"], name="product_family_unique_per_mfr"
            ),
        ]

    def __str__(self) -> str:
        return self.name


class ProductModel(TimeStamped, RetentionGoverned):
    """The canonical entity: physical, condition-free (ADR-0010 rule 1).

    Identity anchor = manufacturer + normalized_model_number (surrogate id).
    Family may be unknown for listing-discovered models pending catalog backfill.
    Carries retention columns unconstrained (DR-009): the MS-1 catalog ingest
    stamps manufacturer_reference on seeded rows; blank = unclassified/manual.
    """

    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.PROTECT, related_name="models")
    product_family = models.ForeignKey(
        ProductFamily, on_delete=models.PROTECT, related_name="models", null=True, blank=True
    )
    model_number = models.CharField(max_length=100)
    normalized_model_number = models.CharField(max_length=100)

    class Meta:
        db_table = "product_model"
        constraints = [
            models.UniqueConstraint(
                fields=["manufacturer", "normalized_model_number"],
                name="product_model_identity_anchor",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.manufacturer} {self.model_number}"


class ProductVariant(TimeStamped):
    """The sellable identity (ADR-0010 rule 2): price analytics roll up here."""

    product_model = models.ForeignKey(ProductModel, on_delete=models.PROTECT, related_name="variants")
    condition = models.CharField(max_length=20, choices=Condition.choices, default=Condition.UNKNOWN)
    packaging = models.CharField(max_length=20, choices=Packaging.choices, default=Packaging.UNKNOWN)
    recert_channel = models.CharField(
        max_length=20, choices=RecertChannel.choices, default=RecertChannel.UNKNOWN
    )
    warranty_channel = models.CharField(
        max_length=20, choices=WarrantyChannel.choices, default=WarrantyChannel.UNKNOWN
    )
    warranty_months = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        db_table = "product_variant"
        constraints = [
            models.UniqueConstraint(
                fields=["product_model", "condition", "packaging", "recert_channel", "warranty_channel"],
                name="product_variant_unique_sellable_identity",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product_model} [{self.condition}/{self.recert_channel}]"


class DriveSpec(TimeStamped, RetentionGoverned):
    """Typed 1:1 satellite (ADR-0010 rule 4): the only drive-shaped table.

    Scoring-critical fields are typed columns; the long tail lives in spec_json.
    Full field tables: research/machine-usable-drive-suitability-taxonomy report.
    Nullable columns are 'unknown until catalog/parse fills them' (ADR-0018).
    Retention columns per DR-009, unconstrained (see retention_constraints doc).
    """

    product_model = models.OneToOneField(
        ProductModel, on_delete=models.CASCADE, primary_key=True, related_name="drive_spec"
    )
    media_type = models.CharField(max_length=10, choices=MediaType.choices, default=MediaType.UNKNOWN)
    interface = models.CharField(max_length=50, blank=True, default="")
    form_factor = models.CharField(max_length=50, blank=True, default="")
    capacity_tb = models.DecimalField(max_digits=7, decimal_places=3, null=True, blank=True)
    rpm = models.PositiveIntegerField(null=True, blank=True)
    cache_mb = models.PositiveIntegerField(null=True, blank=True)
    recording_tech = models.CharField(
        max_length=20, choices=RecordingTech.choices, null=True, blank=True
    )
    plp = models.BooleanField(null=True, blank=True)  # power-loss protection (SSD)
    market_tier = models.CharField(max_length=50, blank=True, default="")
    model_family = models.CharField(max_length=100, blank=True, default="")
    dwpd = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    workload_tb_year = models.PositiveIntegerField(null=True, blank=True)
    tbw = models.PositiveIntegerField(null=True, blank=True)
    sector_format = models.CharField(max_length=20, blank=True, default="")
    sed = models.BooleanField(null=True, blank=True)  # self-encrypting drive
    spec_json = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "drive_spec"


class ProductAlias(RetentionGoverned):
    """External identifiers as many-to-one alias rows, never canonical columns
    (ADR-0010 rule 3; ADR-0019/DR-010 shape from day one):
    - grain-addressed: exactly one of model / family / variant is set — OEM
      part numbers attach at family/model grain only, the manufacturer catalog
      persists variant-grain MPNs (IR-007);
    - marketplace-local: source_site participates in uniqueness (ASIN/ePID are
      marketplace-scoped); NULL source_site = source-independent identifier;
    - provenance-classed: source_kind — listing_derived rows become revocable
      at MS-1 (revocation + listing_resolution cascade land there).
    Retention columns per DR-009, unconstrained (catalog ingest stamps
    manufacturer_reference at MS-1).
    """

    alias_type = models.CharField(max_length=20, choices=AliasType.choices)
    normalized_alias_text = models.CharField(max_length=200)
    product_model = models.ForeignKey(
        ProductModel, on_delete=models.CASCADE, related_name="aliases", null=True, blank=True
    )
    product_family = models.ForeignKey(
        ProductFamily, on_delete=models.CASCADE, related_name="aliases", null=True, blank=True
    )
    product_variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.CASCADE,
        related_name="aliases",
        null=True,
        blank=True,
    )
    source_site = models.ForeignKey(
        "catalog.SourceSite",
        on_delete=models.SET_NULL,
        related_name="aliases",
        null=True,
        blank=True,
    )
    source_kind = models.CharField(max_length=30, choices=AliasSourceKind.choices)
    is_primary = models.BooleanField(default=False)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "product_alias"
        verbose_name_plural = "product aliases"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        product_model__isnull=False,
                        product_family__isnull=True,
                        product_variant__isnull=True,
                    )
                    | models.Q(
                        product_model__isnull=True,
                        product_family__isnull=False,
                        product_variant__isnull=True,
                    )
                    | models.Q(
                        product_model__isnull=True,
                        product_family__isnull=True,
                        product_variant__isnull=False,
                    )
                ),
                name="product_alias_exactly_one_grain",
            ),
            models.CheckConstraint(
                condition=~models.Q(source_kind=""), name="product_alias_source_kind_set"
            ),
            # ADR-0019/D-019: OEM part numbers attach at family/model grain
            # ONLY — never variant (the OEM↔MPN relationship is too coarse to
            # pick a sellable variant). Structural, not conventional.
            models.CheckConstraint(
                condition=~models.Q(alias_type="oem_pn", product_variant__isnull=False),
                name="product_alias_oem_pn_not_variant_grain",
            ),
            # Identifier-type aliases (GTIN/ASIN/ePID/MPN/... incl. OTHER)
            # resolve to exactly ONE target per marketplace — the same ASIN on
            # the same site must not map to two products. ONLY OEM_PN is
            # exempt: the OEM cross-reference research established OEM PN ↔
            # MPN is genuinely N:N, so OEM_PN rows are unique per (text, site,
            # target) instead — multi-target allowed, exact duplicates not.
            # (OTHER deliberately NOT exempt: ambiguous identifiers go through
            # the MS-1 review queue, not a blanket multi-target escape hatch.)
            models.UniqueConstraint(
                fields=["alias_type", "normalized_alias_text", "source_site"],
                condition=~models.Q(alias_type="oem_pn"),
                name="product_alias_single_target_per_site",
                nulls_distinct=False,
            ),
            models.UniqueConstraint(
                fields=[
                    "alias_type",
                    "normalized_alias_text",
                    "source_site",
                    "product_model",
                    "product_family",
                ],
                condition=models.Q(alias_type="oem_pn"),
                name="product_alias_oem_multi_target_no_dupes",
                nulls_distinct=False,
            ),
        ]


class DriveUnit(models.Model):
    """The physical-unit grain (ADR-0010 rule 5): serial + SMART/FARM evidence.

    v1 populates it only opportunistically from seller-posted SMART data.
    """

    product_model = models.ForeignKey(ProductModel, on_delete=models.PROTECT, related_name="units")
    serial_number = models.CharField(max_length=100)
    smart_json = models.JSONField(null=True, blank=True)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "drive_unit"
        constraints = [
            models.UniqueConstraint(
                fields=["product_model", "serial_number"], name="drive_unit_unique_serial_per_model"
            ),
        ]
```

`src/hw_radar/catalog/models/market.py` — created NOW with only `SourceType`/`SourceSite` (the alias uniqueness key needs it); Task 4 appends `Seller`/`Listing`/`OfferSnapshot`/`StockStatus` to this file:

```python
from django.db import models

from hw_radar.catalog.models.base import TimeStamped


class SourceType(models.TextChoices):
    MANUFACTURER_STORE = "manufacturer_store", "Manufacturer store"
    SPECIALIST_RESELLER = "specialist_reseller", "Storage-specialist reseller"
    MARKETPLACE = "marketplace", "Marketplace"
    RETAILER = "retailer", "Retailer"
    SEARCH_PROVIDER = "search_provider", "Search provider (discovery only)"
    OTHER = "other", "Other"


class SourceSite(TimeStamped):
    """One marketplace/store (Appendix C.1 rows become rows here at MS-1)."""

    name = models.CharField(max_length=100)
    normalized_name = models.CharField(max_length=100, unique=True)
    source_type = models.CharField(max_length=30, choices=SourceType.choices, default=SourceType.OTHER)
    region = models.CharField(max_length=10, blank=True, default="US")
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "source_site"

    def __str__(self) -> str:
        return self.name
```

`src/hw_radar/catalog/models/__init__.py` (Task 4 extends the import list):

```python
from hw_radar.catalog.models.base import (
    BOUNDED_RETENTION_CLASSES,
    INDEFINITE_RETENTION_CLASSES,
    RetentionClass,
    RetentionGoverned,
    TimeStamped,
    retention_constraints,
)
from hw_radar.catalog.models.identity import (
    AliasSourceKind,
    AliasType,
    Category,
    Condition,
    DriveSpec,
    DriveUnit,
    Manufacturer,
    MediaType,
    Packaging,
    ProductAlias,
    ProductFamily,
    ProductModel,
    ProductVariant,
    RecertChannel,
    RecordingTech,
    WarrantyChannel,
)
from hw_radar.catalog.models.market import SourceSite, SourceType

__all__ = [
    "BOUNDED_RETENTION_CLASSES",
    "INDEFINITE_RETENTION_CLASSES",
    "AliasSourceKind",
    "AliasType",
    "Category",
    "Condition",
    "DriveSpec",
    "DriveUnit",
    "Manufacturer",
    "MediaType",
    "Packaging",
    "ProductAlias",
    "ProductFamily",
    "ProductModel",
    "ProductVariant",
    "RecertChannel",
    "RecordingTech",
    "RetentionClass",
    "RetentionGoverned",
    "SourceSite",
    "SourceType",
    "TimeStamped",
    "WarrantyChannel",
    "retention_constraints",
]
```

Note `identity.py` imports: `ProductAlias` references `"catalog.ProductVariant"`/`"catalog.SourceSite"` as **string FKs** (both defined later in the module / in `market.py`), so no import-order issue exists.

`src/hw_radar/catalog/admin.py` (composite-PK `OfferSnapshot` deliberately never registered — Django 6.0 limitation):

```python
from django.contrib import admin

from hw_radar.catalog.models import (
    Category,
    DriveSpec,
    DriveUnit,
    Manufacturer,
    ProductAlias,
    ProductFamily,
    ProductModel,
    ProductVariant,
    SourceSite,
)

admin.site.register(Category)
admin.site.register(Manufacturer)
admin.site.register(ProductFamily)
admin.site.register(ProductModel)
admin.site.register(ProductVariant)
admin.site.register(DriveSpec)
admin.site.register(ProductAlias)
admin.site.register(DriveUnit)
admin.site.register(SourceSite)
```

Add `"hw_radar.catalog",` to `INSTALLED_APPS` in `settings.py`.

- [ ] **Step 4: Generate the migration, then hand-edit in extensions + seed**

```bash
uv run python manage.py makemigrations catalog
```

Edit the generated `src/hw_radar/catalog/migrations/0001_initial.py`: add the extension `RunSQL`s as the **first** operations and the category seed as the **last**:

```python
def _seed_drive_category(apps, schema_editor):
    category = apps.get_model("catalog", "Category")
    category.objects.get_or_create(slug="drive", defaults={"name": "Drive"})


def _unseed_drive_category(apps, schema_editor):
    apps.get_model("catalog", "Category").objects.filter(slug="drive").delete()
```

```python
    operations = [
        # Superuser-created in dev/CI (container role is superuser); pre-created
        # by the provisioning runbook on the CT, where these are no-ops.
        migrations.RunSQL("CREATE EXTENSION IF NOT EXISTS timescaledb;", reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL("CREATE EXTENSION IF NOT EXISTS pg_trgm;", reverse_sql=migrations.RunSQL.noop),
        # ... generated CreateModel/AddConstraint operations stay here unchanged ...
        migrations.RunPython(_seed_drive_category, _unseed_drive_category),
    ]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run coverage run -m pytest tests/db/test_identity.py tests/db/test_migrations.py -v`
Expected: PASS (13 identity tests + no-missing-migrations).

- [ ] **Step 6: Gate and commit**

```bash
uv run ruff format . && uv run ruff check . --fix
uv run python -m scripts.check
git add src/hw_radar tests/db/test_identity.py
git commit -m "feat(catalog): ADR-0010 identity ladder — category through drive_spec, grain-addressed aliases"
```

---

### Task 4: Catalog app — market & evidence tables + the offer_snapshot hypertable

**Files:**
- Create: `src/hw_radar/catalog/models/evidence.py`, `src/hw_radar/catalog/migrations/0002_market_evidence.py` (generated), `src/hw_radar/catalog/migrations/0003_offer_snapshot_hypertable.py` (hand-written)
- Modify: `src/hw_radar/catalog/models/market.py` (append `StockStatus`, `Seller`, `Listing`, `OfferSnapshot`), `src/hw_radar/catalog/models/__init__.py`, `src/hw_radar/catalog/admin.py`
- Test: `tests/db/test_market.py`

**Interfaces:**
- Consumes: Task 3 models/enums; `RetentionGoverned`, `RetentionClass`, `retention_constraints`, `SourceSite`.
- Produces (MS-1 builds on these): `Seller`, `Listing` (unique `(source_site, source_listing_key)`; nullable `product_variant` FK — resolution edges land MS-1), `OfferSnapshot` (**hypertable**, PK `(listing_id, observed_at)`, DR-002 FX stamp columns, generated `total_landed_price`), `RawPayload`, `SearchObservation` (IR-006-minimal — URL + query metadata only), `VerificationEvent`, `StockStatus` enum.

- [ ] **Step 1: Write the failing tests**

`tests/db/test_market.py`:

```python
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, connection

from hw_radar.catalog.models import (
    Listing,
    OfferSnapshot,
    RawPayload,
    RetentionClass,
    SourceSite,
    SourceType,
    StockStatus,
)

# Deterministic timestamps: composite PK is (listing_id, observed_at) — two
# same-instant inserts would collide, so tests never rely on wall-clock spacing.
T0 = datetime(2026, 7, 4, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def spd(db: None) -> SourceSite:
    return SourceSite.objects.create(
        name="ServerPartDeals",
        normalized_name="serverpartdeals",
        source_type=SourceType.SPECIALIST_RESELLER,
    )


@pytest.fixture
def listing(spd: SourceSite) -> Listing:
    return Listing.objects.create(
        source_site=spd,
        source_listing_key="spd-st16-recert",
        canonical_url="https://serverpartdeals.com/products/st16000nm001g",
        url_hash="a" * 64,
        title_raw="Seagate Exos X16 16TB recertified",
        retention_class=RetentionClass.MERCHANT_FACT,
    )


def test_offer_snapshot_is_a_hypertable(db: None) -> None:
    # ADR-0007/0010 confirmation: observation table declared as a hypertable.
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM timescaledb_information.hypertables"
            " WHERE hypertable_name = 'offer_snapshot'"
        )
        assert cursor.fetchone() is not None


def test_snapshots_append_not_duplicate(listing: Listing) -> None:
    # DR-005: re-observation appends observations under the same listing.
    for offset, price in ((0, Decimal("189.99")), (1, Decimal("179.99"))):
        OfferSnapshot.objects.create(
            listing=listing,
            observed_at=T0 + timedelta(hours=offset),
            item_price=price,
            stock_status=StockStatus.IN_STOCK,
            retention_class=RetentionClass.MERCHANT_FACT,
        )
    assert Listing.objects.count() == 1
    assert OfferSnapshot.objects.filter(listing=listing).count() == 2


def test_total_landed_price_is_generated(listing: Listing) -> None:
    snapshot = OfferSnapshot.objects.create(
        listing=listing,
        observed_at=T0,
        item_price=Decimal("100.00"),
        shipping_price=Decimal("12.50"),
        stock_status=StockStatus.IN_STOCK,
        retention_class=RetentionClass.MERCHANT_FACT,
    )
    snapshot.refresh_from_db()
    assert snapshot.total_landed_price == Decimal("112.50")


def test_duplicate_listing_key_rejected(spd: SourceSite, listing: Listing) -> None:
    with pytest.raises(IntegrityError):
        Listing.objects.create(
            source_site=spd,
            source_listing_key="spd-st16-recert",
            canonical_url="https://serverpartdeals.com/products/other",
            url_hash="b" * 64,
            title_raw="dup",
            retention_class=RetentionClass.MERCHANT_FACT,
        )


def test_retention_class_is_mandatory(db: None) -> None:
    # DR-001: '' (Django's CharField default) must be rejected by the check constraint.
    with pytest.raises(IntegrityError):
        RawPayload.objects.create(
            provider="test",
            endpoint="/x",
            fetched_at=T0,
            content_hash="c" * 64,
            http_status=200,
        )


def test_indefinite_class_rejects_expiry(db: None) -> None:
    # DEV-002 TTL coherence: indefinite classes must have expires_at NULL.
    with pytest.raises(IntegrityError):
        RawPayload.objects.create(
            provider="test",
            endpoint="/x",
            fetched_at=T0,
            content_hash="d" * 64,
            http_status=200,
            retention_class=RetentionClass.MERCHANT_FACT,
            expires_at=T0 + timedelta(days=1),
        )


def test_bounded_class_requires_expiry(db: None) -> None:
    # DEV-002 TTL coherence: bounded classes (TTL 0 included) must set expires_at.
    with pytest.raises(IntegrityError):
        RawPayload.objects.create(
            provider="test",
            endpoint="/x",
            fetched_at=T0,
            content_hash="e" * 64,
            http_status=200,
            retention_class=RetentionClass.AMAZON_EPHEMERAL,
        )


def test_search_observation_stores_no_provider_content(db: None) -> None:
    # IR-006 (CR-002): Serper/Brave snippets/titles/provider JSON must never be
    # persistable — the columns themselves must not exist.
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT column_name FROM information_schema.columns"
            " WHERE table_schema = 'public' AND table_name = 'search_observation'"
            " AND column_name IN ('result_title', 'result_snippet', 'provider_payload_json',"
            " 'response_json', 'response_text')"
        )
        assert cursor.fetchall() == []


def test_no_binary_columns_anywhere(db: None) -> None:
    # DR-003: no image bytes anywhere — URLs/hashes only.
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT table_name, column_name FROM information_schema.columns"
            " WHERE table_schema = 'public' AND data_type = 'bytea'"
        )
        assert cursor.fetchall() == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run coverage run -m pytest tests/db/test_market.py -v`
Expected: FAIL — imports (`SourceSite`, …) don't exist.

- [ ] **Step 3: Implement market + evidence models**

Append to `src/hw_radar/catalog/models/market.py` (extend the imports at the top to):

```python
from decimal import Decimal

from django.db import models
from django.db.models.functions import Coalesce

from hw_radar.catalog.models.base import RetentionGoverned, TimeStamped, retention_constraints
from hw_radar.catalog.models.identity import ProductVariant
```

then add below `SourceSite`:

```python
class StockStatus(models.TextChoices):
    IN_STOCK = "in_stock", "In stock"
    OUT_OF_STOCK = "out_of_stock", "Out of stock"
    PREORDER = "preorder", "Pre-order"
    UNKNOWN = "unknown", "Unknown"


class Seller(TimeStamped):
    """Marketplace-scoped merchant identity (reputation observations land MS-2)."""

    source_site = models.ForeignKey(SourceSite, on_delete=models.PROTECT, related_name="sellers")
    name = models.CharField(max_length=200)
    normalized_name = models.CharField(max_length=200)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "seller"
        constraints = [
            models.UniqueConstraint(
                fields=["source_site", "normalized_name"], name="seller_unique_per_site"
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Listing(RetentionGoverned):
    """One merchant offer page (ADR-0010 listing grain).

    product_variant is the grain-elastic resolution target — NULL until the
    MS-1 matcher attaches it (ADR-0019 adds listing_resolution edges + the
    denormalized most-specific-wins FKs; do not pre-build those here).
    listing_fingerprint derivation (repost dedup) is an MS-1/MS-4 concern —
    the column exists, blank until then.
    """

    source_site = models.ForeignKey(SourceSite, on_delete=models.PROTECT, related_name="listings")
    seller = models.ForeignKey(
        Seller, on_delete=models.SET_NULL, related_name="listings", null=True, blank=True
    )
    product_variant = models.ForeignKey(
        ProductVariant, on_delete=models.SET_NULL, related_name="listings", null=True, blank=True
    )
    source_listing_key = models.CharField(max_length=255)
    canonical_url = models.URLField(max_length=1000)
    url_hash = models.CharField(max_length=64)
    title_raw = models.TextField()
    title_normalized = models.TextField(blank=True, default="")
    condition_label_raw = models.CharField(max_length=255, blank=True, default="")
    listing_fingerprint = models.CharField(max_length=64, blank=True, default="")
    page_metadata_json = models.JSONField(default=dict, blank=True)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "listing"
        constraints = [
            *retention_constraints("listing"),
            models.UniqueConstraint(
                fields=["source_site", "source_listing_key"], name="listing_unique_per_site_key"
            ),
        ]


class OfferSnapshot(RetentionGoverned):
    """Time-series observation (the TimescaleDB hypertable, ADR-0007/0010).

    PK is (listing_id, observed_at): TimescaleDB requires the partition column
    in every unique constraint, so a lone surrogate id is invalid here.
    Consequences (Django 6.0 documented limits): never register in admin;
    relational fields cannot target this model — MS-2's listing_score references
    (listing FK, observed_at) instead of a snapshot FK.
    FX stamp columns (DR-002/ADR-0008) exist from day one; the FX pipeline
    that fills them lands MS-1. total_landed_price is row-local economics →
    stored generated column (ADR-0007); $/TB is cross-table → MS-2 views.
    """

    pk = models.CompositePrimaryKey("listing_id", "observed_at")
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="snapshots")
    observed_at = models.DateTimeField()
    currency = models.CharField(max_length=3, default="USD")
    item_price = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tax_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_landed_price = models.GeneratedField(
        expression=models.F("item_price")
        + Coalesce(models.F("shipping_price"), models.Value(Decimal("0")))
        + Coalesce(models.F("tax_price"), models.Value(Decimal("0"))),
        output_field=models.DecimalField(max_digits=12, decimal_places=2),
        db_persist=True,
    )
    stock_status = models.CharField(
        max_length=20, choices=StockStatus.choices, default=StockStatus.UNKNOWN
    )
    quantity_available = models.PositiveIntegerField(null=True, blank=True)
    fx_rate = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    fx_pair = models.CharField(max_length=7, blank=True, default="")
    fx_rate_date = models.DateField(null=True, blank=True)
    fx_source = models.CharField(max_length=50, blank=True, default="")
    extraction_method = models.CharField(max_length=50, blank=True, default="")
    confidence_score = models.FloatField(null=True, blank=True)
    attrs_json = models.JSONField(default=dict, blank=True)
    raw_payload = models.ForeignKey(
        "catalog.RawPayload", on_delete=models.SET_NULL, related_name="snapshots", null=True, blank=True
    )

    class Meta:
        db_table = "offer_snapshot"
        constraints = [*retention_constraints("offer_snapshot")]
```

`src/hw_radar/catalog/models/evidence.py`:

```python
from django.db import models

from hw_radar.catalog.models.base import RetentionGoverned, retention_constraints
from hw_radar.catalog.models.identity import DriveUnit


class RawPayload(RetentionGoverned):
    """Cold raw evidence: provider responses kept re-parseable (ADR-0010 rule 6).

    Retention differs per source — that's what retention_class rows encode.
    Serper/Brave provider responses NEVER land here (IR-006 forbids persisting
    them); Tavily-extracted content may (retention_class=tavily_extract).
    """

    provider = models.CharField(max_length=50)
    endpoint = models.CharField(max_length=255)
    fetched_at = models.DateTimeField()
    request_json = models.JSONField(null=True, blank=True)
    response_json = models.JSONField(null=True, blank=True)
    response_text = models.TextField(null=True, blank=True)
    content_hash = models.CharField(max_length=64)
    http_status = models.PositiveSmallIntegerField()
    parse_version = models.CharField(max_length=20, blank=True, default="")

    class Meta:
        db_table = "raw_payload"
        indexes = [models.Index(fields=["content_hash"], name="raw_payload_content_hash")]
        constraints = [*retention_constraints("raw_payload")]


class SearchObservation(RetentionGoverned):
    """Discovery-only search evidence, IR-006-MINIMAL by design (CR-002).

    Serper/Brave terms forbid persisting snippets/titles/provider JSON — the
    spec says "persist only the discovered URL". So this table has NO
    result_title / result_snippet / provider_payload column, and none may be
    added (guarded by test_search_observation_stores_no_provider_content).
    query_* fields are OUR request, not provider content. Provider result IDs
    are transient, never keys (DR-003). Rows are transient_discovery (TTL 0 —
    expires_at = observed_at) except Tavily, whose extracted FACTS flow through
    raw_payload/listing rows, not here.
    """

    provider = models.CharField(max_length=50)
    query_text = models.TextField()
    query_params_json = models.JSONField(default=dict, blank=True)
    observed_at = models.DateTimeField()
    result_rank = models.PositiveIntegerField(null=True, blank=True)
    result_url = models.URLField(max_length=1000)
    matched_listing = models.ForeignKey(
        "catalog.Listing", on_delete=models.SET_NULL, related_name="search_observations",
        null=True, blank=True,
    )

    class Meta:
        db_table = "search_observation"
        constraints = [*retention_constraints("search_observation")]


class VerificationEvent(RetentionGoverned):
    """Warranty-lookup result cache for a physical unit (ADR-0010 rule 5)."""

    drive_unit = models.ForeignKey(DriveUnit, on_delete=models.CASCADE, related_name="verifications")
    provider = models.CharField(max_length=50)
    checked_at = models.DateTimeField()
    result_json = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "verification_event"
        constraints = [*retention_constraints("verification_event")]
```

Extend `models/__init__.py` imports/`__all__` with: `Listing`, `OfferSnapshot`, `RawPayload`, `SearchObservation`, `Seller`, `StockStatus`, `VerificationEvent`.

Extend `admin.py`: register `Seller`, `Listing` (NOT `OfferSnapshot` — composite PK; `SourceSite` was registered in Task 3).

- [ ] **Step 4: Generate migration + hand-write the hypertable migration**

```bash
uv run python manage.py makemigrations catalog -n market_evidence
```

Create `src/hw_radar/catalog/migrations/0003_offer_snapshot_hypertable.py`:

```python
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("catalog", "0002_market_evidence")]

    operations = [
        # by_range(): the modern dimension API (two-arg create_hypertable is
        # deprecated since TimescaleDB 2.13). Table is empty at this point.
        migrations.RunSQL(
            "SELECT create_hypertable('offer_snapshot', by_range('observed_at'));",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run coverage run -m pytest tests/db/test_market.py tests/db/test_migrations.py -v`
Expected: PASS (9 market tests + no-missing-migrations).

If `basedpyright` flags `pk = models.CompositePrimaryKey(...)` or `GeneratedField` (django-types may lag Django 6 features), use a targeted `# pyright: ignore[<exact-rule>]` with a `django-types gap` reason comment — never a blanket ignore.

- [ ] **Step 6: Gate and commit**

```bash
uv run ruff format . && uv run ruff check . --fix
uv run python -m scripts.check
git add src/hw_radar tests/db/test_market.py
git commit -m "feat(catalog): market/evidence tables with offer_snapshot TimescaleDB hypertable"
```

---

### Task 5: Poller stub (APScheduler under the ADR-0012 contract)

**Files:**
- Create: `src/hw_radar/poller/__init__.py`, `src/hw_radar/poller/__main__.py`
- Test: `tests/unit/test_poller.py`

**Interfaces:**
- Produces: `python -m hw_radar.poller` — long-running heartbeat-only AsyncIOScheduler (the systemd poller unit's ExecStart); `build_scheduler()` and `heartbeat()` for tests. MS-1 replaces the heartbeat with real per-source jobs.

- [ ] **Step 1: Add the dependency**

```bash
uv add "apscheduler>=3.11,<4"
# CR-005 license gate (APScheduler is MIT — must stay inside the allowlist):
uvx licensecheck --zero --only-licenses MIT BSD APACHE LGPL PYTHON ISC MPL UNLICENSE
```

(4.x is explicitly not production-ready as of mid-2026 — the spec §8.6 prohibition stands.)

- [ ] **Step 2: Write the failing tests**

`tests/unit/test_poller.py`:

```python
import logging

import pytest

from hw_radar.poller import HEARTBEAT_SECONDS, build_scheduler, heartbeat


def test_heartbeat_logs(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="hw_radar.poller"):
        heartbeat()
    assert "heartbeat" in caplog.text


def test_scheduler_registers_heartbeat_job() -> None:
    scheduler = build_scheduler()
    job = scheduler.get_job("poller-heartbeat")
    assert job is not None
    assert job.trigger.interval.total_seconds() == HEARTBEAT_SECONDS


def test_scheduler_job_defaults_follow_adr_0012() -> None:
    scheduler = build_scheduler()
    assert scheduler._job_defaults["max_instances"] == 1
    assert scheduler._job_defaults["coalesce"] is True
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run coverage run -m pytest tests/unit/test_poller.py -v`
Expected: FAIL — module doesn't exist.

- [ ] **Step 4: Implement the poller stub**

`src/hw_radar/poller/__init__.py`:

```python
# pyright: reportMissingTypeStubs=false
# APScheduler 3.x ships no py.typed/stubs; scoped to this module (AGENTS.md rule).
"""MS-0 poller stub: proves the systemd-supervised single-process scheduler
contract (ADR-0012) with a heartbeat-only job. MS-1 replaces the heartbeat
with per-source acquisition jobs plus the shared admission/breaker state that
is the reason this is ONE process, not systemd timers.
"""

import asyncio
import logging
import signal

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)

HEARTBEAT_SECONDS = 60


def heartbeat() -> None:
    logger.info("poller heartbeat: alive, no jobs scheduled (MS-0 stub)")


def build_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(job_defaults={"max_instances": 1, "coalesce": True})
    scheduler.add_job(heartbeat, "interval", seconds=HEARTBEAT_SECONDS, id="poller-heartbeat")
    return scheduler


async def run() -> None:
    scheduler = build_scheduler()
    scheduler.start()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    logger.info("poller started (heartbeat every %ss)", HEARTBEAT_SECONDS)
    await stop.wait()
    scheduler.shutdown(wait=False)
    logger.info("poller stopped")
```

`src/hw_radar/poller/__main__.py`:

```python
import asyncio
import logging

from hw_radar.poller import run

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    asyncio.run(run())
```

If `basedpyright` still reports unknown types on `scheduler.get_job`/`add_job` call sites in tests, add the same scoped `# pyright:` comment to the test file with the reason.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run coverage run -m pytest tests/unit/test_poller.py -v`
Expected: PASS (3 tests). (`run()`'s signal loop is exercised at acceptance, not unit-tested; if coverage dips below 85%, add an asyncio test that starts `run()` as a task, sends `stop` via `asyncio.Event`, and asserts clean shutdown.)

- [ ] **Step 6: Gate and commit**

```bash
uv run ruff format . && uv run ruff check . --fix
uv run python -m scripts.check
git add pyproject.toml uv.lock src/hw_radar/poller tests/unit/test_poller.py
git commit -m "feat(poller): APScheduler 3.11 heartbeat stub under the ADR-0012 supervision contract"
```

---

### Task 6: Deployment artifacts — systemd units, nginx, CD workflow, remote script

**Files:**
- Create: `deploy/systemd/hw-radar-web.service`, `deploy/systemd/hw-radar-poller.service`, `deploy/nginx/hw-radar.conf`, `deploy/deploy-remote.sh`, `.github/workflows/deploy.yml`, `docs/runbooks/deploy-and-rollback.md`

**Interfaces:**
- Consumes: `hw_radar.wsgi:application` (Task 1), `python -m hw_radar.poller` (Task 5), `/healthz` (Task 2), reusable `check.yml` (Task 1).
- Produces: everything Task 8's operator phase installs/executes. GitHub Environment secrets contract: `TS_OAUTH_CLIENT_ID`, `TS_OAUTH_SECRET`, `DEPLOY_HOST` (tailnet name — never committed), `DEPLOY_USER`.

No unit tests — these are config artifacts; verification is YAML/syntax checks here and the live acceptance in Task 8.

- [ ] **Step 1: systemd units**

`deploy/systemd/hw-radar-web.service`:

```ini
# Installed to /etc/systemd/system/ by the provisioning runbook.
# ADR-0006: plain gunicorn — never Type=notify (it doesn't call sd_notify()).
# ADR-0009: secrets arrive ONLY via the bao-agent tmpfs render.
[Unit]
Description=hw-radar web (gunicorn)
After=network-online.target bao-agent.service postgresql.service
Wants=network-online.target
Requires=bao-agent.service

[Service]
Type=exec
User=hwradar
Group=hwradar
WorkingDirectory=/opt/hw-radar/app
Environment=HW_RADAR_ENV=production
EnvironmentFile=/run/bao-agent/hw-radar.env
ExecStart=/opt/hw-radar/app/.venv/bin/gunicorn hw_radar.wsgi:application --bind 127.0.0.1:8000 --workers 2 --timeout 60
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

`deploy/systemd/hw-radar-poller.service`:

```ini
[Unit]
Description=hw-radar poller (APScheduler, ADR-0012)
After=network-online.target bao-agent.service postgresql.service
Wants=network-online.target
Requires=bao-agent.service

[Service]
Type=exec
User=hwradar
Group=hwradar
WorkingDirectory=/opt/hw-radar/app
Environment=HW_RADAR_ENV=production
EnvironmentFile=/run/bao-agent/hw-radar.env
ExecStart=/opt/hw-radar/app/.venv/bin/python -m hw_radar.poller
Restart=on-failure
RestartSec=10
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
# Spec §18.1 names resource limits for the poller: on a 4 GiB CT sharing
# in-CT PostgreSQL, a runaway poller must not starve the DB. Revisit at MS-5
# (browser tiers change the memory profile).
MemoryHigh=512M
MemoryMax=1G
TasksMax=200

[Install]
WantedBy=multi-user.target
```

(The web unit carries no explicit memory clamp at MS-0 — gunicorn with 2 sync workers is bounded and CT-level limits back-stop it; the spec names resource limits only for the poller/worker units.)

- [ ] **Step 2: nginx config**

`deploy/nginx/hw-radar.conf`:

```nginx
# Installed to /etc/nginx/sites-available/ at provisioning; certificates via
# certbot --nginx (Let's Encrypt). App binds 127.0.0.1 only (ADR-0005 posture).
server {
    listen 80;
    listen [::]:80;
    server_name hw-radar.l3digital.net;
    location /.well-known/acme-challenge/ { root /var/www/letsencrypt; }
    location / { return 301 https://$host$request_uri; }
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    http2 on;
    server_name hw-radar.l3digital.net;

    ssl_certificate     /etc/letsencrypt/live/hw-radar.l3digital.net/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/hw-radar.l3digital.net/privkey.pem;

    location /static/ {
        alias /opt/hw-radar/app/staticfiles/;
        access_log off;
        expires 7d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

- [ ] **Step 3: remote deploy script**

`deploy/deploy-remote.sh`:

```bash
#!/usr/bin/env bash
# Runs ON the CT, invoked by deploy.yml over Tailscale SSH after rsync.
# Contract (ADR-0006): venv built on-CT (uv sync --frozen), migrations run
# BEFORE restart (expand/contract), restart via a sudoers-allowlisted command.
# The deploy user must be in the hwradar group to read the bao-agent render.
set -euo pipefail

cd /opt/hw-radar/app

export PATH="$HOME/.local/bin:$PATH"

export HW_RADAR_ENV=production
set -a
# shellcheck disable=SC1091  # rendered at runtime by bao-agent (ADR-0009)
source /run/bao-agent/hw-radar.env
set +a

uv python install          # no-op once the pinned 3.14 is present
uv sync --frozen --no-dev

# CR-NEW-001: plain `uv run` re-syncs and would pull the dev group back into
# the production venv — invoke the synced venv's interpreter directly instead.
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py collectstatic --noinput
sudo -n /usr/bin/systemctl restart hw-radar-web.service hw-radar-poller.service
```

Make it executable: `chmod +x deploy/deploy-remote.sh`.

- [ ] **Step 4: the deploy workflow**

`.github/workflows/deploy.yml`:

```yaml
name: Deploy

# ADR-0006 trigger discipline: push/workflow_dispatch to main ONLY — never
# pull_request*. The deploy job sits behind the 'production' GitHub Environment
# (required reviewer), which also scopes the secrets away from PR-triggered runs.
# Rollback = Run workflow with ref set to the previous release SHA.
on:
  push:
    branches: ["main"]
  workflow_dispatch:
    inputs:
      ref:
        description: "Commit SHA to deploy (previous release SHA = rollback)"
        required: false
        type: string

permissions:
  contents: read

concurrency:
  group: deploy-production
  cancel-in-progress: false

jobs:
  check:
    # CR-003: pass the EXACT ref being deployed — a same-repo reusable workflow
    # otherwise runs on the caller's event ref, so a rollback dispatch would
    # gate main HEAD while shipping an older SHA.
    uses: ./.github/workflows/check.yml
    with:
      ref: ${{ inputs.ref || github.sha }}

  deploy:
    needs: check
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v7
        with:
          ref: ${{ inputs.ref || github.sha }}

      - name: Record release SHA
        run: echo "${{ inputs.ref || github.sha }}" > RELEASE

      - name: Join tailnet (ephemeral tag:ci node)
        uses: tailscale/github-action@v4
        with:
          oauth-client-id: ${{ secrets.TS_OAUTH_CLIENT_ID }}
          oauth-secret: ${{ secrets.TS_OAUTH_SECRET }}
          tags: tag:ci

      - name: Wait for CT reachability
        # No count flag: `tailscale ping` retries until direct contact (default
        # cap 10) — flag spelling for the count option varies across CLI docs.
        run: tailscale ping "${{ secrets.DEPLOY_HOST }}"

      - name: Rsync source to CT
        run: |
          rsync -az --delete \
            --exclude ".git" --exclude ".venv" --exclude "staticfiles" \
            -e "ssh -o StrictHostKeyChecking=accept-new" \
            ./ "${{ secrets.DEPLOY_USER }}@${{ secrets.DEPLOY_HOST }}:/opt/hw-radar/app/"

      - name: Migrate and restart (venv built on-CT)
        run: |
          ssh -o StrictHostKeyChecking=accept-new \
            "${{ secrets.DEPLOY_USER }}@${{ secrets.DEPLOY_HOST }}" \
            "bash /opt/hw-radar/app/deploy/deploy-remote.sh"

      - name: Smoke test
        run: |
          ssh -o StrictHostKeyChecking=accept-new \
            "${{ secrets.DEPLOY_USER }}@${{ secrets.DEPLOY_HOST }}" \
            "curl -fsS http://127.0.0.1:8000/healthz"
```

- [ ] **Step 5: runbook**

`docs/runbooks/deploy-and-rollback.md`:

```markdown
# Runbook: deploy & rollback

## Deploy (normal path)
1. Commit to `dev`; CI (`check`) runs on push.
2. Open/merge the `dev → main` PR (merge commit). CI `check` + `dependency-review` must be green.
3. The merge triggers `deploy.yml`: gate re-runs, then the deploy job waits for
   the **production Environment reviewer approval** (ADR-0006 control — an
   authorization gate, not a deploy step; the deploy itself is zero-manual).
4. Approve → ephemeral tailnet join → rsync → on-CT `uv sync --frozen --no-dev`
   → `migrate` (expand/contract, before restart) → `collectstatic` → restart →
   healthz smoke test.

## Rollback
1. Find the previous release SHA: `git log --first-parent main` (or the last
   green Deploy run in Actions).
2. Actions → Deploy → **Run workflow** → `ref` = that SHA → approve the
   environment gate.
3. Old code redeploys against the newer schema — safe because migrations are
   expand/contract (spec §18.3). Verify: `/healthz` reports the rolled-back
   `release` SHA.

## Failure modes
- Smoke test fails → the workflow fails loudly; the previous code is already
  replaced on disk, so immediately rollback via the same workflow_dispatch path.
- `bao-agent` render missing (`/run/bao-agent/hw-radar.env` absent) → units
  fail dependencies; check `systemctl status bao-agent` (runbook in the private
  homelab repo; ADR-0009).
```

- [ ] **Step 6: Validate and commit**

```bash
uv run --with pyyaml python -c "import pathlib, yaml; [yaml.safe_load(pathlib.Path(p).read_text()) for p in ('.github/workflows/deploy.yml', '.github/workflows/check.yml', 'compose.yaml')]"
bash -n deploy/deploy-remote.sh
shellcheck -S warning deploy/deploy-remote.sh
systemd-analyze verify deploy/systemd/hw-radar-web.service deploy/systemd/hw-radar-poller.service || true
uv run python -m scripts.check
git add deploy .github/workflows/deploy.yml docs/runbooks/deploy-and-rollback.md
git commit -m "feat(deploy): CD workflow, systemd units, nginx config, on-CT deploy script (ADR-0006/0009)"
```

(`uv run --with pyyaml` keeps pyyaml out of the project deps — one-shot parse check. `systemd-analyze verify` is best-effort locally — it errors on paths that only exist on the CT (`/opt/hw-radar/...`), so read its output for *syntax* problems and ignore missing-path errors; the authoritative run happens on the CT at provisioning (runbook step 6), alongside `nginx -t` (step 7) — CR-006.)

---

### Task 7: Docs, traceability, deviations, closeout

**Files:**
- Create: `docs/runbooks/provisioning.md`
- Modify: `docs/specs/hw-radar-master-spec.md` (§17.3 matrix + Deviations Log), `README.md` (Development quickstart), `docs/handoff.md` + `TODO.md` (local session-state ritual)

- [ ] **Step 1: provisioning runbook (public-safe operator checklist)**

`docs/runbooks/provisioning.md` — write exactly this content (live values stay in the private homelab repo):

```markdown
# Runbook: CT provisioning for MS-0 (operator, one-time)

Live values (CT ID, addresses, CIDR, issuer script paths) live in the private
`homelab` repo. This checklist is the public-safe contract. Executing it
triggers the infra pre-flight + backup wiring recorded in TODO §User.

1. **CT:** Debian 13 LXC per spec §18.1 — 2 vCPU · 4 GiB · 32 GiB rootfs ·
   512 MiB swap. Appears in `pct list` → auto-monitored (ADR-0003).
2. **Packages:** nginx, certbot + python3-certbot-nginx, PostgreSQL from PGDG,
   **TimescaleDB Community (TSL) from Timescale's packagecloud repo — NOT
   Debian's `postgresql-*-timescaledb` (Apache-2 build: no compression/
   retention/continuous aggregates)**; run `timescaledb-tune`. Tailscale with
   Tailscale SSH enabled. uv (per-user, deploy + hwradar users).
3. **Users:** `hwradar` (app, no shell needed) and `deploy` (CI target),
   `deploy` in group `hwradar` (reads the bao-agent render). App dir
   `/opt/hw-radar/app` owned deploy:hwradar. Sudoers (exact single line):
   `deploy ALL=(root) NOPASSWD: /usr/bin/systemctl restart hw-radar-web.service hw-radar-poller.service`
4. **Database bootstrap (as postgres superuser):**
   `CREATE ROLE hw_radar LOGIN PASSWORD '<from OpenBao>';`
   `CREATE DATABASE hw_radar OWNER hw_radar;` then in that DB:
   `CREATE EXTENSION IF NOT EXISTS timescaledb; CREATE EXTENSION IF NOT EXISTS pg_trgm;`
   (app role is non-superuser; migrations' IF NOT EXISTS then no-op).
5. **bao-agent (ADR-0009):** onboard as the next bao-services consumer per the
   homelab runbook — AppRole + CIDR-bound persistent SecretID via the issuer
   script; agent template renders `DJANGO_SECRET_KEY`,
   `HW_RADAR_DB_PASSWORD` (+ `HW_RADAR_DB_USER/NAME` if not defaults) to
   `/run/bao-agent/hw-radar.env` (root:hwradar 0640). Verify render survives
   `systemctl restart bao-agent`.
6. **systemd:** copy `deploy/systemd/*.service` to `/etc/systemd/system/`,
   run `systemd-analyze verify /etc/systemd/system/hw-radar-*.service` (must be
   clean on the CT — paths exist there), then
   `systemctl daemon-reload && systemctl enable hw-radar-web hw-radar-poller`.
7. **nginx + TLS:** install `deploy/nginx/hw-radar.conf`, run `nginx -t` (must
   pass before reload), DNS A/AAAA for `hw-radar.l3digital.net` → Hetzner IP,
   `certbot --nginx`.
8. **GitHub:** create Environment `production` with a required reviewer;
   Environment secrets: `TS_OAUTH_CLIENT_ID`/`TS_OAUTH_SECRET` (OpenBao
   `secret/infra/tailscale-oauth`), `DEPLOY_HOST` (tailnet name), `DEPLOY_USER`.
9. **Tailnet ACL:** ensure `tag:ci` can reach the CT over SSH (wildcard today;
   add the explicit `tag:ci → CT:22` + SSH-section grant when the scoped-ACL
   migration lands — ADR-0006 forward dependency).
10. **Owner account:** first deploy runs migrations, then
    `uv run python manage.py createsuperuser` on the CT (password ≥16 chars).
11. **Backups (OQ3 residual — before first real data):** wire the CT subvol
    into `backup-restic.sh`, a TimescaleDB-aware dump block into
    `backup-dumps.sh`, extended monthly retention, disk-threshold alert,
    restore-test discipline (TODO §User items a–e).
12. **Consumer AppRole CIDR bind** must include the CT address (ADR-0009
    follow-up); verify OpenBao reachability from the CT.
```

- [ ] **Step 2: spec traceability + deviations**

In `docs/specs/hw-radar-master-spec.md` §17.3, replace the empty matrix row with (keep the table header):

```markdown
| NFR-005 | `uv run python -m scripts.check` green locally; CI `check.yml` (PR + dev/main push) | Verified (MS-0) |
| NFR-003 (partial) | MS-0 acceptance: ≥1 secret read from OpenBao render; no plaintext `.env` on CT; `bao-agent` survives restart | Pending provisioning |
| FR-003 (schema shape) | `tests/db/test_identity.py::test_recert_and_new_are_one_model_two_variants` | Verified (resolver lands MS-1) |
| DR-001 (as amended by DEV-002) | Schema-shape constraints only: `tests/db/test_market.py::test_retention_class_is_mandatory` + `test_indefinite_class_rejects_expiry` + `test_bounded_class_requires_expiry`. **Per-class TTL values (eBay 6 h, Amazon 24 h, TTL 0) are stamped by the ingest pipeline and the expiry sweep enforces them — both land MS-1; DR-001 is NOT fully verified at MS-0.** | Partially verified (schema constraints); TTL enforcement pending MS-1 |
| DR-003 | `tests/db/test_market.py::test_no_binary_columns_anywhere` | Verified |
| DR-009 (schema prep) | `tests/db/test_identity.py::test_reference_tables_carry_retention_columns`; catalog ingest stamps `manufacturer_reference` at MS-1 | Verified (columns) |
| DR-010 (alias shape) | `tests/db/test_identity.py::test_alias_supports_variant_grain` + `test_alias_is_marketplace_local`; `listing_resolution`/revocation at MS-1 | Verified (schema) |
| IR-006 (persistence boundary) | `tests/db/test_market.py::test_search_observation_stores_no_provider_content` | Verified (schema guard) |
| DR-005 (schema shape) | `tests/db/test_market.py::test_snapshots_append_not_duplicate` | Verified (pipeline MS-1) |
| IR-001 (partial) | Authenticated pages over HTTPS-only via NGINX+LE | Pending provisioning |
| IR-005 | systemd `EnvironmentFile=/run/bao-agent/hw-radar.env` + `After=bao-agent` in `deploy/systemd/*`; live check at acceptance | Pending provisioning |
| ADR-0010 confirmation | `catalog` migrations 0001–0003 + `tests/db/test_identity.py`, `tests/db/test_market.py::test_offer_snapshot_is_a_hypertable` | Verified |
| §17.2 Database layer | `tests/db/test_migrations.py::test_no_missing_migrations` + pytest-django creating the test DB from empty on every run | Verified |
```

Append to the spec's **Deviations Log** (match its existing column format when editing):

```markdown
| DEV-001 | §8.6 | Dev-group deps `pytest-django`, `django-types` added (not in the §8.6 table) | Required to test (D-004 stack under D-002 gate) and to type-check Django without the mypy plugin; approved via the MS-0 plan (2026-07-04) | Accepted |
| DEV-002 | DR-001 | `expires_at` is nullable: NULL = indefinite, with per-class check constraints (indefinite classes require NULL, bounded classes require NOT NULL) | DR-001's literal "non-null `expires_at`" is unsatisfiable for indefinite classes (merchant_fact, amazon_identifier, tavily_extract, manufacturer_reference); the class-tied constraint is strictly stronger than an unconditional NOT NULL of arbitrary sentinel dates | Accepted |
```

- [ ] **Step 3: README Development quickstart**

Add under README's Development section (adjust to existing prose):

```markdown
### Local development

    podman compose up -d db        # TimescaleDB dev database (docker works too)
    uv sync --all-groups
    uv run python manage.py migrate
    uv run python manage.py createsuperuser
    uv run python manage.py runserver

The verification gate (`uv run python -m scripts.check`) needs the dev DB running.
```

- [ ] **Step 4: gate, commit, session closeout**

```bash
uv run python -m scripts.check
git add docs/runbooks docs/specs/hw-radar-master-spec.md README.md
git commit -m "docs(ms0): provisioning runbook, §17.3 traceability, DEV-001, dev quickstart"
```

Then update the **local, never-committed** `docs/handoff.md` (MS-0 code complete; acceptance pending provisioning) and `TODO.md` (tick completed items; the provisioning User item now gates MS-0 acceptance). Appendix B.4 session-handoff ritual.

---

### Task 8: OPERATOR-GATED — provisioning, first deploy, MS-0 acceptance

**Blocked on:** the owner's "provision the server" TODO item. Execution follows `docs/runbooks/provisioning.md` (Task 7) + the private homelab repo, and triggers the global infra pre-flight (homelab pull → live-state verify → CT-ID assignment) per TODO §User. Agent involvement happens in a session with homelab access — steps 1–12 of the runbook, then:

- [ ] **Step 1: First deploy** — open the `dev → main` PR ("MS-0 Foundation"), merge on green CI, approve the `production` environment gate, watch `deploy.yml` complete.

- [ ] **Step 2: MS-0 acceptance checklist** (spec §19; check each, record evidence in `docs/handoff.md`):

```text
[ ] Merge to main deployed with zero manual steps (environment approval is an
    authorization control per ADR-0006, not a deploy step)
[ ] https://hw-radar.l3digital.net serves the login page over HTTPS only;
    authenticated hello dashboard renders after owner login
[ ] The web service reads ≥1 secret sourced from OpenBao: DJANGO_SECRET_KEY
    arrives only via /run/bao-agent/hw-radar.env; verify no plaintext .env:
    `find /opt/hw-radar -maxdepth 2 -name ".env"` → empty
[ ] `uv sync --frozen --no-dev` on the CT reproduces the locked prod env (exit 0,
    no resolver output) AND dev-only tooling is absent from the venv:
    `.venv/bin/python -c "import pytest"` must FAIL (CR-NEW-001)
[ ] Migrations applied cleanly from empty (first deploy log) — also proven
    continuously by pytest-django test-DB creation
[ ] Rollback demonstrated: workflow_dispatch with the previous SHA →
    /healthz "release" shows that SHA; then roll forward again
[ ] bao-agent unit Active; survives `systemctl restart bao-agent` AND a full
    CT restart without re-issuing the SecretID (NFR-003)
[ ] hw-radar-poller unit Active; journal shows heartbeat lines
[ ] pct list shows the CT (auto-monitoring); backup allowlists wired (a–e)
```

- [ ] **Step 3: Completion report (Appendix B.3)** — summary of changes, the completed §17.3 rows flipped from "Pending provisioning" to "Verified", tests added, DEV-001 status, known limitations (poller is a stub; FX columns unfilled until MS-1), documentation deliverables (§18.7: deploy/rollback + provisioning runbooks done; incident/backup-restore/secret-rotation runbooks due by MS-5).

---

## Codex review rounds 1–2 — applied (2026-07-04)

Round 1 (all four blocking verified against the spec and applied): **CR-001** → retention columns on `product_model`/`drive_spec`/`product_alias` + class↔TTL coherence constraints + DEV-002; **CR-002** → `search_observation` stripped to the IR-006 minimum + schema guard test; **CR-003** → `check.yml` `ref` input, `deploy.yml` passes the deployed ref to the gate; **CR-004** → `product_alias` gains variant grain, `source_kind`, marketplace-local uniqueness (`SourceSite` moved to Task 3). **CR-005** → licensecheck after every `uv add`; **CR-006** → poller resource limits + `systemd-analyze verify`/`nginx -t`.

Round 2 residuals applied: **CR-001** → DR-001 traceability downgraded to "partially verified — TTL values/sweep land MS-1" (no overclaim); **CR-004** → identifier aliases single-target per `(alias_type, text, source_site)` with per-target dupe protection; **CR-005** → explicit allowlist commands incl. `-g dev`; **CR-NEW-001** → `deploy-remote.sh` invokes `.venv/bin/python` directly after the `--no-dev` sync (plain `uv run` would re-sync the dev group into prod) + acceptance check that pytest is absent from the prod venv; `tailscale ping` count flag dropped (spelling drift across CLI docs).

Round 3 residuals applied: **CR-004** → `OEM_PN` structurally barred from variant grain (check constraint + regression test); `OTHER` removed from the N:N exemption (ambiguity routes through the MS-1 review queue instead — only `OEM_PN` has the research-backed N:N justification); **CR-005** → `--only-licenses` corrected to space-separated values per the documented `ONLY_LICENSES [ONLY_LICENSES ...]` form. Audits: `docs/codex-reviews/2026-07-04-213339-…round1.md`, `…-215010-…round2.md`, `…-215925-…round3.md`.

## Self-Review (performed at authoring)

- **Spec coverage:** MS-0 task list — Django scaffold (T1), ADR-0010 schema as initial migrations (T3/T4), users stub + Argon2id login (T1/T2), CD (T6/T8), systemd web+poller+bao-agent contract (T6/T8). All five MS-0 acceptance criteria appear in T8's checklist. §13.6 CSRF/CORS confirm-at-MS-0 → settings comment + CSRF_TRUSTED_ORIGINS (T1).
- **Known intentional exclusions:** heartbeat tables/scoring/alerting/scraper-ops tables (later milestones per ADR-0010 "deferred detail"); `listing_resolution`/`source_kind` (MS-1, ADR-0019); HTMX (first interactive page is MS-3); vcrpy/syrupy/Pydantic (first scraper is MS-1).
- **Type consistency check:** `RetentionClass`/`RetentionGoverned` names match across base/market/evidence; `Listing.snapshots` ↔ `OfferSnapshot.listing` related_names consistent; `build_scheduler`/`heartbeat`/`HEARTBEAT_SECONDS` consistent between T5 code and tests; `db_table` names match spec vocabulary throughout.
- **Placeholder scan:** clean — every code step contains complete code; the two flagged uncertainties (django-types coverage of `CompositePrimaryKey`/`GeneratedField`; TimescaleDB image patch tag) have concrete fallback instructions inline.
