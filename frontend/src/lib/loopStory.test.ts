import { describe, expect, it } from "vitest";

import { buildLoopStory } from "./loopStory";
import type { AgentEvent } from "../types/protocol";

describe("buildLoopStory", () => {
  it("builds user → loop turn → final answer narrative", () => {
    const events: AgentEvent[] = [
      {
        type: "loop_checkpoint",
        run_id: "r1",
        session_id: "s",
        seq: 2,
        payload: {
          checkpoint: "after_user_append",
          turn_index: -1,
          messages: [
            { role: "system", content: "You are Kgent" },
            { role: "user", content: "计算 8+8" },
          ],
        },
      },
      {
        type: "loop_checkpoint",
        run_id: "r1",
        session_id: "s",
        seq: 3,
        payload: {
          checkpoint: "before_model_call",
          turn_index: 0,
          tool_count: 3,
          tool_schemas: [
            {
              name: "calculator",
              description: "Evaluate math",
              input_schema: { type: "object", properties: { expression: { type: "string" } } },
            },
          ],
          messages: [
            { role: "system", content: "You are Kgent" },
            { role: "user", content: "计算 8+8" },
          ],
        },
      },
      {
        type: "agent_step",
        run_id: "r1",
        session_id: "s",
        seq: 4,
        payload: {
          step: { type: "think", turn_index: 0, content: "我来算一下" },
        },
      },
      {
        type: "agent_step",
        run_id: "r1",
        session_id: "s",
        seq: 5,
        payload: {
          step: {
            type: "call",
            turn_index: 0,
            tool_name: "calculator",
            tool_use_id: "t1",
            tool_input: { expression: "8+8" },
            decision: "allow",
          },
        },
      },
      {
        type: "agent_step",
        run_id: "r1",
        session_id: "s",
        seq: 6,
        payload: {
          step: {
            type: "observe",
            turn_index: 0,
            tool_name: "calculator",
            tool_use_id: "t1",
            content: "16",
          },
        },
      },
      {
        type: "loop_checkpoint",
        run_id: "r1",
        session_id: "s",
        seq: 7,
        payload: {
          checkpoint: "before_model_call",
          turn_index: 1,
          tool_count: 3,
          messages: [
            { role: "user", content: "计算 8+8" },
            {
              role: "user",
              content: [{ type: "tool_result", tool_use_id: "t1", content: "16" }],
            },
          ],
        },
      },
      {
        type: "agent_step",
        run_id: "r1",
        session_id: "s",
        seq: 8,
        payload: {
          step: { type: "final", turn_index: 1, content: "8+8=16" },
        },
      },
      {
        type: "run_finished",
        run_id: "r1",
        session_id: "s",
        seq: 9,
        payload: {
          answer: "8+8=16",
          message_count: 6,
          steps: [],
        },
      },
    ];

    const story = buildLoopStory(events);
    expect(story.userMessage).toBe("计算 8+8");
    expect(story.turns).toHaveLength(2);
    expect(story.turns[0].phases[0].kind).toBe("prompt");
    if (story.turns[0].phases[0].kind === "prompt") {
      expect(story.turns[0].phases[0].toolSchemas).toHaveLength(1);
    }
    expect(story.turns[0].phases.some((phase) => phase.kind === "tool_call")).toBe(true);
    expect(story.turns[1].phases.some((phase) => phase.kind === "final")).toBe(true);
    expect(story.finalAnswer).toBe("8+8=16");
  });
});
