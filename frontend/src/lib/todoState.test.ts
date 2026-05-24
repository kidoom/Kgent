import { describe, expect, it } from "vitest";

import type { AgentEvent } from "../types/protocol";
import { latestTodoState } from "./todoState";

describe("latestTodoState", () => {
  it("prefers live todo_state events over transcript entries", () => {
    const events: AgentEvent[] = [
      {
        type: "todo_state",
        run_id: "run_1",
        session_id: "sess_1",
        seq: 2,
        payload: {
          items: [{ id: "b", text: "live", status: "in_progress" }],
          rounds_since_todo_write: 0,
        },
      },
    ];

    const state = latestTodoState(
      [
        {
          entry_id: "evt_1",
          session_id: "sess_1",
          type: "todo_state",
          created_at: "2026-05-24T00:00:00Z",
          project_root: "D:/Kgent",
          schema_version: 1,
          payload: {
            items: [{ id: "a", text: "old", status: "pending" }],
          },
        },
      ],
      events,
    );

    expect(state?.items).toEqual([{ id: "b", text: "live", status: "in_progress" }]);
  });
});
