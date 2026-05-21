import type { ConnectionStatus, RunPhase } from "../types/protocol";

interface Props {
  connectionStatus: ConnectionStatus;
  connectionDetail: string | null;
  sessionId: string;
  runId: string | null;
  phase: RunPhase;
  onReconnect: () => void;
}

const STATUS_LABEL: Record<ConnectionStatus, string> = {
  disconnected: "Disconnected",
  connecting: "Connecting…",
  connected: "Connected",
  error: "Error",
};

export function StatusBar({
  connectionStatus,
  connectionDetail,
  sessionId,
  runId,
  phase,
  onReconnect,
}: Props) {
  return (
    <header className="status-bar">
      <div>
        <span className={`status-dot status-${connectionStatus}`} />
        <span>{STATUS_LABEL[connectionStatus]}</span>
        {connectionDetail && <span className="muted"> — {connectionDetail}</span>}
      </div>
      <div className="status-meta">
        <span>session: {sessionId}</span>
        {runId && <span>run: {runId}</span>}
        <span>phase: {phase}</span>
      </div>
      {connectionStatus !== "connected" && connectionStatus !== "connecting" && (
        <button type="button" className="btn-secondary" onClick={onReconnect}>
          Reconnect
        </button>
      )}
    </header>
  );
}
