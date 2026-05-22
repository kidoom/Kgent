import { applyAgentEvent, beginRun, createRunTracker, emptyTurn } from "../lib/turnReducer";
import type { AgentEvent } from "../types/protocol";

describe("turnReducer stale run isolation", () => {
  const sessionId = "web-default";

  it("ignores late events from previous run during handoff window", () => {
    const tracker = createRunTracker();
    let turn = beginRun(tracker, sessionId);
    turn =
      applyAgentEvent(turn, makeEvent("run_started", "run_old"), tracker) ??
      turn;
    turn =
      applyAgentEvent(
        turn,
        makeEvent("run_finished", "run_old", { answer: "old", steps: [] }),
        tracker,
      ) ?? turn;
    expect(turn.phase).toBe("done");

    turn = beginRun(tracker, sessionId);
    const staleDuringHandoff = applyAgentEvent(
      turn,
      makeEvent("run_finished", "run_old", { answer: "old again", steps: [] }),
      tracker,
    );
    expect(staleDuringHandoff).toBeNull();
    expect(turn.phase).toBe("running");

    turn = applyAgentEvent(turn, makeEvent("run_started", "run_new"), tracker) ?? turn;
    turn =
      applyAgentEvent(
        turn,
        makeEvent("run_finished", "run_new", { answer: "new answer", steps: [] }),
        tracker,
      ) ?? turn;
    expect(turn.answer).toBe("new answer");
  });

  it("ignores late run_finished from a previous run after a new send", () => {
    const tracker = createRunTracker();
    let turn = beginRun(tracker, sessionId);

    turn =
      applyAgentEvent(turn, makeEvent("run_started", "run_old"), tracker) ??
      turn;
    turn =
      applyAgentEvent(
        turn,
        makeEvent("agent_step", "run_old", {
          step: { type: "final", turn_index: 0, content: "old answer" },
        }),
        tracker,
      ) ?? turn;

    turn = beginRun(tracker, sessionId);
    turn =
      applyAgentEvent(turn, makeEvent("run_started", "run_new"), tracker) ??
      turn;
    turn =
      applyAgentEvent(
        turn,
        makeEvent("agent_step", "run_new", {
          step: { type: "think", turn_index: 0, content: "thinking" },
        }),
        tracker,
      ) ?? turn;

    const stale = applyAgentEvent(
      turn,
      makeEvent("run_finished", "run_old", { answer: "old answer", steps: [] }),
      tracker,
    );
    expect(stale).toBeNull();
    expect(turn.phase).toBe("running");
    expect(turn.steps).toHaveLength(1);
  });

  it("completes the fourth turn after three prior runs", () => {
    const tracker = createRunTracker();
    let turn = emptyTurn(sessionId);

    for (const [runId, answer] of [
      ["run_1", "hello"],
      ["run_2", "16"],
      ["run_3", "readme summary"],
    ]) {
      turn = beginRun(tracker, sessionId);
      turn = applyAgentEvent(turn, makeEvent("run_started", runId), tracker) ?? turn;
      turn =
        applyAgentEvent(
          turn,
          makeEvent("agent_step", runId, {
            step: { type: "final", turn_index: 0, content: answer },
          }),
          tracker,
        ) ?? turn;
      turn =
        applyAgentEvent(
          turn,
          makeEvent("run_finished", runId, { answer, steps: [] }),
          tracker,
        ) ?? turn;
      expect(turn.phase).toBe("done");
    }

    turn = beginRun(tracker, sessionId);
    turn = applyAgentEvent(turn, makeEvent("run_started", "run_4"), tracker) ?? turn;
    turn =
      applyAgentEvent(
        turn,
        makeEvent("agent_step", "run_4", {
          step: { type: "final", turn_index: 0, content: "summary of readme" },
        }),
        tracker,
      ) ?? turn;
    turn =
      applyAgentEvent(
        turn,
        makeEvent("run_finished", "run_4", {
          answer: "summary of readme",
          steps: [],
        }),
        tracker,
      ) ?? turn;

    expect(turn.phase).toBe("done");
    expect(turn.answer).toBe("summary of readme");
  });

  it("parses structured run_failed error payload", () => {
    const tracker = createRunTracker();
    let turn = beginRun(tracker, sessionId);
    turn = applyAgentEvent(turn, makeEvent("run_started", "run_err"), tracker) ?? turn;
    turn =
      applyAgentEvent(
        turn,
        makeEvent("run_failed", "run_err", {
          error: { type: "model_error", message: "provider request failed" },
        }),
        tracker,
      ) ?? turn;
    expect(turn.phase).toBe("error");
    expect(turn.error).toBe("provider request failed");
  });
});

function makeEvent(
  type: AgentEvent["type"],
  runId: string,
  payload: Record<string, unknown> = {},
): AgentEvent {
  return {
    type,
    run_id: runId,
    session_id: "web-default",
    seq: 1,
    payload,
  };
}
