"""Unit tests for static aircraft-type and airline lookup helpers."""
from services.data.aircraft_types import aircraft_type_name
from services.data.airlines import airline_from_callsign, airline_iata_from_callsign


def test_aircraft_type_name_known_code():
    assert aircraft_type_name("B738") == "Boeing 737-800"


def test_aircraft_type_name_is_case_insensitive():
    assert aircraft_type_name("b738") == "Boeing 737-800"


def test_aircraft_type_name_unknown_code_falls_back_to_raw_code():
    assert aircraft_type_name("ZZZZ") == "ZZZZ"


def test_aircraft_type_name_none_returns_none():
    assert aircraft_type_name(None) is None


def test_airline_from_callsign_known_prefix():
    assert airline_from_callsign("WZZ1234") == "Wizz Air"
    assert airline_iata_from_callsign("WZZ1234") == "W6"


def test_airline_from_callsign_is_case_insensitive():
    assert airline_from_callsign("wzz1234") == "Wizz Air"


def test_airline_from_callsign_unknown_prefix_returns_none():
    assert airline_from_callsign("ZZZ1234") is None
    assert airline_iata_from_callsign("ZZZ1234") is None


def test_airline_from_callsign_too_short_returns_none():
    assert airline_from_callsign("WZ") is None


def test_airline_from_callsign_none_returns_none():
    assert airline_from_callsign(None) is None
    assert airline_iata_from_callsign(None) is None
