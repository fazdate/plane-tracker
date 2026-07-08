"""OpenSky Network API client using OAuth2 client credentials."""
import time
import logging
from typing import Optional

import httpx

from services.geo import BoundingBox

from services.base_client import AircraftDataSource

logger = logging.getLogger(__name__)

TOKEN_URL = (
    "https://auth.opensky-network.org/auth/realms/"
    "opensky-network/protocol/openid-connect/token"
)
STATES_URL = "https://opensky-network.org/api/states/all"

# Index mapping for OpenSky state vector array
# https://openskynetwork.github.io/opensky-api/rest.html#response
STATE_FIELDS = [
    "icao24", "callsign", "origin_country", "time_position",
    "last_contact", "longitude", "latitude", "baro_altitude",
    "on_ground", "velocity", "true_track", "vertical_rate",
    "sensors", "geo_altitude", "squawk", "spi", "position_source",
]


class OpenSkyClient(AircraftDataSource):
    def __init__(self, client_id: str, client_secret: str):
        self._client_id = client_id
        self._client_secret = client_secret
        self._token: Optional[str] = None
        self._token_expiry: float = 0.0
        self._http = httpx.AsyncClient(timeout=15.0)

    async def _ensure_token(self):
        if self._token and time.time() < self._token_expiry - 30:
            return
        logger.info("Fetching new OpenSky OAuth2 token...")
        resp = await self._http.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data["access_token"]
        self._token_expiry = time.time() + data.get("expires_in", 1800)

    async def fetch_states(self, box: BoundingBox) -> list[dict]:
        """Fetch aircraft state vectors within the bounding box."""
        await self._ensure_token()
        params = {
            "lamin": box.lat_min,
            "lamax": box.lat_max,
            "lomin": box.lon_min,
            "lomax": box.lon_max,
        }
        headers = {"Authorization": f"Bearer {self._token}"}
        resp = await self._http.get(STATES_URL, params=params, headers=headers)

        if resp.status_code == 401:
            # token might be stale; force refresh once
            self._token = None
            await self._ensure_token()
            headers = {"Authorization": f"Bearer {self._token}"}
            resp = await self._http.get(STATES_URL, params=params, headers=headers)

        resp.raise_for_status()
        payload = resp.json()
        raw_states = payload.get("states") or []
        return [self._parse_state(s) for s in raw_states]

    @staticmethod
    def _parse_state(state: list) -> dict:
        d = dict(zip(STATE_FIELDS, state))
        if d.get("callsign"):
            d["callsign"] = d["callsign"].strip()
        # Normalized enrichment keys (OpenSky states/all doesn't provide these)
        d.setdefault("aircraft_type", None)
        d.setdefault("registration", None)
        return d

    async def close(self):
        await self._http.aclose()