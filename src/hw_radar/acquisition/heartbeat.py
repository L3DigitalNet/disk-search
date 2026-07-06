"""ADR-0015 heartbeat: cheap variant/SKU-grain availability fingerprinting.

Pure logic here (fingerprint + decide) is table-tested with no DB. The DB-facing
run_heartbeat (writes observations, dual-writes events, fires the full pipeline
on transition) lands in the poller task (D1)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from hw_radar.catalog.models import HeartbeatDecision

_UNKNOWN_STOCK = {"", "unknown"}


@dataclass(frozen=True)
class HeartbeatReading:
    source_sku: str
    price: Decimal | None
    currency: str
    stock_status: str
    shipping_price: Decimal | None
    http_status: int
    latency_ms: int | None
    endpoint: str


def fingerprint(
    *, price: Decimal | None, currency: str, stock_status: str, shipping: Decimal | None
) -> str:
    basis = f"{price}|{currency}|{stock_status}|{shipping}"
    return hashlib.sha256(basis.encode()).hexdigest()


def _fp(r: HeartbeatReading) -> str:
    return fingerprint(
        price=r.price, currency=r.currency, stock_status=r.stock_status, shipping=r.shipping_price
    )


def decide(
    prev: HeartbeatReading | None, new: HeartbeatReading | None, *, price_drop_pct: float = 0.0
) -> HeartbeatDecision:
    if new is None:
        return HeartbeatDecision.FAILED
    if new.stock_status in _UNKNOWN_STOCK:
        return HeartbeatDecision.AMBIGUOUS
    if prev is None:
        return HeartbeatDecision.TRANSITION_DETECTED  # baseline sighting fires the pipeline once
    if _fp(prev) == _fp(new):
        return HeartbeatDecision.UNCHANGED
    if prev.stock_status != new.stock_status:
        return HeartbeatDecision.TRANSITION_DETECTED
    if prev.price is not None and new.price is not None and new.price < prev.price:
        drop = float((prev.price - new.price) / prev.price)
        if drop >= price_drop_pct:  # default 0.0 ⇒ any drop is material
            return HeartbeatDecision.TRANSITION_DETECTED
    return HeartbeatDecision.UNCHANGED  # price rose / non-material change ⇒ no snapshot


class HeartbeatProbe(Protocol):
    """A source adapter that also exposes a cheap availability probe.
    heartbeat_enabled sources implement this alongside SourceAdapter."""

    site_key: str

    async def probe(self) -> list[HeartbeatReading]: ...
