import asyncio

import httpx
import pytest

from hw_radar.acquisition.deadman import ENV_VAR, push


def test_push_is_noop_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_VAR, raising=False)
    assert asyncio.run(push()) is False


def test_push_hits_configured_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_VAR, "https://kuma.invalid/api/push/token")
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json={"ok": True})

    async def drive() -> bool:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await push(client=client)

    assert asyncio.run(drive()) is True
    assert seen == ["https://kuma.invalid/api/push/token"]


def test_push_survives_network_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    # The dead-man job must never crash the poller (§18.5: absence alerts off-box).
    monkeypatch.setenv(ENV_VAR, "https://kuma.invalid/api/push/token")

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    async def drive() -> bool:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await push(client=client)

    assert asyncio.run(drive()) is False
