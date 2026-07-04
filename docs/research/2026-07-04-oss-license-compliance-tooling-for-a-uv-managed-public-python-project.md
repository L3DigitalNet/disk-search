---
schema_version: '1.1'
id: 2026-07-04-oss-license-compliance-tooling-for-a-uv-managed-public-python-project
title: OSS license-compliance tooling and process for a small public Python project using uv
description: Research for hw-radar OQ20 — evaluates license-check tooling (pip-licenses, licensecheck, liccheck, cyclonedx-py/SBOM, GitHub's native dependency-review-action), the real copyleft exposure for a public-source non-distributed self-hosted app, TimescaleDB TSL specifics, and the core stack's actual licenses.
doc_type: research
status: active
created: '2026-07-04'
updated: '2026-07-04'
reviewed: '2026-07-04'
owner: chris
tags: [oss-license, license-compliance, uv, pip-licenses, licensecheck, sbom, cyclonedx, timescaledb, tsl, agpl, lgpl, github-actions, dependency-review]
aliases: [OQ20, oss-license-compliance, license-check-tooling]
related: []
source: []
confidence: high
visibility: public
license: CC-BY-4.0
---

# OSS license-compliance tooling and process for a small public Python project using uv

## Context

hw-radar is a public GitHub repo, single-maintainer, uv-managed (`pyproject.toml` + `uv.lock`), **not distributed** — it runs only on the owner's own Debian LXC. Spec §16 currently claims dependency-license compatibility is "covered by the standard toolchain's audit practices," but `pip-audit` checks CVEs, not licenses. OQ20 asks whether to (a) do a one-time manual review + review-on-new-dep, (b) add an automated license gate, or (c) accept the risk and reword §16.

## ⚠ Existing solution

> **GitHub's native `dependency-review-action`** (`actions/dependency-review-action@v4`, MIT, 853★, actively maintained — v4.9.0 released 2026-03) — appears to cover this use case almost exactly, at zero added tooling cost. As of the 2026-04-23 Dependabot-based Python dependency-graph rollout, GitHub natively resolves `uv.lock` (alongside pip/Poetry) into an accurate transitive dependency graph, and that graph already carries **per-dependency license data**, visible today in the repo's Insights → Dependency graph tab for free on any public repository. `dependency-review-action` runs the same data through a PR-triggered check with `allow-licenses`/`deny-licenses` (SPDX identifiers), fails the PR on a violation, and — critically — **does not hard-fail on an undetectable/`UNKNOWN` license**, it only warns. Available free on public repos (GHAS is only required for *private* repos). Review before building a bespoke `pip-licenses`/`liccheck` gate step.

## Summary

| Angle          | Sources | Strongest finding |
| -------------- | ------- | ------------------ |
| Official Docs  | 5       | GPL/LGPL copyleft triggers on *distribution*; internal/SaaS use is exempt — only AGPL closes that gap (FSF/GPL text via secondary explainers + Black Duck whitepaper) |
| Best Practices | 3       | Use an allowlist (`allow-licenses`), not a denylist — GitHub itself is deprecating `deny-licenses` (issue #938) because allowlists degrade safely on unknown future licenses |
| Footguns       | 4       | `UNKNOWN`/missing PyPI license metadata is the dominant failure mode across every classifier-based tool (pip-licenses, licensecheck, liccheck all reproduce it) |
| Existing Tools | 6       | GitHub's own dependency-graph + `dependency-review-action` already covers this for free on a public uv repo — no new tool needed |
| Security       | 4       | TimescaleDB Community Edition (TSL) explicitly permits self-hosted/internal use of compression, continuous aggregates, and retention policies for free — the **only** prohibited act is reselling it as a hosted DBaaS |
| Recent Changes | 3       | GitHub's Dependabot-based Python dependency graph (2026-04-23) added first-class `uv` lockfile resolution; PEP 639 (SPDX `License-Expression`) is displacing the ambiguous Trove classifiers that cause `UNKNOWN` results |

**Queries:** 15 · **Results parsed:** ~60 · **Deep reads:** 4 · **Follow-up pass:** no

## Official Documentation

- GPL's copyleft trigger is **distribution**, not use — "if you use GPL software internally without distributing it to anyone outside your organization, you have no copyleft obligations" [community] (<https://www.opensourcealternatives.to/blog/open-source-license-guide>), corroborated by [community] (<https://www.mend.io/blog/the-saas-loophole-in-gpl-open-source-licenses>, quoting IP counsel) and [community] (<https://www.blackduck.com/content/dam/black-duck/en-us/whitepapers/wp-opensourse-saas-offerings.pdf>). Only **AGPL §13** extends the trigger to network-interactive use — irrelevant here since hw-radar has no AGPL dependency in its current stack.
- TimescaleDB Community Edition is licensed under the **Timescale License (TSL)**; "you can install TimescaleDB Community Edition in your own on-premises or cloud infrastructure and run it for free... completely free if you manage your own service" and the only prohibition is offering it as a hosted DBaaS [official] (<https://www.tigerdata.com/docs/get-started/choose-your-path/timescaledb-editions>), full agreement text at [official] (<https://www.tigerdata.com/legal/licenses>).
- `psycopg` (v3, the package hw-radar will use) ships **License Expression: LGPL** (LGPL-3.0-only) [official] (<https://pypi.org/project/psycopg>), confirmed by the Fedora package metadata [community] (<https://packages.fedoraproject.org/pkgs/python-psycopg3/python3-psycopg3/index.html>). `psycopg2`'s license page spells out the LGPL-3 + OpenSSL linking exception [official] (<https://www.psycopg.org/docs/license.html>).
- GitHub's dependency graph "for each dependency, you can see the version, **license information**... and whether it has known vulnerabilities," and is on by default for public repos [official] (<https://docs.github.com/code-security/supply-chain-security/understanding-your-software-supply-chain/about-the-dependency-graph>).
- `dependency-review-action`'s `allow-licenses`/`deny-licenses` options take "any SPDX-compliant identifier(s)," are mutually exclusive, and the action **warns rather than fails** when a license can't be detected [official] (<https://github.com/actions/dependency-review-action>, <https://docs.github.com/en/code-security/tutorials/secure-your-dependencies/customize-dependency-review-action>).

## Best Practices

- Prefer an **allowlist** (`allow-licenses: MIT, BSD-3-Clause, Apache-2.0, ...`) over a denylist for a small permissively-licensed stack — GitHub itself is deprecating `deny-licenses` (tracked in issue #938) precisely because a denylist silently passes any license you didn't think to list, while an allowlist fails closed on anything unexpected (new transitive dep, license change on an update) [official] (<https://github.com/actions/dependency-review-action>).
- Record *which* TimescaleDB feature tier is in use, since the license boundary is drawn per-feature, not per-install: query `SHOW timescaledb.license;` (or `pg_settings`) to confirm which edition's features are active in production, and pin the specific Community-Edition features actually relied on (compression, continuous aggregates, retention policies) in a doc so a future maintainer doesn't accidentally reach for a Tiger-Cloud-only feature that isn't licensed for self-hosting [official] (<https://www.tigerdata.com/docs/get-started/choose-your-path/timescaledb-editions>).
- For LGPL (`psycopg`), the safe-harbor path is **dynamic linking without redistributing the library** — which is exactly Python's import model (no static linking of C extensions into your own binary) and matches "cloud services... dynamic linking generally safe, no distribution = no obligations" [blog] (<https://licensecheck.io/blog/lgpl-dynamic-linking>), corroborated by the general LGPL dynamic-linking safe-harbor explainer at [community] (<https://fossa.com/blog/open-source-software-licenses-101-lgpl-license>).

## Footguns and Gotchas

- **`UNKNOWN` license results are the dominant failure mode across every classifier-reading tool**, not a one-off bug: reproduced live in `pip-licenses`' own docs (`setuptools` shows `License: UNKNOWN` under `pip show`, needs `--from=mixed` to recover it from Trove classifiers) [official] (<https://pypi.org/project/pip-licenses/>), in `licensecheck`'s own example output (`Pygments`, `colorama`, `idna` all show `UNKNOWN` despite having real licenses) [official] (<https://pypi.org/project/licensecheck/>), and in `liccheck`'s own example (`feedparser` reported "unknown") [official] (<https://pypi.org/project/liccheck/>) — corroborated across 3 independent tool-maintainer sources. Any gate must either allowlist-with-manual-override for known-good `UNKNOWN` hits or accept periodic manual triage.
- **`uv.lock` is not yet a first-class input to the SBOM/license tool ecosystem.** `cyclonedx-py` explicitly documents "support for uv manifest and lockfile is not explicitly implemented, yet" and the feature request (issue #1029, filed against native `uv` subcommand support) was still open as of this research — the documented workaround is running against the *synced `.venv`* (`cyclonedx-py environment $(uv env path)`), which reflects what's installed, not necessarily what's pinned in the lockfile if the venv is stale [official] (<https://cyclonedx-bom-tool.readthedocs.io/en/latest/usage.html>, <https://github.com/CycloneDX/cyclonedx-python/issues/1029>) — corroborated by the open GitHub issue thread itself as a second independent artifact of the same maintainers.
- **PyPI/Trove license classifiers are a known ambiguous/deprecated data source** — PEP 639 formally deprecates the classifier-based `License ::` fields in favor of a machine-readable SPDX `License-Expression`, citing "outdated and ambiguous PyPI classifiers" as a driving problem [official] (<https://peps.python.org/pep-0639/>). Until the ecosystem migrates, every classifier-reading tool (pip-licenses, licensecheck, liccheck) inherits this ambiguity — this is the root cause of the `UNKNOWN` footgun above, not a tool-specific bug.
- `dependency-review-action`'s license gate only scans **the PR diff**, triggered on `pull_request` events — it does not evaluate the full current dependency set on every push to `main`. Given the repo's solo-dev "commit directly to branches" workflow (per project CLAUDE.md), a license regression introduced outside a PR would not be caught by this gate; the passive dependency-graph view (Insights tab) would still reflect it but nothing would fail a build. [unverified — inferred from the action's documented trigger model, not independently confirmed against a live hw-radar-shaped commit-direct-to-main workflow]

## Existing Tools

| Tool | Maintenance | Link | Fit for use case |
| ---- | ----------- | ---- | ----------------- |
| GitHub `dependency-review-action` (+ built-in dependency graph) | Active, v4.9.0 (2026-03), 853★, official GitHub Actions org | <https://github.com/actions/dependency-review-action> | **Best fit.** Free on public repos, already resolves `uv.lock` (since 2026-04-23), needs only a workflow file + `allow-licenses` list. PR-triggered only (see footgun above). |
| `pip-licenses` (raimon49 fork) | Active — copyright header dated 2025-2026, Jazzband-adjacent | <https://github.com/raimon49/pip-licenses> | Simple CLI for a point-in-time snapshot against the synced venv; no `uv.lock`-native mode, no allow/deny enforcement built in (just a lister) — pair with a shell check or CI step if used. |
| `licensecheck` | Active — 2026.0.8 released 2026, MIT | <https://pypi.org/project/licensecheck> | Reads `pyproject.toml` deps directly, has `--only-licenses`/`--fail-licenses`, best native fit for a `pyproject.toml`-first project — still classifier-based, so inherits the `UNKNOWN` footgun above. |
| `liccheck` | Maintained, widely cited, requirements.txt-oriented | <https://pypi.org/project/liccheck> | Solid allow/forbid strategy file (`licconfig.ini`); built around `requirements.txt` — needs `uv export --format requirements-txt` as a bridge step since it has no native `uv.lock` reader. |
| `cyclonedx-py` (+ optional Syft/Grype) | Active, OWASP-backed, Apache-2.0 | <https://github.com/CycloneDX/cyclonedx-python> | SBOM generation is overkill for a single-maintainer non-distributed app with ~1 dozen top-level deps; also lacks native `uv.lock` support (see footgun) — only worth it if a future consumer needs a formal SBOM artifact. |
| `reuse` (FSFE) | Active, v6.2.0, well-established spec | <https://reuse.software> | File-level per-file SPDX header/copyright tooling for *this project's own* licensing clarity — solves a different problem (declaring hw-radar's own license per-file) than checking dependency licenses; not a dependency-license checker. |

## Security and Compatibility

- **TimescaleDB TSL boundary is narrow and self-hosting-friendly**: "you cannot sell TimescaleDB Community Edition as a service, even if you are the main contributor" is the entire restriction — modifying for internal use, embedding in your own apps, and distributing unmodified binaries are all explicitly allowed [official] (<https://github.com/timescale/docs/blob/latest/about/timescaledb-editions.md>), corroborated independently by the TSL agreement text itself [official] (<https://www.tigerdata.com/legal/licenses>) and a third explainer confirming "if you're using it as part of your infrastructure stack, whether on-prem, in containers, or on the cloud, you're in the clear" [blog] (<https://dev.to/okedialf/what-the-timescale-license-means-for-database-administrators-in-the-cloud-era-1h82>). hw-radar's planned use (compression, continuous aggregates, retention policies, all self-hosted, never resold) is squarely inside the permitted zone — no ADR-level risk, just a documentation note recommended below.
- **psycopg (v3) is LGPL-3.0-only** — the one non-permissive core dependency [official] (<https://pypi.org/project/psycopg>). Because hw-radar only *uses* (imports/dynamically links) psycopg and never distributes a bundled binary/derivative to a third party, the LGPL's redistribution obligations (relinking, providing library source alongside the app) don't attach; this matches the general LGPL dynamic-linking safe harbor confirmed above.
- Rest of the core stack is permissive and low-risk: Django is BSD-3-Clause, APScheduler is MIT (both well-established, stable license history), and the scraping-escalation-ladder additions are MIT (`curl_cffi`, confirmed via its own PyPI/GitHub project page: "originally forked from multippt/python_curl_cffi, which is under the MIT license" [official], <https://pypi.org/project/curl-cffi/>) and Apache-2.0 (Playwright, upstream Microsoft project — well-established, no ambiguity found in this pass). No AGPL/GPL-strong-copyleft dependency was found anywhere in the currently-planned stack.

## Recent Changes

- **2026-04-23: GitHub shipped Dependabot-based dependency graphs for Python**, explicitly covering `pip`, `uv`, and Poetry (v1/v2) — this is what makes the dependency-review-action existing-solution above viable *today* for an uv-managed repo; before this date, Python dependency-graph accuracy for `uv` projects was materially worse [official] (<https://github.blog/changelog/2026-04-23-dependabot-graphs-for-python>), corroborated by a secondary write-up [community] (<https://appsecsanta.com/dependabot>).
- **PEP 639** (SPDX `License-Expression` metadata field) is actively displacing the old ambiguous Trove `License ::` classifiers, and PyPI already rejects new uploads that specify both `License` and `License-Expression` — expect classifier-based tools' `UNKNOWN` rate to *improve* over the next 1-2 years as more packages re-publish with SPDX expressions, but the transition is not complete as of this research [official] (<https://peps.python.org/pep-0639/>).
- `dependency-review-action`'s `deny-licenses` option is marked deprecated for possible removal (tracked in upstream issue #938) in favor of `allow-licenses` — if hw-radar adopts this action, write the config with `allow-licenses` from day one to avoid a forced migration later [official] (<https://github.com/actions/dependency-review-action>).

## Recommendation

Given the corroborated findings, **option (b) — automated, low-effort license gate — is the right call, but via GitHub's native `dependency-review-action` rather than a bespoke `pip-licenses`/`liccheck` script**:

1. Add a `.github/workflows/dependency-review.yml` job (`on: pull_request`) using `actions/dependency-review-action@v4` with `allow-licenses: MIT, BSD-2-Clause, BSD-3-Clause, Apache-2.0, LGPL-3.0` (covering the current stack, including `psycopg`'s LGPL-3.0) and `fail-on-severity: none`/omitted if only license-checking is wanted (the same action also does CVE dependency-review, overlapping with but not replacing `pip-audit`'s deeper scan). This is a ~10-line workflow addition, free on this public repo, and needs no new dependency in `pyproject.toml`.
2. Because the action is PR-triggered only and hw-radar commits directly to branches, pair it with a **lightweight recurring reminder** (not new tooling): re-run `uv run licensecheck` (already `pyproject.toml`-native) as a manual step whenever a new top-level dependency is added outside a PR flow, since that's the actual gap the automated gate doesn't close.
3. Record in the spec's §16 checklist: the TimescaleDB Community-Edition feature set relied on (compression, continuous aggregates, retention policies — self-hosted, never resold, so TSL-compliant) and psycopg's LGPL-3.0 status with the dynamic-linking rationale for why no obligations attach.
4. Re-word §16's checklist line to state the actual mechanism (GitHub's dependency-review allowlist gate + the one-time documented review above) instead of the current false claim that `pip-audit` covers this.

This lands closer to (b) than a pure (a)/(c) choice, but at (a)'s cost — it reuses infrastructure the repo already has (public GitHub, Actions CI) rather than adding a new Python dependency or CI step to maintain.

## Open Questions

| #   | Question | Why unresolved |
| --- | -------- | --------------- |
| 1   | Does `dependency-review-action`'s license data source (the Dependabot Python resolver) correctly attribute licenses for **all** of hw-radar's specific planned dependencies (Django, Scrapy, APScheduler, psycopg, curl_cffi, Playwright) once actually added to `pyproject.toml`, or will any show as `OTHER`/undetected? | Could only be confirmed by adding the workflow and the real dependencies and observing a live PR — no dependencies exist yet in the scaffold (`dependencies = []`). |
| 2   | Does the action's behavior differ meaningfully when commits land directly on `main` outside a PR (the repo's actual workflow) versus the PR-only model documented upstream? | Not found in searched sources; inferred from documented trigger semantics only, flagged `[unverified]` above. |

## Handoff

Persisted at `docs/research/2026-07-04-oss-license-compliance-tooling-for-a-uv-managed-public-python-project.md`. Downstream skills that may consume it:

- `superpowers:brainstorming` — feed the two Open Questions into a design conversation before adding the workflow
- `feature-dev:feature-dev` — implement the `dependency-review.yml` workflow and the §16 reword as a small feature/chore

## Sources

| URL | Title | Date | Authority |
| --- | ----- | ---- | --------- |
| https://www.opensourcealternatives.to/blog/open-source-license-guide | Open Source Licenses Explained: AGPL, MIT, GPL, Apache 2.0 (2026) | 2026 | community |
| https://www.mend.io/blog/the-saas-loophole-in-gpl-open-source-licenses | The SaaS Loophole In GPL Open Source Licenses | — | community |
| https://www.blackduck.com/content/dam/black-duck/en-us/whitepapers/wp-opensourse-saas-offerings.pdf | Open Source Software in SaaS Offerings | — | community |
| https://www.tigerdata.com/docs/get-started/choose-your-path/timescaledb-editions | Compare TimescaleDB editions | — | official |
| https://www.tigerdata.com/legal/licenses | Software Licensing: Timescale License (TSL) | 2025-06-17 | official |
| https://github.com/timescale/docs/blob/latest/about/timescaledb-editions.md | timescaledb-editions.md | — | official |
| https://dev.to/okedialf/what-the-timescale-license-means-for-database-administrators-in-the-cloud-era-1h82 | What the Timescale License Means for DBAs | — | blog |
| https://news.ycombinator.com/item?id=24579905 | An update to the Timescale license | 2020 (context) | community |
| https://pypi.org/project/psycopg | psycopg · PyPI | — | official |
| https://packages.fedoraproject.org/pkgs/python-psycopg3/python3-psycopg3/index.html | python-psycopg3 - Fedora Packages | — | community |
| https://www.psycopg.org/docs/license.html | License — Psycopg 2.9.12 documentation | — | official |
| https://docs.github.com/code-security/supply-chain-security/understanding-your-software-supply-chain/about-the-dependency-graph | Dependency graph - GitHub Docs | — | official |
| https://github.com/actions/dependency-review-action | Dependency Review Action - GitHub | v4.9.0, 2026-03 | official |
| https://docs.github.com/en/code-security/tutorials/secure-your-dependencies/customize-dependency-review-action | Customizing your dependency review action configuration | — | official |
| https://github.blog/changelog/2022-04-06-github-action-for-dependency-review-enforcement | GitHub Action for dependency review enforcement (public repos free) | 2022 (still current per docs) | official |
| https://github.blog/changelog/2026-04-23-dependabot-graphs-for-python | Dependabot-based dependency graphs for Python | 2026-04-23 | official |
| https://appsecsanta.com/dependabot | Is Dependabot Free? 2026 Review + Pricing | 2026 | community |
| https://pypi.org/project/pip-licenses/ | pip-licenses · PyPI | — | official |
| https://github.com/raimon49/pip-licenses | pip-licenses (raimon49 fork) | 2025-2026 | official |
| https://pypi.org/project/licensecheck | licensecheck · PyPI | 2026.0.8 | official |
| https://pypi.org/project/liccheck | liccheck · PyPI | — | official |
| https://cyclonedx-bom-tool.readthedocs.io/en/latest/usage.html | Usage — CycloneDX Python 7.3.0 documentation | — | official |
| https://github.com/CycloneDX/cyclonedx-python/issues/1029 | Feature request: native uv project support | open, 2026 | official |
| https://github.com/CycloneDX/cyclonedx-python/issues/857 | Docs: how to use with uv | — | official |
| https://reuse.software | REUSE - Make licensing easy for everyone | — | official |
| https://reuse.readthedocs.io/en/latest/readme.html | reuse - reuse 6.2.0 documentation | v6.2.0 | official |
| https://peps.python.org/pep-0639/ | PEP 639 – Improving License Clarity with Better Package Metadata | — | official |
| https://pypi.org/project/curl-cffi/ | curl-cffi · PyPI | — | official |
| https://licensecheck.io/blog/lgpl-dynamic-linking | LGPL and Dynamic Linking: What Developers Need to Know | — | blog |
| https://fossa.com/blog/open-source-software-licenses-101-lgpl-license | Open Source Software Licenses 101: The LGPL License | — | community |
