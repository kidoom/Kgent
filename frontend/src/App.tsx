import { useCallback, useEffect, useMemo, useState } from "react";
import { LoaderCircleIcon, PanelRightIcon, SparklesIcon } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
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

function AppStatePanel({
  title,
  description,
  detail,
  destructive = false,
}: {
  title: string;
  description: string;
  detail?: string | null;
  destructive?: boolean;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6">
      <Card className="w-full max-w-md">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Badge variant={destructive ? "destructive" : "secondary"}>
              <SparklesIcon data-icon="inline-start" />
              Kgent
            </Badge>
          </div>
          <CardTitle>{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        {detail ? (
          <CardContent>
            <Alert variant={destructive ? "destructive" : "default"}>
              <AlertTitle>{destructive ? "Startup error" : "Status"}</AlertTitle>
              <AlertDescription>{detail}</AlertDescription>
            </Alert>
          </CardContent>
        ) : null}
      </Card>
    </div>
  );
}

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
      <AppStatePanel
        title="Loading sessions"
        description="Pulling your saved threads and workspace state into the app."
      />
    );
  }

  if (bootError) {
    return (
      <AppStatePanel
        title="Couldn't start Kgent"
        description="The frontend connected, but session bootstrapping did not finish."
        detail={bootError}
        destructive
      />
    );
  }

  if (!activeSessionId) {
    return (
      <AppStatePanel
        title="No sessions available"
        description="Create a new thread to begin working with Kgent."
      />
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
    return window.innerWidth >= 1280;
  });
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);

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
    setWorkspaceError(null);
    try {
      await sendMessage(message);
    } catch (error) {
      onPendingUserMessage(null);
      setWorkspaceError(error instanceof Error ? error.message : String(error));
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
    <>
      <div
        className={cn(
          "flex h-screen min-h-0 flex-col overflow-hidden bg-background lg:grid lg:grid-cols-[320px_minmax(0,1fr)]",
          debugOpen && "xl:grid-cols-[320px_minmax(0,1fr)_384px]",
          !debugOpen && "xl:grid-cols-[320px_minmax(0,1fr)]",
        )}
      >
        <SessionSidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          loading={false}
          onSelect={onSelectSession}
          onCreate={() => void onCreateSession()}
          onDelete={(sessionId) => {
            setWorkspaceError(null);
            void onDeleteSession(sessionId).catch((error) => {
              setWorkspaceError(error instanceof Error ? error.message : String(error));
            });
          }}
        />

        <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden lg:h-screen">
          <StatusBar
            connectionStatus={connectionStatus}
            connectionDetail={connectionDetail}
            sessionId={turn.sessionId}
            runId={turn.runId}
            phase={turn.phase}
            onReconnect={reconnect}
          />

          <main className="mx-auto flex min-h-0 flex-1 w-full max-w-5xl flex-col gap-4 overflow-hidden px-4 py-4 lg:px-6 lg:py-6">
            <header className="shrink-0 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Badge variant="secondary">
                    <SparklesIcon data-icon="inline-start" />
                    Agent workspace
                  </Badge>
                  {loadingTranscript ? (
                    <Badge variant="outline">
                      <LoaderCircleIcon data-icon="inline-start" className="animate-spin" />
                      Syncing transcript
                    </Badge>
                  ) : null}
                </div>
                <div className="space-y-1">
                  <h1 className="text-2xl font-semibold tracking-tight">Build with Kgent</h1>
                  <p className="max-w-2xl text-sm text-muted-foreground">
                    Keep the conversation, live run state, and full execution trail in one place.
                  </p>
                </div>
              </div>

              <Button variant="outline" size="sm" onClick={() => setDebugOpen((open) => !open)}>
                <PanelRightIcon data-icon="inline-start" />
                {debugOpen ? "Hide runtime" : "Show runtime"}
              </Button>
            </header>

            {workspaceError ? (
              <Alert variant="destructive">
                <AlertTitle>Action failed</AlertTitle>
                <AlertDescription>{workspaceError}</AlertDescription>
              </Alert>
            ) : null}

            {turn.error ? (
              <Alert variant="destructive">
                <AlertTitle>Run error</AlertTitle>
                <AlertDescription>{turn.error}</AlertDescription>
              </Alert>
            ) : null}

            <TranscriptView
              messages={chatMessages}
              pendingUserMessage={pendingUserMessage}
              liveAssistantAnswer={liveAssistantAnswer}
            />

            <div className="shrink-0 bg-background pt-2">
              <ChatPanel disabled={inputDisabled} onSend={handleSend} />
            </div>
          </main>
        </div>

        {debugOpen ? (
          <aside className="hidden h-screen min-h-0 overflow-hidden border-l border-border bg-muted/20 xl:block">
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
          </aside>
        ) : null}
      </div>

      {debugOpen ? (
        <aside
          className="fixed inset-y-0 right-0 z-40 w-full max-w-[26rem] border-l border-border bg-background shadow-xl xl:hidden"
          aria-label="Runtime panel"
        >
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
        </aside>
      ) : null}

      {turn.pendingPermission ? (
        <PermissionDialog
          request={turn.pendingPermission}
          onAllow={() => resolvePermission("allow")}
          onDeny={() => resolvePermission("deny")}
          onCancelRun={cancelRun}
        />
      ) : null}
    </>
  );
}
