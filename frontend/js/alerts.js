// ---- Alert banner, flash & per-plane alert dedupe ----
import { playChime } from "./audio.js";
import { t } from "./i18n.js";

const alertedIcaos = new Set(); // planes we've already alerted for

const alertStack = document.getElementById("alert-stack");
const alertFlash = document.getElementById("alert-flash");

// Builds one banner element via DOM APIs (not innerHTML) so callsign/airline/
// reason text from aircraft data can never be interpreted as markup.
function createBannerEl(ac, isEmergency) {
  const el = document.createElement("div");
  el.className = `alert-banner-item${isEmergency ? " emergency" : ""}`;

  const icon = document.createElement("span");
  icon.className = "alert-icon";
  icon.textContent = isEmergency ? "🚨" : "✨";

  const textWrap = document.createElement("div");
  textWrap.className = "alert-text";

  const title = document.createElement("div");
  title.className = "alert-title";
  title.textContent = isEmergency
    ? t("emergency")
    : ac.aircraft_type_name || ac.aircraft_type || t("rareAircraft");

  const subtitle = document.createElement("div");
  subtitle.className = "alert-subtitle";
  if (isEmergency) {
    subtitle.textContent = ac.alert.reason || "";
  } else {
    const airline = ac.airline ? ` · ${ac.airline}` : "";
    subtitle.textContent = `${ac.callsign || ac.icao24}${airline}`;
  }

  textWrap.append(title, subtitle);
  el.append(icon, textWrap);
  return el;
}

function triggerAlert(ac) {
  const isEmergency = ac.alert && ac.alert.level === "emergency";
  const kind = isEmergency ? "emergency" : "gold";

  // --- Flash ---
  alertFlash.className = ""; // reset
  void alertFlash.offsetWidth; // force reflow to restart animation
  alertFlash.className = isEmergency ? "flash-red" : "flash-gold";

  // --- Banner (stacked: multiple can be visible at once) ---
  const el = createBannerEl(ac, isEmergency);
  alertStack.appendChild(el);
  requestAnimationFrame(() => el.classList.add("show"));

  const life = isEmergency ? 12000 : 7000;
  setTimeout(() => {
    el.classList.remove("show");
    el.classList.add("leaving");
    setTimeout(() => el.remove(), 500);
  }, life);

  // --- Sound ---
  playChime(kind);
}

// Fires alerts for newly-in-zone aircraft and forgets planes that have left,
// so re-entry can re-trigger the alert later.
export function processAlerts(aircraft, focusRadiusKm) {
  for (const ac of aircraft) {
    if (!ac.alert) continue;

    // Only alert for planes that are close (within focus radius) and airborne
    const inZone = ac.distance_km != null &&
      ac.distance_km <= focusRadiusKm && !ac.on_ground;
    if (!inZone) continue;

    // Fire once per plane
    if (!alertedIcaos.has(ac.icao24)) {
      alertedIcaos.add(ac.icao24);
      triggerAlert(ac);
    }
  }

  const presentIcaos = new Set(aircraft.map((a) => a.icao24));
  for (const icao of [...alertedIcaos]) {
    if (!presentIcaos.has(icao)) alertedIcaos.delete(icao);
  }
}
