"""Unit tests for AlertEngine."""
from services.alerts import AlertEngine


def make_engine(boring_types=None, emergency_squawks=None) -> AlertEngine:
    return AlertEngine(
        boring_types=boring_types if boring_types is not None else ["B738", "A320"],
        emergency_squawks=emergency_squawks if emergency_squawks is not None else ["7500", "7600", "7700"],
    )


def test_emergency_squawk_takes_priority_over_type():
    engine = make_engine()
    alert = engine.evaluate({"squawk": "7700", "aircraft_type": "B738"})
    assert alert == {
        "level": "emergency",
        "reason": "Emergency squawk 7700",
        "flash": "red",
    }


def test_boring_type_produces_no_alert():
    engine = make_engine()
    assert engine.evaluate({"squawk": "1200", "aircraft_type": "B738"}) is None


def test_boring_type_match_is_case_insensitive():
    engine = make_engine()
    assert engine.evaluate({"squawk": "1200", "aircraft_type": "b738"}) is None


def test_uncommon_type_produces_interesting_alert():
    engine = make_engine()
    alert = engine.evaluate({"squawk": "1200", "aircraft_type": "C172"})
    assert alert == {
        "level": "interesting",
        "reason": "Uncommon type: C172",
        "flash": "gold",
    }


def test_missing_type_produces_no_alert():
    engine = make_engine()
    assert engine.evaluate({"squawk": "1200", "aircraft_type": None}) is None
    assert engine.evaluate({"squawk": "1200"}) is None


def test_missing_squawk_is_not_treated_as_emergency():
    engine = make_engine()
    assert engine.evaluate({"aircraft_type": "B738"}) is None
