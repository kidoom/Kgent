import { BotIcon, SparklesIcon, UserIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import type { ChatMessageView } from "../lib/transcript";
import { MarkdownRenderer } from "./MarkdownRenderer";

interface Props {
  messages: ChatMessageView[];
  pendingUserMessage?: string | null;
  liveAssistantAnswer?: string | null;
}

export function TranscriptView({ messages, pendingUserMessage, liveAssistantAnswer }: Props) {
  const isEmpty = messages.length === 0 && !pendingUserMessage && !liveAssistantAnswer;

  return (
    <ScrollArea className="min-h-0 flex-1 rounded-lg">
      {isEmpty ? (
        <Empty className="mx-auto mt-12 min-h-[26rem] max-w-2xl border border-dashed bg-card/70">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <SparklesIcon />
            </EmptyMedia>
            <EmptyTitle>Start with a concrete outcome.</EmptyTitle>
            <EmptyDescription>
              Ask Kgent to inspect code, draft a plan, run a tool, or change the app.
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : (
        <ul className="mx-auto flex w-full max-w-4xl flex-col gap-4 pb-4 pr-4">
          {messages.map((message) => (
            <li
              key={message.id}
              className={cn("flex", message.role === "user" ? "justify-end" : "justify-start")}
            >
              <Card
                className={cn(
                  "w-full max-w-3xl",
                  message.role === "user" && "max-w-2xl border-primary/20 bg-primary/5",
                )}
              >
                <CardHeader className="pb-0">
                  <Badge variant={message.role === "user" ? "default" : "secondary"}>
                    {message.role === "user" ? (
                      <UserIcon data-icon="inline-start" />
                    ) : (
                      <BotIcon data-icon="inline-start" />
                    )}
                    {message.role === "user" ? "You" : "Kgent"}
                  </Badge>
                </CardHeader>
                <CardContent className="py-4">
                  {message.text ? <MarkdownRenderer text={message.text} /> : null}
                </CardContent>
              </Card>
            </li>
          ))}

          {pendingUserMessage ? (
            <li className="flex justify-end">
              <Card className="w-full max-w-2xl border-dashed border-primary/30 bg-primary/5 opacity-85">
                <CardHeader className="pb-0">
                  <Badge>
                    <UserIcon data-icon="inline-start" />
                    You
                  </Badge>
                </CardHeader>
                <CardContent className="py-4">
                  <MarkdownRenderer text={pendingUserMessage} />
                </CardContent>
              </Card>
            </li>
          ) : null}

          {liveAssistantAnswer ? (
            <li className="flex justify-start">
              <Card className="w-full max-w-3xl border-dashed">
                <CardHeader className="pb-0">
                  <Badge variant="secondary">
                    <BotIcon data-icon="inline-start" />
                    Kgent
                  </Badge>
                </CardHeader>
                <CardContent className="py-4">
                  <MarkdownRenderer text={liveAssistantAnswer} />
                </CardContent>
              </Card>
            </li>
          ) : null}
        </ul>
      )}
    </ScrollArea>
  );
}
