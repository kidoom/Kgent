import { ChatPanel } from "./components/ChatPanel";
import { LoopTracePanel } from "./components/LoopTracePanel";
import { PermissionDialog } from "./components/PermissionDialog";
import { StatusBar } from "./components/StatusBar";
import { useRuntimeWs } from "./hooks/useRuntimeWs";

const SESSION_ID = "web-default";

export function App() {
  const {
    connectionStatus,
    connectionDetail,
    turn,
    isBusy,
    sendMessage,
    resolvePermission,
    cancelRun,
    reconnect,
  } = useRuntimeWs(SESSION_ID);

  const handleSend = (message: string) => {
    try {
      sendMessage(message);
    } catch (error) {
      alert(error instanceof Error ? error.message : String(error));
    }
  };

  const inputDisabled = connectionStatus !== "connected" || isBusy;

  const finalStep = turn.steps.find((step) => step.type === "final");
  const displayAnswer = turn.answer ?? finalStep?.content ?? null;
  const isWaiting =
    turn.phase === "running" || turn.phase === "waiting_permission";

  return (
    <div className="app">
      <StatusBar
        connectionStatus={connectionStatus}
        connectionDetail={connectionDetail}
        sessionId={turn.sessionId}
        runId={turn.runId}
        phase={turn.phase}
        onReconnect={reconnect}
      />

      <main className="layout">
        <section className="panel">
          <h1>Kgent Runtime</h1>
          <p className="muted">
            调试视图：展示 agent loop 从用户输入到最终输出的完整过程。
          </p>
          <ChatPanel disabled={inputDisabled} onSend={handleSend} />
        </section>

        <section className="panel panel-wide">
          <h2>Agent Loop 流程</h2>
          <LoopTracePanel events={turn.events} />
        </section>

        <section className="panel">
          <h2>最终答案</h2>
          {turn.error && <div className="banner banner-error">{turn.error}</div>}
          {isWaiting ? (
            <p className="muted">Waiting for run to finish…</p>
          ) : displayAnswer != null && displayAnswer !== "" ? (
            <div className="final-answer">{displayAnswer}</div>
          ) : turn.phase === "done" ? (
            <p className="muted">(empty answer)</p>
          ) : (
            <p className="muted">Send a message to start.</p>
          )}
        </section>
      </main>

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
