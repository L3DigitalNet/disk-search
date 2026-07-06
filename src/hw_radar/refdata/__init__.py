"""ADR-0018 reference-data ingest (MS-1c): the truncated fetch→parse→normalize→
persist pipeline for the manufacturer spec catalog. Writes product_family /
product_model / drive_spec / product_alias with retention_class =
manufacturer_reference and STOPS — no offer_snapshot/score/alert/heartbeat rows,
and it never gates the observation stream (ADR-0018 rules 1 & 6). Pure schema in
contracts.py; only persist/discovery/refresh touch the ORM."""
