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

export function connect(onData) {
  let reconnectDelay = RECONNECT_BASE_MS;

  function open() {
    setStatus("connecting");
    const ws = new WebSocket(WS_URL);
    ws.onopen = () => {
      setStatus("online");
      reconnectDelay = RECONNECT_BASE_MS;
    };
    ws.onmessage = (e) => {
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
