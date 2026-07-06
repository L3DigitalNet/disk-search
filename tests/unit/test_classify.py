import httpx
import pytest

from hw_radar.acquisition.classify import classify_exception, classify_response
from hw_radar.catalog.models import RunFailureClass


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (500, RunFailureClass.TRANSIENT),
        (502, RunFailureClass.TRANSIENT),
        (504, RunFailureClass.TRANSIENT),
        (408, RunFailureClass.TRANSIENT),
        (401, RunFailureClass.ANTI_BOT),
        (403, RunFailureClass.ANTI_BOT),
        (429, RunFailureClass.ANTI_BOT),
        (503, RunFailureClass.ANTI_BOT),  # §12.1 puts 503 in the anti_bot family
    ],
)
def test_status_classification(status: int, expected: RunFailureClass) -> None:
    assert (
        classify_response(
            http_status=status,
            content_type="text/html",
            expected_json=False,
            body_text="",
            median_body_bytes=None,
        )
        == expected
    )


def test_json_endpoint_answering_html_is_anti_bot() -> None:
    # ERR-002: a JSON endpoint returning text/html is a challenge interstitial.
    verdict = classify_response(
        http_status=200,
        content_type="text/html",
        expected_json=True,
        body_text="<html>checking your browser</html>",
        median_body_bytes=None,
    )
    assert verdict == RunFailureClass.ANTI_BOT


def test_challenge_markers_reclassify_a_200() -> None:
    verdict = classify_response(
        http_status=200,
        content_type="text/html",
        expected_json=False,
        body_text="<script src='/cdn-cgi/challenge-platform/x.js'></script>",
        median_body_bytes=None,
    )
    assert verdict == RunFailureClass.ANTI_BOT


def test_body_size_outlier_is_soft_block() -> None:
    # EC-007: HTTP 200 but <20% of the rolling median body size.
    verdict = classify_response(
        http_status=200,
        content_type="text/html",
        expected_json=False,
        body_text="x" * 100,
        median_body_bytes=10_000,
    )
    assert verdict == RunFailureClass.ANTI_BOT


def test_healthy_200_returns_none() -> None:
    assert (
        classify_response(
            http_status=200,
            content_type="application/json",
            expected_json=True,
            body_text='{"items": []}' * 100,
            median_body_bytes=1000,
        )
        is None
    )


def test_network_exceptions_are_transient() -> None:
    assert classify_exception(TimeoutError()) == RunFailureClass.TRANSIENT
    assert classify_exception(OSError("dns")) == RunFailureClass.TRANSIENT


@pytest.mark.parametrize(
    "exc",
    [
        # httpx.TransportError is the base for every transport-layer failure and
        # derives from httpx.HTTPError(Exception), NOT OSError/ConnectionError —
        # so without an explicit rule these would fall through to UNKNOWN and
        # pause the source for manual review instead of backing off (CR-003).
        httpx.ConnectError("refused"),
        httpx.ReadTimeout("slow"),
        httpx.ConnectTimeout("slow"),
        httpx.PoolTimeout("pool"),
        httpx.RemoteProtocolError("bad frame"),
    ],
)
def test_httpx_transport_errors_are_transient(exc: httpx.TransportError) -> None:
    assert classify_exception(exc) is RunFailureClass.TRANSIENT


def test_unexpected_exception_is_unknown() -> None:
    assert classify_exception(ValueError("boom")) == RunFailureClass.UNKNOWN


@pytest.mark.parametrize("status", [404, 451])
def test_unmapped_error_status_falls_through_to_unknown(status: int) -> None:
    # §12.1 fall-through: a >=400 status not in TRANSIENT/ANTI_BOT with clean
    # content isn't a recognized failure family, so it escalates as UNKNOWN.
    verdict = classify_response(
        http_status=status,
        content_type="text/html",
        expected_json=False,
        body_text="<html>not found</html>",
        median_body_bytes=None,
    )
    assert verdict == RunFailureClass.UNKNOWN
