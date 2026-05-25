import {
  AlertTriangleIcon,
  CheckCircle2Icon,
  LoaderCircleIcon,
  RefreshCwIcon,
  WifiIcon,
  WifiOffIcon,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ConnectionStatus, RunPhase } from "../types/protocol";

interface Props {
  connectionStatus: ConnectionStatus;
  connectionDetail: string | null;
  sessionId: string;
  runId: string | null;
  phase: RunPhase;
  onReconnect: () => void;
}

const STATUS_META: Record<
  ConnectionStatus,
  {
    badgeVariant: "default" | "secondary" | "outline" | "destructive";
    icon: typeof WifiIcon;
    label: string;
  }
> = {
  disconnected: {
    badgeVariant: "outline",
    icon: WifiOffIcon,
    label: "Disconnected",
  },
  connecting: {
    badgeVariant: "secondary",
    icon: LoaderCircleIcon,
    label: "Connecting",
  },
  connected: {
    badgeVariant: "default",
    icon: WifiIcon,
    label: "Connected",
  },
  error: {
    badgeVariant: "destructive",
    icon: AlertTriangleIcon,
    label: "Error",
  },
};

const PHASE_META: Record<
  RunPhase,
  {
    badgeVariant: "default" | "secondary" | "outline" | "destructive";
    icon: typeof CheckCircle2Icon;
    label: string;
  }
> = {
  idle: {
    badgeVariant: "outline",
    icon: CheckCircle2Icon,
    label: "Ready",
  },
  connecting: {
    badgeVariant: "secondary",
    icon: LoaderCircleIcon,
    label: "Connecting",
  },
  running: {
    badgeVariant: "secondary",
    icon: LoaderCircleIcon,
    label: "Running",
  },
  waiting_permission: {
    badgeVariant: "outline",
    icon: AlertTriangleIcon,
    label: "Needs review",
  },
  done: {
    badgeVariant: "default",
    icon: CheckCircle2Icon,
    label: "Completed",
  },
  error: {
    badgeVariant: "destructive",
    icon: AlertTriangleIcon,
    label: "Error",
  },
};

function shortId(value: string | null): string {
  if (!value) return "none";
  if (value.length <= 14) return value;
  return `${value.slice(0, 6)}...${value.slice(-4)}`;
}

export function StatusBar({
  connectionStatus,
  connectionDetail,
  sessionId,
  runId,
  phase,
  onReconnect,
}: Props) {
  const connectionMeta = STATUS_META[connectionStatus];
  const phaseMeta = PHASE_META[phase];
  const ConnectionIcon = connectionMeta.icon;
  const PhaseIcon = phaseMeta.icon;

  return (
    <header className="border-b border-border px-4 py-3 lg:px-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={connectionMeta.badgeVariant}>
              <ConnectionIcon data-icon="inline-start" className={connectionStatus === "connecting" ? "animate-spin" : undefined} />
              {connectionMeta.label}
            </Badge>
            <Badge variant={phaseMeta.badgeVariant}>
              <PhaseIcon data-icon="inline-start" className={phase === "running" || phase === "connecting" ? "animate-spin" : undefined} />
              {phaseMeta.label}
            </Badge>
          </div>
          {connectionDetail ? (
            <p className="truncate text-sm text-muted-foreground">{connectionDetail}</p>
          ) : null}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline">Session {shortId(sessionId)}</Badge>
          <Badge variant="outline">Run {shortId(runId)}</Badge>
          {connectionStatus !== "connected" && connectionStatus !== "connecting" ? (
            <Button variant="outline" size="sm" onClick={onReconnect}>
              <RefreshCwIcon data-icon="inline-start" />
              Reconnect
            </Button>
          ) : null}
        </div>
      </div>
    </header>
  );
}
