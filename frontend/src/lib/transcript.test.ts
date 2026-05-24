import { describe, expect, it } from "vitest";

import type { AgentEvent } from "../types/protocol";
import { mergeLiveAgentEvents } from "./sessionApi";
import { chatMessagesFromTranscript, type ChatMessageView } from "./transcript";

describe("chatMessagesFromTranscript", () => {
  it("parses user and assistant string messages", () => {
    const messages = chatMessagesFromTranscript([
      {
        entry_id: "evt_1",
        session_id: "sess_a",
        type: "message",
        created_at: "2026-05-22T10:00:00.000Z",
        project_root: "/tmp",
        schema_version: 1,
        payload: { role: "user", content: "hello", is_meta: false },
      },
      {
        entry_id: "evt_2",
        session_id: "sess_a",
        type: "message",
        created_at: "2026-05-22T10:00:01.000Z",
        project_root: "/tmp",
        schema_version: 1,
        payload: { role: "assistant", content: "hi", is_meta: false },
      },
    ]);
    expect(messages).toHaveLength(2);
    expect(messages[0].text).toBe("hello");
    expect(messages[1].text).toBe("hi");
  });

  it("hides tool_use and tool_result messages from chat transcript", () => {
    const messages = chatMessagesFromTranscript([
      {
        entry_id: "evt_3",
        session_id: "sess_a",
        type: "message",
        created_at: "2026-05-22T10:00:02.000Z",
        project_root: "/tmp",
        schema_version: 1,
        payload: {
          role: "assistant",
          content: [{ type: "tool_use", id: "toolu_1", name: "read_file", input: { path: "a" } }],
          assistant_text: "reading",
          is_meta: false,
        },
      },
      {
        entry_id: "evt_4",
        session_id: "sess_a",
        type: "message",
        created_at: "2026-05-22T10:00:03.000Z",
        project_root: "/tmp",
        schema_version: 1,
        payload: {
          role: "user",
          content: [
            { type: "tool_result", tool_use_id: "toolu_1", content: "body", is_error: false },
          ],
          is_meta: false,
        },
      },
    ]);
    expect(messages).toEqual([]);
  });

  it("skips meta context messages", () => {
    const messages = chatMessagesFromTranscript([
      {
        entry_id: "evt_meta",
        session_id: "sess_a",
        type: "message",
        created_at: "2026-05-22T10:00:00.000Z",
        project_root: "/tmp",
        schema_version: 1,
        payload: { role: "user", content: "context", is_meta: true },
      },
    ]);
    expect(messages).toEqual([]);
  });
});

describe("mergeLiveAgentEvents", () => {
  it("deduplicates replayed SSE events already in transcript history", () => {
    const historical: AgentEvent[] = [
      {
        type: "run_started",
        run_id: "run_1",
        session_id: "sess_a",
        seq: 1,
        payload: {},
      },
    ];
    const live: AgentEvent[] = [
      {
        type: "run_started",
        run_id: "run_1",
        session_id: "sess_a",
        seq: 1,
        payload: {},
      },
      {
        type: "run_finished",
        run_id: "run_1",
        session_id: "sess_a",
        seq: 2,
        payload: { answer: "done", message_count: 2, steps: [] },
      },
    ];
    const merged = mergeLiveAgentEvents(historical, live, 1);
    expect(merged).toHaveLength(2);
    expect(merged[1].type).toBe("run_finished");
  });
});

export type { ChatMessageView };
