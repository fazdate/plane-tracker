"""Unit tests for DailyStats: the SQLite-backed daily aircraft counter."""
import datetime as dt

from services.daily_stats import DailyStats


class _FixedDate(dt.date):
    """A date subclass whose today() is pinned, so tests can simulate the
    calendar day rolling over without waiting for real time to pass."""

    _fixed: dt.date

    @classmethod
    def today(cls):
        return cls._fixed


def freeze_today(monkeypatch, year, month, day):
    _FixedDate._fixed = dt.date(year, month, day)
    monkeypatch.setattr("services.daily_stats.date", _FixedDate)


def make_db_path(tmp_path) -> str:
    return str(tmp_path / "daily_stats.db")


def test_count_starts_at_zero():
    stats = DailyStats(":memory:")
    assert stats.count == 0


def test_record_counts_distinct_icao24_only():
    stats = DailyStats(":memory:")
    stats.record(["abc", "def"])
    stats.record(["abc", "ghi"])  # "abc" repeated, shouldn't double-count
    assert stats.count == 3


def test_count_survives_restart_same_day(tmp_path):
    db_path = make_db_path(tmp_path)
    stats = DailyStats(db_path)
    stats.record(["abc", "def"])
    stats.close()

    # Simulate the app restarting later the same day.
    restarted = DailyStats(db_path)
    assert restarted.count == 2
    restarted.record(["ghi"])
    assert restarted.count == 3


def test_rows_from_previous_days_are_purged_on_restart(tmp_path, monkeypatch):
    db_path = make_db_path(tmp_path)
    freeze_today(monkeypatch, 2026, 7, 9)
    stats = DailyStats(db_path)
    stats.record(["abc"])
    assert stats.count == 1
    stats.close()

    # Restart "the next day": stale rows from the 9th should not count
    # towards the 10th's total.
    freeze_today(monkeypatch, 2026, 7, 10)
    restarted = DailyStats(db_path)
    assert restarted.count == 0


def test_rollover_without_restart_resets_count(tmp_path, monkeypatch):
    db_path = make_db_path(tmp_path)
    freeze_today(monkeypatch, 2026, 7, 9)
    stats = DailyStats(db_path)
    stats.record(["abc"])
    assert stats.count == 1

    # Midnight passes while the process keeps running (no restart).
    freeze_today(monkeypatch, 2026, 7, 10)
    assert stats.count == 0
    stats.record(["def"])
    assert stats.count == 1
