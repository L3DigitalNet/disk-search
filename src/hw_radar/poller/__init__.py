"""Poller package — deliberately import-light.

`python -m hw_radar.poller` makes runpy import THIS package (to locate
`__main__`) before `__main__.py` runs `django.setup()`. So the package root
must carry no Django-dependent imports at module load — the ORM-touching
implementation lives in `service.py`, imported by `__main__.py` only after
Django is configured (and by tests, where pytest-django configures settings
during collection). Keep this file free of heavy imports; import from
`hw_radar.poller.service`, not from the package root.
"""

from __future__ import annotations
