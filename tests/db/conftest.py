# pyright: reportUnusedFunction=false
# The autouse fixture below is discovered by pytest via its @fixture decorator and
# never referenced by name; strict pyright (failOnWarnings) can't see that use.
"""DB-test fixtures.

Scoped to ``tests/db/`` on purpose: the async-connection cleanup below depends on
``django_db_setup``, so placing it here (not at ``tests/``) keeps pure-unit runs
(``tests/unit/``) from being forced to stand up the test database.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from typing import TYPE_CHECKING

import pytest
from asgiref.sync import sync_to_async
from django.db import connections

if TYPE_CHECKING:
    from pytest_django.fixtures import DjangoDbBlocker


@pytest.fixture(scope="session", autouse=True)
def _close_sync_to_async_connection(
    django_db_setup: object, django_db_blocker: DjangoDbBlocker
) -> Iterator[None]:
    """Close the DB connection that ``sync_to_async`` leaks in its executor thread.

    Transactional async tests (``run_source``/``refresh_daily`` etc.) drive ORM
    writes through ``sync_to_async``, whose default ``thread_sensitive=True`` funnels
    every call through ONE process-wide executor thread. Django opens a connection in
    that thread on first ORM access and only closes connections at request boundaries
    — of which there are none here — so that single connection survives to session
    teardown and blocks pytest-django's ``DROP DATABASE`` ("being accessed by other
    users"). Close it from inside that same thread (via ``sync_to_async``) before the
    drop. Depending on ``django_db_setup`` makes this finalizer run first (LIFO).
    """
    yield

    async def _close() -> None:
        await sync_to_async(connections.close_all)()

    with django_db_blocker.unblock():
        asyncio.run(_close())
