"""Context compression for Kgent agent loop.

Phase 1: Safe trim + token estimator + compression config.
Phase 2+: Microcompact, AutoCompact, ReactiveCompact, Manual Compact.
Phase 3: Resume-time compact.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from app.runtime.messages import Message, ToolResultBlock, ToolUseBlock

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Token estimator
# ---------------------------------------------------------------------------


def _count_cjk(text: str) -> int:
    return sum(1 for ch in text if "一" <= ch <= "鿿")


def estimate_tokens(text: str) -> int:
    """Conservative char-based token estimate for mixed Chinese/English.

    English text: ~4 chars/token.  Chinese text: ~1-2 chars/token.
    CJK chars counted at 1.5 tokens each (conservative); rest at 1/3.
    """
    cjk = _count_cjk(text)
    non_cjk = len(text) - cjk
    return max(1, int(cjk * 1.5 + non_cjk / 3))


# Per-message structural overhead: role label, JSON delimiters, stop tokens.
_MESSAGE_OVERHEAD = 8


def estimate_message_tokens(message: Message) -> int:
    n = _MESSAGE_OVERHEAD
    if isinstance(message.content, str):
        n += estimate_tokens(message.content)
    elif isinstance(message.content, list):
        for block in message.content:
            if isinstance(block, ToolUseBlock):
                n += estimate_tokens(block.name)
                n += 4  # id + type overhead
                for v in block.input.values():
                    if isinstance(v, str):
                        n += estimate_tokens(v)
            elif isinstance(block, ToolResultBlock):
                n += estimate_tokens(block.content)
                n += 4  # id + type overhead
    if message.assistant_text:
        n += estimate_tokens(message.assistant_text)
    return n


def estimate_messages_tokens(messages: list[Message]) -> int:
    return sum(estimate_message_tokens(m) for m in messages)


# ---------------------------------------------------------------------------
# Tool-pairing safe trim
# ---------------------------------------------------------------------------


def _collect_tool_pair_ids(messages: list[Message]) -> tuple[set[str], set[str]]:
    tool_use_ids: set[str] = set()
    tool_result_ids: set[str] = set()
    for message in messages:
        if message.role == "assistant" and isinstance(message.content, list):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    tool_use_ids.add(block.id)
        if message.role == "tool" and isinstance(message.content, list):
            for block in message.content:
                if isinstance(block, ToolResultBlock):
                    tool_result_ids.add(block.tool_use_id)
    return tool_use_ids, tool_result_ids


def repair_tool_message_pairs(messages: list[Message]) -> list[Message]:
    """Remove orphan tool_use / tool_result blocks so the list is safe for API.

    Unpaired tool_use blocks are converted to plain assistant text when
    the original message carried assistant_text.  Orphan tool_result
    blocks are dropped.
    """
    tool_use_ids, tool_result_ids = _collect_tool_pair_ids(messages)
    valid_tool_use = tool_use_ids & tool_result_ids

    # Track tool_use ids that survived filtering in assistant messages.
    retained_tool_use_ids: set[str] = set()
    repaired: list[Message] = []
    for message in messages:
        if message.role == "assistant" and isinstance(message.content, list):
            tool_uses = [b for b in message.content if isinstance(b, ToolUseBlock)]
            if tool_uses and not all(b.id in valid_tool_use for b in tool_uses):
                # Keep only valid tool_use blocks + non-tool blocks.
                filtered = [
                    b for b in message.content
                    if not isinstance(b, ToolUseBlock) or b.id in valid_tool_use
                ]
                has_valid_tool = any(isinstance(b, ToolUseBlock) for b in filtered)
                if has_valid_tool:
                    for b in filtered:
                        if isinstance(b, ToolUseBlock):
                            retained_tool_use_ids.add(b.id)
                    repaired.append(Message(
                        role="assistant",
                        content=filtered,
                        assistant_text=message.assistant_text,
                    ))
                elif message.assistant_text:
                    repaired.append(Message(
                        role="assistant",
                        content=message.assistant_text,
                        assistant_text=message.assistant_text,
                    ))
                continue
            for b in message.content:
                if isinstance(b, ToolUseBlock):
                    retained_tool_use_ids.add(b.id)
            repaired.append(message)
            continue

        if message.role == "tool" and isinstance(message.content, list):
            blocks = [
                b
                for b in message.content
                if not (
                    isinstance(b, ToolResultBlock)
                    and b.tool_use_id not in retained_tool_use_ids
                )
            ]
            if blocks:
                repaired.append(Message(role="tool", content=blocks))
            continue

        repaired.append(message)

    return repaired


def trim_session_messages_safely(messages: list[Message], max_messages: int) -> None:
    """Trim session messages while keeping tool_use/tool_result pairs intact."""
    if max_messages < 1:
        max_messages = 1
    if len(messages) <= max_messages:
        return
    candidate = list(messages[-max_messages:])
    messages[:] = repair_tool_message_pairs(candidate)


# ---------------------------------------------------------------------------
# Microcompact
# ---------------------------------------------------------------------------

# Tools whose large outputs are safe to compact.
COMPACTABLE_TOOLS = {"read_file", "list_files"}


def _collect_compactable_tool_use_ids(
    messages: list[Message],
) -> tuple[list[str], dict[str, str]]:
    """Return ordered compactable tool_use ids and a name lookup map.

    Scans assistant messages in conversation order.  Only tool_use blocks
    whose name is in COMPACTABLE_TOOLS are included in the id list.
    The name map covers *all* tool_use blocks (for placeholder text).
    """
    compactable_ids: list[str] = []
    name_by_id: dict[str, str] = {}
    for message in messages:
        if message.role != "assistant" or not isinstance(message.content, list):
            continue
        for block in message.content:
            if not isinstance(block, ToolUseBlock):
                continue
            name_by_id[block.id] = block.name
            if block.name in COMPACTABLE_TOOLS:
                compactable_ids.append(block.id)
    return compactable_ids, name_by_id


def _deep_copy_messages(messages: list[Message]) -> list[Message]:
    return [Message.model_validate(m.model_dump(mode="json")) for m in messages]


def micro_compact_messages(
    messages: list[Message],
    *,
    keep_recent: int = 5,
    min_chars: int = 1_000,
) -> list[Message]:
    """Replace old large tool results with a placeholder in a request-view copy.

    Session messages are never mutated; only the returned copy is compacted.
    """
    projected = _deep_copy_messages(messages)
    compactable_ids, name_by_id = _collect_compactable_tool_use_ids(projected)

    # Split into retained (most recent) and cleared sets.
    if keep_recent > 0:
        cleared_ids = set(compactable_ids[:-keep_recent])
    else:
        cleared_ids = set(compactable_ids)

    # Clear matching tool_result content by tool_use_id.
    for message in projected:
        if message.role != "tool" or not isinstance(message.content, list):
            continue
        for block in message.content:
            if not isinstance(block, ToolResultBlock):
                continue
            if block.tool_use_id not in cleared_ids:
                continue
            if block.is_error:
                continue
            original = block.content or ""
            if len(original) < min_chars:
                continue
            tool_name = name_by_id.get(block.tool_use_id, "unknown")
            block.content = (
                f"[Old tool result compacted: tool={tool_name}, "
                f"original_chars={len(original)}, full content is preserved in transcript]"
            )

    return projected


# ---------------------------------------------------------------------------
# Session message serializer (for compact summarizer input)
# ---------------------------------------------------------------------------


def serialize_messages_for_compact(messages: list[Message]) -> str:
    """Render session messages into plain transcript text for the summarizer.

    Includes roles, assistant text, tool_use ids/names/inputs, and
    tool_result ids/content.  Structured blocks become readable lines so
    the summarizer receives conversation context without tool-call protocol
    overhead.
    """
    lines: list[str] = []
    for message in messages:
        if isinstance(message.content, str):
            lines.append(f"[{message.role}] {message.content}")
            continue
        if message.role == "assistant" and isinstance(message.content, list):
            if message.assistant_text:
                lines.append(f"[assistant] {message.assistant_text}")
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    lines.append(
                        f"[tool_use] id={block.id} name={block.name} "
                        f"input={block.input}"
                    )
            continue
        if message.role == "tool" and isinstance(message.content, list):
            for block in message.content:
                if isinstance(block, ToolResultBlock):
                    prefix = "[tool_result_error]" if block.is_error else "[tool_result]"
                    content_preview = block.content
                    if len(content_preview) > 2000:
                        content_preview = content_preview[:2000] + f"... ({len(block.content)} chars total)"
                    lines.append(f"{prefix} id={block.tool_use_id} {content_preview}")
            continue
        lines.append(f"[{message.role}] {message.content}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Shared compact core
# ---------------------------------------------------------------------------


@runtime_checkable
class _CompactModelCaller(Protocol):
    async def call_model(self, messages: list[Message], tools: list[dict[str, Any]]) -> Any:
        ...


async def execute_compact(
    *,
    model_client: _CompactModelCaller,
    messages: list[Message],
    reason: str,
    compact_system_prompt: str,
    compact_user_prompt_text: str,
    keep_recent_messages: int = 12,
    persist_fn: Any | None = None,
    session_id: str = "",
    rebuild_request_fn: Any | None = None,
    max_retries: int = 2,
    on_compact_event: Any | None = None,
) -> list[Message]:
    """Shared compact core: serialize, summarize, rewrite session, persist.

    Retries with reduced older context when the compact request itself is
    too long.  Session messages are only rewritten after a successful summary.
    Returns the rebuilt request_messages after session rewrite.
    Raises RuntimeError on empty summary or exhausted retries.
    """
    before_count = len(messages)
    _emit = on_compact_event or (lambda *_a, **_kw: None)
    _emit("compact_start", reason=reason, message_count=before_count)

    transcript_text = serialize_messages_for_compact(messages)
    compact_req = [
        Message(role="system", content=compact_system_prompt),
        Message(role="user", content=transcript_text),
        Message(role="user", content=compact_user_prompt_text),
    ]

    summary_text: str | None = None
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            compact_resp = await model_client.call_model(compact_req, tools=[])
            summary_text = (compact_resp.text or "").strip()
            break
        except Exception as exc:
            last_error = exc
            if _is_prompt_too_long_error(exc) and attempt < max_retries:
                # Reduce older context, keep recent portion of transcript.
                transcript_text = _reduce_transcript(transcript_text)
                compact_req = [
                    Message(role="system", content=compact_system_prompt),
                    Message(role="user", content=transcript_text),
                    Message(role="user", content=compact_user_prompt_text),
                ]
                _emit("compact_retry", attempt=attempt + 1, reason=str(exc))
                continue
            break

    if not summary_text:
        _emit("compact_failure", reason=str(last_error) if last_error else "empty summary")
        raise RuntimeError(
            f"compact summarizer failed after {max_retries + 1} attempts: {last_error or 'empty summary'}"
        )

    boundary = build_summary_boundary_message(summary_text)
    recent = select_recent_messages(messages, keep_count=keep_recent_messages)
    recent_payload = [_lightweight_message(m).model_dump(mode="json") for m in recent]

    # Persist BEFORE rewriting memory so a failure leaves session intact.
    if persist_fn is not None:
        persist_fn(session_id, {
            "reason": reason,
            "summary": summary_text,
            "before_message_count": before_count,
            "after_message_count": 1 + len(recent),
            "recent_messages": recent_payload,
        })

    messages[:] = [boundary, *recent]

    _emit(
        "compact_success",
        reason=reason,
        summary_tokens=len(summary_text) // 2,
        before_message_count=before_count,
        after_message_count=len(messages),
    )

    if rebuild_request_fn is not None:
        return rebuild_request_fn(messages)

    return messages[:]


def _is_prompt_too_long_error(exc: Exception) -> bool:
    """Check if an exception indicates prompt-too-long without importing model.base."""
    name = type(exc).__name__
    if name == "PromptTooLongError":
        return True
    msg = str(exc).lower()
    return any(p in msg for p in ("context_length_exceeded", "prompt too long", "413"))


def _reduce_transcript(transcript_text: str) -> str:
    """Halve older transcript content while keeping the tail intact."""
    lines = transcript_text.split("\n")
    if len(lines) <= 4:
        return transcript_text
    mid = len(lines) // 2
    return "[... older context omitted for brevity ...]\n" + "\n".join(lines[mid:])


_RECENT_RESULT_MAX_CHARS = 2_000


def _lightweight_message(message: Message) -> Message:
    """Return a copy with large tool_result content snipped for persist safety."""
    if not isinstance(message.content, list):
        return message
    changed = False
    new_blocks: list[Any] = []
    for block in message.content:
        if isinstance(block, ToolResultBlock) and len(block.content or "") > _RECENT_RESULT_MAX_CHARS:
            changed = True
            new_blocks.append(ToolResultBlock(
                tool_use_id=block.tool_use_id,
                content=block.content[:_RECENT_RESULT_MAX_CHARS]
                + f"... (snipped, {len(block.content)} chars total)",
                is_error=block.is_error,
            ))
        else:
            new_blocks.append(block)
    if not changed:
        return message
    return Message(
        role=message.role,
        content=new_blocks,
        assistant_text=message.assistant_text,
        is_meta=message.is_meta,
    )


# ---------------------------------------------------------------------------
# AutoCompact
# ---------------------------------------------------------------------------


def should_auto_compact(
    messages: list[Message],
    *,
    context_window_tokens: int = 200_000,
    auto_compact_buffer_tokens: int = 13_000,
    compact_max_summary_tokens: int = 4_000,
    calibrated_token_estimate: int | None = None,
) -> bool:
    if calibrated_token_estimate is not None:
        estimated = calibrated_token_estimate
    else:
        estimated = estimate_messages_tokens(messages)
    threshold = context_window_tokens - compact_max_summary_tokens - auto_compact_buffer_tokens
    return estimated >= threshold


def build_summary_boundary_message(summary_text: str) -> Message:
    return Message(
        role="user",
        content=summary_text,
    )


def select_recent_messages(
    messages: list[Message], keep_count: int
) -> list[Message]:
    """Return the most recent messages with tool-pairing safety."""
    if len(messages) <= keep_count:
        return list(messages)
    candidate = list(messages[-keep_count:])
    return repair_tool_message_pairs(candidate)


# ---------------------------------------------------------------------------
# Token calibration
# ---------------------------------------------------------------------------


class TokenCalibrator:
    """Conservative correction factor keyed by (provider, model).

    When actual prompt tokens exceed the local estimate the factor is raised.
    When actual is lower the factor is never reduced below MIN_FACTOR, so
    estimates remain conservative after a single low-usage outlier.
    """

    MIN_FACTOR = 1.0
    MAX_FACTOR = 3.0
    DEFAULT_FACTOR = 1.0

    def __init__(self) -> None:
        self._factors: dict[str, float] = {}

    def _key(self, provider: str, model: str) -> str:
        return f"{provider}/{model}"

    def get_factor(self, provider: str, model: str) -> float:
        return self._factors.get(self._key(provider, model), self.DEFAULT_FACTOR)

    def record(
        self,
        provider: str,
        model: str,
        *,
        estimated_tokens: int,
        actual_prompt_tokens: int,
    ) -> None:
        if estimated_tokens <= 0 or actual_prompt_tokens <= 0:
            return
        raw = actual_prompt_tokens / estimated_tokens
        key = self._key(provider, model)
        current = self.get_factor(provider, model)
        # Only adjust upward or if this is the first sample.
        if raw > current or key not in self._factors:
            self._factors[key] = min(self.MAX_FACTOR, max(self.MIN_FACTOR, raw))

    def calibrated_estimate(self, provider: str, model: str, local_estimate: int) -> int:
        return int(local_estimate * self.get_factor(provider, model))


# Global singleton — scoped by (provider, model) at runtime.
_token_calibrator = TokenCalibrator()


def get_token_calibrator() -> TokenCalibrator:
    return _token_calibrator


# ---------------------------------------------------------------------------
# Compression config
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompressionConfig:
    context_compression_enabled: bool = True
    micro_compact_enabled: bool = True
    auto_compact_enabled: bool = True
    reactive_compact_enabled: bool = True
    manual_compact_enabled: bool = True
    context_window_tokens: int = 200_000
    auto_compact_buffer_tokens: int = 13_000
    keep_recent_tool_results: int = 5
    micro_compact_min_chars: int = 1_000
    compact_keep_recent_messages: int = 12
    compact_max_summary_tokens: int = 4_000


# ---------------------------------------------------------------------------
# Resume-time compact helpers
# ---------------------------------------------------------------------------


def _append_todo_reminder(
    messages: list[Message],
    todo_state_store: Any,
    session_id: str,
) -> list[Message]:
    """Append todo reminder message if available."""
    if todo_state_store is None:
        return messages
    reminder = todo_state_store.reminder_message(session_id)
    if reminder is None:
        return messages
    return [*messages, reminder]


def build_resume_request_messages(
    session_messages: list[Message],
    *,
    project_root: Path,
    todo_state_store: Any = None,
    session_id: str = "",
    compression_config: CompressionConfig | None = None,
) -> list[Message]:
    """Build the same request view a resumed run would produce.

    Combines hydrated session messages with project context, todo reminder,
    and MicroCompact (when enabled) to estimate the real model request size.
    """
    from app.runtime.context_builder import build_model_messages

    cfg = compression_config or CompressionConfig()
    messages_with_todo = _append_todo_reminder(
        session_messages, todo_state_store, session_id,
    )
    request_messages = build_model_messages(messages_with_todo, project_root=project_root)
    if cfg.context_compression_enabled and cfg.micro_compact_enabled:
        request_messages = micro_compact_messages(
            request_messages,
            keep_recent=cfg.keep_recent_tool_results,
            min_chars=cfg.micro_compact_min_chars,
        )
    return request_messages


def should_resume_compact(
    session_messages: list[Message],
    *,
    project_root: Path,
    todo_state_store: Any = None,
    session_id: str = "",
    compression_config: CompressionConfig | None = None,
) -> bool:
    """Decide whether Resume-time Compact should run.

    Returns False when compression is disabled, auto_compact is disabled,
    or the hydrated session is below the threshold.
    """
    cfg = compression_config or CompressionConfig()
    if not cfg.context_compression_enabled:
        _log.debug("resume_compact skipped: context_compression_enabled=false")
        return False
    if not cfg.auto_compact_enabled:
        _log.debug("resume_compact skipped: auto_compact_enabled=false")
        return False
    request_messages = build_resume_request_messages(
        session_messages,
        project_root=project_root,
        todo_state_store=todo_state_store,
        session_id=session_id,
        compression_config=cfg,
    )
    result = should_auto_compact(
        request_messages,
        context_window_tokens=cfg.context_window_tokens,
        auto_compact_buffer_tokens=cfg.auto_compact_buffer_tokens,
        compact_max_summary_tokens=cfg.compact_max_summary_tokens,
    )
    if result:
        _log.info("resume_compact triggered for session %s (%d messages)", session_id, len(session_messages))
    else:
        _log.debug("resume_compact not needed for session %s", session_id)
    return result
