# Seeds the five MS-1 sources + the demo walking-skeleton source. All disabled;
# MS-1d enables each as its connector lands, flips heartbeat_enabled where a cheap
# signal is verified (WD/Seagate/SPD/eBay), and fast_lane strictly per FR-002
# (WD/Seagate/eBay only — SPD is churning, never fast-laned; design 3 matrix).
# Cadence numbers are OQ9-provisional tunables (spec C.2).
from django.db import migrations

SOURCES = [
    # (name, normalized_name, source_type, tier, domain, baseline_s, ceiling_s,
    #  volatility, cheap_signal)
    (
        "WD Recertified Store",
        "wd-recertified",
        "manufacturer_store",
        "t1",
        "www.westerndigital.com",
        1800,
        300,
        "drop_prone",
        "occ_json",
    ),
    (
        "Seagate Recertified Store",
        "seagate-recertified",
        "manufacturer_store",
        "t1",
        "www.seagate.com",
        1800,
        300,
        "drop_prone",
        "bootstrap_json",
    ),
    (
        "ServerPartDeals",
        "serverpartdeals",
        "specialist_reseller",
        "t2",
        "serverpartdeals.com",
        3600,
        900,
        "churning",
        "shopify_products_json",
    ),
    (
        "goHardDrive",
        "goharddrive",
        "specialist_reseller",
        "t2",
        "www.goharddrive.com",
        3600,
        900,
        "churning",
        "none",
    ),
    ("eBay", "ebay", "marketplace", "t0", "api.ebay.com", 600, 120, "drop_prone", "ebay_browse"),
    ("Demo (walking skeleton)", "demo", "other", "t2", "demo.invalid", 3600, 900, "stable", "none"),
]


def seed(apps, schema_editor):
    SourceSite = apps.get_model("catalog", "SourceSite")
    SourceConfig = apps.get_model("catalog", "SourceConfig")
    for name, key, source_type, tier, domain, baseline, ceiling, volatility, signal in SOURCES:
        site, _ = SourceSite.objects.get_or_create(
            normalized_name=key, defaults={"name": name, "source_type": source_type}
        )
        SourceConfig.objects.get_or_create(
            source_site=site,
            defaults={
                "tier": tier,
                "domain": domain,
                "cadence_baseline_s": baseline,
                "cadence_ceiling_s": ceiling,
                "current_interval_s": baseline,
                "volatility_profile": volatility,
                "cheap_signal": signal,
                # enabled/fast_lane stay at their False defaults deliberately.
            },
        )


def unseed(apps, schema_editor):
    SourceConfig = apps.get_model("catalog", "SourceConfig")
    keys = [row[1] for row in SOURCES]
    SourceConfig.objects.filter(source_site__normalized_name__in=keys).delete()


class Migration(migrations.Migration):
    dependencies = [("catalog", "0004_ops_substrate")]
    operations = [migrations.RunPython(seed, unseed)]
