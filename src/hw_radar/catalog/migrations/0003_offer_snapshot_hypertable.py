from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("catalog", "0002_market_evidence")]

    operations = [
        migrations.RunSQL(
            "SELECT create_hypertable('offer_snapshot', by_range('observed_at'));",
            # noop reverse: unmigrating leaves the table as a hypertable. Forward-only
            # schema — a real down-migration would drop chunks/data, which we never want
            # to do implicitly. Rebuild from an empty DB if a true revert is needed.
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
