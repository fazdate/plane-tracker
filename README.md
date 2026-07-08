# Plane Tracker

A real-time aircraft tracker for a home location, built with a FastAPI backend
and a vanilla-JS/Leaflet frontend. It polls a live ADS-B data source, computes
distance from home, enriches aircraft with airline/type/route info, tracks the
nearest ("focused") aircraft, and pushes updates to connected clients over a
WebSocket. Includes day/night theming, live weather radar, alerting for
emergency squawks and uncommon aircraft types, and English/Hungarian i18n.

## Features

- Live aircraft positions polled from [adsb.lol](https://api.adsb.lol) (no
  API key required), with optional [OpenSky Network](https://opensky-network.org/)
  fallback/primary source and automatic failover with exponential backoff.
- Distance-from-home calculation and a "focused" (nearest in-range) aircraft.
- Enrichment: airline name/logo, aircraft type name, registration, and
  route (origin/destination) lookup, with caching.
- Alerts for emergency squawks (7500/7600/7700) and uncommon aircraft types,
  with an in-browser banner, flash, and chime.
- Smooth dead-reckoning interpolation between server updates, animated
  flight trails, and camera auto-follow on the focused aircraft.
- Day/night theme based on the real sunrise/sunset time for the home location.
- Live weather radar overlay (RainViewer) and aircraft photo lookup
  (Planespotters).
- English / Hungarian language toggle.

## Architecture

```
backend/    FastAPI app: polling, enrichment, alerting, WebSocket broadcast
  services/     Data source clients (adsb.lol, OpenSky), enrichment, alerts, geo
  tests/        pytest unit + integration tests
frontend/   Static single-page app (no build step): Leaflet map + vanilla JS modules
  js/           One module per concern (map, planes, camera, alerts, i18n, ...)
  tests/        Vitest unit tests (jsdom)
```

The backend serves the frontend as static files and exposes:
- `GET /api/aircraft` — current snapshot
- `GET /api/health` — health/status check
- `WS /ws` — live push of the same snapshot on every poll cycle

## Requirements

- Python 3.11+
- Node.js 18+ (only needed to run the frontend test suite; the frontend
  itself ships as plain ES modules with no build step)

## Setup

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your home coordinates (and OpenSky
credentials, if you want to use that provider):

```bash
cp .env.example .env
```

Adjust `config.yaml` for your bounding box, focus radius, data source
provider, and alert rules.

Run the server:

```bash
uvicorn main:app --reload
```

Then open http://localhost:8000.

### Frontend

The frontend has no build step — it's served directly by the backend from
`frontend/`. To run its test suite:

```bash
cd frontend
npm install
npm test
```

## Testing

```bash
# Backend (unit + integration tests, pytest)
cd backend
pip install -r requirements-dev.txt
python -m pytest

# Frontend (unit tests, Vitest + jsdom)
cd frontend
npm install
npm test
```

## Configuration

`backend/config.yaml`:

| Section | Key | Description |
|---|---|---|
| `data_source` | `provider` | `adsblol` or `opensky` |
| `zones` | `bounding_box_km`, `focus_radius_km` | Polling area and "focused aircraft" range |
| `adsblol` / `opensky` | `poll_interval_seconds` | Poll frequency for the active provider |
| `alerts` | `boring_types`, `emergency_squawks` | Aircraft types to *not* alert on, and squawk codes that *always* alert |

Environment variables (`backend/.env`, see `.env.example`):

| Variable | Required | Purpose |
|---|---|---|
| `HOME_LATITUDE` / `HOME_LONGITUDE` | Yes | Home coordinates (kept out of `config.yaml` so they're never committed) |
| `OPENSKY_CLIENT_ID` / `OPENSKY_CLIENT_SECRET` | Only if using OpenSky (as primary or fallback) | OAuth2 client credentials for the OpenSky API |
