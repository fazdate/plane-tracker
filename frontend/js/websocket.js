// ---- WebSocket connection with auto-reconnect ----
import { WS_URL } from "./config.js";

const connDot = document.getElementById("conn-dot");

function setStatus(s) {
  if (!connDot) return;
  connDot.className = `conn-dot ${s}`;
}

export function connect(onData) {
  setStatus("connecting");
  const ws = new WebSocket(WS_URL);
  ws.onopen = () => setStatus("online");
  ws.onmessage = (e) => {
    try { onData(JSON.parse(e.data)); }
    catch (err) { console.error("Bad message", err); }
  };
  ws.onclose = () => {
    setStatus("offline");
    console.warn("WS closed, reconnecting in 2s...");
    setTimeout(() => connect(onData), 2000);
  };
  ws.onerror = () => ws.close();
}
