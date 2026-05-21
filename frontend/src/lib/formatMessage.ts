/** Format debug message snapshots from loop_checkpoint events. */

export interface DebugMessage {
  role: string;
  content: string | ToolBlock[];
  assistant_text?: string | null;
}

interface ToolBlock {
  type: string;
  id?: string;
  name?: string;
  input?: Record<string, unknown>;
  tool_use_id?: string;
  content?: string;
  is_error?: boolean;
}

export function formatMessageContent(message: DebugMessage, maxLen = 600): string {
  if (typeof message.content === "string") {
    const text = message.content.trim();
    if (message.role === "system" && text.length > maxLen) {
      return `${text.slice(0, maxLen)}… (${text.length} chars total)`;
    }
    return text;
  }

  return message.content
    .map((block) => {
      if (block.type === "tool_use") {
        return `tool_use ${block.name ?? "?"}(${block.id ?? "?"}) ${JSON.stringify(block.input ?? {})}`;
      }
      if (block.type === "tool_result") {
        const flag = block.is_error ? " ERROR" : "";
        const body = (block.content ?? "").trim();
        const preview = body.length > 200 ? `${body.slice(0, 200)}…` : body;
        return `tool_result${flag} ← ${block.tool_use_id}: ${preview}`;
      }
      return JSON.stringify(block);
    })
    .join("\n");
}

export const CHECKPOINT_LABELS: Record<string, string> = {
  after_user_append: "User message appended to session",
  turn_begin: "Loop turn begin",
  before_plan_call: "Plan phase prompt assembled",
  before_model_call: "Act prompt assembled → call_model",
  after_plan: "After plan phase (think)",
  after_model: "After call_model",
  after_act: "After act phase",
  after_think_placeholder: "Placeholder think (tool_use only, no visible text)",
  after_permission: "After permission decision",
  after_tool: "Tool result appended to session",
  complete: "Turn complete — final answer",
};

export const EVENT_LABELS: Record<string, string> = {
  run_started: "Run started",
  loop_checkpoint: "Loop checkpoint",
  agent_step: "Agent step",
  tool_call_started: "Tool executing",
  permission_required: "Permission required",
  permission_resolved: "Permission resolved",
  run_finished: "Run finished",
  run_failed: "Run failed",
  run_cancelled: "Run cancelled",
  error: "Error",
};
