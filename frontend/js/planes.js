// ---- Plane state store: applies server snapshots to markers ----
import { map, setFocusRadiusKm, setHomeLocation } from "./map.js";
import { state } from "./config.js";
import { makePlaneIcon, classFor, fillFor } from "./planeIcon.js";
import { updatePanel } from "./panel.js";
import { processAlerts } from "./alerts.js";
import { applyTheme } from "./theme.js";
import { t } from "./i18n.js";

// icao24 -> { marker, lat, lon, velocity, track, lastUpdate, cls, data }
export const planes = new Map();

// Trail: number of past positions kept per plane, and how fast old segments fade.
// Points are sampled far more often than server updates (see animate.js), which
// is what keeps the line smooth instead of jumping once per poll interval.
const TRAIL_MAX_POINTS = 60;
const TRAIL_MAX_OPACITY = 0.9;
const TRAIL_MIN_OPACITY = 0.2;

// Appends a point to a plane's trail. Called both when fresh server data
// arrives and, more frequently, from the animation loop with the
// interpolated position, so the line keeps pace with the smoothly moving
// icon. Only the newest segment is created each call; existing segments are
// re-tinted/faded in place via setStyle instead of being torn down and
// rebuilt from scratch, which gets expensive with many tracked aircraft.
export function addTrailPoint(p, lat, lon) {
  const prev = p.trail.length ? p.trail[p.trail.length - 1] : null;
  p.trail.push([lat, lon]);
  if (p.trail.length > TRAIL_MAX_POINTS) {
    p.trail.shift();
    const oldest = p.trailSegments.shift();
    if (oldest) p.trailLayer.removeLayer(oldest);
  }

  const color = fillFor(p.cls, p.data && p.data.baro_altitude);

  if (prev) {
    const seg = L.polyline([prev, [lat, lon]], {
      color,
      weight: 4,
      opacity: TRAIL_MAX_OPACITY,
      interactive: false,
      className: "plane-trail",
    }).addTo(p.trailLayer);
    p.trailSegments.push(seg);
  }

  const segments = p.trailSegments.length;
  p.trailSegments.forEach((seg, i) => {
    const age = segments > 1 ? i / (segments - 1) : 1; // 0 = oldest, 1 = newest
    const opacity = TRAIL_MIN_OPACITY + (TRAIL_MAX_OPACITY - TRAIL_MIN_OPACITY) * age;
    seg.setStyle({ color, opacity });
  });
}

// Tweens the status-bar aircraft count instead of snapping to the new value.
let displayedCount = null;
let countAnimFrame = null;
function animateCount(target) {
  const el = document.getElementById("status-count");
  if (displayedCount == null) {
    displayedCount = target;
    el.textContent = t("aircraftCount", target);
    return;
  }
  if (target === displayedCount) return;
  cancelAnimationFrame(countAnimFrame);
  const start = displayedCount;
  const startTime = performance.now();
  const duration = 400;
  function step(now) {
    const frac = Math.min(1, (now - startTime) / duration);
    const eased = 1 - Math.pow(1 - frac, 3);
    const value = Math.round(start + (target - start) * eased);
    el.textContent = t("aircraftCount", value);
    if (frac < 1) {
      countAnimFrame = requestAnimationFrame(step);
    } else {
      displayedCount = target;
    }
  }
  countAnimFrame = requestAnimationFrame(step);
}

// Re-renders text that depends on the active language, using the most
// recently seen data. Called after the user switches languages.
let lastData = null;
let lastDailyCount = null;
export function refreshI18nTexts() {
  if (displayedCount != null) {
    document.getElementById("status-count").textContent = t("aircraftCount", displayedCount);
  }
  if (lastDailyCount != null) {
    document.getElementById("daily-count").textContent = t("dailyCount", lastDailyCount);
  }
  if (lastData) {
    const focused = lastData.aircraft.find((a) => a.icao24 === state.focusedIcao);
    updatePanel(focused);
  }
}

export function applyData(data) {
  lastData = data;
  state.home = { lat: data.home.lat, lon: data.home.lon };
  setHomeLocation(data.home.lat, data.home.lon);
  setFocusRadiusKm(data.focus_radius_km);
  applyTheme(data.is_daytime);
  if (data.focused_icao !== state.focusedIcao) {
    // New focus target (or focus cleared): a manual reset no longer applies.
    state.followSuppressed = false;
  }
  state.focusedIcao = data.focused_icao;
  const now = performance.now();
  const seen = new Set();

  for (const ac of data.aircraft) {
    if (ac.latitude == null || ac.longitude == null) continue;
    seen.add(ac.icao24);
    const cls = classFor(ac, state.focusedIcao);

    let p = planes.get(ac.icao24);
    if (!p) {
      const marker = L.marker([ac.latitude, ac.longitude], {
        icon: makePlaneIcon(ac.true_track, cls, ac.baro_altitude, ac.is_helicopter),
      }).addTo(map);
      marker.bindTooltip(ac.callsign || ac.icao24, {
        permanent: true,
        direction: "top",
        offset: [0, -10],
        className: "plane-label",
      });
      p = {};
      planes.set(ac.icao24, p);
      p.marker = marker;
      p.trail = [];
      p.trailSegments = [];
      p.trailLayer = L.layerGroup().addTo(map);
      p.lastTrailPush = 0;
    }
    // Store target position; interpolation animates toward reality.
    // Fall back to the last known velocity/track (rather than snapping to 0 /
    // due-north) when a poll momentarily omits them, so dead-reckoning
    // doesn't zig-zag off in the wrong direction for that interval.
    p.lat = ac.latitude;
    p.lon = ac.longitude;
    p.velocity = ac.velocity != null ? ac.velocity : (p.velocity || 0);  // m/s
    p.track = ac.true_track != null ? ac.true_track : (p.track || 0);   // deg
    p.lastUpdate = now;
    p.cls = cls;
    p.data = ac;

    // Rebuilding the divIcon (a fresh SVG DOM node) for every plane on every
    // poll caused a periodic hitch. The heading changes far more often than the
    // fill color, so only rebuild when the class or color actually changes;
    // otherwise just re-rotate the existing element in place.
    const fill = fillFor(cls, ac.baro_altitude);
    const heading = ac.true_track || 0;
    const iconKey = `${cls}|${fill}|${!!ac.is_helicopter}`;
    if (p.iconKey !== iconKey) {
      p.marker.setIcon(makePlaneIcon(heading, cls, ac.baro_altitude, ac.is_helicopter));
      p.iconKey = iconKey;
    } else {
      const inner = p.marker._icon && p.marker._icon.firstElementChild;
      if (inner) inner.style.transform = `rotate(${heading}deg)`;
    }

    const label = ac.callsign || ac.icao24;
    if (p.marker.getTooltip() && p.marker.getTooltip().getContent() !== label) {
      p.marker.setTooltipContent(label);
    }

    addTrailPoint(p, ac.latitude, ac.longitude);
    p.lastTrailPush = now;
  }

  processAlerts(data.aircraft, data.focus_radius_km);

  // Remove stale
  for (const [icao, p] of planes.entries()) {
    if (!seen.has(icao)) {
      map.removeLayer(p.marker);
      map.removeLayer(p.trailLayer);
      planes.delete(icao);
    }
  }

  const focused = data.aircraft.find((a) => a.icao24 === state.focusedIcao);
  updatePanel(focused);

  document.getElementById("status-updated").textContent =
    new Date().toLocaleTimeString();
  animateCount(data.count);

  if (data.daily_count != null) {
    lastDailyCount = data.daily_count;
    document.getElementById("daily-count").textContent = t("dailyCount", lastDailyCount);
  }
}
