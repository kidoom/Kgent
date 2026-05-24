const STORAGE_KEY = "kgent_session_id";

function apiPath(path: string): string {
  const raw = import.meta.env.VITE_API_BASE;
  const base = raw === undefined || raw === "" ? "" : raw.replace(/\/$/, "");
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return base ? `${base}${normalized}` : normalized;
}

/** Explicit session override via VITE_SESSION_ID (e.g. shared dev session). */
export function configuredSessionId(): string | null {
  const raw = import.meta.env.VITE_SESSION_ID;
  if (typeof raw === "string" && raw.trim()) {
    return raw.trim();
  }
  return null;
}

export function readStoredSessionId(): string | null {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored || null;
  } catch {
    return null;
  }
}

export function persistSessionId(sessionId: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, sessionId);
  } catch {
    // private mode / storage blocked
  }
}

/**
 * Resolve a per-browser session id: env override > localStorage > POST /api/sessions.
 * Falls back to web-default only when the backend is unreachable.
 */
export async function resolveSessionId(): Promise<string> {
  const configured = configuredSessionId();
  if (configured) {
    return configured;
  }

  try {
    const stored = readStoredSessionId();
    if (stored) {
      return stored;
    }
  } catch {
    // private mode / storage blocked
  }

  try {
    const response = await fetch(apiPath("/api/sessions"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    if (response.ok) {
      const body = (await response.json()) as { session_id: string };
      persistSessionId(body.session_id);
      return body.session_id;
    }
  } catch {
    // backend not ready yet
  }

  return "web-default";
}
