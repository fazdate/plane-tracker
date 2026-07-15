"""Unit tests for SpecialAircraftMatcher."""
from services.data.special_aircraft import SpecialAircraftMatcher

ENTRIES = [
    {"prefix": "medic", "name": "OMSZ Helicopter", "is_helicopter": True},
    {"prefix": "NARVL", "name": "Hungarian Air Force (KC-390)"},
    {"prefix": "R", "name": "Hungarian Police", "is_helicopter": True},
    {"prefix": "HUF", "name": "Hungarian Air Force"},
    {"prefix": "RCH", "name": "USAF", "logo_url": "https://example.com/usaf.png"},
]


def test_match_returns_none_with_no_entries():
    matcher = SpecialAircraftMatcher()
    assert matcher.match("MEDIC01") is None


def test_match_finds_entry_by_prefix():
    matcher = SpecialAircraftMatcher(ENTRIES)
    entry = matcher.match("MEDIC01")
    assert entry["name"] == "OMSZ Helicopter"
    assert entry["is_helicopter"] is True


def test_match_is_case_insensitive():
    matcher = SpecialAircraftMatcher(ENTRIES)
    assert matcher.match("medic01")["name"] == "OMSZ Helicopter"
    assert matcher.match("Rch123")["name"] == "USAF"


def test_match_strips_whitespace():
    matcher = SpecialAircraftMatcher(ENTRIES)
    assert matcher.match("  MEDIC01  ")["name"] == "OMSZ Helicopter"


def test_longest_prefix_wins_over_shorter_overlapping_one():
    matcher = SpecialAircraftMatcher(ENTRIES)
    # "RCH123" also starts with the shorter "R" (police) prefix, but the
    # more specific "RCH" (USAF) entry must win.
    assert matcher.match("RCH123")["name"] == "USAF"
    # A callsign that only matches the short "R" prefix still resolves.
    assert matcher.match("R05")["name"] == "Hungarian Police"


def test_match_returns_none_for_unmatched_callsign():
    matcher = SpecialAircraftMatcher(ENTRIES)
    assert matcher.match("WZZ123") is None


def test_prefix_must_be_followed_by_digit_or_nothing():
    matcher = SpecialAircraftMatcher(ENTRIES)
    # "ROF123" merely starts with the "R" prefix's letter but isn't followed
    # by a digit, so it must not be mistaken for Hungarian Police.
    assert matcher.match("ROF123") is None
    # An exact match with no trailing characters is still valid.
    assert matcher.match("R")["name"] == "Hungarian Police"


def test_match_returns_none_for_empty_callsign():
    matcher = SpecialAircraftMatcher(ENTRIES)
    assert matcher.match(None) is None
    assert matcher.match("") is None


def test_entry_exposes_logo_url_when_configured():
    matcher = SpecialAircraftMatcher(ENTRIES)
    assert matcher.match("RCH123")["logo_url"] == "https://example.com/usaf.png"


def test_entry_defaults_logo_url_to_none_when_not_configured():
    matcher = SpecialAircraftMatcher(ENTRIES)
    assert matcher.match("HUF123")["logo_url"] is None


def test_entry_defaults_is_helicopter_to_false_when_not_configured():
    matcher = SpecialAircraftMatcher(ENTRIES)
    assert matcher.match("HUF123")["is_helicopter"] is False
