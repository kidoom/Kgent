import type { AgentStep } from "../types/protocol";

interface Props {
  steps: AgentStep[];
}

const STEP_LABELS: Record<AgentStep["type"], string> = {
  think: "Think",
  call: "Call",
  observe: "Observe",
  final: "Final",
};

export function StepTimeline({ steps }: Props) {
  if (steps.length === 0) {
    return <p className="muted">No steps yet. Send a message to start a run.</p>;
  }

  return (
    <ol className="step-timeline">
      {steps.map((step, index) => (
        <li key={`${step.type}-${step.turn_index}-${index}`} className={`step step-${step.type}`}>
          <div className="step-header">
            <span className="step-badge">{STEP_LABELS[step.type]}</span>
            <span className="step-meta">turn {step.turn_index}</span>
            {step.type === "call" && step.decision && (
              <span className={`decision decision-${step.decision}`}>{step.decision}</span>
            )}
            {step.type === "observe" && step.is_error && (
              <span className="decision decision-deny">error</span>
            )}
          </div>
          {step.type === "call" && (
            <div className="step-body">
              <code>{step.tool_name}</code>
              {step.tool_input && (
                <pre>{JSON.stringify(step.tool_input, null, 2)}</pre>
              )}
            </div>
          )}
          {(step.type === "think" || step.type === "observe" || step.type === "final") && step.content && (
            <div className="step-body">{step.content}</div>
          )}
        </li>
      ))}
    </ol>
  );
}
