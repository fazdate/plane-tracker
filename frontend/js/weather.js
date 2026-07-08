// ---- Weather radar overlay (RainViewer: free, no API key required) ----
// https://www.rainviewer.com/api.html
import { map } from "./map.js";

const RAINVIEWER_INDEX_URL = "https://api.rainviewer.com/public/weather-maps.json";
const REFRESH_MS = 10 * 60 * 1000; // RainViewer publishes a new frame roughly every 10 min
const TILE_SIZE = 256;
const COLOR_SCHEME = 4; // "Universal Blue" - reads well over satellite imagery
const OVERLAY_OPACITY = 0.5;
const OVERLAY_Z_INDEX = 650; // above tiles/trails, below plane markers & UI panels
// RainViewer's radar tiles only actually exist up to zoom 7 (per their API
// docs); requesting deeper zooms returns a tile with "zoom level isn't
// supported" baked into the image instead of a normal 404. Capping
// maxNativeZoom here means Leaflet keeps fetching the z=7 tiles and
// upscales them for closer zooms instead of requesting invalid ones.
const RADAR_MAX_NATIVE_ZOOM = 7;
const RADAR_MAX_ZOOM = 19; // matches the base satellite layer's maxZoom

let radarLayer = null;
let refreshTimer = null;
let enabled = false;

function tileUrlFor(host, path) {
  return `${host}${path}/${TILE_SIZE}/{z}/{x}/{y}/${COLOR_SCHEME}/1_1.png`;
}

async function fetchLatestFrame() {
  const resp = await fetch(RAINVIEWER_INDEX_URL);
  if (!resp.ok) throw new Error(`RainViewer index request failed: ${resp.status}`);
  const data = await resp.json();
  const frames = data && data.radar && data.radar.past;
  if (!frames || !frames.length) return null;
  return { host: data.host, path: frames[frames.length - 1].path };
}

async function refreshLayer() {
  try {
    const frame = await fetchLatestFrame();
    if (!frame) return;
    const url = tileUrlFor(frame.host, frame.path);
    if (radarLayer) {
      radarLayer.setUrl(url);
    } else {
      radarLayer = L.tileLayer(url, {
        opacity: OVERLAY_OPACITY,
        zIndex: OVERLAY_Z_INDEX,
        maxNativeZoom: RADAR_MAX_NATIVE_ZOOM,
        maxZoom: RADAR_MAX_ZOOM,
      });
    }
    if (enabled && !map.hasLayer(radarLayer)) {
      radarLayer.addTo(map);
    }
  } catch (err) {
    console.warn("Weather radar refresh failed", err);
  }
}

// Toggles the radar overlay on/off; returns the new enabled state.
export function toggleWeather() {
  enabled = !enabled;
  if (enabled) {
    if (radarLayer) radarLayer.addTo(map);
    refreshLayer(); // fetch a fresh frame right away rather than waiting for the timer
    if (!refreshTimer) refreshTimer = setInterval(refreshLayer, REFRESH_MS);
  } else if (radarLayer) {
    map.removeLayer(radarLayer);
  }
  return enabled;
}
