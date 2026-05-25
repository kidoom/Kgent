import { BracesIcon, ChevronsRightIcon, CommandIcon, MessageSquareTextIcon, WrenchIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { buildLoopStory, type StoryPhase, type ToolSchema } from "../lib/loopStory";
import { formatMessageContent, type DebugMessage } from "../lib/formatMessage";
import type { AgentEvent } from "../types/protocol";

interface Props {
  events: AgentEvent[];
}

const PHASE_LABELS: Record<StoryPhase["kind"], string> = {
  prompt: "Model request",
  think: "Model reasoning",
  tool_call: "Tool call",
  tool_result: "Tool result",
  final: "Final response",
};

function CodeBlock({ children, className }: { children: string; className?: string }) {
  return (
    <pre
      className={cn(
        "overflow-x-auto rounded-lg border bg-muted/40 p-3 font-mono text-xs leading-5 whitespace-pre-wrap",
        className,
      )}
    >
      {children}
    </pre>
  );
}

function TraceSection({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <section className={cn("rounded-lg border bg-background", className)}>{children}</section>;
}

function TraceHeader({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <div className={cn("border-b px-3 py-3", className)}>{children}</div>;
}

function TraceTitle({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <div className={cn("text-sm font-medium", className)}>{children}</div>;
}

function TraceDescription({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <p className={cn("mt-1 text-sm text-muted-foreground", className)}>{children}</p>;
}

function TraceBody({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <div className={cn("p-3", className)}>{children}</div>;
}

function ToolSchemasView({ schemas }: { schemas: ToolSchema[] }) {
  if (schemas.length === 0) {
    return <p className="text-sm text-muted-foreground">No tool schemas were included in this turn.</p>;
  }

  return (
    <ol className="flex flex-col gap-3">
      {schemas.map((schema) => (
        <li key={schema.name}>
          <TraceSection>
            <TraceHeader>
              <TraceTitle className="flex items-center gap-2">
                <WrenchIcon className="size-4 text-muted-foreground" />
                <code>{schema.name}</code>
              </TraceTitle>
              <TraceDescription>{schema.description}</TraceDescription>
            </TraceHeader>
            <TraceBody>
              <CodeBlock>{JSON.stringify(schema.input_schema, null, 2)}</CodeBlock>
            </TraceBody>
          </TraceSection>
        </li>
      ))}
    </ol>
  );
}

function CallModelRequestView({
  messages,
  toolSchemas,
}: {
  messages: DebugMessage[];
  toolSchemas: ToolSchema[];
}) {
  const system = messages.find((message) => message.role === "system");
  const userContext = messages.filter((message) => message.role !== "system");

  return (
    <div className="flex flex-col gap-3">
      <TraceSection>
        <TraceHeader>
          <TraceTitle>System prompt</TraceTitle>
          <TraceDescription>Created with the session and reused across turns.</TraceDescription>
        </TraceHeader>
        <TraceBody>
          {system ? (
            <CodeBlock>{formatMessageContent(system, 2000)}</CodeBlock>
          ) : (
            <p className="text-sm text-muted-foreground">No system message.</p>
          )}
        </TraceBody>
      </TraceSection>

      <TraceSection>
        <TraceHeader>
          <TraceTitle>User context</TraceTitle>
          <TraceDescription>Prior user, assistant, and tool-result messages.</TraceDescription>
        </TraceHeader>
        <TraceBody>
          {userContext.length === 0 ? (
            <p className="text-sm text-muted-foreground">No context messages yet.</p>
          ) : (
            <ol className="flex flex-col gap-3">
              {userContext.map((message, index) => (
                <li key={`${message.role}-${index}`} className="rounded-lg border bg-muted/20">
                  <div className="border-b px-3 py-2">
                    <Badge variant="outline">{message.role}</Badge>
                  </div>
                  <div className="p-3">
                    <CodeBlock>{formatMessageContent(message)}</CodeBlock>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </TraceBody>
      </TraceSection>

      <TraceSection>
        <TraceHeader>
          <TraceTitle>Tool schemas</TraceTitle>
          <TraceDescription>The model receives these callable tool contracts.</TraceDescription>
        </TraceHeader>
        <TraceBody>
          <ToolSchemasView schemas={toolSchemas} />
        </TraceBody>
      </TraceSection>
    </div>
  );
}

function PhaseBody({ phase }: { phase: StoryPhase }) {
  switch (phase.kind) {
    case "prompt":
      return <CallModelRequestView messages={phase.messages} toolSchemas={phase.toolSchemas} />;
    case "think":
      return <CodeBlock>{phase.content}</CodeBlock>;
    case "tool_call":
      return (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <Badge variant="secondary">
              <WrenchIcon data-icon="inline-start" />
              {phase.toolName}
            </Badge>
            {phase.decision ? <Badge variant="outline">{phase.decision}</Badge> : null}
            {phase.permissionDecision ? (
              <Badge variant="outline">permission: {phase.permissionDecision}</Badge>
            ) : null}
          </div>
          <CodeBlock>{JSON.stringify(phase.toolInput, null, 2)}</CodeBlock>
        </div>
      );
    case "tool_result":
      return (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            {phase.toolName} writes a tool result back into the session for the next model turn.
          </p>
          <CodeBlock className={phase.isError ? "border-destructive/30 text-destructive" : undefined}>
            {phase.content}
          </CodeBlock>
        </div>
      );
    case "final":
      return <CodeBlock>{phase.content}</CodeBlock>;
    default:
      return null;
  }
}

export function LoopTracePanel({ events }: Props) {
  if (events.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Send a message to see how Kgent moves from user input to model calls, tools, and final output.
      </p>
    );
  }

  const story = buildLoopStory(events);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        <Badge variant="outline">
          <MessageSquareTextIcon data-icon="inline-start" />
          User input
        </Badge>
        <ChevronsRightIcon className="size-3" />
        <Badge variant="outline">
          <CommandIcon data-icon="inline-start" />
          Model call
        </Badge>
        <ChevronsRightIcon className="size-3" />
        <Badge variant="outline">
          <WrenchIcon data-icon="inline-start" />
          Tools
        </Badge>
        <ChevronsRightIcon className="size-3" />
        <Badge variant="outline">
          <BracesIcon data-icon="inline-start" />
          Final output
        </Badge>
      </div>

      <TraceSection>
        <TraceHeader>
          <TraceTitle>User input</TraceTitle>
        </TraceHeader>
        <TraceBody>
          <CodeBlock>{story.userMessage ?? "Unknown"}</CodeBlock>
        </TraceBody>
      </TraceSection>

      {story.turns.map((turn) => (
        <TraceSection key={turn.turnIndex}>
          <TraceHeader>
            <TraceTitle>Loop turn {turn.turnIndex + 1}</TraceTitle>
            <TraceDescription>Max step iteration for this run.</TraceDescription>
          </TraceHeader>
          <TraceBody>
            {turn.phases.length === 0 ? (
              <p className="text-sm text-muted-foreground">No steps for this turn.</p>
            ) : (
              <ol className="flex flex-col gap-3">
                {turn.phases.map((phase, index) => (
                  <li key={`${phase.kind}-${index}`}>
                    <TraceSection
                      className={cn(
                        phase.kind === "think" && "border-l-4 border-l-violet-400",
                        phase.kind === "tool_call" && "border-l-4 border-l-amber-400",
                        phase.kind === "tool_result" && "border-l-4 border-l-emerald-400",
                        phase.kind === "final" && "border-l-4 border-l-sky-400",
                      )}
                    >
                      <TraceHeader>
                        <Badge variant="secondary">{PHASE_LABELS[phase.kind]}</Badge>
                      </TraceHeader>
                      <TraceBody>
                        <PhaseBody phase={phase} />
                      </TraceBody>
                    </TraceSection>
                  </li>
                ))}
              </ol>
            )}
          </TraceBody>
        </TraceSection>
      ))}

      <TraceSection>
        <TraceHeader>
          <TraceTitle>Final output</TraceTitle>
        </TraceHeader>
        <TraceBody className="space-y-3">
          {story.error ? <CodeBlock className="border-destructive/30 text-destructive">{story.error}</CodeBlock> : null}
          {story.finalAnswer ? (
            <CodeBlock>{story.finalAnswer}</CodeBlock>
          ) : !story.error ? (
            <p className="text-sm text-muted-foreground">Waiting for the run to finish.</p>
          ) : null}
          {story.sessionMessageCount != null ? (
            <p className="text-xs text-muted-foreground">
              Session now contains {story.sessionMessageCount} messages.
            </p>
          ) : null}
        </TraceBody>
      </TraceSection>

      <details className="rounded-lg border bg-background p-3">
        <summary className="cursor-pointer text-sm font-medium">Raw SSE events</summary>
        <div className="mt-3">
          <CodeBlock>{JSON.stringify(events, null, 2)}</CodeBlock>
        </div>
      </details>
    </div>
  );
}
