import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { RuntimeWsClient } from "../lib/wsClient";
import {
  applyAgentEvent,
  applyConnectionLoss,
  beginRun,
  createRunTracker,
  resetRunTracker,
} from "../lib/turnReducer";
import type { ConnectionStatus, RunPhase, TurnState } from "../types/protocol";

const DEFAULT_SESSION = "web-default";
const RUN_TIMEOUT_MS = 120_000;

export function useRuntimeWs(sessionId: string = DEFAULT_SESSION) {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("disconnected");
  const [connectionDetail, setConnectionDetail] = useState<string | null>(null);
  const [turn, setTurn] = useState<TurnState>(() => ({
    runId: null,
    sessionId,
    phase: "idle",
    steps: [],
    events: [],
    answer: null,
    error: null,
    pendingPermission: null,
  }));
  const clientRef = useRef<RuntimeWsClient | null>(null);
  const runTrackerRef = useRef(createRunTracker());
  const runTimeoutRef = useRef<number | null>(null);

  const clearRunTimeout = useCallback(() => {
    if (runTimeoutRef.current != null) {
      window.clearTimeout(runTimeoutRef.current);
      runTimeoutRef.current = null;
    }
  }, []);

  const armRunTimeout = useCallback(() => {
    clearRunTimeout();
    runTimeoutRef.current = window.setTimeout(() => {
      setTurn((prev) =>
        prev.phase === "running" || prev.phase === "waiting_permission"
          ? {
              ...prev,
              phase: "error",
              error: "Run timed out waiting for server response",
              pendingPermission: null,
            }
          : prev,
      );
      runTrackerRef.current.activeRunId = null;
    }, RUN_TIMEOUT_MS);
  }, [clearRunTimeout]);

  const handleEvent = useCallback(
    (event: Parameters<typeof applyAgentEvent>[1]) => {
      try {
        setTurn((prev) => {
          const next = applyAgentEvent(prev, event, runTrackerRef.current);
          return next ?? prev;
        });
        if (
          event.type === "run_finished" ||
          event.type === "run_failed" ||
          event.type === "run_cancelled" ||
          event.type === "error"
        ) {
          clearRunTimeout();
        }
      } catch (error) {
        clearRunTimeout();
        setTurn((prev) => ({
          ...prev,
          phase: "error",
          error: error instanceof Error ? error.message : "Failed to handle server event",
        }));
      }
    },
    [clearRunTimeout],
  );

  const handleStatus = useCallback(
    (status: ConnectionStatus, detail?: string) => {
      setConnectionStatus(status);
      setConnectionDetail(detail ?? null);
      if (status === "connected") {
        clearRunTimeout();
        resetRunTracker(runTrackerRef.current);
      }
      if (status === "disconnected" || status === "error") {
        clearRunTimeout();
        setTurn((prev) => applyConnectionLoss(prev, detail));
        resetRunTracker(runTrackerRef.current);
      }
    },
    [clearRunTimeout],
  );

  useEffect(() => {
    const client = new RuntimeWsClient(handleEvent, handleStatus);
    clientRef.current = client;
    client.connect();
    return () => {
      clearRunTimeout();
      client.disconnect();
      clientRef.current = null;
    };
  }, [clearRunTimeout, handleEvent, handleStatus]);

  const sendMessage = useCallback(
    (message: string) => {
      const client = clientRef.current;
      if (!client?.connected) {
        throw new Error("Not connected to runtime server");
      }
      clearRunTimeout();
      setTurn(beginRun(runTrackerRef.current, sessionId));
      armRunTimeout();
      try {
        client.send({ type: "start_run", session_id: sessionId, message });
      } catch (error) {
        clearRunTimeout();
        runTrackerRef.current.activeSerial -= 1;
        setTurn((prev) => ({
          ...prev,
          phase: "error",
          error: error instanceof Error ? error.message : "Failed to send message",
        }));
        throw error;
      }
    },
    [armRunTimeout, clearRunTimeout, sessionId],
  );

  const resolvePermission = useCallback(
    (decision: "allow" | "deny") => {
      const client = clientRef.current;
      const req = turn.pendingPermission;
      const runId = turn.runId;
      if (!client?.connected || !req || !runId) return;
      armRunTimeout();
      client.send({
        type: "permission_decision",
        run_id: runId,
        permission_request_id: req.permission_request_id,
        decision,
      });
    },
    [armRunTimeout, turn.pendingPermission, turn.runId],
  );

  const cancelRun = useCallback(() => {
    const client = clientRef.current;
    const runId = turn.runId;
    if (!client?.connected || !runId) return;
    client.send({ type: "cancel_run", run_id: runId });
  }, [turn.runId]);

  const reconnect = useCallback(() => {
    clientRef.current?.connect();
  }, []);

  const isBusy = useMemo(
    () => turn.phase === "running" || turn.phase === "waiting_permission",
    [turn.phase],
  );

  return {
    connectionStatus,
    connectionDetail,
    turn,
    isBusy,
    sendMessage,
    resolvePermission,
    cancelRun,
    reconnect,
  };
}

export type { RunPhase, TurnState };
