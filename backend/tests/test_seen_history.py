"""Unit tests for SeenHistory: the SQLite-backed per-registration sighting
history used to show "seen N times before" in the focused-plane panel."""
import datetime as dt

from services.seen_history import SeenHistory


class _FixedDate(dt.date):
    """A date subclass whose today() is pinned, so tests can simulate
    multiple distinct days without waiting for real time to pass."""

    _fixed: dt.date

    @classmethod
    def today(cls):
        return cls._fixed


def freeze_today(monkeypatch, year, month, day):
    _FixedDate._fixed = dt.date(year, month, day)
    monkeypatch.setattr("services.seen_history.date", _FixedDate)


def make_db_path(tmp_path) -> str:
    return str(tmp_path / "daily_stats.db")


def test_count_starts_at_zero():
    history = SeenHistory(":memory:")
    assert history.count("HA-LVK") == 0


def test_record_then_count_same_day():
    history = SeenHistory(":memory:")
    history.record(["HA-LVK", "OE-LKB"])
    assert history.count("HA-LVK") == 1
    assert history.count("OE-LKB") == 1
    assert history.count("N12345") == 0


def test_repeated_sightings_same_day_only_count_once():
    history = SeenHistory(":memory:")
    history.record(["HA-LVK"])
    history.record(["HA-LVK"])
    history.record(["HA-LVK"])
    assert history.count("HA-LVK") == 1


def test_missing_registrations_are_ignored():
    history = SeenHistory(":memory:")
    history.record([None, "", "HA-LVK"])
    assert history.count("HA-LVK") == 1


def test_sightings_on_different_days_accumulate(monkeypatch):
    history = SeenHistory(":memory:")
    freeze_today(monkeypatch, 2026, 7, 9)
    history.record(["HA-LVK"])
    assert history.count("HA-LVK") == 1

    freeze_today(monkeypatch, 2026, 7, 10)
    history.record(["HA-LVK"])
    assert history.count("HA-LVK") == 2

    freeze_today(monkeypatch, 2026, 7, 11)
    history.record(["HA-LVK"])
    assert history.count("HA-LVK") == 3


def test_history_survives_restart(tmp_path):
    db_path = make_db_path(tmp_path)
    history = SeenHistory(db_path)
    history.record(["HA-LVK"])
    history.close()

    restarted = SeenHistory(db_path)
    assert restarted.count("HA-LVK") == 1
