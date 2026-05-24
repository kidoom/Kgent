import type { SessionSummary } from "../lib/sessionApi";

interface Props {
  sessions: SessionSummary[];
  activeSessionId: string | null;
  loading: boolean;
  onSelect: (sessionId: string) => void;
  onCreate: () => void;
  onDelete: (sessionId: string) => void;
}

function formatWhen(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export function SessionSidebar({
  sessions,
  activeSessionId,
  loading,
  onSelect,
  onCreate,
  onDelete,
}: Props) {
  return (
    <aside className="session-sidebar">
      <div className="session-sidebar-header">
        <h2>Sessions</h2>
        <button type="button" className="btn-secondary" onClick={onCreate}>
          New
        </button>
      </div>
      {loading ? <p className="muted">Loading sessions...</p> : null}
      <ul className="session-list">
        {sessions.map((session) => (
          <li key={session.session_id}>
            <div
              className={
                session.session_id === activeSessionId
                  ? "session-row session-row-active"
                  : "session-row"
              }
            >
              <button
                type="button"
                className="session-item"
                onClick={() => onSelect(session.session_id)}
              >
                <span className="session-title">{session.title || session.session_id}</span>
                <span className="session-meta">{formatWhen(session.updated_at)}</span>
              </button>
              <button
                type="button"
                className="session-delete"
                title="Delete session"
                aria-label={`Delete session ${session.title || session.session_id}`}
                onClick={() => onDelete(session.session_id)}
              >
                &times;
              </button>
            </div>
          </li>
        ))}
      </ul>
    </aside>
  );
}
