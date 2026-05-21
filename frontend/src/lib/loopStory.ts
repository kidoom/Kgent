/** Turn raw WS events into a readable agent-loop story (user turn → output). */

import type { AgentEvent, AgentStep } from "../types/protocol";
import type { DebugMessage } from "./formatMessage";

export interface ToolSchema {
  name: string;
  description: string;
  input_schema: Record<string, unknown>;
}

export interface LoopStory {
  userMessage: string | null;
  turns: LoopTurn[];
  finalAnswer: string | null;
  sessionMessageCount: number | null;
  error: string | null;
}

export interface LoopTurn {
  turnIndex: number;
  phases: StoryPhase[];
}

export type StoryPhase =
  | {
      kind: "prompt";
      messages: DebugMessage[];
      toolSchemas: ToolSchema[];
    }
  | {
      kind: "think";
      content: string;
    }
  | {
      kind: "tool_call";
      toolName: string;
      toolInput: Record<string, unknown>;
      decision: string | null;
      permissionDecision: string | null;
    }
  | {
      kind: "tool_result";
      toolName: string;
      content: string;
      isError: boolean;
    }
  | {
      kind: "final";
      content: string;
    };

function parseMessages(payload: Record<string, unknown>): DebugMessage[] {
  const raw = payload.messages;
  return Array.isArray(raw) ? (raw as DebugMessage[]) : [];
}

function parseStep(payload: Record<string, unknown>): AgentStep | null {
  const step = payload.step;
  return step && typeof step === "object" ? (step as AgentStep) : null;
}

function extractUserMessage(events: AgentEvent[]): string | null {
  const checkpoint = events.find(
    (event) =>
      event.type === "loop_checkpoint" &&
      event.payload.checkpoint === "after_user_append",
  );
  if (!checkpoint) return null;
  const messages = parseMessages(checkpoint.payload);
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (message.role === "user" && typeof message.content === "string") {
      return message.content;
    }
  }
  return null;
}

function collectSteps(events: AgentEvent[]): AgentStep[] {
  const fromStream: AgentStep[] = [];
  for (const event of events) {
    if (event.type !== "agent_step") continue;
    const step = parseStep(event.payload);
    if (step) fromStream.push(step);
  }
  if (fromStream.length > 0) {
    return fromStream;
  }
  const finished = events.find((event) => event.type === "run_finished");
  if (finished && Array.isArray(finished.payload.steps)) {
    return finished.payload.steps as AgentStep[];
  }
  return [];
}

function parseToolSchemas(payload: Record<string, unknown>): ToolSchema[] {
  const raw = payload.tool_schemas;
  if (!Array.isArray(raw)) return [];
  return raw as ToolSchema[];
}

function promptForTurn(events: AgentEvent[], turnIndex: number): StoryPhase | null {
  const checkpoint = events.find(
    (event) =>
      event.type === "loop_checkpoint" &&
      event.payload.checkpoint === "before_model_call" &&
      event.payload.turn_index === turnIndex,
  );
  if (!checkpoint) return null;
  return {
    kind: "prompt",
    messages: parseMessages(checkpoint.payload),
    toolSchemas: parseToolSchemas(checkpoint.payload),
  };
}

function permissionDecisionAfter(
  events: AgentEvent[],
  afterSeq: number,
): string | null {
  for (const event of events) {
    if (event.seq <= afterSeq) continue;
    if (event.type === "permission_resolved") {
      return String(event.payload.decision ?? "");
    }
    if (event.type === "agent_step" && parseStep(event.payload)?.type === "observe") {
      break;
    }
  }
  return null;
}

function buildTurnPhases(
  events: AgentEvent[],
  turnIndex: number,
  steps: AgentStep[],
): StoryPhase[] {
  const phases: StoryPhase[] = [];
  const prompt = promptForTurn(events, turnIndex);
  if (prompt) phases.push(prompt);

  let lastCallSeq = 0;
  for (const step of steps) {
    if (step.turn_index !== turnIndex) continue;
    switch (step.type) {
      case "think":
        if (step.content) {
          phases.push({ kind: "think", content: step.content });
        }
        break;
      case "call":
        lastCallSeq = events.find(
          (event) =>
            event.type === "agent_step" &&
            parseStep(event.payload)?.tool_use_id === step.tool_use_id,
        )?.seq ?? 0;
        phases.push({
          kind: "tool_call",
          toolName: step.tool_name ?? "?",
          toolInput: step.tool_input ?? {},
          decision: step.decision ?? null,
          permissionDecision: permissionDecisionAfter(events, lastCallSeq),
        });
        break;
      case "observe":
        phases.push({
          kind: "tool_result",
          toolName: step.tool_name ?? "?",
          content: step.content ?? "",
          isError: Boolean(step.is_error),
        });
        break;
      case "final":
        phases.push({ kind: "final", content: step.content ?? "" });
        break;
      default:
        break;
    }
  }
  return phases;
}

export function buildLoopStory(events: AgentEvent[]): LoopStory {
  const steps = collectSteps(events);
  const turnIndices = [...new Set(steps.map((step) => step.turn_index))].sort(
    (a, b) => a - b,
  );

  const turns: LoopTurn[] = turnIndices.map((turnIndex) => ({
    turnIndex,
    phases: buildTurnPhases(events, turnIndex, steps),
  }));

  const finished = events.find((event) => event.type === "run_finished");
  const failed = events.find(
    (event) => event.type === "run_failed" || event.type === "error",
  );

  return {
    userMessage: extractUserMessage(events),
    turns,
    finalAnswer: finished ? String(finished.payload.answer ?? "") : null,
    sessionMessageCount:
      finished && typeof finished.payload.message_count === "number"
        ? finished.payload.message_count
        : null,
    error: failed ? String(failed.payload.error ?? "Unknown error") : null,
  };
}
