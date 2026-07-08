// ---- Day/night theme: applied from the server-computed sun position ----
// The server includes `is_daytime` (computed from the home location's real
// sunrise/sunset, see services/geo.py) in every payload; we just reflect
// that as a body class so CSS can swap the color scheme and map filter.
let currentIsDaytime = null;

export function applyTheme(isDaytime) {
  if (isDaytime == null || isDaytime === currentIsDaytime) return;
  currentIsDaytime = isDaytime;
  document.body.classList.toggle("theme-day", isDaytime);
  document.body.classList.toggle("theme-night", !isDaytime);
}

// Best-effort guess for the instant before the first server payload
// arrives, so there's no flash of the wrong theme on load.
export function applyInitialGuess() {
  const prefersLight =
    window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches;
  applyTheme(prefersLight);
}
