import { FormEvent, useState } from "react";
import {
  ArrowUpIcon,
  ChevronDownIcon,
  MicIcon,
  PlusIcon,
  ShieldCheckIcon,
  SparklesIcon,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface Props {
  disabled: boolean;
  onSend: (message: string) => void;
}

export function ChatPanel({ disabled, onSend }: Props) {
  const [message, setMessage] = useState("");

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    const text = message.trim();
    if (!text || disabled) return;
    onSend(text);
    setMessage("");
  };

  return (
    <form
      className="rounded-xl border bg-card px-2 py-2 text-card-foreground shadow-sm"
      onSubmit={handleSubmit}
    >
      <div className="flex min-w-0 items-end gap-2">
        <Button type="button" variant="ghost" size="icon-sm" aria-label="Add context">
          <PlusIcon />
        </Button>

        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <label htmlFor="user-message" className="sr-only">
            Message
          </label>
          <Textarea
            id="user-message"
            rows={1}
            value={message}
            disabled={disabled}
            className="max-h-28 min-h-8 resize-none border-0 bg-transparent px-1 py-1.5 shadow-none focus-visible:ring-0"
            placeholder="Message Kgent..."
            onChange={(event) => setMessage(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                event.currentTarget.form?.requestSubmit();
              }
            }}
          />
          <div className="flex min-w-0 items-center justify-between gap-2">
            <Badge variant="secondary" className="shrink-0">
              <ShieldCheckIcon data-icon="inline-start" />
              Auto review
              <ChevronDownIcon data-icon="inline-end" />
            </Badge>
            <div className="flex shrink-0 items-center gap-1">
              <Badge variant="outline">
                <SparklesIcon data-icon="inline-start" />
                5.5 High
                <ChevronDownIcon data-icon="inline-end" />
              </Badge>
              <Button type="button" variant="ghost" size="icon-sm" aria-label="Voice input">
                <MicIcon />
              </Button>
            </div>
          </div>
        </div>

        <Button
          type="submit"
          size="icon-sm"
          disabled={disabled || !message.trim()}
          aria-label="Send message"
        >
          <ArrowUpIcon />
        </Button>
      </div>
    </form>
  );
}
