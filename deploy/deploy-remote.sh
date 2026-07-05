#!/usr/bin/env bash
# Runs on the CT, invoked by deploy.yml over Tailscale SSH after rsync.
set -euo pipefail

cd /opt/hw-radar/app

export PATH="$HOME/.local/bin:$PATH"

# uv-managed interpreters + cache must live OUTSIDE /home: the web/poller units
# run as hwradar with ProtectHome=true, and uv builds .venv/bin/python as a symlink
# to the managed interpreter. Under the deploy user's default ~/.local/share/uv,
# that target is hidden from hwradar's namespace and the service fails to exec.
# /opt/uv is created deploy:hwradar 0755 at provisioning (docs/runbooks/provisioning.md).
export UV_PYTHON_INSTALL_DIR=/opt/uv/python
export UV_CACHE_DIR=/opt/uv/cache

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
