import { useCallback, useEffect, useMemo, useState } from "react";

import { ChatPanel } from "./components/ChatPanel";
import { DebugDrawer } from "./components/DebugDrawer";
import { PermissionDialog } from "./components/PermissionDialog";
import { SessionSidebar } from "./components/SessionSidebar";
import { StatusBar } from "./components/StatusBar";
import { TranscriptView } from "./components/TranscriptView";
import { useRuntimeHttp } from "./hooks/useRuntimeHttp";
import {
  createSession,
  deleteSession,
  getTranscript,
  listSessions,
  maxAgentEventSeq,
  mergeLiveAgentEvents,
  transcriptAgentEvents,
  type SessionSummary,
} from "./lib/sessionApi";
import { configuredSessionId, persistSessionId, readStoredSessionId } from "./lib/sessionId";
import { latestTodoState } from "./lib/todoState";
import { chatMessagesFromTranscript } from "./lib/transcript";

export function App() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [transcriptEntries, setTranscriptEntries] = useState<
    Awaited<ReturnType<typeof getTranscript>>["entries"]
  >([]);
  const [pendingUserMessage, setPendingUserMessage] = useState<string | null>(null);
  const [loadingSessions, setLoadingSessions] = useState(true);
  const [loadingTranscript, setLoadingTranscript] = useState(false);
  const [bootError, setBootError] = useState<string | null>(null);

  const refreshSessions = useCallback(async () => {
    const items = await listSessions();
    setSessions(items);
    return items;
  }, []);

  const loadTranscript = useCallback(async (sessionId: string) => {
    setLoadingTranscript(true);
    try {
      const body = await getTranscript(sessionId);
      setTranscriptEntries(body.entries);
    } finally {
      setLoadingTranscript(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      setLoadingSessions(true);
      setBootError(null);
      try {
        const configured = configuredSessionId();
        let items = await listSessions();
        const stored = configured ?? readStoredSessionId();
        if (stored && items.some((item) => item.session_id === stored)) {
          if (cancelled) return;
          setSessions(items);
          setActiveSessionId(stored);
          return;
        }
        const latestEmpty = items.find(
          (item) => item.message_count === 0 && item.event_count === 0,
        );
        let initial = latestEmpty?.session_id ?? items[0]?.session_id ?? null;
        if (!initial) {
          const created = await createSession();
          items = await listSessions();
          if (!configured) {
            persistSessionId(created);
          }
          initial = created;
        }
        if (cancelled) return;
        setSessions(items);
        if (!configured && initial) {
          persistSessionId(initial);
        }
        setActiveSessionId(initial);
      } catch (error) {
        if (!cancelled) {
          setBootError(error instanceof Error ? error.message : "Failed to load sessions");
        }
      } finally {
        if (!cancelled) {
          setLoadingSessions(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!activeSessionId) return;
    persistSessionId(activeSessionId);
    void loadTranscript(activeSessionId);
    setPendingUserMessage(null);
  }, [activeSessionId, loadTranscript]);

  const reloadActiveTranscript = useCallback(async () => {
    if (!activeSessionId) return;
    await loadTranscript(activeSessionId);
  }, [activeSessionId, loadTranscript]);

  const handleDeleteSession = useCallback(
    async (sessionId: string) => {
      await deleteSession(sessionId);
      const remaining = await refreshSessions();
      if (sessionId !== activeSessionId) {
        return;
      }
      setTranscriptEntries([]);
      setPendingUserMessage(null);
      const next = remaining.find((item) => item.session_id !== sessionId)?.session_id ?? null;
      if (next) {
        persistSessionId(next);
        setActiveSessionId(next);
        return;
      }
      const created = await createSession();
      persistSessionId(created);
      await refreshSessions();
      setActiveSessionId(created);
    },
    [activeSessionId, refreshSessions],
  );

  if (loadingSessions && !activeSessionId) {
    return (
      <div className="app">
        <p className="muted">Loading sessions...</p>
      </div>
    );
  }

  if (bootError) {
    return (
      <div className="app">
        <div className="banner banner-error">{bootError}</div>
      </div>
    );
  }

  if (!activeSessionId) {
    return (
      <div className="app">
        <p className="muted">No sessions available.</p>
      </div>
    );
  }

  return (
    <AppShell
      sessions={sessions}
      activeSessionId={activeSessionId}
      transcriptEntries={transcriptEntries}
      loadingTranscript={loadingTranscript}
      pendingUserMessage={pendingUserMessage}
      onSelectSession={setActiveSessionId}
      onCreateSession={async () => {
        const sessionId = await createSession();
        persistSessionId(sessionId);
        await refreshSessions();
        setActiveSessionId(sessionId);
      }}
      onDeleteSession={handleDeleteSession}
      onSessionsRefresh={refreshSessions}
      onPendingUserMessage={setPendingUserMessage}
      onTranscriptReload={reloadActiveTranscript}
    />
  );
}

function AppShell({
  sessions,
  activeSessionId,
  transcriptEntries,
  loadingTranscript,
  pendingUserMessage,
  onSelectSession,
  onCreateSession,
  onSessionsRefresh,
  onPendingUserMessage,
  onTranscriptReload,
  onDeleteSession,
}: {
  sessions: SessionSummary[];
  activeSessionId: string;
  transcriptEntries: Awaited<ReturnType<typeof getTranscript>>["entries"];
  loadingTranscript: boolean;
  pendingUserMessage: string | null;
  onSelectSession: (sessionId: string) => void;
  onCreateSession: () => Promise<void>;
  onSessionsRefresh: () => Promise<SessionSummary[]>;
  onPendingUserMessage: (message: string | null) => void;
  onTranscriptReload: () => Promise<void>;
  onDeleteSession: (sessionId: string) => Promise<void>;
}) {
  const [debugOpen, setDebugOpen] = useState(() => {
    if (typeof window === "undefined") return true;
    return window.innerWidth >= 1180;
  });
  const lastHistoricalSeq = useMemo(
    () => maxAgentEventSeq(transcriptEntries),
    [transcriptEntries],
  );
  const historicalEvents = useMemo(
    () => transcriptAgentEvents(transcriptEntries),
    [transcriptEntries],
  );
  const chatMessages = useMemo(
    () => chatMessagesFromTranscript(transcriptEntries),
    [transcriptEntries],
  );

  const {
    connectionStatus,
    connectionDetail,
    turn,
    isBusy,
    sendMessage,
    resolvePermission,
    cancelRun,
    reconnect,
  } = useRuntimeHttp(activeSessionId, lastHistoricalSeq);

  const mergedTraceEvents = useMemo(
    () => mergeLiveAgentEvents(historicalEvents, turn.events, lastHistoricalSeq),
    [historicalEvents, lastHistoricalSeq, turn.events],
  );
  const todoState = useMemo(
    () => latestTodoState(transcriptEntries, mergedTraceEvents),
    [mergedTraceEvents, transcriptEntries],
  );

  useEffect(() => {
    if (turn.phase === "done") {
      void onSessionsRefresh();
      void onTranscriptReload();
      onPendingUserMessage(null);
    }
  }, [onPendingUserMessage, onSessionsRefresh, onTranscriptReload, turn.phase]);

  const handleSend = async (message: string) => {
    onPendingUserMessage(message);
    try {
      await sendMessage(message);
    } catch (error) {
      onPendingUserMessage(null);
      alert(error instanceof Error ? error.message : String(error));
    }
  };

  const inputDisabled = connectionStatus !== "connected" || isBusy;
  const finalStep = turn.steps.find((step) => step.type === "final");
  const displayAnswer = turn.answer ?? finalStep?.content ?? null;
  const isWaiting =
    turn.phase === "running" || turn.phase === "waiting_permission";
  const hasAnswerInTranscript =
    displayAnswer != null &&
    chatMessages.some(
      (message) => message.role === "assistant" && message.text === displayAnswer,
    );
  const liveAssistantAnswer =
    displayAnswer != null && displayAnswer !== "" && !hasAnswerInTranscript
      ? displayAnswer
      : null;

  return (
    <div className={`app app-workspace ${debugOpen ? "debug-open" : "debug-closed"}`}>
      <SessionSidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        loading={false}
        onSelect={onSelectSession}
        onCreate={() => void onCreateSession()}
        onDelete={(sessionId) => {
          void onDeleteSession(sessionId).catch((error) => {
            alert(error instanceof Error ? error.message : String(error));
          });
        }}
      />

      <div className="workspace-main">
        <StatusBar
          connectionStatus={connectionStatus}
          connectionDetail={connectionDetail}
          sessionId={turn.sessionId}
          runId={turn.runId}
          phase={turn.phase}
          onReconnect={reconnect}
        />

        <main className="chat-workspace">
          <header className="chat-workspace-header">
            <div>
              <h1>Kgent</h1>
              <p className="muted">Local agent workspace</p>
            </div>
            <button
              type="button"
              className="btn-secondary debug-toggle"
              aria-expanded={debugOpen}
              onClick={() => setDebugOpen((open) => !open)}
            >
              {debugOpen ? "Hide debug" : "Show debug"}
            </button>
          </header>

          {turn.error ? <div className="banner banner-error chat-error">{turn.error}</div> : null}
          {loadingTranscript ? <p className="muted loading-transcript">Loading transcript...</p> : null}

          <TranscriptView
            messages={chatMessages}
            pendingUserMessage={pendingUserMessage}
            liveAssistantAnswer={liveAssistantAnswer}
          />

          <div className="composer-shell">
            <ChatPanel disabled={inputDisabled} onSend={handleSend} />
          </div>
        </main>
      </div>

      {debugOpen ? (
        <DebugDrawer
          events={mergedTraceEvents}
          connectionStatus={connectionStatus}
          connectionDetail={connectionDetail}
          sessionId={turn.sessionId}
          runId={turn.runId}
          phase={turn.phase}
          answer={displayAnswer}
          error={turn.error}
          isWaiting={isWaiting}
          todoState={todoState}
          onClose={() => setDebugOpen(false)}
          onReconnect={reconnect}
        />
      ) : null}

      {turn.pendingPermission && (
        <PermissionDialog
          request={turn.pendingPermission}
          onAllow={() => resolvePermission("allow")}
          onDeny={() => resolvePermission("deny")}
          onCancelRun={cancelRun}
        />
      )}
    </div>
  );
}
