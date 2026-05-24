import type { TranscriptEntry } from "./sessionApi";

export interface ToolUseBlockView {
  type: "tool_use";
  id: string;
  name: string;
  input: Record<string, unknown>;
}

export interface ToolResultBlockView {
  type: "tool_result";
  tool_use_id: string;
  content: string;
  is_error: boolean;
}

export interface ChatMessageView {
  id: string;
  role: "user" | "assistant";
  text?: string;
}

export function chatMessagesFromTranscript(entries: TranscriptEntry[]): ChatMessageView[] {
  const messages: ChatMessageView[] = [];
  for (const entry of entries) {
    if (entry.type !== "message") continue;
    const payload = entry.payload;
    if (payload.is_meta === true) continue;
    const role = payload.role;
    if (role !== "user" && role !== "assistant") continue;
    const content = payload.content;
    if (typeof content === "string") {
      messages.push({ id: entry.entry_id, role, text: content });
      continue;
    }
  }
  return messages;
}
