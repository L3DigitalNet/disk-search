from decimal import Decimal

from hw_radar.acquisition.heartbeat import HeartbeatReading, decide, fingerprint
from hw_radar.catalog.models import HeartbeatDecision


def _r(price: str, stock: str, ship: str | None = None) -> HeartbeatReading:
    return HeartbeatReading(
        source_sku="SKU1",
        price=Decimal(price),
        currency="USD",
        stock_status=stock,
        shipping_price=Decimal(ship) if ship else None,
        http_status=200,
        latency_ms=42,
        endpoint="x",
    )


def test_identical_is_unchanged() -> None:
    r = _r("100.00", "in_stock")
    assert decide(r, _r("100.00", "in_stock")) is HeartbeatDecision.UNCHANGED


def test_first_sighting_is_transition() -> None:
    assert decide(None, _r("100.00", "in_stock")) is HeartbeatDecision.TRANSITION_DETECTED


def test_oos_to_in_stock_is_transition() -> None:
    assert (
        decide(_r("100.00", "out_of_stock"), _r("100.00", "in_stock"))
        is HeartbeatDecision.TRANSITION_DETECTED
    )


def test_price_drop_is_transition() -> None:
    assert (
        decide(_r("100.00", "in_stock"), _r("80.00", "in_stock"))
        is HeartbeatDecision.TRANSITION_DETECTED
    )


def test_unknown_stock_is_ambiguous() -> None:
    assert decide(_r("100.00", "in_stock"), _r("100.00", "unknown")) is HeartbeatDecision.AMBIGUOUS


def test_failed_fetch_is_failed() -> None:
    assert decide(_r("100.00", "in_stock"), None) is HeartbeatDecision.FAILED


def test_fingerprint_stable_and_sensitive() -> None:
    a = fingerprint(price=Decimal("100.00"), currency="USD", stock_status="in_stock", shipping=None)
    assert a == fingerprint(
        price=Decimal("100.00"), currency="USD", stock_status="in_stock", shipping=None
    )
    assert a != fingerprint(
        price=Decimal("80.00"), currency="USD", stock_status="in_stock", shipping=None
    )
