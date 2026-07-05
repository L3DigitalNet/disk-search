#!/usr/bin/env bash
# Runs on the CT, invoked by deploy.yml over Tailscale SSH after rsync.
set -euo pipefail

cd /opt/hw-radar/app

export PATH="$HOME/.local/bin:$PATH"

export HW_RADAR_ENV=production
set -a
# shellcheck disable=SC1091  # rendered at runtime by bao-agent (ADR-0009)
source /run/bao-agent/hw-radar.env
set +a

uv python install
uv sync --frozen --no-dev

.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py collectstatic --noinput
sudo -n /usr/bin/systemctl restart hw-radar-web.service hw-radar-poller.service
