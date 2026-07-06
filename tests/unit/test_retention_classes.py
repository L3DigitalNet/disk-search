from hw_radar.catalog.models.base import (
    BOUNDED_RETENTION_CLASSES,
    INDEFINITE_RETENTION_CLASSES,
    RetentionClass,
    retention_constraints,
)


def test_heartbeat_classes_exist_and_are_bounded() -> None:
    assert RetentionClass.AVAILABILITY_HEARTBEAT.value == "availability_heartbeat"
    assert RetentionClass.AVAILABILITY_HEARTBEAT_EVENT.value == "availability_heartbeat_event"
    assert RetentionClass.AVAILABILITY_HEARTBEAT in BOUNDED_RETENTION_CLASSES
    assert RetentionClass.AVAILABILITY_HEARTBEAT_EVENT in BOUNDED_RETENTION_CLASSES
    # bounded ⇒ NOT indefinite (a row of this class must carry expires_at)
    assert RetentionClass.AVAILABILITY_HEARTBEAT not in INDEFINITE_RETENTION_CLASSES


def test_new_bounded_classes_flow_into_constraint_predicate() -> None:
    # retention_constraints bakes the bounded list into the CHECK; the two new
    # classes must appear so new-table constraints accept them.
    constraints = retention_constraints("availability_heartbeat_observation")
    ttl = next(c for c in constraints if c.name.endswith("_retention_ttl_coherent"))
    assert "availability_heartbeat" in str(ttl.condition)
