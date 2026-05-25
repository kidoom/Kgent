import { MessageSquareTextIcon, PlusIcon, SparklesIcon, Trash2Icon } from "lucide-react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogMedia,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";
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
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function sessionTitle(session: SessionSummary): string {
  return session.title || session.session_id;
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
    <aside className="shrink-0 border-b border-border bg-muted/30 lg:min-h-0 lg:border-r lg:border-b-0">
      <div className="flex h-full min-h-0 flex-col gap-4 p-4">
        <div className="flex items-center gap-3">
          <div className="flex size-10 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
            <SparklesIcon className="size-5" />
          </div>
          <div className="min-w-0">
            <p className="text-xs font-medium tracking-[0.14em] text-muted-foreground uppercase">
              Local Agent
            </p>
            <h1 className="truncate text-lg font-semibold">Kgent</h1>
          </div>
        </div>

        <Card className="min-h-0 flex-1">
          <CardHeader className="border-b">
            <CardTitle className="text-sm">Threads</CardTitle>
            <CardDescription>Recent workspaces and live transcripts.</CardDescription>
            <CardAction className="flex items-center gap-2">
              <Badge variant="outline">{sessions.length}</Badge>
              <Button size="icon-sm" onClick={onCreate} aria-label="Create session">
                <PlusIcon />
              </Button>
            </CardAction>
          </CardHeader>
          <CardContent className="min-h-0 flex-1 py-4">
            {loading ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Spinner />
                <span>Loading threads...</span>
              </div>
            ) : null}

            <ScrollArea className="h-[min(50vh,26rem)] w-full lg:h-[calc(100vh-17rem)]">
              <ul className="flex w-full min-w-0 flex-col gap-2 pr-3">
                {sessions.map((session) => {
                  const isActive = session.session_id === activeSessionId;

                  return (
                    <li key={session.session_id} className="min-w-0">
                      <div
                        className={cn(
                          "grid w-full min-w-0 grid-cols-[minmax(0,1fr)_auto] items-start rounded-lg border bg-card transition-colors",
                          isActive && "border-primary/30 bg-primary/5",
                        )}
                      >
                        <button
                          type="button"
                          className="block w-full min-w-0 overflow-hidden px-3 py-3 text-left"
                          title={sessionTitle(session)}
                          onClick={() => onSelect(session.session_id)}
                        >
                          <div className="grid w-full min-w-0 grid-cols-[auto_minmax(0,1fr)] items-center gap-2">
                            <MessageSquareTextIcon className="size-4 shrink-0 text-muted-foreground" />
                            <span className="block min-w-0 overflow-hidden truncate whitespace-nowrap text-sm font-medium">
                              {sessionTitle(session)}
                            </span>
                          </div>
                          <div className="mt-2 flex min-w-0 items-center gap-2 text-xs text-muted-foreground">
                            <Badge className="shrink-0" variant={isActive ? "default" : "secondary"}>
                              {session.message_count} messages
                            </Badge>
                            <span className="min-w-0 truncate">{formatWhen(session.updated_at)}</span>
                          </div>
                        </button>

                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              className="mt-2 mr-2 shrink-0 text-muted-foreground"
                              aria-label={`Delete session ${sessionTitle(session)}`}
                            >
                              <Trash2Icon />
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent size="sm">
                            <AlertDialogHeader>
                              <AlertDialogMedia>
                                <Trash2Icon />
                              </AlertDialogMedia>
                              <AlertDialogTitle>Delete thread?</AlertDialogTitle>
                              <AlertDialogDescription>
                                This removes <strong>{sessionTitle(session)}</strong> and its saved
                                transcript.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>Keep it</AlertDialogCancel>
                              <AlertDialogAction
                                variant="destructive"
                                onClick={() => onDelete(session.session_id)}
                              >
                                Delete
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      </div>
                    </li>
                  );
                })}
              </ul>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </aside>
  );
}
