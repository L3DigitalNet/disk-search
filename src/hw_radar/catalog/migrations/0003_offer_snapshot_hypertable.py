from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("catalog", "0002_market_evidence")]

    operations = [
        migrations.RunSQL(
            "SELECT create_hypertable('offer_snapshot', by_range('observed_at'));",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
