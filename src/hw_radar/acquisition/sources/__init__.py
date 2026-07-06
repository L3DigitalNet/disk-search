"""Adapter registry: site_key → adapter factory. MS-1d connectors register here."""

from collections.abc import Callable

from hw_radar.acquisition.contracts import SourceAdapter
from hw_radar.acquisition.sources.demo import DemoAdapter
from hw_radar.acquisition.sources.ebay import EbayAdapter
from hw_radar.acquisition.sources.goharddrive import GoHardDriveAdapter
from hw_radar.acquisition.sources.seagate import SeagateAdapter
from hw_radar.acquisition.sources.serverpartdeals import ServerPartDealsAdapter
from hw_radar.acquisition.sources.wd import WdAdapter

ADAPTERS: dict[str, Callable[[], SourceAdapter]] = {
    "demo": DemoAdapter,
    "ebay": EbayAdapter,
    "goharddrive": GoHardDriveAdapter,
    "seagate-recertified": SeagateAdapter,
    "serverpartdeals": ServerPartDealsAdapter,
    "wd-recertified": WdAdapter,
}
