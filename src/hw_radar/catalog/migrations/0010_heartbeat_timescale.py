from django.db import migrations

# cagg cannot be created inside a transaction; retention/compression policies
# are background jobs. Pattern mirrors 0003_offer_snapshot_hypertable (noop
# reverse — forward-only; a real revert rebuilds from an empty DB).
SETUP = """
SELECT create_hypertable(
    'availability_heartbeat_observation', by_range('observed_at', INTERVAL '1 month'),
    migrate_data => TRUE
);
ALTER TABLE availability_heartbeat_observation SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'source_site_id',
    timescaledb.compress_orderby = 'observed_at DESC'
);
SELECT add_compression_policy('availability_heartbeat_observation', INTERVAL '7 days');
SELECT add_retention_policy('availability_heartbeat_observation', INTERVAL '30 days');
CREATE MATERIALIZED VIEW availability_heartbeat_daily
WITH (timescaledb.continuous) AS
SELECT source_site_id,
       time_bucket('1 day', observed_at) AS day,
       decision,
       count(*) AS n
FROM availability_heartbeat_observation
GROUP BY source_site_id, day, decision
WITH NO DATA;
-- start_offset - end_offset must span >= 2 bucket widths (2 x 1 day = 48h);
-- 3 days - 1 hour = 71h clears it and stays well inside the 30d retention.
SELECT add_continuous_aggregate_policy(
    'availability_heartbeat_daily',
    start_offset => INTERVAL '3 days', end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour'
);
"""


class Migration(migrations.Migration):
    atomic = False  # TimescaleDB rejects continuous-aggregate DDL inside a transaction
    dependencies = [("catalog", "0009_heartbeat_models")]
    operations = [migrations.RunSQL(SETUP, reverse_sql=migrations.RunSQL.noop)]
