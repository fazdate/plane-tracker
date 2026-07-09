"""Enrichment service: airline names, type names, and route lookups.

Routes come from adsbdb.com (free, no auth):
  GET https://api.adsbdb.com/v0/callsign/{callsign}
Returns origin/destination airports for the flight if known.

If adsbdb has no entry for a callsign (or errors), we fall back to
hexdb.io, a second free/no-auth community-maintained callsign/route
database:
  GET https://hexdb.io/api/v1/route/icao/{callsign}       -> "EIDW-EGLL"
  GET https://hexdb.io/api/v1/airport/icao/{icao}          -> airport details

Neither source is a live flight-plan feed - both are static
callsign->route lookup tables maintained by volunteers, so either one can
be missing an entry or (rarely) have a stale one if an airline reuses a
callsign for a different city pair. Checking a second, independently
maintained source mainly helps recover routes the first is simply
missing; it is not a guarantee of correctness.
"""
import logging
import time

import httpx

from services.data.airlines import airline_from_callsign, airline_iata_from_callsign
from services.data.aircraft_types import aircraft_type_name

logger = logging.getLogger(__name__)

ADSBDB_URL = "https://api.adsbdb.com/v0/callsign/"
HEXDB_ROUTE_URL = "https://hexdb.io/api/v1/route/icao/"
HEXDB_AIRPORT_URL = "https://hexdb.io/api/v1/airport/icao/"
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

    async def get_route(
        self,
        callsign: str | None,
        *,
        altitude_m: float | None = None,
        home_iata: str | None = None,
        max_altitude_m: float | None = None,
    ) -> dict | None:
        """Return {'origin_iata': ..., 'destination_iata': ..., ...} or None.

        Tries adsbdb.com first, falling back to hexdb.io if adsbdb has no
        entry (or the request errors). See module docstring for caveats.

        If `altitude_m`, `home_iata` and `max_altitude_m` are all given and
        the aircraft is below `max_altitude_m`, the route is expected to
        touch `home_iata` (a plane that low nearby is almost certainly
        taking off from or landing at the home airport). If it doesn't, the
        route looks wrong: hexdb.io is checked as a second opinion, and if
        that doesn't clear things up either, the returned route is marked
        `"uncertain": True` so callers (the frontend) can flag it.

        A route can be cached for up to `ROUTE_CACHE_TTL` from a lookup made
        while the aircraft was still high up / far away, i.e. before this
        sanity check applied. If the aircraft has since descended below
        `max_altitude_m` near `home_iata`, a cached route that hasn't been
        checked against that yet is re-validated (once) instead of being
        returned blindly.
        """
        if not callsign:
            return None
        callsign = callsign.strip().upper()

        low_altitude = (
            altitude_m is not None
            and max_altitude_m is not None
            and altitude_m < max_altitude_m
        )

        now = time.time()
        cached = self._route_cache.get(callsign)
        if cached and cached[1] > now:
            route, errored = cached[0], False
            suspicious = bool(
                route and "uncertain" not in route and low_altitude and home_iata
                and not self._touches_airport(route, home_iata)
            )
            if not suspicious:
                return route
            # falls through to re-check this cached route against hexdb below,
            # since it hasn't yet been validated against the aircraft's current
            # low-altitude position
        else:
            route, errored = await self._fetch_adsbdb_route(callsign)
            suspicious = bool(
                route and low_altitude and home_iata
                and not self._touches_airport(route, home_iata)
            )

        if route is None or suspicious:
            fallback_route, fallback_errored = await self._fetch_hexdb_route(callsign)
            errored = errored or fallback_errored
            if route is None:
                route = fallback_route
            elif fallback_route is not None and self._touches_airport(fallback_route, home_iata):
                route = fallback_route  # second opinion resolves the discrepancy
            elif suspicious:
                route["uncertain"] = True  # both sources agree it's odd (or fallback had nothing)

        # short negative cache to avoid hammering on transient errors,
        # longer negative cache when both sources cleanly say "no route"
        ttl = ROUTE_CACHE_TTL if route else (60 if errored else NEGATIVE_TTL)
        self._route_cache[callsign] = (route, now + ttl)
        return route

    @staticmethod
    def _touches_airport(route: dict, iata: str) -> bool:
        """Whether a route's origin or destination matches the given IATA code."""
        return route.get("origin_iata") == iata or route.get("destination_iata") == iata

    async def _fetch_adsbdb_route(self, callsign: str) -> tuple[dict | None, bool]:
        """Query adsbdb.com. Returns (route_or_None, errored)."""
        try:
            resp = await self._http.get(ADSBDB_URL + callsign)
            if resp.status_code == 404:
                return None, False
            resp.raise_for_status()
            route = self._parse_route(resp.json())
            if route:
                route["source"] = "adsbdb"
            return route, False
        except Exception as e:
            logger.debug(f"adsbdb route lookup failed for {callsign}: {e}")
            return None, True

    async def _fetch_hexdb_route(self, callsign: str) -> tuple[dict | None, bool]:
        """Query hexdb.io as a fallback. Returns (route_or_None, errored)."""
        try:
            resp = await self._http.get(HEXDB_ROUTE_URL + callsign)
            if resp.status_code == 404:
                return None, False
            resp.raise_for_status()
            data = resp.json()
            route_str = data.get("route")
            if not route_str or "-" not in route_str:
                return None, False

            origin_icao, _, dest_icao = route_str.partition("-")
            origin = await self._fetch_hexdb_airport(origin_icao)
            dest = await self._fetch_hexdb_airport(dest_icao)
            return {
                "origin_iata": origin.get("iata") if origin else None,
                "origin_name": origin.get("airport") if origin else None,
                "destination_iata": dest.get("iata") if dest else None,
                "destination_name": dest.get("airport") if dest else None,
                "source": "hexdb",
            }, False
        except Exception as e:
            logger.debug(f"hexdb route lookup failed for {callsign}: {e}")
            return None, True

    async def _fetch_hexdb_airport(self, icao: str | None) -> dict | None:
        """Look up an airport's name/IATA code on hexdb.io."""
        if not icao:
            return None
        try:
            resp = await self._http.get(HEXDB_AIRPORT_URL + icao)
            if resp.status_code != 200:
                return None
            return resp.json()
        except Exception as e:
            logger.debug(f"hexdb airport lookup failed for {icao}: {e}")
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