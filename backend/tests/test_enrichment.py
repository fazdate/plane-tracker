"""Unit and integration tests for EnrichmentService."""
import asyncio
from unittest.mock import AsyncMock, Mock

from services.enrichment import EnrichmentService


def test_enrich_static_adds_computed_fields():
    svc = EnrichmentService()
    ac = {"icao24": "abc123", "callsign": "WZZ123", "aircraft_type": "B738"}
    svc.enrich_static(ac)
    assert ac["airline"] == "Wizz Air"
    assert ac["airline_iata"] == "W6"
    assert ac["aircraft_type_name"] == "Boeing 737-800"


def test_enrich_static_uses_cache_for_unchanged_aircraft():
    svc = EnrichmentService()
    ac1 = {"icao24": "abc123", "callsign": "WZZ123", "aircraft_type": "B738"}
    svc.enrich_static(ac1)

    # Mutate the underlying data source; the cached value should still win
    # because callsign/type are unchanged, proving the cache path is used.
    import services.enrichment as enrichment_module
    original = enrichment_module.airline_from_callsign
    enrichment_module.airline_from_callsign = Mock(return_value="SHOULD_NOT_BE_USED")
    try:
        ac2 = {"icao24": "abc123", "callsign": "WZZ123", "aircraft_type": "B738"}
        svc.enrich_static(ac2)
    finally:
        enrichment_module.airline_from_callsign = original

    assert ac2["airline"] == "Wizz Air"


def test_enrich_static_recomputes_when_callsign_changes():
    svc = EnrichmentService()
    ac1 = {"icao24": "abc123", "callsign": "WZZ123", "aircraft_type": "B738"}
    svc.enrich_static(ac1)

    ac2 = {"icao24": "abc123", "callsign": "RYR456", "aircraft_type": "B738"}
    svc.enrich_static(ac2)

    assert ac2["airline"] == "Ryanair"


def test_get_route_returns_none_without_callsign():
    svc = EnrichmentService()
    assert asyncio.run(svc.get_route(None)) is None
    assert asyncio.run(svc.get_route("")) is None


def test_get_route_parses_successful_response():
    svc = EnrichmentService()
    response = Mock()
    response.status_code = 200
    response.raise_for_status = Mock()
    response.json = Mock(return_value={
        "response": {
            "flightroute": {
                "origin": {"iata_code": "BUD", "municipality": "Budapest"},
                "destination": {"iata_code": "LHR", "name": "Heathrow"},
            }
        }
    })
    svc._http.get = AsyncMock(return_value=response)

    route = asyncio.run(svc.get_route("wzz123"))

    assert route == {
        "origin_iata": "BUD",
        "origin_name": "Budapest",
        "destination_iata": "LHR",
        "destination_name": "Heathrow",
    }


def test_get_route_caches_result_and_avoids_second_call():
    svc = EnrichmentService()
    response = Mock()
    response.status_code = 200
    response.raise_for_status = Mock()
    response.json = Mock(return_value={
        "response": {"flightroute": {"origin": {}, "destination": {}}}
    })
    svc._http.get = AsyncMock(return_value=response)

    asyncio.run(svc.get_route("WZZ123"))
    asyncio.run(svc.get_route("WZZ123"))

    svc._http.get.assert_awaited_once()


def test_get_route_returns_none_and_caches_on_404():
    svc = EnrichmentService()
    response = Mock()
    response.status_code = 404
    svc._http.get = AsyncMock(return_value=response)

    route = asyncio.run(svc.get_route("UNKNOWN1"))

    assert route is None
    assert "UNKNOWN1" in svc._route_cache


def test_get_route_returns_none_on_request_error():
    svc = EnrichmentService()
    svc._http.get = AsyncMock(side_effect=RuntimeError("network down"))

    route = asyncio.run(svc.get_route("WZZ123"))

    assert route is None
    assert "WZZ123" in svc._route_cache


def test_parse_route_returns_none_on_malformed_data():
    assert EnrichmentService._parse_route({}) is None
    assert EnrichmentService._parse_route({"response": {}}) is None


def test_close_closes_http_client():
    svc = EnrichmentService()
    svc._http.aclose = AsyncMock()
    asyncio.run(svc.close())
    svc._http.aclose.assert_awaited_once()
