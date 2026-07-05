#!/usr/bin/env bash
# Runs on the CT, invoked by deploy.yml over Tailscale SSH after rsync.
set -euo pipefail

cd /opt/hw-radar/app

export PATH="$HOME/.local/bin:$PATH"

export HW_RADAR_ENV=production
set -a
# Secrets come only from the bao-agent tmpfs render (ADR-0009), never a file at rest.
# The deploy SSH user must have read access to this render (group membership on
# /run/bao-agent — see docs/runbooks/provisioning.md) or `source` fails closed here.
# shellcheck disable=SC1091  # rendered at runtime by bao-agent (ADR-0009)
source /run/bao-agent/hw-radar.env
set +a

uv python install
uv sync --frozen --no-dev

# .venv/bin/python directly, NOT `uv run`: `uv run` re-resolves and would sync the
# dev dependency group back into the production venv (CR-NEW-001). `--frozen --no-dev`
# above builds a prod-only venv; invoking its interpreter directly keeps it that way.
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py collectstatic --noinput
sudo -n /usr/bin/systemctl restart hw-radar-web.service hw-radar-poller.service
