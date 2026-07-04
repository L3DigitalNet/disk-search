---
schema_version: '1.1'
id: 'adr-0004-hw-radar-web-framework-django-htmx'
title: 'ADR 0004: Web framework — Django + server-rendered templates + HTMX'
description: 'Build Hardware Radar on Django with server-rendered templates and HTMX rather than FastAPI or an SPA, because the app is an authenticated listings database with dashboards, CRUD, alerts, and internal operations — not an API platform.'
doc_type: 'adr'
status: 'active'
created: '2026-07-03'
updated: '2026-07-03'
reviewed: null
owner: ''
consumer: 'mix'
tags:
  - 'adr'
  - 'framework'
  - 'django'
  - 'htmx'
  - 'web'
aliases: []
related:
  - 'docs/adr/README.md'
  - 'docs/specs/hw-radar-master-spec.md'
  - 'docs/resolved-questions.md'
  - 'docs/research/opinionated-core-stack-recommendations-for-a-python-drive-price-monitor.md'
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

# ADR 0004: Web framework — Django + server-rendered templates + HTMX

MADR status: **accepted**.

## Context and Problem Statement

The spec left the web framework undecided (`_TBD_` — "FastAPI or Django"). The choice is foundational: it dictates the auth mechanism (ADR 0005), the ORM and migration workflow, the admin/back-office story, and the shape of every view and template.

Hardware Radar's center of gravity is an **authenticated listings database with dashboards, CRUD (watches/alert-rules), email alerts, and internal operations** (inspecting scraped offers, correcting entity matches, triaging ingestion) — _not_ a public API platform. The research report [`opinionated-core-stack-recommendations…`](../research/opinionated-core-stack-recommendations-for-a-python-drive-price-monitor.md) recommends Django for exactly this app shape, and gaps #1 (auth) and #7 (UI) independently converge on it.

## Considered Options

- **Option 1 — Django + server-rendered templates + HTMX.** (chosen)
- **Option 2 — FastAPI + server-rendered templates (Jinja) + HTMX**, auth/ORM/admin hand-assembled.
- **Option 3 — FastAPI JSON API + a separate SPA frontend** (React/Vue).

## Decision Outcome

Chosen option: **Option 1 — Django with server-rendered templates and HTMX.**

Django's batteries — `contrib.auth`, the ORM, migrations, and the admin — remove exactly the scaffolding a single maintainer would otherwise hand-build and maintain. HTMX supplies the modest interactivity (filtering, inline state changes, partial refreshes) the dashboard/detail/watch pages need without an SPA build chain. The **Django admin serves as the internal back-office** (offer inspection, entity-match correction, ingestion triage) — but not as the user-facing front end, so the dashboard/detail/watch pages are still built on top.

Option 3 was rejected because a separate SPA adds a build pipeline, a second language surface, and an API contract to maintain — pure cost for a data-heavy CRUD app with one maintainer. Option 2 was rejected because it re-implements auth, an admin, and migration conventions that Django already provides for free; FastAPI's async-API strengths aren't what this app is bottlenecked on.

### Consequences

- **Good** — auth (ADR 0005), ORM, migrations, and a back-office admin come built-in; converges with the auth decision (`contrib.auth`).
- **Good** — server-rendered + HTMX means no SPA build/deploy chain and no client/server model duplication; simpler to reason about and to deploy on a single CT (ADR 0003).
- **Good** — the admin covers internal operations from day one, before bespoke ops UI exists.
- **Bad** — Django is heavier than FastAPI for any genuinely API-first surface added later (e.g. a mobile client) — that would need Django REST Framework or a bolt-on.
- **Bad** — HTMX has an interactivity ceiling; a future highly-dynamic view might need a JS island or a partial rethink.
- **Neutral** — the ORM/migration and app-layout conventions are now fixed for every contributor; the Python-tooling gate (ADR 0002) governs the code either way.

### Confirmation

The spec's framework `_TBD_` is resolved to Django, and resolved-questions.md resolved question RQ1 records **framework → Django**. Confirmed at scaffold when `manage.py`, `contrib.auth`, initial migrations, and the admin registration land.

## More Information

- Research: [`opinionated-core-stack-recommendations…`](../research/opinionated-core-stack-recommendations-for-a-python-drive-price-monitor.md).
- Related decisions: ADR 0005 (single-account auth, built on `contrib.auth`), ADR 0003 (CT deployment). Confirm against pending research prompt #10's final framework write-up before scaffolding.
