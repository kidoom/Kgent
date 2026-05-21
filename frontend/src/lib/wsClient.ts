import type { AgentEvent, ConnectionStatus, RuntimeCommand } from "../types/protocol";

export type EventHandler = (event: AgentEvent) => void;
export type StatusHandler = (status: ConnectionStatus, detail?: string) => void;

const DEFAULT_WS_URL = "ws://127.0.0.1:8765/runtime";
const RECONNECT_BASE_MS = 800;
const RECONNECT_MAX_MS = 8_000;

export class RuntimeWsClient {
  private ws: WebSocket | null = null;
  private url: string;
  private onEvent: EventHandler;
  private onStatus: StatusHandler;
  private shouldReconnect = false;
  private reconnectTimer: number | null = null;
  private reconnectAttempts = 0;

  constructor(onEvent: EventHandler, onStatus: StatusHandler, url?: string) {
    this.url = url ?? import.meta.env.VITE_WS_URL ?? DEFAULT_WS_URL;
    this.onEvent = onEvent;
    this.onStatus = onStatus;
  }

  get connected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  connect(): void {
    this.clearReconnectTimer();
    if (this.ws?.readyState === WebSocket.OPEN || this.ws?.readyState === WebSocket.CONNECTING) {
      return;
    }
    this.shouldReconnect = true;
    this.onStatus("connecting");
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.onStatus("connected");
    };

    this.ws.onmessage = (message) => {
      try {
        const event = JSON.parse(message.data as string) as AgentEvent;
        this.onEvent(event);
      } catch {
        this.onStatus("error", "Failed to parse server event");
      }
    };

    this.ws.onerror = () => {
      this.onStatus("error", "WebSocket error");
    };

    this.ws.onclose = () => {
      this.ws = null;
      if (this.shouldReconnect) {
        this.onStatus("disconnected", "Connection closed — retrying…");
        this.scheduleReconnect();
      }
    };
  }

  disconnect(): void {
    this.shouldReconnect = false;
    this.clearReconnectTimer();
    this.ws?.close();
    this.ws = null;
    this.onStatus("disconnected");
  }

  send(command: RuntimeCommand): void {
    if (!this.connected || !this.ws) {
      throw new Error("WebSocket is not connected");
    }
    this.ws.send(JSON.stringify(command));
  }

  private scheduleReconnect(): void {
    if (!this.shouldReconnect || this.reconnectTimer != null) {
      return;
    }
    const delay = Math.min(
      RECONNECT_BASE_MS * 2 ** this.reconnectAttempts,
      RECONNECT_MAX_MS,
    );
    this.reconnectAttempts += 1;
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      if (this.shouldReconnect) {
        this.connect();
      }
    }, delay);
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer != null) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }
}
