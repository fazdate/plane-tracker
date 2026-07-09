// ---- Camera / follow-mode ----
import { map } from "./map.js";
import { state, OVERVIEW_ZOOM, FOLLOW_ZOOM } from "./config.js";

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

export function enterFollowMode(latlng) {
  if (state.cameraMode !== "following") {
    state.cameraMode = "following";
    flyTo(latlng, FOLLOW_ZOOM);
  }
}

export function exitFollowMode() {
  if (state.cameraMode !== "overview") {
    state.cameraMode = "overview";
    flyTo([state.home.lat, state.home.lon], OVERVIEW_ZOOM);
  }
}

export function resetView() {
  // Always fly home, even if already in "overview" mode or mid-follow.
  state.cameraMode = "overview";
  state.followSuppressed = true;
  flyTo([state.home.lat, state.home.lon], OVERVIEW_ZOOM);
}

// Minimum pixel drift of the followed plane from screen center before we
// bother re-centering. panTo() repaints every layer on the map, so nudging
// on every animation frame for sub-pixel movement is what made following a
// fast plane choppy on the tablet. Below this threshold we simply don't move.
const FOLLOW_DEADZONE_PX = 40;

export function smoothPan(targetLatLng) {
  // Don't fight an in-flight flyTo() transition
  if (transitioning) return;

  // Measure drift in screen pixels rather than degrees so the deadzone is
  // consistent across zoom levels / latitudes.
  const size = map.getSize();
  const targetPt = map.latLngToContainerPoint(targetLatLng);
  const dx = targetPt.x - size.x / 2;
  const dy = targetPt.y - size.y / 2;
  if (Math.hypot(dx, dy) < FOLLOW_DEADZONE_PX) return;

  const current = map.getCenter();
  const lerp = 0.08; // easing factor (higher = snappier)
  const lat = current.lat + (targetLatLng.lat - current.lat) * lerp;
  const lng = current.lng + (targetLatLng.lng - current.lng) * lerp;
  map.panTo([lat, lng], { animate: false });
}
