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
        "origin_country_iso": None,
        "destination_iata": "LHR",
        "destination_name": "Heathrow",
        "destination_country_iso": None,
        "source": "adsbdb",
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


def test_get_route_falls_back_to_hexdb_when_adsbdb_has_no_route():
    svc = EnrichmentService()

    adsbdb_response = Mock(status_code=404)
    route_response = Mock(status_code=200, raise_for_status=Mock())
    route_response.json = Mock(return_value={"flight": "RYR1AB", "route": "EIDW-EGLL"})
    origin_response = Mock(status_code=200)
    origin_response.json = Mock(return_value={"airport": "Dublin Airport", "iata": "DUB"})
    dest_response = Mock(status_code=200)
    dest_response.json = Mock(return_value={"airport": "Heathrow Airport", "iata": "LHR"})

    async def fake_get(url):
        if url.startswith("https://api.adsbdb.com"):
            return adsbdb_response
        if url == "https://hexdb.io/api/v1/route/icao/RYR1AB":
            return route_response
        if url.endswith("/EIDW"):
            return origin_response
        if url.endswith("/EGLL"):
            return dest_response
        raise AssertionError(f"unexpected url {url}")

    svc._http.get = AsyncMock(side_effect=fake_get)

    route = asyncio.run(svc.get_route("ryr1ab"))

    assert route == {
        "origin_iata": "DUB",
        "origin_name": "Dublin Airport",
        "origin_country_iso": None,
        "destination_iata": "LHR",
        "destination_name": "Heathrow Airport",
        "destination_country_iso": None,
        "source": "hexdb",
    }


def test_get_route_returns_none_when_both_sources_have_no_route():
    svc = EnrichmentService()
    response = Mock(status_code=404)
    svc._http.get = AsyncMock(return_value=response)

    route = asyncio.run(svc.get_route("UNKNOWN1"))

    assert route is None
    assert "UNKNOWN1" in svc._route_cache


def _adsbdb_ok_response(origin_iata, dest_iata):
    response = Mock(status_code=200, raise_for_status=Mock())
    response.json = Mock(return_value={
        "response": {
            "flightroute": {
                "origin": {"iata_code": origin_iata},
                "destination": {"iata_code": dest_iata},
            }
        }
    })
    return response


def test_get_route_ignores_altitude_check_when_not_low_altitude():
    svc = EnrichmentService()
    svc._http.get = AsyncMock(return_value=_adsbdb_ok_response("LIN", "LTN"))

    route = asyncio.run(svc.get_route(
        "WZZ123", altitude_m=10000, home_iata="BUD", max_altitude_m=3000,
    ))

    assert route["origin_iata"] == "LIN"
    assert "uncertain" not in route
    svc._http.get.assert_awaited_once()  # no fallback lookup needed


def test_get_route_uses_hexdb_second_opinion_when_low_altitude_route_misses_home():
    svc = EnrichmentService()
    adsbdb_response = _adsbdb_ok_response("LIN", "LTN")  # doesn't touch BUD - suspicious
    hexdb_route_response = Mock(status_code=200, raise_for_status=Mock())
    hexdb_route_response.json = Mock(return_value={"route": "LIML-LHBP"})
    origin_response = Mock(status_code=200, json=Mock(return_value={"airport": "Milan Linate", "iata": "LIN"}))
    dest_response = Mock(status_code=200, json=Mock(return_value={"airport": "Budapest", "iata": "BUD"}))

    async def fake_get(url):
        if url.startswith("https://api.adsbdb.com"):
            return adsbdb_response
        if url == "https://hexdb.io/api/v1/route/icao/WZZ123":
            return hexdb_route_response
        if url.endswith("/LIML"):
            return origin_response
        if url.endswith("/LHBP"):
            return dest_response
        raise AssertionError(f"unexpected url {url}")

    svc._http.get = AsyncMock(side_effect=fake_get)

    route = asyncio.run(svc.get_route(
        "WZZ123", altitude_m=1500, home_iata="BUD", max_altitude_m=3000,
    ))

    assert route["destination_iata"] == "BUD"
    assert route["source"] == "hexdb"
    assert "uncertain" not in route


def test_get_route_flags_uncertain_when_fallback_does_not_resolve_it():
    svc = EnrichmentService()
    adsbdb_response = _adsbdb_ok_response("LIN", "LTN")  # doesn't touch BUD - suspicious
    hexdb_response = Mock(status_code=404)  # fallback has nothing either

    async def fake_get(url):
        if url.startswith("https://api.adsbdb.com"):
            return adsbdb_response
        return hexdb_response

    svc._http.get = AsyncMock(side_effect=fake_get)

    route = asyncio.run(svc.get_route(
        "WZZ123", altitude_m=1500, home_iata="BUD", max_altitude_m=3000,
    ))

    assert route["origin_iata"] == "LIN"
    assert route["destination_iata"] == "LTN"
    assert route["uncertain"] is True


def test_get_route_revalidates_cached_route_when_aircraft_descends():
    """A route cached while the aircraft was high up/far away must still be
    sanity-checked once it later shows up low and near home, instead of being
    served blindly from the cache with no `uncertain` flag."""
    svc = EnrichmentService()
    adsbdb_response = _adsbdb_ok_response("LIN", "LTN")  # never touches BUD
    svc._http.get = AsyncMock(return_value=adsbdb_response)

    # First lookup: cruising, far from home - no sanity check applies, gets cached.
    first = asyncio.run(svc.get_route(
        "WZZ123", altitude_m=10000, home_iata="BUD", max_altitude_m=3000,
    ))
    assert "uncertain" not in first
    svc._http.get.assert_awaited_once()

    # Second lookup: same callsign, now low and near home - the cached route
    # should be re-checked (hexdb) rather than returned as-is.
    hexdb_response = Mock(status_code=404)  # fallback has nothing either

    async def fake_get(url):
        if url.startswith("https://api.adsbdb.com"):
            raise AssertionError("should use cached adsbdb result, not refetch")
        return hexdb_response

    svc._http.get = AsyncMock(side_effect=fake_get)

    second = asyncio.run(svc.get_route(
        "WZZ123", altitude_m=1500, home_iata="BUD", max_altitude_m=3000,
    ))

    assert second["uncertain"] is True


def test_parse_route_returns_none_on_malformed_data():
    assert EnrichmentService._parse_route({}) is None
    assert EnrichmentService._parse_route({"response": {}}) is None


def test_close_closes_http_client():
    svc = EnrichmentService()
    svc._http.aclose = AsyncMock()
    asyncio.run(svc.close())
    svc._http.aclose.assert_awaited_once()
