# Runbook: CT provisioning for MS-0 (operator, one-time)

Live values (CT ID, addresses, CIDR, issuer script paths) live in the private
`homelab` repo. This checklist is the public-safe contract.

1. **CT:** Debian 13 LXC per spec §18.1: 2 vCPU, 4 GiB RAM, 32 GiB rootfs, 512 MiB swap. It appears in `pct list` for auto-monitoring.
2. **Packages:** nginx, certbot + python3-certbot-nginx, PostgreSQL from PGDG, TimescaleDB Community (TSL) from Timescale's packagecloud repo, Tailscale with Tailscale SSH enabled, and uv for deploy/app users.
3. **Users:** `hwradar` app user and `deploy` CI target user. Put `deploy` in group `hwradar`; app dir `/opt/hw-radar/app` owned `deploy:hwradar`. Sudoers: `deploy ALL=(root) NOPASSWD: /usr/bin/systemctl restart hw-radar-web.service hw-radar-poller.service`.
4. **Database bootstrap:** create role/database `hw_radar`, then create extensions `timescaledb` and `pg_trgm` in the DB. App migrations use `IF NOT EXISTS` so these no-op after provisioning.
5. **bao-agent:** onboard as the next `bao-services` consumer per the homelab runbook. The agent renders `DJANGO_SECRET_KEY`, `HW_RADAR_DB_PASSWORD`, and DB identifiers if needed to `/run/bao-agent/hw-radar.env` as `root:hwradar 0640`.
6. **systemd:** copy `deploy/systemd/*.service` to `/etc/systemd/system/`, run `systemd-analyze verify /etc/systemd/system/hw-radar-*.service`, then `systemctl daemon-reload && systemctl enable hw-radar-web hw-radar-poller`.
7. **nginx + TLS:** install `deploy/nginx/hw-radar.conf`, run `nginx -t`, point DNS for `hw-radar.l3digital.net`, then run `certbot --nginx`.
8. **GitHub:** create Environment `production` with required reviewer. Environment secrets: `TS_OAUTH_CLIENT_ID`, `TS_OAUTH_SECRET`, `DEPLOY_HOST`, `DEPLOY_USER`.
9. **Tailnet ACL:** ensure `tag:ci` can reach the CT over SSH; add the explicit grant when the scoped-ACL migration lands.
10. **Owner account:** after first deploy, run `uv run python manage.py createsuperuser` on the CT with a password of at least 16 characters.
11. **Backups:** wire the CT subvolume into restic and a TimescaleDB-aware dump block before first real data; keep restore-test discipline.
12. **Consumer AppRole CIDR bind:** include the CT address and verify OpenBao reachability from the CT.
