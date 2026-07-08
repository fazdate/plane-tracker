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

  it("marks the status offline and auto-reconnects 2s after the socket closes", async () => {
    const { connect } = await freshWebsocket();
    connect(() => {});
    const dot = document.getElementById("conn-dot");

    const first = FakeWebSocket.instances[0];
    first.onclose();
    expect(dot.className).toBe("conn-dot offline");
    expect(FakeWebSocket.instances.length).toBe(1); // not reconnected yet

    vi.advanceTimersByTime(2000);

    expect(FakeWebSocket.instances.length).toBe(2); // reconnected
  });

  it("closes the socket on error", async () => {
    const { connect } = await freshWebsocket();
    connect(() => {});
    const ws = FakeWebSocket.instances[0];
    ws.onerror();
    expect(ws.closed).toBe(true);
  });
});
