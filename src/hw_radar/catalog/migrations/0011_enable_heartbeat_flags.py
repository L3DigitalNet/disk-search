# Flips heartbeat_enabled/fast_lane per source as each MS-1d connector lands
# (see 0005_seed_sources.py header). FLAGS is deliberately extensible: WD/
# Seagate/eBay tasks append their own (heartbeat_enabled, fast_lane) entries
# to this same dict/migration rather than each writing a new migration.
from django.db import migrations

FLAGS = {  # (heartbeat_enabled, fast_lane) — fast_lane per FR-002 (drop_prone ∩ cheap signal)
    "serverpartdeals": (True, False),  # churning ⇒ heartbeat but never fast-laned
}


def apply(apps, schema_editor):
    SourceConfig = apps.get_model("catalog", "SourceConfig")
    for key, (hb, fl) in FLAGS.items():
        SourceConfig.objects.filter(source_site__normalized_name=key).update(
            heartbeat_enabled=hb, fast_lane=fl
        )


def unapply(apps, schema_editor):
    SourceConfig = apps.get_model("catalog", "SourceConfig")
    SourceConfig.objects.filter(source_site__normalized_name__in=FLAGS).update(
        heartbeat_enabled=False, fast_lane=False
    )


class Migration(migrations.Migration):
    dependencies = [("catalog", "0010_heartbeat_timescale")]
    operations = [migrations.RunPython(apply, unapply)]
