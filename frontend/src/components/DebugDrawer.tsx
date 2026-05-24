import { LoopTracePanel } from "./LoopTracePanel";
import type { AgentEvent, ConnectionStatus, RunPhase } from "../types/protocol";
import type { TodoStateView } from "../lib/todoState";

interface Props {
  events: AgentEvent[];
  connectionStatus: ConnectionStatus;
  connectionDetail: string | null;
  sessionId: string;
  runId: string | null;
  phase: RunPhase;
  answer: string | null;
  error: string | null;
  isWaiting: boolean;
  todoState: TodoStateView | null;
  onClose: () => void;
  onReconnect: () => void;
}

const STATUS_LABEL: Record<ConnectionStatus, string> = {
  disconnected: "Disconnected",
  connecting: "Connecting...",
  connected: "Connected",
  error: "Error",
};

export function DebugDrawer({
  events,
  connectionStatus,
  connectionDetail,
  sessionId,
  runId,
  phase,
  answer,
  error,
  isWaiting,
  todoState,
  onClose,
  onReconnect,
}: Props) {
  return (
    <aside className="debug-drawer" aria-label="Debug drawer">
      <div className="debug-drawer-header">
        <div>
          <h2>Runtime</h2>
          <p className="muted">SSE, run state, and loop trace</p>
        </div>
        <button type="button" className="btn-secondary" onClick={onClose}>
          Hide
        </button>
      </div>

      <section className="debug-section">
        <h3>Connection</h3>
        <dl className="debug-meta-list">
          <div>
            <dt>Status</dt>
            <dd>
              <span className={`status-dot status-${connectionStatus}`} />
              {STATUS_LABEL[connectionStatus]}
            </dd>
          </div>
          {connectionDetail ? (
            <div>
              <dt>Detail</dt>
              <dd>{connectionDetail}</dd>
            </div>
          ) : null}
          <div>
            <dt>Session</dt>
            <dd>{sessionId}</dd>
          </div>
          {runId ? (
            <div>
              <dt>Run</dt>
              <dd>{runId}</dd>
            </div>
          ) : null}
          <div>
            <dt>Phase</dt>
            <dd>{phase}</dd>
          </div>
        </dl>
        {connectionStatus !== "connected" && connectionStatus !== "connecting" ? (
          <button type="button" className="btn-secondary" onClick={onReconnect}>
            Reconnect
          </button>
        ) : null}
      </section>

      <section className="debug-section">
        <h3>Todo / Plan</h3>
        {todoState && todoState.items.length > 0 ? (
          <ul className="todo-list">
            {todoState.items.map((item) => (
              <li key={item.id} className={`todo-item todo-${item.status}`}>
                <span className="todo-marker">
                  {item.status === "completed"
                    ? "[x]"
                    : item.status === "in_progress"
                      ? "[>]"
                      : "[ ]"}
                </span>
                <span className="todo-text">{item.text}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">No todo plan yet.</p>
        )}
      </section>

      <section className="debug-section">
        <h3>Final Answer</h3>
        {error ? <div className="banner banner-error">{error}</div> : null}
        {isWaiting ? (
          <p className="muted">Waiting for run to finish...</p>
        ) : answer != null && answer !== "" ? (
          <div className="final-answer">{answer}</div>
        ) : phase === "done" ? (
          <p className="muted">(empty answer)</p>
        ) : (
          <p className="muted">No completed run yet.</p>
        )}
      </section>

      <section className="debug-section debug-section-trace">
        <h3>Agent Loop</h3>
        <LoopTracePanel events={events} />
      </section>
    </aside>
  );
}
