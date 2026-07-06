"""Shared httpx GET with an explicit robots.txt preflight.

httpx bypasses Scrapy's ROBOTSTXT_OBEY, so JSON/API connectors (WD, Seagate,
ServerPartDeals, eBay) MUST route through here to keep the C-007 guardrail
honest. robots.txt is parsed once per host per process (cheap, correctness-first
cache — a long-lived poller re-reads on restart, which is acceptable at this
cadence). store.seagate.com (Disallow: /) is blocked by this, not by convention.
"""

from __future__ import annotations

from urllib.robotparser import RobotFileParser

import httpx

from hw_radar.acquisition.scrapy_support import USER_AGENT as HONEST_UA

# Cache only SUCCESSFUL robots parses (keyed by origin). Unreachable robots
# (5xx / transport error) is NOT cached — a transient outage must be re-checked
# next call, not frozen into a permanent block for the process lifetime.
_ROBOTS_CACHE: dict[str, RobotFileParser] = {}


class RobotsDisallowed(Exception):
    """robots.txt EXPLICITLY disallows the path (persistent). Classifies UNKNOWN
    → pauses the source for human review — correct: we should not poll a path the
    site forbids (e.g. store.seagate.com)."""

    def __init__(self, url: str) -> None:
        super().__init__(f"robots.txt disallows {url}")


class RobotsUnavailable(ConnectionError):
    """robots.txt UNREACHABLE (5xx / network) — RFC 9309 requires complete
    disallow. Subclasses ConnectionError so the existing classify_exception maps
    it to TRANSIENT → the source backs off and retries, rather than fetching
    without permission or pausing."""


async def _robots_for(url: str, *, client: httpx.AsyncClient) -> RobotFileParser | None:
    """Return a parser for the origin's robots rules, or None if UNREACHABLE."""
    parts = httpx.URL(url)
    origin = f"{parts.scheme}://{parts.host}"
    cached = _ROBOTS_CACHE.get(origin)
    if cached is not None:
        return cached
    try:
        resp = await client.get(f"{origin}/robots.txt")
    except httpx.HTTPError:
        return None  # RFC 9309: network-unreachable ⇒ deny (not cached — retry next call)
    if resp.status_code >= 500:
        return None  # RFC 9309: server error ⇒ unreachable ⇒ deny (not cached)
    parser = RobotFileParser()
    # 4xx (incl. 404 = no robots) ⇒ unrestricted; 2xx ⇒ parse the rules.
    parser.parse(resp.text.splitlines() if resp.status_code < 400 else [])
    _ROBOTS_CACHE[origin] = parser
    return parser


async def robots_allows(
    url: str, *, client: httpx.AsyncClient, user_agent: str = HONEST_UA
) -> bool:
    """False when explicitly disallowed OR when robots is unreachable (fail-closed)."""
    parser = await _robots_for(url, client=client)
    return parser is not None and parser.can_fetch(user_agent, url)


async def get(
    url: str,
    *,
    client: httpx.AsyncClient,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    user_agent: str = HONEST_UA,
    check_robots: bool = True,
) -> httpx.Response:
    if check_robots:
        parser = await _robots_for(url, client=client)
        if parser is None:
            raise RobotsUnavailable(f"robots.txt unreachable for {url}")  # transient → backoff
        if not parser.can_fetch(user_agent, url):
            raise RobotsDisallowed(url)  # persistent disallow → never fetch this path
    merged = {"User-Agent": user_agent, **(headers or {})}
    return await client.get(url, params=params, headers=merged)
