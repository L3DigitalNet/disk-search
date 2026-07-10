# Project Status

## Current snapshot

- MS-0 and MS-1a through MS-1d are implemented and merged: Django/TimescaleDB foundation, ingestion substrate, matching, catalog seed, five connectors, and availability heartbeat.
- All marketplace sources ship disabled; scoring and alerting are not implemented.
- Source go-live remains gated by the SA-004 operations checklist, bounded-retention expiry enforcement, and the eBay listing soft-delete path.
- The MS-1e validation-corpus and ADR-0019 ratification design is Codex-converged; implementation planning is next.
- The recorded verification baseline is 357 tests with 93% branch coverage; DB-backed tests require TimescaleDB.
- Work belongs on `dev`; protected `main` advances through pull requests.
- Agent Handoff v1 provides one shared repo-local SessionStart runtime for the dual Claude/Codex profile.
