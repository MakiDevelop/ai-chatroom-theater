import type {
  ClientMessage,
  ConnectionErrorEvent,
  ConnectionEventType,
  ReconnectEvent,
  ServerMessage,
} from "../types";

type Listener = (payload?: unknown) => void;

export class WebSocketClient {
  private ws: WebSocket | null = null;

  private readonly listeners = new Map<ConnectionEventType, Listener[]>();

  private reconnectAttempts = 0;

  private readonly maxReconnectAttempts = 3;

  private sessionId: string | null = null;

  private manuallyClosed = false;

  connect(sessionId: string): void {
    this.sessionId = sessionId;
    this.manuallyClosed = false;
    this.openSocket();
  }

  send(message: ClientMessage): void {
    if (this.ws?.readyState !== WebSocket.OPEN) {
      this.emit("send_error", { message: "WebSocket is not connected." });
      return;
    }

    this.ws.send(JSON.stringify(message));
  }

  on(type: ConnectionEventType, callback: Listener): void {
    const callbacks = this.listeners.get(type) ?? [];
    callbacks.push(callback);
    this.listeners.set(type, callbacks);
  }

  close(): void {
    this.manuallyClosed = true;
    this.ws?.close();
    this.ws = null;
  }

  private openSocket(): void {
    if (!this.sessionId) {
      return;
    }

    if (
      this.ws &&
      (this.ws.readyState === WebSocket.OPEN ||
        this.ws.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${location.host}/api/sessions/${this.sessionId}/ws`;
    this.ws = new WebSocket(wsUrl);

    this.ws.addEventListener("open", () => {
      this.reconnectAttempts = 0;
      this.emit("open");
    });

    this.ws.addEventListener("message", (event) => {
      const payload = JSON.parse(event.data) as ServerMessage;
      this.emit(payload.type, payload);
    });

    this.ws.addEventListener("error", () => {
      const message = "WebSocket 連線失敗。";
      this.emit("connection_error", { message } satisfies ConnectionErrorEvent);
    });

    this.ws.addEventListener("close", () => {
      this.emit("close");

      if (this.manuallyClosed) {
        return;
      }

      this.emit("connection_lost");

      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        return;
      }

      this.reconnectAttempts += 1;
      this.emit("reconnecting", {
        attempt: this.reconnectAttempts,
        maxAttempts: this.maxReconnectAttempts,
      } satisfies ReconnectEvent);

      window.setTimeout(() => {
        if (!this.manuallyClosed) {
          this.openSocket();
        }
      }, 800 * this.reconnectAttempts);
    });
  }

  private emit(type: ConnectionEventType, payload?: unknown): void {
    const callbacks = this.listeners.get(type);

    if (!callbacks) {
      return;
    }

    for (const callback of callbacks) {
      callback(payload);
    }
  }
}
