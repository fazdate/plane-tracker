// ---- WebSocket connection with auto-reconnect ----
import { WS_URL } from "./config.js";

const connDot = document.getElementById("conn-dot");

function setStatus(s) {
  if (!connDot) return;
  connDot.className = `conn-dot ${s}`;
}

// Reconnect backoff: start at 1s and double up to 30s so a prolonged outage
// doesn't hammer the server with a reconnect every 2s. Reset to the base
// delay once a connection successfully opens.
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;

// Health self-heal: kiosk tablets can't be manually refreshed, so if we've
// gone this long without hearing from the backend (repeated reconnect
// failures, a hung socket, etc.) just reload the whole page. A fresh load
// clears out any stuck app state and starts the reconnect cycle from zero.
const RELOAD_AFTER_MS = 2 * 60 * 1000;
const HEALTH_CHECK_INTERVAL_MS = 5000;

export function connect(onData) {
  let reconnectDelay = RECONNECT_BASE_MS;
  let lastOnlineAt = Date.now();

  setInterval(() => {
    if (Date.now() - lastOnlineAt > RELOAD_AFTER_MS) {
      console.warn(`No connection for over ${RELOAD_AFTER_MS}ms, reloading page...`);
      location.reload();
    }
  }, HEALTH_CHECK_INTERVAL_MS);

  function open() {
    setStatus("connecting");
    const ws = new WebSocket(WS_URL);
    ws.onopen = () => {
      setStatus("online");
      reconnectDelay = RECONNECT_BASE_MS;
      lastOnlineAt = Date.now();
    };
    ws.onmessage = (e) => {
      lastOnlineAt = Date.now();
      try { onData(JSON.parse(e.data)); }
      catch (err) { console.error("Bad message", err); }
    };
    ws.onclose = () => {
      setStatus("offline");
      console.warn(`WS closed, reconnecting in ${reconnectDelay}ms...`);
      setTimeout(open, reconnectDelay);
      reconnectDelay = Math.min(reconnectDelay * 2, RECONNECT_MAX_MS);
    };
    ws.onerror = () => ws.close();
  }

  open();
}
