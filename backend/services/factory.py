"""Factory for constructing the configured aircraft data source."""
import logging
import os

from config import Config
from services.adsb_client import AdsbLolClient
from services.base_client import AircraftDataSource
from services.opensky_client import OpenSkyClient

logger = logging.getLogger("plane-tracker")


def _build_adsblol(config: Config) -> AdsbLolClient:
    return AdsbLolClient(center_lat=config.home_lat, center_lon=config.home_lon)


def _build_opensky_if_configured() -> OpenSkyClient | None:
    """Build an OpenSky client for use as a fallback, if credentials are
    available; otherwise return None (failover to it is simply skipped)."""
    client_id = os.environ.get("OPENSKY_CLIENT_ID")
    client_secret = os.environ.get("OPENSKY_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None
    return OpenSkyClient(client_id=client_id, client_secret=client_secret)


def create_data_source(
    config: Config,
) -> tuple[AircraftDataSource, AircraftDataSource | None, int]:
    """Build the configured primary data source, an optional fallback source
    for automatic failover, and the primary's poll interval."""
    provider = config.raw["data_source"]["provider"].lower()

    if provider == "opensky":
        client = OpenSkyClient(
            client_id=Config.env("OPENSKY_CLIENT_ID"),
            client_secret=Config.env("OPENSKY_CLIENT_SECRET"),
        )
        interval = config.raw["opensky"]["poll_interval_seconds"]
        fallback = _build_adsblol(config)
        logger.info("Data source: OpenSky (fallback: adsb.lol)")
        return client, fallback, interval

    if provider == "adsblol":
        client = _build_adsblol(config)
        interval = config.raw["adsblol"]["poll_interval_seconds"]
        fallback = _build_opensky_if_configured()
        logger.info(
            "Data source: adsb.lol (fallback: %s)"
            % ("OpenSky" if fallback else "none configured")
        )
        return client, fallback, interval

    raise ValueError(f"Unknown data_source.provider: {provider}")
