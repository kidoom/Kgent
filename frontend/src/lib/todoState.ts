import type { AgentEvent } from "../types/protocol";
import type { TranscriptEntry } from "./sessionApi";

export type TodoStatus = "pending" | "in_progress" | "completed";

export interface TodoItem {
  id: string;
  text: string;
  status: TodoStatus;
}

export interface TodoStateView {
  items: TodoItem[];
  updated_at?: string;
  rounds_since_todo_write?: number;
}

function parseTodoState(payload: Record<string, unknown>): TodoStateView | null {
  const rawItems = payload.items;
  if (!Array.isArray(rawItems)) return null;
  const items: TodoItem[] = [];
  for (const raw of rawItems) {
    if (typeof raw !== "object" || raw === null) return null;
    const item = raw as Record<string, unknown>;
    if (typeof item.id !== "string" || typeof item.text !== "string") return null;
    if (
      item.status !== "pending" &&
      item.status !== "in_progress" &&
      item.status !== "completed"
    ) {
      return null;
    }
    items.push({ id: item.id, text: item.text, status: item.status });
  }
  return {
    items,
    updated_at: typeof payload.updated_at === "string" ? payload.updated_at : undefined,
    rounds_since_todo_write:
      typeof payload.rounds_since_todo_write === "number"
        ? payload.rounds_since_todo_write
        : undefined,
  };
}

export function latestTodoState(
  entries: TranscriptEntry[],
  events: AgentEvent[],
): TodoStateView | null {
  let latest: TodoStateView | null = null;
  for (const entry of entries) {
    if (entry.type !== "todo_state") continue;
    latest = parseTodoState(entry.payload);
  }
  for (const event of events) {
    if (event.type !== "todo_state") continue;
    latest = parseTodoState(event.payload);
  }
  return latest;
}
