// ---- Plane marker icon & CSS class ----
import { ALTITUDE_COLOR_MIN_M, ALTITUDE_COLOR_MAX_M } from "./config.js";

const DEFAULT_FILL = "#ffe14d";

function planeSvg(fill) {
  return `<svg width="38" height="38" viewBox="0 0 24 24">
    <path fill="${fill}" stroke="rgba(0,0,0,0.85)" stroke-width="1.4" stroke-linejoin="round" paint-order="stroke fill" d="M12 2c-.5 0-1 .5-1 1.5V9L3 14v2l8-2.5V19l-2 1.5V22l3-1 3 1v-1.5L13 19v-5.5L21 16v-2l-8-5V3.5C13 2.5 12.5 2 12 2z"/>
  </svg>`;
}

// Top-down helicopter silhouette: main rotor bar, fuselage/cabin, tail boom
// with a small tail rotor - distinct enough from the fixed-wing icon at a
// glance while still rotating with heading like the plane icon does.
function helicopterSvg(fill) {
  return `<svg width="38" height="38" viewBox="0 0 24 24">
    <line x1="3" y1="5" x2="21" y2="5" stroke="rgba(0,0,0,0.85)" stroke-width="1.6" stroke-linecap="round"/>
    <path fill="${fill}" stroke="rgba(0,0,0,0.85)" stroke-width="1.4" stroke-linejoin="round" paint-order="stroke fill" d="M9.5 7.5h5c1.1 0 1.8 1 1.8 2.2v4.3c0 1-.7 1.8-1.6 1.8h-.4v3.6l1.4.6v1H8.3v-1l1.4-.6v-3.6h-.4c-.9 0-1.6-.8-1.6-1.8V9.7c0-1.2.7-2.2 1.8-2.2z"/>
    <line x1="15.2" y1="12" x2="20" y2="12" stroke="rgba(0,0,0,0.85)" stroke-width="1.3" stroke-linecap="round"/>
    <line x1="19" y1="10.3" x2="19" y2="13.7" stroke="rgba(0,0,0,0.85)" stroke-width="1.1" stroke-linecap="round"/>
  </svg>`;
}

// Interpolate hue from warm red/orange (low altitude) straight to hot
// magenta/violet (high altitude), deliberately skipping the green/cyan/blue
// range so markers never blend into the water, foliage or haze of the
// satellite basemap.
export function altitudeColor(altitudeM) {
  if (altitudeM == null) return DEFAULT_FILL;
  const min = ALTITUDE_COLOR_MIN_M;
  const max = ALTITUDE_COLOR_MAX_M;
  const t = Math.max(0, Math.min(1, (altitudeM - min) / (max - min)));
  const hue = t < 0.5 ? t * 2 * 45 : 300 + (t - 0.5) * 2 * 55; // 0-45 red->orange, then jump to 300-355 magenta->pink
  return `hsl(${hue.toFixed(0)}, 100%, 60%)`;
}

export function makePlaneIcon(heading, cssClass, altitudeM, isHelicopter) {
  const fill = colorForClass(cssClass) || altitudeColor(altitudeM);
  const svg = isHelicopter ? helicopterSvg(fill) : planeSvg(fill);
  const className = isHelicopter ? `plane-icon helicopter ${cssClass}` : `plane-icon ${cssClass}`;
  return L.divIcon({
    className,
    html: `<div style="transform: rotate(${heading || 0}deg);">${svg}</div>`,
    iconSize: [38, 38],
    iconAnchor: [19, 19],
  });
}

// Special states override altitude color-coding.
export function colorForClass(cssClass) {
  switch (cssClass) {
    case "emergency": return "var(--red)";
    // Solid white reads far better than the cyan accent, which blends into
    // water/sky on the satellite basemap; the cyan glow ring (see camera.js
    // and .plane-icon.focused in style.css) still ties it back to --accent.
    case "focused": return "#ffffff";
    case "rare": return "var(--gold)";
    case "grounded": return "var(--text-dim)";
    default: return null;
  }
}

export function classFor(ac, focusedIcao) {
  if (ac.alert && ac.alert.level === "emergency") return "emergency";
  if (ac.icao24 === focusedIcao) return "focused";
  if (ac.alert && ac.alert.level === "rare") return "rare";
  if (ac.on_ground) return "grounded";
  return "";
}
