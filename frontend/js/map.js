// ---- Map setup ----
import { state, OVERVIEW_ZOOM } from "./config.js";

export const map = L.map("map", {
  center: [state.home.lat, state.home.lon],
  zoom: OVERVIEW_ZOOM,
  zoomControl: false,
});

let interactionTimeout = null;

map.on("dragstart zoomstart", () => {
  state.userInteracting = true;
  state.followPanEnabled = false;
  clearTimeout(interactionTimeout);
});

map.on("dragend zoomend", () => {
  // Resume auto-follow after 8s of no interaction
  clearTimeout(interactionTimeout);
  interactionTimeout = setTimeout(() => {
    state.userInteracting = false;
    state.followPanEnabled = true;
  }, 8000);
});

// Cancels the pending auto-follow-resume timer and immediately restores
// auto-follow, used by the manual "reset view" button.
export function clearInteractionTimeout() {
  clearTimeout(interactionTimeout);
  state.userInteracting = false;
  state.followPanEnabled = true;
}

// Satellite imagery basemap. (No text/label overlay: Esri's reference tiles
// render blurry at our zoom levels, so we skip them entirely.)
L.tileLayer(
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
  { maxZoom: 19 }
).addTo(map);

const homeIcon = L.divIcon({
  className: "",
  html: '<div class="home-icon"></div>',
  iconSize: [20, 20],
  iconAnchor: [10, 10],
});
const homeMarker = L.marker([state.home.lat, state.home.lon], { icon: homeIcon }).addTo(map);

// Radius starts at 0 (rather than a hardcoded guess) since it sits at the
// placeholder home coordinates until the server's first payload arrives
// anyway; setFocusRadiusKm() then sets the real value from config.yaml.
const focusCircle = L.circle([state.home.lat, state.home.lon], {
  radius: 0, color: "#00e5ff", weight: 1.5, opacity: 0.55, fillOpacity: 0.06,
}).addTo(map);

// Keeps the drawn circle in sync with the server's actual focus radius
// (the distance within which a plane can become the followed/focused one),
// instead of an unrelated hardcoded value that made the ring misleading.
export function setFocusRadiusKm(km) {
  if (km == null) return;
  focusCircle.setRadius(km * 1000);
}

let homeLocated = false;

// Moves the map/home marker/focus circle to the real home location once,
// the first time it's known (from the server's first payload). Before that,
// everything sits at the config.js placeholder so no real coordinates need
// to be baked into the frontend source.
export function setHomeLocation(lat, lon) {
  if (homeLocated || lat == null || lon == null) return;
  homeLocated = true;
  homeMarker.setLatLng([lat, lon]);
  focusCircle.setLatLng([lat, lon]);
  map.setView([lat, lon], OVERVIEW_ZOOM);
}
