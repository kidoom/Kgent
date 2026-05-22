/** Mirror of backend app.runtime.protocol + messages.AgentStep */

export type AgentEventType =
  | "run_started"
  | "loop_checkpoint"
  | "agent_step"
  | "tool_call_started"
  | "permission_required"
  | "permission_resolved"
  | "tool_result"
  | "run_finished"
  | "run_failed"
  | "run_cancelled"
  | "error"
  | "heartbeat";

export type StepType = "think" | "call" | "observe" | "final";
export type PermissionDecision = "allow" | "deny";
export type RunPhase = "idle" | "connecting" | "running" | "waiting_permission" | "done" | "error";

export interface AgentStep {
  type: StepType;
  turn_index: number;
  content?: string | null;
  tool_use_id?: string | null;
  tool_name?: string | null;
  tool_input?: Record<string, unknown> | null;
  is_error?: boolean;
  decision?: "allow" | "deny" | "ask" | null;
}

export interface PermissionRequest {
  permission_request_id: string;
  run_id: string;
  session_id: string;
  tool_use_id: string;
  tool_name: string;
  risk_level: "low" | "medium" | "high";
  tool_input: Record<string, unknown>;
  reason?: string | null;
}

export interface AgentEvent {
  type: AgentEventType;
  run_id: string;
  session_id: string;
  seq: number;
  payload: Record<string, unknown>;
  created_at?: string;
}

export interface StartRunCommand {
  type: "start_run";
  session_id: string;
  message: string;
}

export interface PermissionDecisionCommand {
  type: "permission_decision";
  run_id: string;
  permission_request_id: string;
  decision: PermissionDecision;
  remember?: boolean;
}

export interface CancelRunCommand {
  type: "cancel_run";
  run_id: string;
}

export type RuntimeCommand = StartRunCommand | PermissionDecisionCommand | CancelRunCommand;

export type ConnectionStatus = "disconnected" | "connecting" | "connected" | "error";

export interface TurnState {
  runId: string | null;
  sessionId: string;
  phase: RunPhase;
  steps: AgentStep[];
  events: AgentEvent[];
  answer: string | null;
  error: string | null;
  pendingPermission: PermissionRequest | null;
}
