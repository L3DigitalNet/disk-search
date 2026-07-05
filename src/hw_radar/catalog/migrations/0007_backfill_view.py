"""C.3.4 unknown_model backfill queue as a VIEW — no second source of truth.

Grouping key: (vendor_hint, decoded mpn_hypothesis) from the current edge when
present, else a per-listing synthetic key ('listing:<id>') so hypothesis-less
unresolved listings still surface individually. Vendor is IN the grouping key
so equal token text from different vendors never collapses into one queue row
(Codex CR-005). MS-1b scope is occurrence-only: the C.3.4 deal-attractiveness
signal needs scoring (MS-3) and is deliberately absent. Reversible: DROP VIEW.

SeparateDatabaseAndState (Codex CR-NEW-001): Django's autodetector tracks
UNMANAGED models in migration state — RunSQL alone would leave the model
stateless and the repo's makemigrations --check gate (tests/db/
test_migrations.py) would fail. The CreateModel below is state-only; the
managed=False option makes database_forwards skip it, so the view SQL is the
sole DDL."""

from django.db import migrations, models

CREATE_VIEW = """
CREATE VIEW unknown_model_backfill AS
WITH current_res AS (
    SELECT lr.listing_id,
           NULLIF(lr.evidence->>'mpn_hypothesis', '') AS mpn_hypothesis,
           COALESCE(lr.evidence->>'vendor_hint', '') AS vendor_hint
    FROM listing_resolution lr
    WHERE lr.is_current
),
below_model AS (
    SELECT l.id AS listing_id,
           cr.mpn_hypothesis,
           COALESCE(cr.vendor_hint, '') AS vendor_hint,
           l.resolution_grain AS grain,
           l.first_seen,
           l.last_seen
    FROM listing l
    LEFT JOIN current_res cr ON cr.listing_id = l.id
    WHERE l.resolution_grain IN ('none', 'family')
)
SELECT vendor_hint || ':' || COALESCE(mpn_hypothesis, 'listing:' || listing_id::text)
           AS hypothesis_key,
       mpn_hypothesis,
       NULLIF(vendor_hint, '') AS vendor_hint,
       COUNT(*) AS occurrences,
       COUNT(*) FILTER (WHERE grain = 'family') AS family_grain_count,
       MIN(first_seen) AS first_seen,
       MAX(last_seen) AS last_seen
FROM below_model
GROUP BY vendor_hint, COALESCE(mpn_hypothesis, 'listing:' || listing_id::text), mpn_hypothesis;
"""


class Migration(migrations.Migration):
    dependencies = [("catalog", "0006_resolution")]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(sql=CREATE_VIEW, reverse_sql="DROP VIEW unknown_model_backfill;"),
            ],
            state_operations=[
                migrations.CreateModel(
                    name="UnknownModelBackfill",
                    fields=[
                        (
                            "hypothesis_key",
                            models.CharField(max_length=300, primary_key=True, serialize=False),
                        ),
                        ("mpn_hypothesis", models.CharField(max_length=200, null=True)),
                        ("vendor_hint", models.CharField(max_length=50, null=True)),
                        ("occurrences", models.BigIntegerField()),
                        ("family_grain_count", models.BigIntegerField()),
                        ("first_seen", models.DateTimeField()),
                        ("last_seen", models.DateTimeField()),
                    ],
                    options={"db_table": "unknown_model_backfill", "managed": False},
                ),
            ],
        ),
    ]
