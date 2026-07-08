// ---- Camera / follow-mode & focus ring ----
import { map } from "./map.js";
import { state, OVERVIEW_ZOOM, FOLLOW_ZOOM } from "./config.js";

let focusRing = null;

// True while a flyTo() transition is in flight. Leaflet's flyTo doesn't set
// map._panAnim (that's only for the separate panTo animation), so without
// this, smoothPan's per-frame panTo would fight the fly-to curve every
// animation frame and produce visible stutter/jiggle.
let transitioning = false;
let transitionTimer = null;
const FLY_DURATION_MS = 1500;

function flyTo(latlng, zoom) {
  clearTimeout(transitionTimer);
  transitioning = true;
  transitionTimer = setTimeout(() => {
    transitioning = false;
  }, FLY_DURATION_MS + 50);
  map.flyTo(latlng, zoom, {
    animate: true,
    duration: FLY_DURATION_MS / 1000,
    easeLinearity: 0.25,
  });
}

export function showFocusRing(latlng) {
  if (!focusRing) {
    focusRing = L.circleMarker(latlng, {
      radius: 34,
      color: "#00e5ff",
      weight: 3,
      opacity: 0.95,
      fillOpacity: 0.1,
      className: "focus-ring",
    }).addTo(map);
  } else {
    focusRing.setLatLng(latlng);
  }
}

export function hideFocusRing() {
  if (focusRing) {
    map.removeLayer(focusRing);
    focusRing = null;
  }
}

export function enterFollowMode(latlng) {
  if (state.cameraMode !== "following") {
    state.cameraMode = "following";
    flyTo(latlng, FOLLOW_ZOOM);
  }
}

export function exitFollowMode() {
  if (state.cameraMode !== "overview") {
    state.cameraMode = "overview";
    hideFocusRing();
    flyTo([state.home.lat, state.home.lon], OVERVIEW_ZOOM);
  }
}

export function resetView() {
  // Always fly home, even if already in "overview" mode or mid-follow.
  state.cameraMode = "overview";
  state.followSuppressed = true;
  hideFocusRing();
  flyTo([state.home.lat, state.home.lon], OVERVIEW_ZOOM);
}

export function smoothPan(targetLatLng) {
  // Don't fight an in-flight flyTo() transition
  if (transitioning) return;

  const current = map.getCenter();
  const lerp = 0.08; // easing factor (higher = snappier)
  const lat = current.lat + (targetLatLng.lat - current.lat) * lerp;
  const lng = current.lng + (targetLatLng.lng - current.lng) * lerp;

  // Only move if drift is meaningful (avoids micro-jitter)
  if (Math.abs(lat - current.lat) > 1e-6 || Math.abs(lng - current.lng) > 1e-6) {
    map.panTo([lat, lng], { animate: false });
  }
}
