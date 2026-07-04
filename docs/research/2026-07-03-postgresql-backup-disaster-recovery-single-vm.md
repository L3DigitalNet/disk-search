---
schema_version: '1.0'
id: 2026-07-03-postgresql-backup-disaster-recovery-single-vm
title: PostgreSQL Backup and Disaster Recovery for a Single Small VM (2026)
description: Pragmatic backup/PITR/offsite strategy for a single Debian 13 PostgreSQL+TimescaleDB VM, comparing pg_dump/pg_basebackup/pgBackRest/Barman/wal-g/pgbackweb, TimescaleDB caveats, Proxmox snapshot limits, and restore-test cadence.
doc_type: research
status: active
created: '2026-07-03'
updated: '2026-07-03'
reviewed: '2026-07-03'
owner: chris
tags:
- postgresql
- timescaledb
- backup
- disaster-recovery
- proxmox
- pgbackrest
aliases:
- postgres backup and DR research
- pg backup strategy single VM
- hw-radar backup research
related: []
source:
- https://pgbackrest.org
- https://www.postgresql.org/docs/current/continuous-archiving.html
- https://www.tigerdata.com/docs/deploy/self-hosted/backup-and-restore
- https://pve.proxmox.com/wiki/VM_Backup_Consistency
- https://lwn.net/Articles/1069951/
confidence: high
visibility: private
license: null
---

# PostgreSQL Backup and Disaster Recovery for a Single Small VM (2026)

## Executive recommendation

Use **pgBackRest** as the primary backup engine, running physical (`pg1-path`) backups plus continuous WAL archiving directly on the Debian 13 VM, with a second repository (`repo2`) pointed at an S3-compatible offsite bucket (Backblaze B2 or a Hetzner Object Storage / Storage Box target) using pgBackRest's built-in `repo2-cipher-*` encryption. This gives PITR (point-in-time recovery to any second, not just to the last nightly snapshot), differential/incremental backups so the offsite transfer stays small even as the time-series table grows, and a config format specifically documented to work correctly with TimescaleDB physical backups (`pg_basebackup`, pgBackRest, and Barman are all listed by TigerData's own docs as supported physical-backup methods with no hypertable-specific caveats) [official](https://www.tigerdata.com/docs/deploy/self-hosted/backup-and-restore/physical).

Treat **plain `pg_dump`/`pg_dumpall`** as a supplementary, not primary, safety net: keep a weekly logical dump as a portable, version-independent copy (useful for major-version upgrades or moving to a different host), but do not rely on it alone for the price-history data — TimescaleDB's own docs warn that `pg_dump` does not preserve hypertable compression state, requires `timescaledb_pre_restore()`/`timescaledb_post_restore()` around the restore, and needs the *same* TimescaleDB extension version on source and target before any extension upgrade [official](https://github.com/timescale/timescaledb/blob/main/sql/restoring.sql).

**Barman is a reasonable second choice**, not overkill exactly, but adds a dedicated backup-server mental model (SSH-based orchestration, its own retention/catalog server) that buys you little extra for one VM with one maintainer — it shines when you're centrally managing backups for *multiple* PostgreSQL servers. **wal-g** is a fine minimalist CLI alternative (no daemon, single static binary, strong cloud-object-storage support) but has thinner docs/tooling around retention policy management than pgBackRest and is explicitly positioned by comparisons as the choice when you "don't need a control plane" — a reasonable substitute if you want less config surface than pgBackRest, but pgBackRest's documented config-file model, WAL retention safety rails, and community size make it the safer default. **pgbackweb** (renaming to "UFO Backup") is explicitly a *web UI wrapper around pgBackRest*, not a competing backup engine — worth adding later purely for the dashboard/monitoring convenience, not instead of pgBackRest [community](https://sourceforge.net/projects/pgbackweb.mirror).

**Overkill for this scale:** a dedicated Barman backup *server* (separate VM/host acting as the backup catalog), Kubernetes-native tools (CloudNativePG's Barman Cloud plugin), and Proxmox Backup Server as your *only* recovery mechanism for the database (see §4 — it is a valuable complementary layer, not a substitute for WAL-level PITR).

## ⚠ Recent-changes flag (important, resolve before committing)

**pgBackRest's maintenance status had a six-week scare in 2026** that is directly relevant to "which tool to bet on." On **27 April 2026**, sole maintainer David Steele archived the pgBackRest GitHub repo and posted a "Notice of Obsolescence," citing loss of employer sponsorship after Crunchy Data was acquired by Snowflake [official](https://lwn.net/Articles/1069951/). On **18 May 2026**, the project reversed course: a six-company sponsor coalition (AWS, Supabase, pgEdge, Tiger Data/Timescale, Percona, and Eon.io) funded continued maintenance, and Steele resumed work under "pgBackRest Will Continue!" [official](https://pgbackrest.org). As of this research (3 July 2026, roughly six weeks after the resolution), pgBackRest v2.58.0 is the current stable release and the project page shows active maintenance news. Net: pgBackRest is a safe default again, and notably one of its new sponsors is Tiger Data (Timescale) itself — but this is recent enough (six weeks) that it's worth a calendar reminder to re-check `pgbackrest.org` news in another few months before treating the coalition as durable.

## 1. Backup method comparison

| Method | Setup complexity | Restore capability | Operational weight (1 VM) | Verdict |
| --- | --- | --- | --- | --- |
| `pg_dump`/`pg_dumpall` | Trivial (one cron line) | Point-in-time-of-dump only; portable across PG versions | Very low | Keep as supplementary weekly/monthly export, not primary |
| `pg_basebackup` + manual WAL archiving | Low-moderate (hand-roll `archive_command`, retention, cleanup) | Full PITR | Low-moderate, but you own all the failure-mode plumbing (archive gaps, disk fill, retention pruning) | Viable DIY path but pgBackRest gives you the same result with less hand-rolled scripting |
| **pgBackRest** | Moderate (one config file, one stanza) | Full PITR; full/diff/incr backups; multi-repo (local + S3/Azure/GCS/SFTP) with built-in encryption | Low once configured — single binary, cron-driven | **Recommended default** |
| Barman | Moderate-high (Python service, SSH trust, its own retention/catalog model) | Full PITR; designed for centralized multi-server management | Moderate — a "backup server" concept even for one target | Reasonable, but heavier than needed for one VM |
| wal-g | Low-moderate (single static binary, env-var config) | Full PITR; strong native S3/GCS/Azure support | Low | Good minimalist alternative to pgBackRest |
| pgbackweb / UFO Backup | Low (Docker container + web UI) | Delegates actual backup/restore to pgBackRest under the hood | Low, adds a UI layer | Nice-to-have dashboard on top of pgBackRest, not a replacement |
| pg_probackup | Moderate | Full PITR, synthetic full backups from incrementals | Moderate | Only worth it if you specifically want synthetic-full compression savings; niche pick |

Sources: pgBackRest official docs and config reference [official](https://pgbackrest.org); PostgreSQL continuous-archiving/PITR docs [official](https://www.postgresql.org/docs/current/continuous-archiving.html); tool comparison articles [community](https://www.bytebase.com/blog/top-open-source-postgres-backup-solution), [community](https://www.kunalganglani.com/blog/postgresql-backup-tools-compared).

## 2. TimescaleDB-specific considerations

- **Physical backups (pg_basebackup, pgBackRest, Barman) need no special TimescaleDB handling.** TigerData's own current docs list all three as supported physical-backup methods for a "full instance" backup, with no hypertable/compression caveats — this is the path of least surprise for the price-history hypertable [official](https://www.tigerdata.com/docs/deploy/self-hosted/backup-and-restore/physical).
- **Logical backups (pg_dump/pg_restore) have three documented footguns**, corroborated by the TimescaleDB source and TigerData docs directly:
  1. Compression is **not preserved** through a logical dump — compressed chunks come back as regular rows and must be re-compressed (or explicitly `decompress_chunk`'d then recompressed) after restore, per TimescaleDB's own test suite pattern [official](https://github.com/timescale/timescaledb/blob/main/tsl/test/sql/include/compression_test_hypertable.sql).
  2. You **must** wrap the restore with `timescaledb_pre_restore()` / `timescaledb_post_restore()` to disable background workers during the load, or the restore can race with TimescaleDB's own job scheduler [official](https://github.com/timescale/timescaledb/blob/main/sql/restoring.sql).
  3. `pg_dump` does not record the TimescaleDB extension version, so you must restore into an instance running the **same** extension version as the source before running any `ALTER EXTENSION ... UPDATE` — restoring straight into a newer extension version can skip needed upgrade migrations [official, current TigerData docs](https://www.tigerdata.com/docs/deploy/self-hosted/backup-and-restore/logical-backup).
- Continuous aggregates are ordinary materialized views under the hood and are backed up/restored along with the schema in both physical and logical paths; no extra caveat surfaced beyond the general recommendation to let refresh jobs re-populate them after a restore rather than assuming aggregate freshness at restore time.
- **Practical takeaway for this project:** because the design intent is "logical backup as supplementary export," if you do lean on `pg_dumpall` occasionally, script the pre/post-restore function calls and don't assume compression survives the round trip — treat every `pg_dump` restore as "restore, then re-run your compression/retention policies."

## 3. Off-box / offsite targets

- **3-2-1 (or 3-2-1-1-0) at hobby scale, minimum viable version:** (1) the live DB on the VM, (2) a local pgBackRest repo or nightly dump on a *different* Proxmox-host disk/dataset than the VM's own storage, (3) an encrypted copy pushed to object storage in a different physical location (Hetzner Storage Box or B2/S3). The "0" (verified restorable) matters more than the "1" (immutable) at this scale — see §5.
- **Object storage options, ranked for this use case:**
  - **Hetzner Storage Box** — cheapest if you're already a Hetzner customer, reachable over SSH/SFTP/rclone/restic from the same Hetzner network (fast, no egress cost concerns for a Hetzner-hosted VM); community guides document rclone+restic and even append-only repo setups against it, though Hetzner's own Storage Box docs are noted as thin [community](https://kcore.org/2023/02/01/hetzner-storagebox-backups), [community](https://fluix.one/blog/hetzner-restic-append-only). pgBackRest also supports SFTP repos natively (`repo-type=sftp`), so it can push directly to a Storage Box without an extra rclone hop [official](https://pgbackrest.org) (config reference, `repo5-type=sftp` example).
  - **S3-compatible / Backblaze B2** — pgBackRest, wal-g, and restic all speak S3 natively; B2 and most S3-compatible providers now support **Object Lock / WORM** for ransomware-resistant immutability on at least one copy, which is worth enabling on whichever tier holds your offsite copy [official](https://www.backblaze.com/blog/lifecycle-rules-now-supported-through-s3-compatible-apis/).
  - **Encryption at rest:** don't rely on the provider's server-side encryption alone — encrypt client-side before/while it leaves the VM. pgBackRest has this built in (`repo-cipher-type=aes-256-cbc`, `repo-cipher-pass`), so the offsite repo is encrypted end-to-end without a separate tool.
- **Retention/rotation sketch (single maintainer, moderate volume):** full backup weekly, differential daily, WAL continuously archived, local repo retains ~2 full backups, offsite repo retains ~4 full backups (roughly a month), with `repo-retention-full-type=time` so pruning is calendar-based rather than count-based and doesn't surprise you when backup cadence changes.

## 4. Proxmox VM-level backups vs in-DB backups

- **vzdump/Proxmox Backup Server snapshots are a valuable complement, not a substitute, for pg-level backups — and by default they are only crash-consistent, not application-consistent**, for a running database. Proxmox's own wiki is explicit: application/filesystem consistency at snapshot time depends entirely on the **QEMU Guest Agent** performing an `fsfreeze`/`fsthaw` around the snapshot; without the guest agent (or with "Freeze/thaw guest filesystems on backup for consistency" disabled), you get the equivalent of "pulling the power cable" — the guest filesystem journal will replay on boot, but the database is not guaranteed to be in the state PostgreSQL itself considers consistent unless PostgreSQL's own crash-recovery (WAL replay) can recover from it [official](https://pve.proxmox.com/wiki/VM_Backup_Consistency). This is corroborated independently by the Proxmox `vzdump` chapter's documented consistency/downtime tradeoff modes [official](https://pve.proxmox.com/pve-docs/chapter-vzdump.html) and by multiple community threads describing the same freeze/thaw dependency [community](https://forum.proxmox.com/threads/inconsistent-snapshots-of-running-vm.9200), [community](https://www.reddit.com/r/Proxmox/comments/129gvhv/are_proxmox_backups_database_safe).
- In practice this is *usually fine for PostgreSQL specifically*, because PostgreSQL is designed to recover from a crash-consistent state via WAL replay on next start (the same guarantee that protects you from an actual power outage) — but it is **not** equivalent to PITR: a VM snapshot only gives you the state at snapshot time, with no ability to roll forward/back to an arbitrary second, and if the snapshot lands mid-write in a way the fsfreeze didn't fully quiesce, you're depending on PostgreSQL's crash recovery working correctly rather than on an application-consistent backup.
- **Recommendation:** enable QEMU Guest Agent with filesystem freeze/thaw on the VM (cheap, already built into Proxmox VE), and keep vzdump/PBS running on its normal schedule as your **VM-disaster recovery layer** (rebuild the whole VM fast after host failure, hardware loss, or a botched OS-level change) — but keep pgBackRest's PITR as the **data-recovery layer** (recover from "I deleted rows two hours ago" or "corruption crept in over several days," neither of which a nightly VM snapshot alone can surgically fix).

## 5. Restore testing

- **The corroborated consensus across official and community guidance is the same:** an untested backup is not a backup; RPO/RTO should be defined explicitly, and restore drills should be automated and scheduled, not manual and occasional [community](https://dev.to/dean_dautovich/13-postgresql-backup-best-practices-for-developers-and-dbas-3oi5), [community](https://oneuptime.com/blog/post/2026-01-21-postgresql-backup-testing/view).
- **Concrete cadence for a single-maintainer hobby/small-business setup:**
  - **Weekly (automated, cheap):** verify the latest pgBackRest backup with `pgbackrest check`/`verify` and confirm WAL archiving has no gaps (`pgbackrest info`), plus confirm the offsite repo received the expected objects.
  - **Monthly (automated, semi-heavy):** spin up a throwaway VM/container, run `pgbackrest restore` (or `pg_basebackup` + WAL replay) against it, and run a handful of sanity queries against the price-history hypertable (row counts, latest timestamp, a known historical value) — this is the step that actually proves recoverability, not just "the file exists."
  - **Quarterly (manual, PITR-specific):** perform an actual point-in-time restore to a timestamp a few hours before a synthetic "incident," confirming the recovery target works end-to-end (this is the drill most teams skip and the one most likely to reveal a broken `restore_command` or missing WAL segment).
- Reddit/community practitioner threads describe essentially the same pattern at small scale — spin up a same-sized VM, restore, and check the app boots against it [community](https://www.reddit.com/r/PostgreSQL/comments/1h9qr9u/how_do_you_test_your_backups).

## Backup + offsite + retention sketch (concrete default)

```
[Debian 13 VM]
  postgresql.conf: archive_mode=on, archive_command -> pgbackrest archive-push
  pgBackRest stanza "hwradar":
    repo1 (local disk, different volume than PGDATA): retention-full=2, type=time
    repo2 (S3-compatible: B2 or Hetzner object storage): retention-full=4 (~1 month), cipher=aes-256-cbc

  Cron:
    daily 02:00  -> pgbackrest --type=diff backup   (weekdays)
    weekly Sun   -> pgbackrest --type=full backup
    continuous   -> WAL archive-push (async)
    weekly       -> pgbackrest check / verify + offsite object-count sanity check

  Proxmox layer (complementary, not PITR):
    QEMU Guest Agent installed + freeze/thaw enabled
    vzdump/PBS nightly VM-level backup, kept separately from the pgBackRest repo
```

## Sources

| URL | Title | Date | Authority |
| --- | ----- | ---- | --------- |
| https://pgbackrest.org | pgBackRest - Reliable PostgreSQL Backup & Restore | 2026-06-22 (updated) | official |
| https://pgbackrest.org (via Context7 /pgbackrest/pgbackrest) | pgBackRest config/backup/restore reference | current | official |
| https://www.postgresql.org/docs/current/continuous-archiving.html | PostgreSQL: Continuous Archiving and PITR | current | official |
| https://www.postgresql.org/support/security/CVE-2025-8714/ | CVE-2025-8714: pg_dump arbitrary code execution on restore | 2026 | official |
| https://www.postgresql.org/about/news/postgresql-176-1610-1514-1419-1322-and-18-beta-3-released-3118/ | PostgreSQL 17.6/16.10/etc security release notes | 2026 | official |
| https://www.heise.de/en/news/PostgreSQL-Updates-patch-high-risk-security-vulnerabilities-11297673.html | PostgreSQL patches high-risk CVEs (pg_basebackup/pg_rewind symlink, CVE-2026-6473/75/77, CVE-2026-6637) | 2026 | community (reporting on official advisories) |
| https://www.tigerdata.com/docs/deploy/self-hosted/backup-and-restore/physical | Physical backups \| Tiger Data Docs | current | official |
| https://www.tigerdata.com/docs/deploy/self-hosted/backup-and-restore/logical-backup | Logical backup with pg_dump and pg_restore \| Tiger Data Docs | current | official |
| https://github.com/timescale/timescaledb/blob/main/sql/restoring.sql | timescaledb_pre_restore/post_restore functions | current | official |
| https://github.com/timescale/timescaledb/blob/main/tsl/test/sql/include/compression_test_hypertable.sql | Compression not preserved through dump/restore | current | official |
| https://www.tigerdata.com/legal/licenses | TimescaleDB / Tiger Data licensing (TSL vs Apache-2) | current | official |
| https://pve.proxmox.com/wiki/VM_Backup_Consistency | VM Backup Consistency - Proxmox VE | current | official |
| https://pve.proxmox.com/pve-docs/chapter-vzdump.html | Backup and Restore (vzdump) - Proxmox VE docs | current | official |
| https://forum.proxmox.com/threads/inconsistent-snapshots-of-running-vm.9200 | Inconsistent snapshots of running VM | n/a | community |
| https://www.reddit.com/r/Proxmox/comments/129gvhv/are_proxmox_backups_database_safe | Are Proxmox backups database safe? | 2026 | community |
| https://lwn.net/Articles/1069951/ | pgBackRest is no longer maintained | 2026-04-27 | official (LWN reporting, quotes maintainer directly) |
| https://percona.community/blog/2026/04/28/pgbackrest-is-archived-what-now/ | pgBackRest is archived, what now? | 2026-04-28 | official (Percona) |
| https://percona.community/blog/2026/05/19/backrests-back-alright/ | Backrest's back, alright! | 2026-05-19 | official (Percona) |
| https://mydbanotebook.org/posts/pgbackrest-is-dead.-now-what/ | pgBackRest is dead. Now what? (with 2026-05-19 correction) | 2026-04/05 | community |
| https://groundy.com/articles/pgbackrest-is-no-longer-maintained-postgresql-backup-alternatives-after/ | pgBackRest alternatives after the stall, incl. coalition timeline | 2026 | blog |
| https://www.bytebase.com/blog/top-open-source-postgres-backup-solution | Top Open-Source Postgres Backup Solutions in 2026 | 2026 | community |
| https://www.kunalganglani.com/blog/postgresql-backup-tools-compared | PostgreSQL Backup Tools Compared: pgBackRest, Barman, pg_probackup | 2026 | blog |
| https://sourceforge.net/projects/pgbackweb.mirror | pgBackWeb (web UI for pgBackRest) | current | community |
| https://kcore.org/2023/02/01/hetzner-storagebox-backups | Using Hetzner Storageboxes as backup targets for Restic/Rclone | 2023 (still cited 2026) | community |
| https://www.backblaze.com/blog/lifecycle-rules-now-supported-through-s3-compatible-apis/ | Backblaze B2 lifecycle rules via S3-compatible API (Object Lock context) | 2026 | official (Backblaze) |
| https://dev.to/dean_dautovich/13-postgresql-backup-best-practices-for-developers-and-dbas-3oi5 | 13 PostgreSQL Backup Best Practices | 2026 | blog |
| https://oneuptime.com/blog/post/2026-01-21-postgresql-backup-testing/view | How to Test PostgreSQL Backup Restoration | 2026-01-21 | blog |
| https://www.reddit.com/r/PostgreSQL/comments/1h9qr9u/how_do_you_test_your_backups | How do you test your backups? | n/a | community |
| https://www.alessioligabue.it/en/blog/install-postgresql-debian-13 | Debian 13 ships PostgreSQL 17 by default | 2026 | blog |
| https://www.postgresql.org/download/linux/debian | PostgreSQL: Linux downloads (Debian) / PGDG apt repo | current | official |
