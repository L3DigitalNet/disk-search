"""Adapter registry: site_key → adapter factory. MS-1d connectors register here."""

from collections.abc import Callable

from hw_radar.acquisition.contracts import SourceAdapter
from hw_radar.acquisition.sources.demo import DemoAdapter

ADAPTERS: dict[str, Callable[[], SourceAdapter]] = {
    "demo": DemoAdapter,
}
