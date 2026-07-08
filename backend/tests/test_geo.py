"""Unit tests for the sunrise/sunset approximation used for the day/night
theme. Regression-guards a bug found during development where mixing up the
relative ("days since J2000") and absolute Julian date in the mean-anomaly
formula silently produced a wrong solar declination (short/shifted days).
"""
from datetime import date, datetime, timezone

from services.geo import is_daytime, sun_times

# Generic public landmark (Hungarian Parliament Building)
BUDAPEST = (47.5070, 19.0459)


def test_sunrise_before_sunset_same_day():
    sunrise, sunset = sun_times(*BUDAPEST, date(2026, 7, 8))
    assert sunrise < sunset


def test_summer_day_is_long_in_northern_hemisphere():
    sunrise, sunset = sun_times(*BUDAPEST, date(2026, 6, 21))
    day_length_hours = (sunset - sunrise).total_seconds() / 3600
    assert 15 < day_length_hours < 17  # Budapest summer solstice is ~15.9h


def test_winter_day_is_short_in_northern_hemisphere():
    sunrise, sunset = sun_times(*BUDAPEST, date(2026, 1, 8))
    day_length_hours = (sunset - sunrise).total_seconds() / 3600
    assert 7 < day_length_hours < 10  # Budapest early-January day is ~8.7h


def test_polar_day_returns_none():
    # Tromso, Norway in July: sun never sets.
    assert sun_times(69.6, 18.96, date(2026, 7, 8)) is None


def test_polar_night_returns_none():
    # Tromso, Norway in January: sun never rises.
    assert sun_times(69.6, 18.96, date(2026, 1, 8)) is None


def test_is_daytime_true_at_local_noon():
    sunrise, _ = sun_times(*BUDAPEST, date(2026, 7, 8))
    local_noon_utc = sunrise.replace(hour=11, minute=0, second=0, microsecond=0)
    assert is_daytime(*BUDAPEST, local_noon_utc) is True


def test_is_daytime_false_at_utc_midnight():
    midnight = datetime(2026, 7, 8, 0, 0, tzinfo=timezone.utc)
    assert is_daytime(*BUDAPEST, midnight) is False


def test_is_daytime_defaults_true_for_polar_edge_case():
    # No sunrise/sunset that day (polar night) -> defaults to "day" theme
    # rather than raising, per the documented fallback behavior.
    winter_midday = datetime(2026, 1, 8, 11, 0, tzinfo=timezone.utc)
    assert is_daytime(69.6, 18.96, winter_midday) is True
