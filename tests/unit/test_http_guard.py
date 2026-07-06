import asyncio

import httpx
import pytest

from hw_radar.acquisition.http import (
    _ROBOTS_CACHE,  # pyright: ignore[reportPrivateUsage]
    RobotsDisallowed,
    RobotsUnavailable,
    get,
    robots_allows,
)

DISALLOW_ALL = "User-agent: *\nDisallow: /\n"
ALLOW = "User-agent: *\nDisallow: /admin\n"


@pytest.fixture(autouse=True)
def clear_robots_cache() -> None:
    # _ROBOTS_CACHE is process-global (keyed by origin); without clearing it a
    # successful parse cached by one test would silently short-circuit robots
    # fetches in a later test that expects a different robots_status/transport.
    _ROBOTS_CACHE.clear()


def _transport(
    *,
    robots_status: int,
    robots_body: str = "",
    robots_raises: bool = False,
    target_hits: dict[str, int] | None = None,
) -> httpx.MockTransport:
    """robots_status drives the /robots.txt response; a non-/robots.txt path
    returns 200 {"ok": true}. robots_raises simulates a network transport error.

    target_hits, when given, is incremented on every non-/robots.txt request so
    fail-closed tests can assert the target was never fetched (not merely that
    get() raised) — a handler that always answers 200 can't otherwise
    distinguish "target blocked" from "target errored"."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            if robots_raises:
                raise httpx.ConnectError("robots unreachable")
            return httpx.Response(robots_status, text=robots_body)
        if target_hits is not None:
            target_hits["count"] = target_hits.get("count", 0) + 1
        return httpx.Response(200, json={"ok": True})

    return httpx.MockTransport(handler)


def test_explicit_disallow_raises() -> None:
    tr = _transport(robots_status=200, robots_body=DISALLOW_ALL)

    async def drive() -> None:
        async with httpx.AsyncClient(transport=tr) as c:
            with pytest.raises(RobotsDisallowed):
                await get("https://store.seagate.com/graphql", client=c)

    asyncio.run(drive())


def test_allowed_path_fetches() -> None:
    tr = _transport(robots_status=200, robots_body=ALLOW)

    async def drive() -> httpx.Response:
        async with httpx.AsyncClient(transport=tr) as c:
            return await get("https://serverpartdeals.com/collections/x/products.json", client=c)

    resp = asyncio.run(drive())
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_robots_404_is_unrestricted() -> None:  # RFC 9309: 4xx => allow
    tr = _transport(robots_status=404)

    async def drive() -> httpx.Response:
        async with httpx.AsyncClient(transport=tr) as c:
            return await get("https://api.westerndigital.com/x/products", client=c)

    resp = asyncio.run(drive())
    assert resp.status_code == 200


def test_robots_503_denies_and_does_not_fetch_target() -> None:  # RFC 9309: 5xx => deny
    target_hits: dict[str, int] = {}
    tr = _transport(robots_status=503, target_hits=target_hits)

    async def drive() -> bool:
        async with httpx.AsyncClient(transport=tr) as c:
            with pytest.raises(RobotsUnavailable):
                await get("https://serverpartdeals.com/x/products.json", client=c)
            return await robots_allows("https://serverpartdeals.com/x", client=c)

    allowed = asyncio.run(drive())
    assert allowed is False
    assert target_hits.get("count", 0) == 0


def test_robots_network_error_denies() -> None:  # RFC 9309: unreachable => deny
    target_hits: dict[str, int] = {}
    tr = _transport(robots_status=200, robots_raises=True, target_hits=target_hits)

    async def drive() -> None:
        async with httpx.AsyncClient(transport=tr) as c:
            with pytest.raises(RobotsUnavailable):
                await get("https://serverpartdeals.com/x/products.json", client=c)

    asyncio.run(drive())
    assert target_hits.get("count", 0) == 0
