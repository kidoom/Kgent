import type { AgentEvent, AgentStep, PermissionRequest, TurnState } from "../types/protocol";

export function emptyTurn(sessionId: string): TurnState {
  return {
    runId: null,
    sessionId,
    phase: "idle",
    steps: [],
    events: [],
    answer: null,
    error: null,
    pendingPermission: null,
  };
}

function appendEvent(state: TurnState, event: AgentEvent): TurnState {
  return { ...state, events: [...state.events, event] };
}

export interface RunTracker {
  /** Incremented on every sendMessage; used to ignore stale run events. */
  activeSerial: number;
  /** run_id -> serial when that run was started. */
  runSerialById: Map<string, number>;
  /** Current run_id once run_started arrives for the active serial. */
  activeRunId: string | null;
}

export function createRunTracker(): RunTracker {
  return {
    activeSerial: 0,
    runSerialById: new Map(),
    activeRunId: null,
  };
}

export function beginRun(tracker: RunTracker, sessionId: string): TurnState {
  tracker.activeSerial += 1;
  tracker.activeRunId = null;
  return {
    ...emptyTurn(sessionId),
    phase: "running",
  };
}

export function resetRunTracker(tracker: RunTracker): void {
  tracker.activeSerial = 0;
  tracker.runSerialById.clear();
  tracker.activeRunId = null;
}

function parseStep(event: AgentEvent): AgentStep | null {
  const step = event.payload.step;
  if (!step || typeof step !== "object") return null;
  return step as AgentStep;
}

function parsePermission(event: AgentEvent): PermissionRequest | null {
  const req = event.payload.permission_request;
  if (!req || typeof req !== "object") return null;
  return req as PermissionRequest;
}

function isStaleRunEvent(tracker: RunTracker, event: AgentEvent): boolean {
  if (!event.run_id) {
    return false;
  }

  const knownSerial = tracker.runSerialById.get(event.run_id);

  // After send, before run_started: reject anything from older runs.
  if (tracker.activeRunId === null && knownSerial !== undefined) {
    return true;
  }

  if (knownSerial !== undefined && knownSerial !== tracker.activeSerial) {
    return true;
  }

  if (tracker.activeRunId !== null && event.run_id !== tracker.activeRunId) {
    return true;
  }

  // Handoff window: only run_started may arrive before the new run id is known.
  if (
    tracker.activeRunId === null &&
    tracker.activeSerial > 0 &&
    event.type !== "run_started"
  ) {
    return true;
  }

  return false;
}

/** Returns null when the event should be ignored (stale run). */
export function applyAgentEvent(
  prev: TurnState,
  event: AgentEvent,
  tracker: RunTracker,
): TurnState | null {
  if (isStaleRunEvent(tracker, event)) {
    return null;
  }

  const next = {
    ...prev,
    runId: event.run_id || prev.runId,
    sessionId: event.session_id || prev.sessionId,
  };

  switch (event.type) {
    case "run_started":
      tracker.runSerialById.set(event.run_id, tracker.activeSerial);
      tracker.activeRunId = event.run_id;
      return appendEvent(
        {
          ...emptyTurn(next.sessionId),
          runId: event.run_id,
          sessionId: next.sessionId,
          phase: "running",
        },
        event,
      );
    case "agent_step": {
      const step = parseStep(event);
      if (!step) return appendEvent(next, event);
      const steps = [...next.steps, step];
      const patch: Partial<TurnState> = { steps };
      if (step.type === "final" && step.content != null) {
        patch.answer = step.content;
        patch.phase = "done";
      }
      return appendEvent({ ...next, ...patch }, event);
    }
    case "permission_required": {
      const req = parsePermission(event);
      return appendEvent(
        {
          ...next,
          phase: "waiting_permission",
          pendingPermission: req,
        },
        event,
      );
    }
    case "permission_resolved":
      return appendEvent(
        {
          ...next,
          phase: "running",
          pendingPermission: null,
        },
        event,
      );
    case "run_finished": {
      tracker.activeRunId = null;
      const payloadSteps = event.payload.steps;
      const steps =
        Array.isArray(payloadSteps) && payloadSteps.length > 0
          ? (payloadSteps as AgentStep[])
          : next.steps;
      const answerFromPayload = event.payload.answer;
      const finalFromSteps = steps.find((step) => step.type === "final")?.content;
      return appendEvent(
        {
          ...next,
          phase: "done",
          steps,
          answer:
            answerFromPayload != null && String(answerFromPayload).length > 0
              ? String(answerFromPayload)
              : finalFromSteps ?? next.answer,
          pendingPermission: null,
          error: null,
        },
        event,
      );
    }
    case "run_failed":
    case "error":
      tracker.activeRunId = null;
      return appendEvent(
        {
          ...next,
          phase: "error",
          error: String(event.payload.error ?? "Unknown error"),
          pendingPermission: null,
        },
        event,
      );
    case "run_cancelled":
      tracker.activeRunId = null;
      return appendEvent(
        {
          ...next,
          phase: "done",
          error: "Run cancelled",
          pendingPermission: null,
        },
        event,
      );
    default:
      return appendEvent(next, event);
  }
}

export function applyConnectionLoss(prev: TurnState, detail?: string): TurnState {
  if (prev.phase !== "running" && prev.phase !== "waiting_permission") {
    return prev;
  }
  return {
    ...prev,
    phase: "error",
    error: detail ?? "Connection lost",
    pendingPermission: null,
  };
}
