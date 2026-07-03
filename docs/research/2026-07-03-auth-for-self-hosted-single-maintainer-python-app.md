---
schema_version: '1.1'
id: 2026-07-03-auth-for-self-hosted-single-maintainer-python-app
title: Authentication for a Self-Hosted, Single-Maintainer Python Web App Behind NGINX (2026)
description: Tiered auth recommendation (Tailscale-only -> single-account session -> forward-auth or app-native OIDC) for disk-search, comparing reverse-proxy identity gateways against app-native auth for a single-maintainer FastAPI/Django app.
doc_type: research
status: active
created: '2026-07-03'
updated: '2026-07-03'
reviewed: null
owner: chris
tags:
- authentication
- nginx
- forward-auth
- self-hosted
- tailscale
- fastapi
- django
- security
aliases:
- auth research disk-search
- disk-search authentication options
related: []
source:
- https://www.authelia.com/reference/guides/validating-forwarded-authentication
- https://www.authelia.com/integration/proxies/nginx
- https://nvd.nist.gov/vuln/detail/CVE-2025-54576
- https://www.sentinelone.com/vulnerability-database/cve-2026-34457
- https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
- https://docs.djangoproject.com/en/5.2/topics/auth/passwords
- https://github.com/fastapi-users/fastapi-users
confidence: high
visibility: private
license: null
---

# Authentication for a Self-Hosted, Single-Maintainer Python Web App Behind NGINX (2026)

## Context

disk-search (https://disk-search.l3digital.net) is a single-maintainer FastAPI/Django tool on one Debian 13 VM behind NGINX + Let's Encrypt, currently single-user with a stated future need for multi-user support. This report compares reverse-proxy (forward-auth) identity gateways against app-native auth, covers the header-spoofing risk in forward-auth setups, and gives a tiered recommendation.

## Tier recommendation (answer first)

| Tier | What | Effort | Gives up | When to move on |
| --- | --- | --- | --- | --- |
| **0 — now** | Tailscale-only access (no public NGINX vhost, or `tailscale serve`/Funnel gate); no app auth needed | Minutes (already using Tailscale) | Public URL access for anyone off-tailnet; no per-user identity | You need to share the URL with someone outside your tailnet |
| **1 — if public access is required today** | Single-account session login in-app (Django's built-in `django.contrib.auth` or a hand-rolled FastAPI session-cookie login), Argon2id-hashed password, `Secure`+`HttpOnly`+`SameSite=Lax` cookie | Hours | MFA, self-service registration, no audit trail beyond app logs | You need a second real user or MFA |
| **2 — multi-user, still one maintainer** | Forward-auth at NGINX via **Authelia** (lightest) or **Authentik** (fuller IdP), using `auth_request` + trusted headers, app trusts headers *only* if it cannot be reached except through NGINX | 1 evening | Some operational surface (extra container/service to patch); requires getting header-trust boundary right | Never — this is the durable answer for "start simple, extend to multi-user" |
| **2-alt** | App-native OIDC/social login via **django-allauth** (Django) or **Authlib** (FastAPI) instead of a forward-auth gateway | 1 evening–1 day | Centralized policy/MFA across other self-hosted apps (forward-auth gateways give you that for free if you add more services later) | You only ever want auth logic inside this one app, never shared across services |

Tier 0 and Tier 2 (Authelia) are the two defensible end states; Tier 1 is a legitimate bridge but should not be the permanent answer once a second user shows up.

## Existing solution

No single existing tool fully covers "start with one user, extend cleanly to multi-user auth for a small self-hosted app" out of the box — this is an architecture decision, not a drop-in package. However, **Authelia** specifically targets exactly this homelab-scale forward-auth use case and is worth adopting directly rather than building app-native auth from scratch once a second user is real. [community] (https://www.authelia.com/)

## Summary

| Angle | Sources | Strongest finding |
| --- | --- | --- |
| Official Docs | 3 | Authelia's NGINX guide requires reading "Forwarded Headers" + "Validating Forwarded Authentication" as mandatory security steps, not optional reading [official] |
| Best Practices | 4 | OWASP (2026) recommends Argon2id as the default password hash, with bcrypt (work factor >=10, ideally >=12) as a legacy fallback [official/community] |
| Footguns | 5 | Forward-auth gateways only add security if the backend app is unreachable except through the proxy; NGINX must strip client-supplied copies of the trust header before setting its own |
| Existing Tools | 4 | Authelia (~50MB RAM, single Go binary) fits a 1-maintainer VM far better than Authentik (~2GB+ RAM, Python/Django, needs its own DB) unless you need a visual admin UI or SAML |
| Security | 4 | Two 2025-2026 CVEs in oauth2-proxy (regex bypass, health-check header-spoofing bypass) directly illustrate the header-trust failure mode this research was asked to check |
| Recent Changes | 3 | fastapi-users is now in maintenance mode (security fixes only, no new features) as of its current GitHub status; Authentik removed its Redis dependency in the 2025.10 release |

**Queries:** 12 · **Results parsed:** ~68 · **Deep reads:** 5 · **Follow-up pass:** no (all six angles reached 2+ distinct sources on the first sweep)

## 1. Reverse-proxy / forward-auth vs app-native auth

### Reverse-proxy (forward-auth) gateways

NGINX's `auth_request` directive delegates the authentication decision to a subrequest against an external service (Authelia, Authentik, oauth2-proxy, Pomerium). If that subrequest returns 2xx, NGINX proceeds and can copy identity headers from the auth service's response into the request forwarded to the app; a 401/403 short-circuits the request before it ever reaches the app. [community] (https://www.authelia.com/integration/proxies/nginx)

- **Authelia** — Go binary, ~50MB RAM, YAML config, purpose-built forward-auth + MFA/WebAuthn/OIDC portal. Recommended by multiple 2026 comparison pieces for <2GB RAM hosts and <10 protected apps. [community] (https://blog.canadianwebhosting.com/authelia-vs-authentik-self-hosted-sso-comparison)
- **Authentik** — Python/Django, full IdP with visual flow builder, user-management UI, SAML/SCIM/LDAP; needs 2GB+ RAM and its own Postgres. As of the 2025.10 release it no longer requires Redis, lowering the container count. [official-ish] (https://x.com/authentikio) corroborated by release-notes index (https://goauthentik.io/blog/2026-02-27-authentik-version-2026-2)
- **oauth2-proxy** — Go, OAuth2/OIDC-only forward-auth proxy, no built-in user DB (delegates identity to an external OIDC provider e.g. Google/GitHub/Keycloak). Actively maintained (v7.15.x in 2026) but see the CVE note in §5 — the exact `auth_request` integration mode this research asked about has shipped two real bypass CVEs. [official] (https://github.com/oauth2-proxy/oauth2-proxy/releases)
- **Pomerium** — Go, identity-aware proxy, "successor to oauth2_proxy" per its own positioning; has an open-source "Pomerium Core" edition and is actively developed in 2026, including native SSH proxying. [community] (https://www.pomerium.com/zero)
- **Cloudflare Access** — hosted, not self-hosted; free tier covers up to 50 users, $7/user/month beyond that. Removes the need to run any auth service yourself, at the cost of routing all traffic through Cloudflare and trusting a third party with your access-control policy. [community, 3 independent pricing sources] (https://zerometric.net/review/cloudflare-zero-trust/, https://costbench.com/software/ztna/cloudflare-access/)
- **Tailscale serve/tsnet** — not a proxy-auth product; it removes public exposure entirely (see §5).

**Setup effort ranking (lightest to heaviest):** Tailscale-only (near zero) < Authelia < oauth2-proxy < Cloudflare Access (no install, but account/DNS delegation) < Pomerium < Authentik < Keycloak.

**Single-user-now, multi-user-later flexibility:** forward-auth gateways win decisively here — adding a second user is a config/UI change in the gateway, with zero application code changes, because the app never manages credentials.

### App-native auth

- **Django**: `django.contrib.auth` ships session auth, `Argon2PasswordHasher` (configure it first in `PASSWORD_HASHERS`), login/logout views, and `SESSION_COOKIE_SECURE`/`SESSION_COOKIE_HTTPONLY` settings checked by Django's own system checks. [official] (https://docs.djangoproject.com/en/5.2/topics/auth/passwords, https://docs.djangoproject.com/en/5.2/ref/checks)
- **FastAPI**: no built-in auth; common choices are **fastapi-users** (session/JWT/OAuth backends, `Transport + Strategy` model) or hand-rolled session cookies + `passlib`/`argon2-cffi` directly. **fastapi-users is now in maintenance mode** — the project's own README states it will receive security and dependency updates only, no new features, as of its current release. Treat it as stable-but-frozen, not as a growing platform. [official] (https://github.com/fastapi-users/fastapi-users)
- **OIDC/social login**: **django-allauth** is the mature, actively developed choice for Django (now also ships an OpenID-Connect *provider*/IdP mode via `django-allauth[idp-oidc]`, not just client-side social login). For FastAPI, **Authlib** is the community-standard OAuth/OIDC client library used in most current tutorials (Auth0, WorkOS, and independent guides). [community, corroborated 3 sources] (https://docs.allauth.org/en/latest/socialaccount/configuration.html, https://docs.authlib.org/en/latest/client/django.html, https://developer.auth0.com/resources/guides/web-app/fastapi/basic-authentication)

**Operational weight for one maintainer:** app-native auth means one fewer service to run/patch, but it means you own password reset, session security, and (later) MFA and OAuth client management inside your own codebase. Forward-auth means one more container, but it is a container purpose-built and hardened for exactly this job, and it is the only path that gets you MFA without writing MFA code yourself.

## 2. Forward-auth mechanics and the header-spoofing risk

`auth_request` works as: NGINX receives the real request -> issues an internal subrequest to the auth service (e.g. `/internal/authelia/authz/...`) -> on 2xx, NGINX reads response headers from that subrequest via `auth_request_set` and re-injects them as request headers to the upstream app (e.g. `Remote-User`, `Remote-Groups`, `Remote-Email`) -> the app trusts those headers as the authenticated identity. [official] (https://www.authelia.com/integration/proxies/nginx, stackoverflow pattern confirms the exact `auth_request_set` + `proxy_set_header` two-step is required — a single `proxy_set_header $upstream_http_x_user` does not work)

**The header-spoofing risk is real and has already been exploited in the wild in this exact integration pattern**: CVE-2026-34457 (oauth2-proxy < 7.15.2) is an authentication bypass where an attacker sends a spoofed `User-Agent` header matching the configured health-check value (e.g. GCP's well-documented `GoogleHC/1.0`), causing oauth2-proxy to treat the entire request as a health check and skip auth — with **no changes to the actual request path**, just a header. [official CVE record + independent vendor writeup] (https://www.sentinelone.com/vulnerability-database/cve-2026-34457, NVD https://nvd.nist.gov/vuln/detail/CVE-2025-54576 — related regex-bypass sibling CVE in `skip_auth_routes`, also corroborated by CCB Belgium's national CSIRT advisory: https://ccb.belgium.be/advisories/warning-critical-authentication-bypass-vulnerability-oauth2-proxy-can-lead-attackers)

**The mitigation that matters for disk-search's stated concern ("header-spoofing risk if the app is reachable bypassing the proxy")**: the vulnerability class you should worry about is not "can NGINX be tricked" but **"can a client reach the FastAPI/Django process directly, bypassing NGINX and the auth gateway entirely"**. If so, that client can set `Remote-User: admin` themselves and the app will trust it. Concrete controls, corroborated across the Authelia docs and general reverse-proxy security guidance:

- Bind the app process to `127.0.0.1` (or a Unix socket) only — never to a public interface — so it is physically unreachable except through NGINX on the same host. [community, standard practice, corroborated: httptoolkit.com, devsec-blog.com]
- In NGINX, always overwrite the trust header rather than append to it (`proxy_set_header X-Remote-User $upstream_http_remote_user;` after clearing any client-supplied value) so a client cannot pre-set the header and have it pass through unchanged.
- Restrict Authelia's/oauth2-proxy's own "trusted proxies"/network config so it does not honor `X-Forwarded-For` from arbitrary sources — this is called out explicitly in Authelia's own "Validating Network Access Control Rules" guide as something operators must actively verify, not assume. [official] (https://www.authelia.com/reference/guides/validating-forwarded-authentication)
- Patch promptly: both real-world oauth2-proxy CVEs above are fixed in 7.11.0 and 7.15.2 respectively — pin a version >= 7.15.2 if you choose oauth2-proxy.

## 3. App-native auth details (if you skip the gateway)

- **Session vs JWT for a server-rendered app**: for a server-rendered single app (not a decoupled SPA/API), server-side sessions with an opaque cookie are the better default — no token-revocation problem, no client-side storage-XSS surface, simpler CSRF story with `SameSite=Lax`. JWT-in-cookie is popular in tutorials but adds complexity (revocation, expiry skew) disk-search does not need. Multiple 2026 sources converge on "sessions for first-party web apps, JWT for cross-service APIs." [community, corroborated 2 sources] (https://fastro.ai/blog/fastapi-authentication, https://fastapi-users.github.io/fastapi-users/10.1/configuration/authentication)
- **Cookie flags**: `Secure` (mandatory over TLS, which disk-search already has via Let's Encrypt), `HttpOnly` (prevents JS/XSS token theft), `SameSite=Lax` for standard first-party login flows (`Strict` if you never need cross-site referral links into the app). MDN and multiple security blogs agree on this triad as the 2026 minimum bar. [official] (https://developer.mozilla.org/en-US/docs/Web/Security/Practical_implementation_guides/Cookies)
- **Password hashing**: Argon2id is OWASP's current recommendation; bcrypt (work factor >=10, ideally >=12+) remains an acceptable fallback for legacy systems. Django: list `Argon2PasswordHasher` first in `PASSWORD_HASHERS` (requires `argon2-cffi`). FastAPI: use `argon2-cffi` directly or via `passlib`'s Argon2 handler — do not use a fast hash (MD5/SHA-256 alone). [official] (https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html, https://docs.djangoproject.com/en/5.2/topics/auth/passwords)
- **OAuth/OIDC social login**: worth adding only once you have real second/third users who want "log in with Google" — django-allauth (Django) or Authlib (FastAPI) are the community-standard choices; both are actively maintained as of 2026.

## 4. The pragmatic "single user today" options, compared

| Option | What you get | What you give up |
| --- | --- | --- |
| **HTTP Basic behind TLS** | Trivial to set up (NGINX `auth_basic` or app-level), credentials are encrypted in transit over TLS (RFC 7617 explicitly notes Basic is safe *given* TLS) | No logout, no session timeout UX, browser-native ugly prompt, no MFA path, awkward to extend to per-user accounts later (it's file-based, not a user table) [official spec + corroboration] (https://datatracker.ietf.org/doc/html/rfc7617) |
| **Single-account session login (app-native)** | Real login page, real session cookie with proper flags, natural upgrade path to a multi-row `users` table later, no new services to run | You still own password storage/reset flow yourself; no MFA out of the box |
| **Tailscale-only (no public exposure)** | Zero auth code needed at all — the tailnet *is* the auth boundary (device + user identity via Tailscale's own auth); free, already in use by the owner | Nobody outside the tailnet can reach the tool at all — this conflicts with disk-search having a public URL today unless that's changed |

Given disk-search **already has a public URL** (https://disk-search.l3digital.net), the realistic minimal-viable options are HTTP Basic or single-account session login, not Tailscale-only, unless the public URL requirement is renegotiated (see §5).

## 5. Is public exposure necessary at all?

Multiple independent 2026 sources describe the same pattern the owner is already positioned to use: run `tailscale serve` (or Tailscale Funnel if selective public sharing is ever needed) so the service gets a stable HTTPS hostname and is reachable only over the tailnet, with **zero open ports on the public internet** and no auth code required in the app at all. [community, corroborated 3 sources] (https://webnestify.cloud/insights/cybersecurity-hardening/linux-server-security-fundamentals, https://www.xda-developers.com/i-dont-expose-my-home-server-anymore-i-let-tailscale-do-the-scary-part, https://blog.openreplay.com/secure-local-web-apps-tailscale)

- If disk-search's public URL exists mainly so the owner can reach it from personal devices, **switching to Tailscale-only removes the entire auth problem** — no NGINX public vhost, no login page, no password to manage, no CVEs in a forward-auth gateway to track.
- If the public URL is required because non-tailnet parties (future customers/collaborators) need access, public exposure is necessary and Tier 1/2 above applies.
- A middle path: keep the public vhost for occasional sharing via **Tailscale Funnel** (selectively exposes a tailnet service to the public internet with automatic HTTPS) while defaulting to tailnet-only access day to day.

## Best Practices

- OWASP: Argon2id is the current recommended password hash; treat bcrypt as fallback-only. [official] (https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- Django's own security checks (`SECRET_KEY` strength, `SESSION_COOKIE_SECURE`/`HTTPONLY`) are enforced via `manage.py check --deploy` — run it before going to production. [official] (https://docs.djangoproject.com/en/5.2/ref/checks)
- Authelia's docs explicitly require re-validating forwarded-auth behavior after every proxy/app config change, not just at initial setup — this is process guidance worth adopting regardless of which gateway you pick. [official] (https://www.authelia.com/reference/guides/validating-forwarded-authentication)

## Footguns and Gotchas

- **Header-spoofing via direct backend access** — if the FastAPI/Django process is reachable on a public interface/port bypassing NGINX, the entire forward-auth trust model collapses; corroborated by Authelia's own "Forwarded Headers"/trusted-proxies docs [official] and general X-Forwarded-* spoofing writeups (https://httptoolkit.com/blog/what-is-x-forwarded-for, https://devsec-blog.com/2025/04/understanding-the-x-forwarded-for-http-header-security-risks-and-best-practices).
- **oauth2-proxy health-check bypass (CVE-2026-34457)** and **skip_auth_routes regex bypass (CVE-2025-54576)** — both are real, patched (7.15.2 and 7.11.0 respectively) authentication-bypass CVEs in the exact `auth_request`-style integration this research covers — corroborated by NVD, a national CSIRT advisory (CCB Belgium), and an independent vendor writeup (ZeroPath). [official CVE + 2 independent]
- **`auth_request_set` is required, not optional** — a naive `proxy_set_header x-user $http_x_user;` silently does not forward the auth service's response header; you must capture it into an NGINX variable first via `auth_request_set` — corroborated by Authelia's own config examples and a widely-cited Stack Overflow answer. [official + community, 2 sources]
- **fastapi-users is frozen in maintenance mode** — no new features will land, only security/dependency patches, per the project's own GitHub README. If you pick FastAPI and want a growing auth feature set (not just stability), plan on Authlib + hand-rolled session logic rather than betting on fastapi-users growing new capabilities. [official, single-source but authoritative (project's own statement)]

## Existing Tools

| Tool | Maintenance | Link | Fit for use case |
| --- | --- | --- | --- |
| Authelia | Active, Go, ~50MB RAM | https://www.authelia.com/ | Best fit — lightest forward-auth gateway for a 1-maintainer VM, built-in MFA/WebAuthn, clean multi-user upgrade path |
| Authentik | Active, Python/Django, dropped Redis dependency 2025.10 | https://goauthentik.io/ | Overkill today; consider if you later want a visual admin UI, SAML, or plan to front many services |
| oauth2-proxy | Active (Go), two 2025/2026 CVEs patched | https://github.com/oauth2-proxy/oauth2-proxy | Good if you only need "log in with an existing OIDC provider," no local user DB wanted; pin >=7.15.2 |
| Pomerium | Active, Go, open-source "Core" edition | https://www.pomerium.com/ | Viable alternative to oauth2-proxy; more emphasis on zero-trust policy than homelab simplicity |
| Cloudflare Access | Hosted SaaS, free up to 50 users | https://www.cloudflare.com/sase/products/access/ | Zero self-hosted ops, but routes traffic through a third party and requires DNS delegation to Cloudflare |
| Tailscale serve/Funnel | Active, first-party feature of Tailscale (already in use) | https://tailscale.com/kb/1242/tailscale-serve | Removes the auth problem entirely if public exposure isn't strictly required |
| fastapi-users | Maintenance mode only (security/deps, no new features) | https://github.com/fastapi-users/fastapi-users | Fine for FastAPI today, but treat as a stable/frozen base, not a growing platform |
| django-allauth | Active | https://docs.allauth.org/ | Best OIDC/social-login path if Django is chosen and app-native auth is preferred |

## Security and Compatibility

- CVE-2025-54576 — oauth2-proxy `skip_auth_routes` regex bypass matches full URI including query string, not just path; fixed in 7.11.0. (https://nvd.nist.gov/vuln/detail/CVE-2025-54576)
- CVE-2026-34457 — oauth2-proxy health-check User-Agent spoofing bypasses auth entirely in `auth_request`-style deployments with `--ping-user-agent`/`--gcp-healthchecks` set; fixed in 7.15.2. (https://www.sentinelone.com/vulnerability-database/cve-2026-34457)
- OWASP Password Storage Cheat Sheet (current): Argon2id primary, bcrypt work factor >=10 (ideally 12+) as fallback, PBKDF2 (600k+ iterations) only if FIPS-140 compliance is required. (https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- RFC 7617 confirms HTTP Basic auth is only acceptable in conjunction with TLS — never bare HTTP. (https://datatracker.ietf.org/doc/html/rfc7617)

## Recent Changes

- fastapi-users entered maintenance mode (security/dependency updates only, no new features) — check this before building new functionality around it. (https://github.com/fastapi-users/fastapi-users)
- Authentik removed its Redis dependency starting with the 2025.10 release, simplifying its container footprint (still needs Postgres). (https://x.com/authentikio, cross-checked against https://goauthentik.io/blog/2026-02-27-authentik-version-2026-2)
- oauth2-proxy shipped two authentication-bypass security releases within the last ~12 months (7.11.0 for CVE-2025-54576, 7.15.2 for CVE-2026-34457) — if adopting it, pin to the latest patch and subscribe to its GitHub security advisories.

## Open Questions

| # | Question | Why unresolved |
| --- | --- | --- |
| 1 | Does disk-search's public URL need to stay reachable by non-Tailscale parties (customers, collaborators), or was it made public mainly for the owner's own convenience? | Determines whether Tier 0 (Tailscale-only) is actually sufficient — this is a product decision, not something search can resolve |
| 2 | FastAPI vs Django is still undecided per the prompt | Materially changes the app-native auth library choice (fastapi-users/Authlib vs django.contrib.auth/django-allauth) and tips the balance slightly toward Django if a rich built-in admin/auth stack is valued over async performance |

## Handoff

Persisted at `/home/chris/projects/disk-search/docs/research/2026-07-03-auth-for-self-hosted-single-maintainer-python-app.md`. Downstream skills that may consume it:

- `superpowers:brainstorming` — feed the two Open Questions (public-exposure necessity, FastAPI vs Django) into a design conversation
- `feature-dev:feature-dev` — start implementation with Tier 0/1 as the v1 slice and Tier 2 (Authelia forward-auth) as the planned upgrade path

## Sources

| URL | Title | Date | Authority |
| --- | --- | --- | --- |
| https://www.authelia.com/integration/proxies/nginx | NGINX \| Integration \| Authelia | 2026 | official |
| https://www.authelia.com/reference/guides/validating-forwarded-authentication | Validating Forwarded Authentication \| Authelia | 2026 | official |
| https://www.authelia.com/reference/guides/proxy-authorization | Proxy Authorization \| Authelia | 2026 | official |
| https://github.com/oauth2-proxy/oauth2-proxy/releases | oauth2-proxy releases | 2026 | official |
| https://nvd.nist.gov/vuln/detail/CVE-2025-54576 | CVE-2025-54576 | 2025-07-30 | official |
| https://www.sentinelone.com/vulnerability-database/cve-2026-34457 | CVE-2026-34457: OAuth2 Proxy Authentication Bypass | 2026-04-14 | community |
| https://zeropath.com/blog/cve-2025-54576-oauth2-proxy-auth-bypass | OAuth2-Proxy CVE-2025-54576 summary | 2025 | blog |
| https://ccb.belgium.be/advisories/warning-critical-authentication-bypass-vulnerability-oauth2-proxy-can-lead-attackers | CCB Belgium advisory | 2025 | official (national CSIRT) |
| https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html | Password Storage Cheat Sheet | 2026 | official |
| https://docs.djangoproject.com/en/5.2/topics/auth/passwords | Django password management | 2026 | official |
| https://docs.djangoproject.com/en/5.2/ref/checks | Django system check framework (security checks) | 2026 | official |
| https://github.com/fastapi-users/fastapi-users | fastapi-users (maintenance mode notice) | 2026 | official |
| https://docs.allauth.org/en/latest/socialaccount/configuration.html | django-allauth configuration | 2026 | official |
| https://docs.authlib.org/en/latest/client/django.html | Authlib Django OAuth client | 2026 | official |
| https://blog.canadianwebhosting.com/authelia-vs-authentik-self-hosted-sso-comparison | Authelia vs Authentik comparison | 2026 | blog |
| https://www.cerbos.dev/blog/authelia-vs-authentik-2026-idp | Authelia vs Authentik in 2026 | 2026 | blog |
| https://blog.elest.io/authentik-vs-authelia-vs-keycloak-choosing-the-right-self-hosted-identity-provider-in-2026 | Authentik vs Authelia vs Keycloak | 2026 | blog |
| https://x.com/authentikio | Authentik Security announcement (Redis removal) | 2026 | official (vendor account) |
| https://goauthentik.io/blog/2026-02-27-authentik-version-2026-2 | authentik 2026.2 release notes | 2026-02-27 | official |
| https://www.pomerium.com/zero | Pomerium: clientless remote access | 2026 | community |
| https://zerometric.net/review/cloudflare-zero-trust/ | Cloudflare Zero Trust 2026 review | 2026 | blog |
| https://costbench.com/software/ztna/cloudflare-access/ | Cloudflare Access pricing 2026 | 2026-06 | blog |
| https://webnestify.cloud/insights/cybersecurity-hardening/linux-server-security-fundamentals | Linux Server Security in 2026 (Tailscale baseline) | 2026 | blog |
| https://www.xda-developers.com/i-dont-expose-my-home-server-anymore-i-let-tailscale-do-the-scary-part | I don't expose my home server anymore | 2026 | blog |
| https://blog.openreplay.com/secure-local-web-apps-tailscale | Access Local Web Apps Securely with Tailscale | 2026 | blog |
| https://datatracker.ietf.org/doc/html/rfc7617 | RFC 7617: The 'Basic' HTTP Authentication Scheme | - | official |
| https://developer.mozilla.org/en-US/docs/Web/Security/Practical_implementation_guides/Cookies | Secure cookie configuration - MDN | 2026 | official |
| https://httptoolkit.com/blog/what-is-x-forwarded-for | What is X-Forwarded-For and when can you trust it? | - | blog |
| https://devsec-blog.com/2025/04/understanding-the-x-forwarded-for-http-header-security-risks-and-best-practices | Understanding the X-Forwarded-For HTTP Header | 2025-04 | blog |
| https://stackoverflow.com/questions/19366215/setting-headers-with-nginx-auth-request-and-oauth2-proxy | Setting headers with NGINX auth_request and oauth2_proxy | - | community |
| https://fastro.ai/blog/fastapi-authentication | FastAPI Authentication: JWT, Sessions, and OAuth | 2026 | blog |
