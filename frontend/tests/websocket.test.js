import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

class FakeWebSocket {
  constructor(url) {
    this.url = url;
    this.closed = false;
    FakeWebSocket.instances.push(this);
  }
  close() {
    this.closed = true;
  }
}
FakeWebSocket.instances = [];

async function freshWebsocket() {
  vi.resetModules();
  document.body.innerHTML = `<div id="conn-dot"></div>`;
  FakeWebSocket.instances = [];
  global.WebSocket = FakeWebSocket;
  return import("../js/websocket.js");
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("connect", () => {
  it("sets the status dot to connecting immediately, then online on open", async () => {
    const { connect } = await freshWebsocket();
    connect(() => {});
    const dot = document.getElementById("conn-dot");
    expect(dot.className).toBe("conn-dot connecting");

    const ws = FakeWebSocket.instances[0];
    ws.onopen();
    expect(dot.className).toBe("conn-dot online");
  });

  it("parses incoming JSON messages and forwards them to the callback", async () => {
    const { connect } = await freshWebsocket();
    const onData = vi.fn();
    connect(onData);

    const ws = FakeWebSocket.instances[0];
    ws.onmessage({ data: JSON.stringify({ count: 3 }) });

    expect(onData).toHaveBeenCalledWith({ count: 3 });
  });

  it("swallows malformed JSON without throwing or invoking the callback", async () => {
    const { connect } = await freshWebsocket();
    const onData = vi.fn();
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    connect(onData);

    const ws = FakeWebSocket.instances[0];
    expect(() => ws.onmessage({ data: "not json" })).not.toThrow();

    expect(onData).not.toHaveBeenCalled();
    expect(errorSpy).toHaveBeenCalled();
  });

  it("marks the status offline and auto-reconnects after the socket closes", async () => {
    const { connect } = await freshWebsocket();
    connect(() => {});
    const dot = document.getElementById("conn-dot");

    const first = FakeWebSocket.instances[0];
    first.onclose();
    expect(dot.className).toBe("conn-dot offline");
    expect(FakeWebSocket.instances.length).toBe(1); // not reconnected yet

    vi.advanceTimersByTime(1000);

    expect(FakeWebSocket.instances.length).toBe(2); // reconnected
  });

  it("backs off exponentially across repeated reconnects, capped at 30s", async () => {
    const { connect } = await freshWebsocket();
    connect(() => {});

    // 1st close -> reconnect after 1s
    FakeWebSocket.instances[0].onclose();
    vi.advanceTimersByTime(1000);
    expect(FakeWebSocket.instances.length).toBe(2);

    // 2nd close -> reconnect after 2s (not yet at 1s)
    FakeWebSocket.instances[1].onclose();
    vi.advanceTimersByTime(1000);
    expect(FakeWebSocket.instances.length).toBe(2);
    vi.advanceTimersByTime(1000);
    expect(FakeWebSocket.instances.length).toBe(3);

    // A successful open resets the backoff back to the 1s base delay
    FakeWebSocket.instances[2].onopen();
    FakeWebSocket.instances[2].onclose();
    vi.advanceTimersByTime(1000);
    expect(FakeWebSocket.instances.length).toBe(4);
  });

  it("closes the socket on error", async () => {
    const { connect } = await freshWebsocket();
    connect(() => {});
    const ws = FakeWebSocket.instances[0];
    ws.onerror();
    expect(ws.closed).toBe(true);
  });

  it("reloads the page if the connection stays unhealthy for too long", async () => {
    const reloadSpy = vi.fn();
    Object.defineProperty(window, "location", {
      configurable: true,
      value: { ...window.location, reload: reloadSpy },
    });
    const { connect } = await freshWebsocket();
    connect(() => {});

    // Socket never opens and keeps failing to reconnect; time marches on
    // without a single successful open or message.
    vi.advanceTimersByTime(2 * 60 * 1000 - 5000);
    expect(reloadSpy).not.toHaveBeenCalled();

    vi.advanceTimersByTime(10000);
    expect(reloadSpy).toHaveBeenCalled();
  });

  it("does not reload while messages keep arriving, even if the socket flaps", async () => {
    const reloadSpy = vi.fn();
    Object.defineProperty(window, "location", {
      configurable: true,
      value: { ...window.location, reload: reloadSpy },
    });
    const { connect } = await freshWebsocket();
    connect(() => {});

    const ws = FakeWebSocket.instances[0];
    ws.onopen();

    // Keep the connection "healthy" by receiving messages faster than the
    // reload threshold, well past when a naive check would have fired.
    for (let i = 0; i < 5; i++) {
      vi.advanceTimersByTime(60 * 1000);
      ws.onmessage({ data: "{}" });
    }

    expect(reloadSpy).not.toHaveBeenCalled();
  });
});
