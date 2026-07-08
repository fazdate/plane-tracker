"""Enrichment service: airline names, type names, and route lookups.

Routes come from adsbdb.com (free, no auth):
  GET https://api.adsbdb.com/v0/callsign/{callsign}
Returns origin/destination airports for the flight if known.
"""
import logging
import time

import httpx

from services.data.airlines import airline_from_callsign, airline_iata_from_callsign
from services.data.aircraft_types import aircraft_type_name

logger = logging.getLogger(__name__)

ADSBDB_URL = "https://api.adsbdb.com/v0/callsign/"
ROUTE_CACHE_TTL = 6 * 3600   # cache routes for 6 hours
NEGATIVE_TTL = 30 * 60       # remember "no route" for 30 min
MAX_STATIC_CACHE_ENTRIES = 5000  # cap memory use for long-running processes


class EnrichmentService:
    def __init__(self):
        self._http = httpx.AsyncClient(
            timeout=8.0,
            headers={"User-Agent": "plane-tracker-hobby/1.0"},
        )
        # callsign -> (route_dict_or_None, expiry_ts)
        self._route_cache: dict[str, tuple[dict | None, float]] = {}
        # icao24 -> (callsign, aircraft_type, computed_fields) so unchanged
        # aircraft skip re-doing the lookups every poll cycle.
        self._static_cache: dict[str, tuple[str | None, str | None, dict]] = {}

    def enrich_static(self, ac: dict) -> None:
        """Add fields that need no network call (mutates ac in place)."""
        icao24 = ac.get("icao24")
        callsign = ac.get("callsign")
        ac_type = ac.get("aircraft_type")

        cached = self._static_cache.get(icao24) if icao24 else None
        if cached and cached[0] == callsign and cached[1] == ac_type:
            ac.update(cached[2])
            return

        computed = {
            "airline": airline_from_callsign(callsign),
            "airline_iata": airline_iata_from_callsign(callsign),
            "aircraft_type_name": aircraft_type_name(ac_type),
        }
        ac.update(computed)

        if icao24:
            self._static_cache[icao24] = (callsign, ac_type, computed)
            if len(self._static_cache) > MAX_STATIC_CACHE_ENTRIES:
                self._static_cache.pop(next(iter(self._static_cache)))

    async def get_route(self, callsign: str | None) -> dict | None:
        """Return {'origin': ..., 'destination': ...} or None."""
        if not callsign:
            return None
        callsign = callsign.strip().upper()

        cached = self._route_cache.get(callsign)
        now = time.time()
        if cached and cached[1] > now:
            return cached[0]

        try:
            resp = await self._http.get(ADSBDB_URL + callsign)
            if resp.status_code == 404:
                self._route_cache[callsign] = (None, now + NEGATIVE_TTL)
                return None
            resp.raise_for_status()
            data = resp.json()
            route = self._parse_route(data)
            ttl = ROUTE_CACHE_TTL if route else NEGATIVE_TTL
            self._route_cache[callsign] = (route, now + ttl)
            return route
        except Exception as e:
            logger.debug(f"Route lookup failed for {callsign}: {e}")
            # short negative cache to avoid hammering on errors
            self._route_cache[callsign] = (None, now + 60)
            return None

    @staticmethod
    def _parse_route(data: dict) -> dict | None:
        """Extract origin/destination from adsbdb response."""
        try:
            fr = data["response"]["flightroute"]
            origin = fr.get("origin", {})
            dest = fr.get("destination", {})
            return {
                "origin_iata": origin.get("iata_code"),
                "origin_name": origin.get("municipality") or origin.get("name"),
                "destination_iata": dest.get("iata_code"),
                "destination_name": dest.get("municipality") or dest.get("name"),
            }
        except (KeyError, TypeError):
            return None

    async def close(self):
        await self._http.aclose()