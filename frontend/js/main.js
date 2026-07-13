// ---- Entry point: wires modules together and boots the app ----
import { clearInteractionTimeout } from "./map.js"; // sets up the Leaflet map & home marker as a side effect
import { ensureAudio } from "./audio.js";
import { applyData, refreshI18nTexts } from "./planes.js";
import { animate } from "./animate.js";
import { connect } from "./websocket.js";
import { resetView } from "./camera.js";
import { getLang, nextLang, onLangChange, applyStaticI18n } from "./i18n.js";
import { toggleWeather } from "./weather.js";

requestAnimationFrame(animate);
connect(applyData);

document.getElementById("reset-view").addEventListener("click", () => {
  clearInteractionTimeout();
  resetView();
});

// ---- Weather radar toggle ----
const weatherToggle = document.getElementById("weather-toggle");
weatherToggle.addEventListener("click", () => {
  const enabled = toggleWeather();
  weatherToggle.classList.toggle("active", enabled);
});
// Enabled by default on load; the button still lets the user turn it off.
weatherToggle.classList.toggle("active", toggleWeather());

// ---- Language toggle ----
const langToggle = document.getElementById("lang-toggle");
function updateLangToggleLabel() {
  langToggle.textContent = getLang().toUpperCase();
}
langToggle.addEventListener("click", () => nextLang());
onLangChange(() => {
  applyStaticI18n();
  updateLangToggleLabel();
  refreshI18nTexts();
});
applyStaticI18n();
updateLangToggleLabel();

// Unlock audio on first user interaction (browser autoplay policy)
function unlockAudio() {
  ensureAudio();
  document.removeEventListener("click", unlockAudio);
  document.removeEventListener("touchstart", unlockAudio);
}
document.addEventListener("click", unlockAudio);
document.addEventListener("touchstart", unlockAudio);

// Try to init audio on load too (works if page already has interaction permission)
ensureAudio();

