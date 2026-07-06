# Deployed State

Last updated: 2026-07-06

## Current Deployment

- The service deploys from `main` via the GitHub Actions Deploy workflow.
  Latest confirmed deployed increment: MS-1b (PR #10). The MS-1c merge (PR #11)
  deploy run was in progress at the 2026-07-06 session end — verify its outcome
  before relying on refdata features in production.
- Production runtime uses the deployment assets under `deploy/` and the Django
  settings in `src/hw_radar/settings.py`.
- The app exposes `/healthz` for release and database health checks.

## Public-Safe Boundary

Private hostnames, private IPs, container IDs, and credential values are not
recorded in this public repo. Store those facts in the private infrastructure
systems of record.

## MS-1d: Operational Gate (SA-004) and Enable Runbook

MS-1d ships five source connectors (ServerPartDeals, goHardDrive, WD, Seagate,
eBay), but every `SourceConfig.enabled` row is left `False` by migration 0005.
Flipping a source to `enabled=True` is a deliberate **operational** act, done
by an operator against the running database — never by a migration or a
deploy. It must not happen until the checklist below has been verified.

### Pre-real-data operational gate (Codex SA-004)

Verify each item below before the **first** `enabled=True` flip on any
source. The handoff record for a prior session claims these were "wired
2026-07-05c" — treat that as a claim to re-verify, not a fact to assume, since
none of it is checkable from this repo.

- [ ] The hourly TimescaleDB-aware logical dump job covers the three new
      MS-1d tables: `availability_heartbeat_observation`,
      `availability_heartbeat_event`, and `raw_payload`.
- [ ] The CT-116 disk-space alert is active. Raw payloads are retained and
      grow over time; this is the early-warning signal before disk pressure
      becomes an incident.
- [ ] Raw-payload storage stays DB-resident for MS-1d — there is no
      disk-path payload stage in this design, so the dump above is the only
      backup surface that matters today. If a future stage writes payloads
      to disk instead of the database, the CT-116 subvolume holding them
      must be added to restic `BACKUP_PATHS` **before** that stage ships,
      not after.
- [ ] The restore path for the dump above is documented (runbook §18.6) and
      has been read by whoever is about to flip the first source live.

Do not flip any source's `enabled` to `True` until every box above is
checked by an operator against the live system, not from this document.

### Per-source enable procedure

Once the SA-004 gate passes, enable sources one at a time — never all at
once — via a direct SQL `UPDATE` against the `SourceConfig` row (the
ADR-0016 settings-row pattern: an operator-tunable row flipped by `UPDATE`,
not a deploy):

```sql
UPDATE source_config
SET enabled = true
FROM source_site
WHERE source_config.source_site_id = source_site.id
  AND source_site.normalized_name = '<source-normalized-name>';
```

After each flip:

1. Watch `scraper_runs` for that `source_site` until the first run reaches
   `status = 'success'`.
2. Confirm at least one resolved listing from that run has a non-`none`
   grain (check `detail_json` on the run, or the resulting
   `listing_resolution` rows) — a successful run with everything stuck at
   `grain=none` means the catalog resolver isn't matching and should be
   investigated before enabling the next source.
3. Only then proceed to the next source in the list.

Enable order: **ServerPartDeals → goHardDrive → WD → Seagate → eBay.**
eBay is last and, per below, stays blocked after the other four are live.

### eBay go-live block (CR-004) — blocked independent of SA-004

The eBay connector (fetch/parse/persist/heartbeat) ships fully in MS-1d.
Its `enabled=True` flip does **not** ship with it and stays **blocked**,
gated on a separate piece of work, not on the SA-004 checklist above:

- eBay's delete-on-delist obligation (DR-008) requires a Listing-grain
  soft-delete / terminal-state mechanism (mirroring the existing
  `RetentionGoverned` + `is_current` pattern) that does not relax the
  `superseded_by` `PROTECT` on the resolution edge. `Listing` has no such
  field today — this is a schema addition tracked separately (TODO IR-002),
  outside MS-1d's adapter scope.
- The heartbeat's ≤6h TTL bounds how stale an eBay listing can appear to be,
  but TTL expiry is not the delete-on-delist path and does not by itself
  satisfy DR-008.
- ServerPartDeals, goHardDrive, WD, and Seagate gate only on the SA-004
  checklist above. eBay additionally requires the Listing-grain soft-delete
  plan to land and ship before its `enabled=True` flip is in scope.
