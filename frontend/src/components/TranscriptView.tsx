import type { ChatMessageView } from "../lib/transcript";
import { MarkdownRenderer } from "./MarkdownRenderer";

interface Props {
  messages: ChatMessageView[];
  pendingUserMessage?: string | null;
  liveAssistantAnswer?: string | null;
}

export function TranscriptView({ messages, pendingUserMessage, liveAssistantAnswer }: Props) {
  const bubbleClass = (role: ChatMessageView["role"]) => {
    if (role === "user") return "chat-bubble chat-bubble-user";
    return "chat-bubble chat-bubble-assistant";
  };

  return (
    <div className="transcript-view">
      {messages.length === 0 && !pendingUserMessage && !liveAssistantAnswer ? (
        <p className="muted">No messages yet. Send a prompt to start.</p>
      ) : null}
      <ul className="chat-message-list">
        {messages.map((message) => (
          <li
            key={message.id}
            className={bubbleClass(message.role)}
          >
            <div className="chat-role">{message.role}</div>
            {message.text ? <MarkdownRenderer text={message.text} /> : null}
          </li>
        ))}
        {pendingUserMessage ? (
          <li className="chat-bubble chat-bubble-user chat-bubble-pending">
            <div className="chat-role">user</div>
            <MarkdownRenderer text={pendingUserMessage} />
          </li>
        ) : null}
        {liveAssistantAnswer ? (
          <li className="chat-bubble chat-bubble-assistant chat-bubble-live">
            <div className="chat-role">assistant</div>
            <MarkdownRenderer text={liveAssistantAnswer} />
          </li>
        ) : null}
      </ul>
    </div>
  );
}
