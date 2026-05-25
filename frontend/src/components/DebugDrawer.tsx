import {
  ActivityIcon,
  CheckCircle2Icon,
  ListTodoIcon,
  PanelRightIcon,
  RefreshCwIcon,
  ShieldAlertIcon,
  SparklesIcon,
} from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { LoopTracePanel } from "./LoopTracePanel";
import type { TodoStateView } from "../lib/todoState";
import type { AgentEvent, ConnectionStatus, RunPhase } from "../types/protocol";

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

function StatusBadge({ connectionStatus }: { connectionStatus: ConnectionStatus }) {
  const variant =
    connectionStatus === "connected"
      ? "default"
      : connectionStatus === "error"
        ? "destructive"
        : "outline";

  return <Badge variant={variant}>{connectionStatus}</Badge>;
}

function PhaseBadge({ phase }: { phase: RunPhase }) {
  const variant =
    phase === "done"
      ? "default"
      : phase === "error"
        ? "destructive"
        : phase === "idle"
          ? "outline"
          : "secondary";

  return <Badge variant={variant}>{phase.replace("_", " ")}</Badge>;
}

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
    <div className="flex h-full min-h-0 flex-col gap-4 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <SparklesIcon className="size-4 text-muted-foreground" />
            <p className="text-xs font-medium tracking-[0.14em] text-muted-foreground uppercase">
              Agent Runtime
            </p>
          </div>
          <h2 className="text-lg font-semibold">Control Panel</h2>
          <p className="text-sm text-muted-foreground">Connection, plan, output, and loop trace.</p>
        </div>
        <Button variant="ghost" size="icon-sm" onClick={onClose} aria-label="Hide runtime panel">
          <PanelRightIcon />
        </Button>
      </div>

      <ScrollArea className="min-h-0 flex-1">
        <div className="flex flex-col gap-4 pr-4">
          <Card>
            <CardHeader className="border-b">
              <CardTitle className="flex items-center gap-2">
                <ActivityIcon className="size-4 text-muted-foreground" />
                Live state
              </CardTitle>
              <CardDescription>Current connection and run metadata.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 py-4">
              <div className="grid gap-3 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-muted-foreground">Status</span>
                  <StatusBadge connectionStatus={connectionStatus} />
                </div>
                {connectionDetail ? (
                  <div className="space-y-1">
                    <span className="text-muted-foreground">Detail</span>
                    <p className="break-words">{connectionDetail}</p>
                  </div>
                ) : null}
                <div className="flex items-center justify-between gap-3">
                  <span className="text-muted-foreground">Session</span>
                  <code className="text-xs">{sessionId}</code>
                </div>
                {runId ? (
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-muted-foreground">Run</span>
                    <code className="text-xs">{runId}</code>
                  </div>
                ) : null}
                <div className="flex items-center justify-between gap-3">
                  <span className="text-muted-foreground">Phase</span>
                  <PhaseBadge phase={phase} />
                </div>
              </div>

              {connectionStatus !== "connected" && connectionStatus !== "connecting" ? (
                <Button variant="outline" size="sm" onClick={onReconnect}>
                  <RefreshCwIcon data-icon="inline-start" />
                  Reconnect
                </Button>
              ) : null}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="border-b">
              <CardTitle className="flex items-center gap-2">
                <ListTodoIcon className="size-4 text-muted-foreground" />
                Plan
              </CardTitle>
              <CardDescription>Latest todo state emitted during the run.</CardDescription>
            </CardHeader>
            <CardContent className="py-4">
              {todoState && todoState.items.length > 0 ? (
                <ul className="flex flex-col gap-2">
                  {todoState.items.map((item) => (
                    <li
                      key={item.id}
                      className={cn(
                        "rounded-lg border p-3",
                        item.status === "completed" && "border-emerald-200 bg-emerald-50/70",
                        item.status === "in_progress" && "border-amber-200 bg-amber-50/70",
                      )}
                    >
                      <div className="flex items-start gap-3">
                        <Badge
                          variant={
                            item.status === "completed"
                              ? "default"
                              : item.status === "in_progress"
                                ? "secondary"
                                : "outline"
                          }
                        >
                          {item.status === "completed" ? (
                            <CheckCircle2Icon data-icon="inline-start" />
                          ) : null}
                          {item.status.replace("_", " ")}
                        </Badge>
                        <p
                          className={cn(
                            "text-sm",
                            item.status === "completed" && "text-muted-foreground line-through",
                          )}
                        >
                          {item.text}
                        </p>
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-muted-foreground">No plan has been emitted yet.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="border-b">
              <CardTitle className="flex items-center gap-2">
                <ShieldAlertIcon className="size-4 text-muted-foreground" />
                Answer
              </CardTitle>
              <CardDescription>Latest final response captured from the active run.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 py-4">
              {error ? (
                <Alert variant="destructive">
                  <ShieldAlertIcon />
                  <AlertTitle>Run error</AlertTitle>
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              ) : null}

              {isWaiting ? (
                <p className="text-sm text-muted-foreground">Waiting for the run to finish...</p>
              ) : answer != null && answer !== "" ? (
                <div className="rounded-lg border bg-muted/30 p-3 text-sm leading-6 whitespace-pre-wrap">
                  {answer}
                </div>
              ) : phase === "done" ? (
                <p className="text-sm text-muted-foreground">(empty answer)</p>
              ) : (
                <p className="text-sm text-muted-foreground">No completed run yet.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="border-b">
              <CardTitle>Loop trace</CardTitle>
              <CardDescription>How the run moved through prompts, tools, and outputs.</CardDescription>
            </CardHeader>
            <CardContent className="py-4">
              <LoopTracePanel events={events} />
            </CardContent>
          </Card>
        </div>
      </ScrollArea>
    </div>
  );
}
