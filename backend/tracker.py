"""Aircraft polling, enrichment, and shared state."""
import asyncio
import logging
import time

import httpx

from connection_manager import ConnectionManager
from services.alerts import AlertEngine
from services.base_client import AircraftDataSource
from services.daily_stats import DEFAULT_DB_PATH, DailyStats
from services.enrichment import EnrichmentService
from services.geo import BoundingBox, haversine_km
from services.seen_history import SeenHistory

logger = logging.getLogger("plane-tracker")

# Consecutive failures on the active source before switching to the fallback
# (or, if already on the fallback, before retrying the primary).
FAILOVER_THRESHOLD = 3
# Successful poll cycles to run on the fallback before re-attempting the primary.
RECOVERY_PROBE_EVERY = 10
# Ceiling for exponential backoff between failed poll attempts.
MAX_BACKOFF_SECONDS = 60


class AircraftTracker:
    """Polls a data source, enriches aircraft, and broadcasts state over WebSockets."""

    def __init__(
        self,
        data_source: AircraftDataSource,
        poll_interval: int,
        home_lat: float,
        home_lon: float,
        focus_km: float,
        box: BoundingBox,
        alert_engine: AlertEngine,
        enrichment: EnrichmentService,
        manager: ConnectionManager,
        fallback_source: AircraftDataSource | None = None,
        home_airport_iata: str | None = None,
        route_sanity_max_altitude_m: float = 3000,
        ignored_callsign_prefixes: list[str] | None = None,
        daily_stats_db_path: str = DEFAULT_DB_PATH,
    ):
        self.data_source = data_source  # currently active source
        self._primary_source = data_source
        self._fallback_source = fallback_source
        self.poll_interval = poll_interval
        self.home_lat = home_lat
        self.home_lon = home_lon
        self.focus_km = focus_km
        self.box = box
        self.alert_engine = alert_engine
        self.enrichment = enrichment
        self.manager = manager
        self.home_airport_iata = home_airport_iata
        self.route_sanity_max_altitude_m = route_sanity_max_altitude_m
        # Uppercased so matching in _is_ignored_callsign() is case-insensitive.
        self.ignored_callsign_prefixes = tuple(
            p.upper() for p in (ignored_callsign_prefixes or [])
        )

        self._consecutive_failures = 0
        self._cycles_on_fallback = 0
        self.daily_stats = DailyStats(daily_stats_db_path)
        # Reuses the same DB file as daily_stats (different table), so no
        # extra config is needed to enable this.
        self.seen_history = SeenHistory(daily_stats_db_path)

        self.state = {
            "aircraft": [],
            "focused_icao": None,
            "updated_at": None,
        }

    def build_payload(self) -> dict:
        return {
            "home": {"lat": self.home_lat, "lon": self.home_lon},
            "focus_radius_km": self.focus_km,
            "focused_icao": self.state["focused_icao"],
            "count": len(self.state["aircraft"]),
            "aircraft": self.state["aircraft"],
            "daily_count": self.daily_stats.count,
        }

    def process_aircraft(self, raw: list[dict]) -> tuple[list[dict], dict | None]:
        """Enrich all aircraft with distance/alerts; select focused separately."""
        enriched = []
        for ac in raw:
            if ac.get("latitude") is None or ac.get("longitude") is None:
                continue
            if not ac.get("callsign"):
                continue  # no callsign -> ground vehicle, not an aircraft
            if self._is_ignored_callsign(ac["callsign"]):
                continue
            dist = haversine_km(self.home_lat, self.home_lon, ac["latitude"], ac["longitude"])
            ac["distance_km"] = round(dist, 2)
            self.enrichment.enrich_static(ac)
            ac["alert"] = self.alert_engine.evaluate(ac)
            enriched.append(ac)

        candidates = [
            a for a in enriched
            if not a.get("on_ground") and a["distance_km"] <= self.focus_km
        ]
        focused = None
        if candidates:
            focused = min(candidates, key=lambda a: a["distance_km"])
            focused["focused"] = True

        return enriched, focused

    def _is_ignored_callsign(self, callsign: str) -> bool:
        """True if callsign starts with a configured ignored prefix (e.g. a
        ground vehicle like AIRSIDE1), so it can be filtered out."""
        callsign = callsign.strip().upper()
        return callsign.startswith(self.ignored_callsign_prefixes)

    async def _refresh_once(self):
        """Fetch, enrich, and broadcast a single polling cycle."""
        raw = await self.data_source.fetch_states(self.box)
        aircraft, focused = self.process_aircraft(raw)
        self.daily_stats.record(a["icao24"] for a in aircraft)
        self.seen_history.record(a.get("registration") for a in aircraft)

        if focused:
            focused["route"] = await self.enrichment.get_route(
                focused.get("callsign"),
                altitude_m=focused.get("baro_altitude"),
                home_iata=self.home_airport_iata,
                max_altitude_m=self.route_sanity_max_altitude_m,
            )
            if focused.get("registration"):
                focused["times_seen"] = self.seen_history.count(focused["registration"])

        focused_icao = focused["icao24"] if focused else None
        self.state["aircraft"] = aircraft
        self.state["focused_icao"] = focused_icao
        self.state["updated_at"] = time.monotonic()

        await self.manager.broadcast(self.build_payload())
        self._log_summary(aircraft, focused_icao)

    @staticmethod
    def _log_summary(aircraft: list[dict], focused: str | None):
        logger.info(f"{len(aircraft)} aircraft in box. Focused: {focused or 'none'}")
        for a in sorted(aircraft, key=lambda x: x["distance_km"])[:5]:
            cs = a.get("callsign") or "??????"
            alt = a.get("baro_altitude")
            typ = a.get("aircraft_type") or "?"
            logger.info(f"  {cs:8} {a['distance_km']:6.2f} km  "
                        f"alt={alt}  type={typ}")

    async def poll_loop(self):
        """Background task polling the active data source. Backs off
        exponentially on repeated failures and, if a fallback source is
        configured, fails over to it after enough consecutive failures
        (periodically retrying the primary while on the fallback)."""
        logger.info(f"Bounding box: {self.box}")
        while True:
            try:
                await self._refresh_once()
                self._on_poll_success()
            except httpx.TimeoutException as e:
                logger.warning(f"Poll timed out: {e}")
                self._on_poll_failure()
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error: {e.response.status_code}")
                self._on_poll_failure()
            except Exception:
                logger.exception("Poll failed")
                self._on_poll_failure()

            await asyncio.sleep(self._next_sleep_seconds())

    def _on_poll_success(self):
        self._consecutive_failures = 0
        if self.data_source is self._fallback_source:
            self._cycles_on_fallback += 1
            if self._cycles_on_fallback >= RECOVERY_PROBE_EVERY:
                logger.info("Retrying primary data source after recovery window")
                self.data_source = self._primary_source
                self._cycles_on_fallback = 0

    def _on_poll_failure(self):
        self._consecutive_failures += 1
        if (
            self._consecutive_failures >= FAILOVER_THRESHOLD
            and self._fallback_source is not None
            and self.data_source is not self._fallback_source
        ):
            logger.warning(
                f"Data source failing repeatedly ({self._consecutive_failures} in a row); "
                "switching to fallback source"
            )
            self.data_source = self._fallback_source
            self._consecutive_failures = 0
            self._cycles_on_fallback = 0

    def _next_sleep_seconds(self) -> float:
        if self._consecutive_failures == 0:
            return self.poll_interval
        backoff = self.poll_interval * (2 ** (self._consecutive_failures - 1))
        return min(backoff, MAX_BACKOFF_SECONDS)

    async def close_sources(self):
        """Close the HTTP clients for both the primary and fallback sources,
        and the daily stats database connection."""
        await self._primary_source.close()
        if self._fallback_source is not None:
            await self._fallback_source.close()
        self.daily_stats.close()
