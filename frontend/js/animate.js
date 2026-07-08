// ---- Interpolation loop (dead-reckoning) ----
import { state } from "./config.js";
import { planes, addTrailPoint } from "./planes.js";
import { enterFollowMode, exitFollowMode, showFocusRing, smoothPan } from "./camera.js";

// How often (ms) to sample the interpolated position into the trail. Much
// shorter than the server poll interval, so the route line grows smoothly
// in step with the icon instead of jumping once per server update.
const TRAIL_SAMPLE_INTERVAL_MS = 250;

function metersToLatLon(lat, dNorth, dEast) {
  const dLat = dNorth / 111320;
  const dLon = dEast / (111320 * Math.cos((lat * Math.PI) / 180));
  return [dLat, dLon];
}

export function animate() {
  const now = performance.now();

  let focusedLatLng = null;

  for (const p of planes.values()) {
    const grounded = p.data && p.data.on_ground;
    if (grounded || !p.velocity || p.velocity < 1) {
      // still track position for focus ring even if slow
      if (p.data && p.data.icao24 === state.focusedIcao) {
        focusedLatLng = p.marker.getLatLng();
      }
      continue;
    }

    const dt = (now - p.lastUpdate) / 1000;
    const dist = p.velocity * dt;
    const rad = (p.track * Math.PI) / 180;
    const dNorth = dist * Math.cos(rad);
    const dEast = dist * Math.sin(rad);
    const [dLat, dLon] = metersToLatLon(p.lat, dNorth, dEast);
    const newLatLng = [p.lat + dLat, p.lon + dLon];
    p.marker.setLatLng(newLatLng);

    if (now - p.lastTrailPush > TRAIL_SAMPLE_INTERVAL_MS) {
      addTrailPoint(p, newLatLng[0], newLatLng[1]);
      p.lastTrailPush = now;
    }

    if (p.data && p.data.icao24 === state.focusedIcao) {
      focusedLatLng = L.latLng(newLatLng[0], newLatLng[1]);
    }
  }

  // Camera follow
  if (state.focusedIcao && focusedLatLng && !state.followSuppressed) {
    enterFollowMode(focusedLatLng);
    showFocusRing(focusedLatLng);
    // Smoothly keep the plane centered while following
    if (state.cameraMode === "following" && state.followPanEnabled) {
      // panTo with animation off = we do our own gentle easing
      smoothPan(focusedLatLng);
    }
  } else {
    exitFollowMode();
  }

  requestAnimationFrame(animate);
}
