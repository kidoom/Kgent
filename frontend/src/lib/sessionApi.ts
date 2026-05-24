import type { AgentEvent } from "../types/protocol";

export interface SessionSummary {
  session_id: string;
  title: string;
  first_prompt: string;
  last_prompt: string;
  project_root: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  event_count: number;
}

export interface TranscriptEntry {
  entry_id: string;
  session_id: string;
  type: string;
  created_at: string;
  project_root: string;
  schema_version: number;
  payload: Record<string, unknown>;
}

export interface TranscriptResponse {
  session_id: string;
  entries: TranscriptEntry[];
  warnings: string[];
}

function apiPath(path: string): string {
  const raw = import.meta.env.VITE_API_BASE;
  const base = raw === undefined || raw === "" ? "" : raw.replace(/\/$/, "");
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return base ? `${base}${normalized}` : normalized;
}

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as {
      error?: { message?: string };
      detail?: { error?: { message?: string } } | string;
    };
    if (body.error?.message) return body.error.message;
    if (typeof body.detail === "object" && body.detail?.error?.message) {
      return body.detail.error.message;
    }
    if (typeof body.detail === "string") return body.detail;
    return response.statusText;
  } catch {
    return response.statusText;
  }
}

export async function listSessions(): Promise<SessionSummary[]> {
  const response = await fetch(apiPath("/api/sessions"));
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  const body = (await response.json()) as { sessions: SessionSummary[] };
  return body.sessions;
}

export async function createSession(): Promise<string> {
  const response = await fetch(apiPath("/api/sessions"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  const body = (await response.json()) as { session_id: string };
  return body.session_id;
}

export async function deleteSession(sessionId: string): Promise<void> {
  const response = await fetch(apiPath(`/api/sessions/${encodeURIComponent(sessionId)}`), {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
}

export async function getTranscript(sessionId: string): Promise<TranscriptResponse> {
  const response = await fetch(
    apiPath(`/api/sessions/${encodeURIComponent(sessionId)}/transcript`),
  );
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return (await response.json()) as TranscriptResponse;
}

export function maxAgentEventSeq(entries: TranscriptEntry[]): number {
  let maxSeq = 0;
  for (const entry of entries) {
    if (entry.type !== "agent_event") continue;
    const seq = entry.payload.seq;
    if (typeof seq === "number" && seq > maxSeq) {
      maxSeq = seq;
    }
  }
  return maxSeq;
}

export function transcriptAgentEvents(entries: TranscriptEntry[]): AgentEvent[] {
  const events: AgentEvent[] = [];
  for (const entry of entries) {
    if (entry.type !== "agent_event") continue;
    events.push(entry.payload as unknown as AgentEvent);
  }
  return events.sort((a, b) => a.seq - b.seq);
}

export function mergeLiveAgentEvents(
  historical: AgentEvent[],
  live: AgentEvent[],
  lastHistoricalSeq: number,
): AgentEvent[] {
  const liveTail = live.filter((event) => event.seq > lastHistoricalSeq);
  const seen = new Set(historical.map((event) => event.seq));
  const dedupedLive = liveTail.filter((event) => !seen.has(event.seq));
  return [...historical, ...dedupedLive];
}
