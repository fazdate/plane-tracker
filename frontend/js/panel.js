// ---- Focused-plane info panel ----
import { t } from "./i18n.js";

const panel = document.getElementById("info-panel");

// Airline logos are served by Kiwi.com's public CDN, keyed by IATA code.
// No API key needed; falls back to hidden if the airline/logo is unknown.
const LOGO_URL = (iata) => `https://images.kiwi.com/airlines/64/${iata}.png`;

function updateLogo(ac) {
  const logo = document.getElementById("info-logo");
  const iata = ac.airline_iata;
  if (!iata) {
    logo.classList.add("hidden");
    logo.removeAttribute("src");
    return;
  }
  logo.alt = ac.airline || iata;
  logo.onerror = () => logo.classList.add("hidden");
  logo.onload = () => logo.classList.remove("hidden");
  logo.src = LOGO_URL(iata);
}

// Build a "City, Country" label for an airport, falling back to its IATA
// code (or "???") when city/country data isn't available.
function formatAirport(name, country, iata) {
  if (name && country) return `${name}, ${country}`;
  if (name) return name;
  return iata || "???";
}

// Aircraft photo, via Planespotters.net's free public photo API (no key
// needed). Looked up by registration first, falling back to the ICAO24 hex
// code. Per their API terms we point <img>/<a> straight at the URLs they
// return (no rehosting) and credit the photographer with a link back.
// https://www.planespotters.net/photo/api
const PHOTO_API = "https://api.planespotters.net/pub/photos";
const photoCache = new Map(); // "reg:XXX" | "hex:xxx" -> Promise<photo|null>

function fetchPhoto(key, path) {
  if (!photoCache.has(key)) {
    photoCache.set(key, fetch(`${PHOTO_API}/${path}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        const p = data && data.photos && data.photos[0];
        if (!p) return null;
        return {
          src: (p.thumbnail_large || p.thumbnail).src,
          link: p.link,
          photographer: p.photographer,
        };
      })
      .catch(() => null));
  }
  return photoCache.get(key);
}

let currentPhotoTarget = null; // icao24 the photo panel currently reflects

async function updatePhoto(ac) {
  if (ac.icao24 === currentPhotoTarget) return; // already showing/loading this plane
  currentPhotoTarget = ac.icao24;
  const { icao24 } = ac;

  const wrap = document.getElementById("info-photo-wrap");
  const img = document.getElementById("info-photo");
  const credit = document.getElementById("info-photo-credit");
  wrap.classList.add("hidden");
  img.onerror = () => wrap.classList.add("hidden");

  let photo = null;
  if (ac.registration) {
    photo = await fetchPhoto(`reg:${ac.registration}`, `reg/${encodeURIComponent(ac.registration)}`);
  }
  if (!photo) {
    photo = await fetchPhoto(`hex:${icao24}`, `hex/${encodeURIComponent(icao24)}`);
  }
  if (icao24 !== currentPhotoTarget || !photo) return; // stale, or none found

  img.src = photo.src;
  img.alt = ac.registration ? t("photoOf", ac.registration) : t("aircraftPhoto");
  wrap.classList.remove("hidden");
}

let lastFocusedIcao = null;

export function updatePanel(ac) {
  if (!ac) { panel.classList.add("hidden"); lastFocusedIcao = null; return; }
  panel.classList.remove("hidden");

  // Play a short entrance animation whenever the focused plane changes
  // (not on every data refresh of the same plane).
  if (ac.icao24 !== lastFocusedIcao) {
    lastFocusedIcao = ac.icao24;
    panel.classList.remove("panel-pop");
    void panel.offsetWidth; // force reflow so the animation restarts
    panel.classList.add("panel-pop");
  }

  updateLogo(ac);
  updatePhoto(ac);
  document.getElementById("info-callsign").textContent = ac.callsign || ac.icao24;
  document.getElementById("info-airline").textContent = ac.airline || "—";
  document.getElementById("info-actype").textContent =
    ac.aircraft_type_name || ac.aircraft_type || "—";
  document.getElementById("info-reg").textContent = ac.registration || "—";

  // Route
  const route = ac.route;
  if (route && (route.origin_iata || route.destination_iata)) {
    const from = formatAirport(route.origin_name, route.origin_country, route.origin_iata);
    const to = formatAirport(route.destination_name, route.destination_country, route.destination_iata);
    document.getElementById("info-route").textContent = `${from} → ${to}`;
  } else {
    document.getElementById("info-route").textContent = "—";
  }

  document.getElementById("info-alt").textContent =
    ac.baro_altitude != null ? `${Math.round(ac.baro_altitude)} m` : "—";
  document.getElementById("info-speed").textContent =
    ac.velocity != null ? `${Math.round(ac.velocity * 3.6)} km/h` : "—";
  document.getElementById("info-dist").textContent =
    ac.distance_km != null ? `${ac.distance_km} km` : "—";

  const badge = document.getElementById("info-badge");
  if (ac.alert) {
    badge.textContent = ac.alert.level;
    badge.className = `badge ${ac.alert.level}`;
  } else {
    badge.textContent = ""; badge.className = "badge";
  }
}
