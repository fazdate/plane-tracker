"""FastAPI backend: polls a data source, computes distances, serves aircraft data."""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import Config
from connection_manager import ConnectionManager
from routes import register_routes
from services.alerts import AlertEngine
from services.enrichment import EnrichmentService
from services.factory import create_data_source
from tracker import AircraftTracker

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("plane-tracker")

config = Config()
data_source, fallback_source, poll_interval = create_data_source(config)

tracker = AircraftTracker(
    data_source=data_source,
    fallback_source=fallback_source,
    poll_interval=poll_interval,
    home_lat=config.home_lat,
    home_lon=config.home_lon,
    focus_km=config.focus_km,
    box=config.box,
    alert_engine=AlertEngine(
        boring_types=config.raw["alerts"]["boring_types"],
        emergency_squawks=config.raw["alerts"]["emergency_squawks"],
    ),
    enrichment=EnrichmentService(),
    manager=ConnectionManager(),
    home_airport_iata=config.home_airport_iata,
    route_sanity_max_altitude_m=config.route_sanity_max_altitude_m,
    ignored_callsign_prefixes=config.ignored_callsign_prefixes,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(tracker.poll_loop())
    yield
    task.cancel()
    await tracker.close_sources()
    await tracker.enrichment.close()


app = FastAPI(title="Plane Tracker", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

register_routes(app, tracker, tracker.manager)
