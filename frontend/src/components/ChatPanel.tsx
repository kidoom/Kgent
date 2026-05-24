import { FormEvent, useState } from "react";

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
    <form className="chat-panel" onSubmit={handleSubmit}>
      <label htmlFor="user-message" className="sr-only">
        Message
      </label>
      <textarea
        id="user-message"
        rows={3}
        value={message}
        disabled={disabled}
        placeholder="Ask Kgent to inspect, explain, or change something..."
        onChange={(event) => setMessage(event.target.value)}
      />
      <button type="submit" disabled={disabled || !message.trim()}>
        Send
      </button>
    </form>
  );
}
