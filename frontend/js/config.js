// ---- Config & shared mutable state ----
export const WS_URL = `ws://${location.host}/ws`;

export const OVERVIEW_ZOOM = 12;
export const FOLLOW_ZOOM = 14;

// Altitude range (meters) used for color-coding plane icons: low=red, high=blue
export const ALTITUDE_COLOR_MIN_M = 0;
export const ALTITUDE_COLOR_MAX_M = 11000; // ~ typical airliner cruise altitude

// Shared state object, mutated in place by the modules that own each concern.
// Kept as a single object (rather than separate `let` exports) so all modules
// observe the same live values without needing setter functions.
export const state = {
  // Placeholder only, used for the very first frame before the server's
  // first payload arrives (see planes.js applyData, which overwrites this
  // and recenters the map). No real coordinates need to live in source
  // control this way.
  home: { lat: 0, lon: 0 },
  focusedIcao: null,
  cameraMode: "overview",      // "overview" | "following"
  followPanEnabled: true,      // keep camera centered on focused plane
  userInteracting: false,
  followSuppressed: false,     // true after manual "reset view" until focus target changes
};
