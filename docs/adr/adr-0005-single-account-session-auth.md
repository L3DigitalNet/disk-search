---
schema_version: '1.1'
id: 'adr-0005-hw-radar-single-account-session-auth'
title: 'ADR 0005: Single-account session authentication'
description: 'Protect the internet-facing app with a single strong-password account (Argon2id session login) rather than Tailscale-only or full multi-user, load-bearing on the constraint that the app holds no sensitive data; Authelia forward-auth is reserved for a future multi-user end state.'
doc_type: 'adr'
status: 'active'
created: '2026-07-03'
updated: '2026-07-03'
reviewed: null
owner: ''
consumer: 'mix'
tags:
  - 'adr'
  - 'auth'
  - 'security'
  - 'web'
aliases: []
related:
  - 'docs/adr/README.md'
  - 'docs/specs/hw-radar.md'
  - 'docs/open-questions.md'
  - 'docs/research/2026-07-03-auth-for-self-hosted-single-maintainer-python-app.md'
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

# ADR 0005: Single-account session authentication

MADR status: **accepted**.

## Context and Problem Statement

The spec asserts "user authentication for secure access" and anticipates future multi-user support, but never defines an auth model, mechanism, or user schema. The app is intended to be **internet-facing** (a public URL, not tailnet-only), which makes the auth surface a real security decision — sharpened by the repo being public.

The owner's controlling constraint: the web app is designed to hold **no secrets or sensitive data** (secrets resolve at runtime via a local OpenBao Agent — gap #2 — and never live in the app). That constraint is what makes a minimal auth model acceptable rather than reckless.

## Considered Options

- **Option 1 — Single-account session login** (Argon2id password hashing). (chosen)
- **Option 2 — Tailscale-only access** (no app-level auth; remove the public surface entirely).
- **Option 3 — Full multi-user auth with MFA now** (Authelia forward-auth or Authentik from the start).

## Decision Outcome

Chosen option: **Option 1 — a single strong-password account with session login.**

Use Django `contrib.auth` (ADR 0004) with **Argon2id** hashing (OWASP 2026 default) and `Secure` + `HttpOnly` + `SameSite=Lax` cookies; enforce a strong password. Optional TOTP can be added later without a schema change. **Stub a `users` table now** so growing to multi-user is a feature, not a migration crisis.

The **load-bearing rationale — keep sensitive data out of the app entirely** — is carried into the spec, not just this record: it is the assumption under which a single-account compromise cannot leak secrets, and it must remain true for this decision to stay valid.

Option 2 was rejected because the owner wants the app reachable off-tailnet. Option 3 was rejected as premature for a single user — it adds an identity provider to operate now for a need that doesn't yet exist.

**Multi-user end state (unchanged direction):** Authelia forward-auth at NGINX (`auth_request`) — a ~50 MB Go binary, far lighter than Authentik — adds MFA + multi-user without hand-rolling it. Security-critical rules for that path when it arrives: **bind the app to localhost only** so it cannot be reached bypassing the proxy, have NGINX **overwrite (not append)** the trusted-identity header, and **pin a patched gateway release** (live 2025–2026 header-trust / `auth_request` bypasses: `CVE-2025-54576`, `CVE-2026-34457`).

### Consequences

- **Good** — minimal attack surface and near-zero auth code; built directly on Django `contrib.auth` (ADR 0004), nothing hand-rolled.
- **Good** — the `users`-table stub means multi-user later is additive, not a migration crisis.
- **Bad** — a single shared account gives no per-user audit trail or granular access; acceptable at one maintainer.
- **Bad** — a public login surface exists and can be brute-forced/credential-stuffed; mitigated by Argon2id + a strong password + the no-sensitive-data constraint (and later, optional TOTP / rate-limiting).
- **Neutral** — Authelia and MFA are deferred, not designed away; the forward-auth security rules are recorded here so they aren't rediscovered under pressure.

### Confirmation

open-questions.md gap #1 is resolved to single-account session login, and resolved question RQ2 (public URL vs Tailscale-only) is **public URL required**. Confirmed when the schema includes the `users` stub and login uses Argon2id with hardened cookie flags.

## More Information

- Research: [`auth-for-self-hosted-single-maintainer-python-app`](../research/2026-07-03-auth-for-self-hosted-single-maintainer-python-app.md).
- Related: ADR 0004 (Django `contrib.auth`), gap #2 (secrets kept out of the app via a local OpenBao Agent — the constraint this decision leans on).
