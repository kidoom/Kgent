import type { AgentEvent, ConnectionStatus, PermissionDecision } from "../types/protocol";

export type EventHandler = (event: AgentEvent) => void;
export type StatusHandler = (status: ConnectionStatus, detail?: string) => void;

function apiBase(): string {
  const raw = import.meta.env.VITE_API_BASE;
  if (raw === undefined || raw === "") {
    return typeof window !== "undefined" && window.location.protocol === "file:"
      ? "http://127.0.0.1:8000"
      : "";
  }
  return raw.replace(/\/$/, "");
}

/** Build fetch/EventSource path: absolute when VITE_API_BASE set, else same-origin relative. */
function apiPath(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  const base = apiBase();
  return base ? `${base}${normalized}` : normalized;
}

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as {
      error?: { message?: string };
      detail?: { error?: { message?: string } } | string;
    };
    if (body.error?.message) {
      return body.error.message;
    }
    if (typeof body.detail === "object" && body.detail?.error?.message) {
      return body.detail.error.message;
    }
    if (typeof body.detail === "string") {
      return body.detail;
    }
    return response.statusText;
  } catch {
    return response.statusText;
  }
}

export class RuntimeHttpClient {
  private sessionId: string;
  private eventSource: EventSource | null = null;
  private onEvent: EventHandler;
  private onStatus: StatusHandler;
  private lastSeq = 0;
  private shouldReconnect = false;
  private reconnectTimer: number | null = null;
  private reconnectAttempts = 0;

  constructor(
    sessionId: string,
    onEvent: EventHandler,
    onStatus: StatusHandler,
    initialFromSeq = 0,
  ) {
    this.sessionId = sessionId;
    this.onEvent = onEvent;
    this.onStatus = onStatus;
    this.lastSeq = initialFromSeq;
  }

  get connected(): boolean {
    return this.eventSource?.readyState === EventSource.OPEN;
  }

  get lastEventSeq(): number {
    return this.lastSeq;
  }

  setLastSeq(seq: number): void {
    this.lastSeq = seq;
  }

  async connect(): Promise<void> {
    this.clearReconnectTimer();
    this.shouldReconnect = true;
    this.onStatus("connecting");

    try {
      const health = await fetch(apiPath("/health"));
      if (!health.ok) {
        throw new Error(`Health check failed (${health.status})`);
      }
    } catch (error) {
      this.onStatus("error", error instanceof Error ? error.message : "Backend unreachable");
      this.scheduleReconnect();
      return;
    }

    const eventsPath = apiPath(
      `/api/sessions/${encodeURIComponent(this.sessionId)}/events${
        this.lastSeq > 0 ? `?from_seq=${this.lastSeq}` : ""
      }`,
    );

    this.eventSource?.close();
    const es = new EventSource(eventsPath);
    this.eventSource = es;

    es.onopen = () => {
      this.reconnectAttempts = 0;
      this.onStatus("connected");
    };

    es.addEventListener("agent_event", (message) => {
      try {
        const event = JSON.parse((message as MessageEvent).data as string) as AgentEvent;
        if (event.type === "heartbeat") {
          return;
        }
        if (event.seq <= this.lastSeq) {
          return;
        }
        this.lastSeq = event.seq;
        this.onEvent(event);
      } catch {
        this.onStatus("error", "Failed to parse server event");
      }
    });

    es.onerror = () => {
      es.close();
      this.eventSource = null;
      if (this.shouldReconnect) {
        this.onStatus("disconnected", "SSE connection lost, retrying...");
        this.scheduleReconnect();
      }
    };
  }

  disconnect(): void {
    this.shouldReconnect = false;
    this.clearReconnectTimer();
    this.eventSource?.close();
    this.eventSource = null;
    this.onStatus("disconnected");
  }

  async sendMessage(message: string): Promise<{ run_id: string; session_id: string }> {
    const response = await fetch(apiPath(`/api/sessions/${encodeURIComponent(this.sessionId)}/messages`), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    if (!response.ok) {
      throw new Error(await readError(response));
    }
    return (await response.json()) as { run_id: string; session_id: string };
  }

  async resolvePermission(
    runId: string,
    permissionRequestId: string,
    decision: PermissionDecision,
  ): Promise<void> {
    const response = await fetch(apiPath(`/api/runs/${encodeURIComponent(runId)}/permission`), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        permission_request_id: permissionRequestId,
        decision,
      }),
    });
    if (!response.ok) {
      throw new Error(await readError(response));
    }
  }

  async cancelRun(runId: string): Promise<void> {
    const response = await fetch(apiPath(`/api/runs/${encodeURIComponent(runId)}/cancel`), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    if (!response.ok) {
      throw new Error(await readError(response));
    }
  }

  private scheduleReconnect(): void {
    if (!this.shouldReconnect || this.reconnectTimer != null) {
      return;
    }
    const delay = Math.min(800 * 2 ** this.reconnectAttempts, 8_000);
    this.reconnectAttempts += 1;
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      if (this.shouldReconnect) {
        void this.connect();
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
